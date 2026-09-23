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
            self.assertEqual(actual, set(builder.ASSETS) | {"data/leaderboard.json", "data/leaderboard.csv", ".nojekyll"})
            config = json.loads((output / "site-config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["repositoryUrl"], "https://github.com/netopt-team/ctbench")
            self.assertTrue(config["repositoryAvailable"])
            self.assertNotIn("127.0.0.1", (output / "index.html").read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
