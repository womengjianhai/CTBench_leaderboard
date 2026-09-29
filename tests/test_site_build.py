import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SiteBuildTests(unittest.TestCase):
    def test_public_artifact_contains_only_explicit_website_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = builder.build(Path(directory), "netopt-team/ctbench")
            actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
            self.assertEqual(actual, set(builder.ASSETS) | {"data/leaderboard.json", "data/leaderboard.csv", "data/agent-details.json", ".nojekyll"})
            config = json.loads((output / "site-config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["repositoryUrl"], "https://github.com/netopt-team/ctbench")
            self.assertTrue(config["repositoryAvailable"])
            self.assertNotIn("127.0.0.1", (output / "index.html").read_text(encoding="utf-8"))

    def test_pages_repository_does_not_replace_framework_link(self):
        with tempfile.TemporaryDirectory() as directory:
            output = builder.build(Path(directory), "womengjianhai/CTBench_leaderboard")
            config = json.loads((output / "site-config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["siteRepository"], "womengjianhai/CTBench_leaderboard")
            self.assertEqual(config["siteRepositoryUrl"], "https://github.com/womengjianhai/CTBench_leaderboard")
            self.assertEqual(config["repository"], "netopt-team/ctbench")
            self.assertEqual(config["repositoryUrl"], "https://github.com/netopt-team/ctbench")
            self.assertTrue(config["repositoryAvailable"])

    def test_published_results_preserve_paper_version(self):
        data = json.loads((builder.PUBLISHED).read_text(encoding="utf-8"))
        builder.validate_data(data)
        self.assertEqual(data["sourceVersion"], "arXiv:2608.12002v1 / Table 5")
        qwen = next(row for row in data["results"] if row["harness"] == "ClaudeCode")
        self.assertEqual(qwen["path"]["accuracy"], {"mean": 17.59, "sd": 3.7})
        self.assertEqual(len(builder.results_csv(data).splitlines()), 11)

    def test_invalid_scores_and_repository_fail(self):
        data = json.loads((builder.PUBLISHED).read_text(encoding="utf-8"))
        data["results"][0]["rca"]["accuracy"]["mean"] = 101
        with self.assertRaises(ValueError):
            builder.validate_data(data)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            builder.build(Path(directory), "../private/secrets")


class AgentDetailValidationTests(unittest.TestCase):
    def load_details(self):
        paper = json.loads(builder.PUBLISHED.read_text(encoding="utf-8"))
        details = json.loads(builder.AGENT_DETAILS.read_text(encoding="utf-8"))
        return details, paper

    def example(self, kind="synthetic", agent=None):
        example = {
            "kind": kind, "id": "DEMO-TEST" if kind == "synthetic" else "APPROVED-TEST",
            "title": "Validation fixture", "question": "A synthetic fixture question.",
            "finalAnswer": "A fixture answer.",
            "steps": [{"title": "Inspect", "command": "show fixture", "observation": "Fixture evidence.", "summary": "Report the fixture finding."}],
        }
        if kind == "recorded":
            example.update(publicationApproved=True, harness=agent["harness"], model=agent["model"], sourceNote="Approved test fixture; no real trajectory content.")
        return example

    def test_public_detail_fixture_validates(self):
        details, paper = self.load_details()
        builder.validate_details(details, paper)

    def test_details_reject_mismatched_agent(self):
        details, paper = self.load_details()
        details["agents"][0]["model"] = "Unpublished fixture agent"
        with self.assertRaisesRegex(ValueError, "identities"):
            builder.validate_details(details, paper)

    def test_details_reject_invalid_coverage(self):
        cases = ({"observed": -1}, {"observed": 127}, {"observed": 0.5},
                 {"observed": True}, {"observed": None}, {"total": 125})
        for change in cases:
            with self.subTest(change=change):
                details, paper = self.load_details()
                metric = details["agents"][0]["efficiency"]["rca"]["rounds"]
                metric.update(status="available", value=1, observed=1, total=126)
                metric.update(change)
                with self.assertRaisesRegex(ValueError, "coverage/denominator"):
                    builder.validate_details(details, paper)

    def test_details_reject_nonfinite_or_invalid_available_values(self):
        for value in (float("nan"), float("inf"), -float("inf"), -1, True, "1"):
            with self.subTest(value=value):
                details, paper = self.load_details()
                details["agents"][0]["efficiency"]["rca"]["rounds"].update(status="available", value=value, observed=1)
                with self.assertRaisesRegex(ValueError, "finite value"):
                    builder.validate_details(details, paper)
        details, paper = self.load_details()
        details["agents"][0]["efficiency"]["rca"]["rounds"].update(status="available", value=1, observed=0)
        with self.assertRaisesRegex(ValueError, "observations"):
            builder.validate_details(details, paper)

    def test_details_reject_unavailable_measurement_with_nonnull_value(self):
        details, paper = self.load_details()
        details["agents"][0]["efficiency"]["rca"]["rounds"].update(status="unavailable", value=0, observed=0, reason="Missing fixture telemetry")
        with self.assertRaisesRegex(ValueError, "must be null"):
            builder.validate_details(details, paper)

    def test_recorded_example_requires_explicit_approval(self):
        for approval in (None, False, "true", 1):
            with self.subTest(approval=approval):
                details, paper = self.load_details()
                agent = details["agents"][0]
                example = self.example("recorded", agent)
                if approval is None:
                    example.pop("publicationApproved")
                else:
                    example["publicationApproved"] = approval
                agent.setdefault("examples", {})["rca"] = example
                with self.assertRaisesRegex(ValueError, "publication approval"):
                    builder.validate_details(details, paper)

    def test_recorded_example_requires_matching_identity_and_source(self):
        for field, value, error in (("harness", "Other harness", "different agent"),
                                    ("model", "Other model", "different agent"),
                                    ("sourceNote", None, "source note"),
                                    ("sourceNote", "", "source note")):
            with self.subTest(field=field, value=value):
                details, paper = self.load_details()
                agent = details["agents"][0]
                example = self.example("recorded", agent)
                if value is None:
                    example.pop(field)
                else:
                    example[field] = value
                agent.setdefault("examples", {})["rca"] = example
                with self.assertRaisesRegex(ValueError, error):
                    builder.validate_details(details, paper)

    def test_approved_recorded_example_with_matching_identity_validates(self):
        details, paper = self.load_details()
        agent = details["agents"][0]
        agent.setdefault("examples", {})["rca"] = self.example("recorded", agent)
        builder.validate_details(details, paper)

    def test_synthetic_example_requires_demo_identifier(self):
        details, paper = self.load_details()
        example = self.example()
        details.setdefault("examples", {})["rca"] = example
        builder.validate_details(details, paper)
        example["id"] = "QUESTION-1"
        with self.assertRaisesRegex(ValueError, "DEMO-"):
            builder.validate_details(details, paper)


if __name__ == "__main__":
    unittest.main()
