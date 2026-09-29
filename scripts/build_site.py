"""Build a small, dependency-free GitHub Pages artifact from an explicit file list."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "website"
PUBLISHED = ROOT / "results/published/paper-v1.json"
AGENT_DETAILS = ROOT / "results/published/agent-details.json"
ASSETS = ("index.html", "assets/styles.css", "assets/app.js", "assets/agent-details.js", "assets/favicon.svg", "citation.bib", "site-config.json")


def validate_data(data):
    if data.get("tasks") != {"rca": 126, "path": 108}:
        raise ValueError("Unexpected benchmark task counts; review the source release.")
    names = set()
    for row in data["results"]:
        identity = (row["harness"], row["model"])
        if identity in names:
            raise ValueError(f"Duplicate agent-model result: {identity}")
        names.add(identity)
        for track in ("rca", "path"):
            for name in ("accuracy", "localization", "reasoning", "evidence"):
                metric = row[track][name]
                if (any(isinstance(metric[key], bool) or not isinstance(metric[key], (int, float)) or not math.isfinite(metric[key]) for key in ("mean", "sd"))
                    or not 0 <= metric["mean"] <= 100 or metric["sd"] < 0):
                    raise ValueError(f"Invalid metric: {identity} / {track} / {name}")
    if not names:
        raise ValueError("The leaderboard must contain results.")


def validate_example(example, agent=None):
    if not isinstance(example, dict) or example.get("kind") not in {"synthetic", "recorded"}:
        raise ValueError("Example must declare synthetic or recorded provenance.")
    if example["kind"] == "recorded":
        if not agent or example.get("publicationApproved") is not True:
            raise ValueError("Recorded examples require explicit publication approval and an agent identity.")
        if (example.get("harness"), example.get("model")) != agent:
            raise ValueError("Recorded example belongs to a different agent.")
        if not example.get("sourceNote"):
            raise ValueError("Recorded examples need a source note.")
    if example["kind"] == "synthetic" and not str(example.get("id", "")).startswith("DEMO-"):
        raise ValueError("Synthetic examples must have a DEMO- identifier.")
    for field in ("id", "title", "question", "finalAnswer"):
        if not isinstance(example.get(field), str) or not example[field].strip():
            raise ValueError(f"Missing example field: {field}")
    if not isinstance(example.get("steps"), list) or not 1 <= len(example["steps"]) <= 100:
        raise ValueError("Example needs 1-100 observable diagnostic steps.")
    for step in example["steps"]:
        if any(not isinstance(step.get(key), str) or not step[key].strip() for key in ("title", "command", "observation", "summary")):
            raise ValueError("Each step needs a title, command, observation and action summary.")


def validate_details(details, paper):
    if details.get("schemaVersion") != 1:
        raise ValueError("Unsupported agent-detail schema version.")
    source = details.get("efficiencySource", {})
    if not source.get("label") or not source.get("note"):
        raise ValueError("Efficiency measurements need explicit provenance.")
    expected = {(row["harness"], row["model"]) for row in paper["results"]}
    actual = set()
    for agent in details.get("agents", []):
        identity = (agent["harness"], agent["model"])
        if identity in actual:
            raise ValueError("Duplicate agent details.")
        actual.add(identity)
        for track, total in paper["tasks"].items():
            for key in ("rounds", "latency", "tokens"):
                metric = agent["efficiency"][track][key]
                observed = metric.get("observed")
                if type(observed) is not int or not 0 <= observed <= total or metric.get("total") != total:
                    raise ValueError("Invalid efficiency coverage/denominator.")
                if not metric.get("unit") or not metric.get("definition"):
                    raise ValueError("Efficiency metric needs units and a definition.")
                if metric.get("status") == "available":
                    value = metric.get("value")
                    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or observed == 0:
                        raise ValueError("Available efficiency metric must have a finite value and observations.")
                elif metric.get("status") != "unavailable" or metric.get("value") is not None or not metric.get("reason"):
                    raise ValueError("Unavailable measurements must be null and explain the reason.")
            example = agent.get("examples", {}).get(track)
            if example is not None:
                validate_example(example, identity)
    if actual != expected:
        raise ValueError("Agent details must match the published leaderboard identities.")
    for track, example in details.get("examples", {}).items():
        if track not in paper["tasks"]:
            raise ValueError("Unknown example task track.")
        validate_example(example)


def results_csv(data):
    output = io.StringIO(newline="")
    fields = ["harness", "model", "task", "n", "accuracy_mean", "accuracy_sd", "localization_mean", "localization_sd", "identification_or_restoration_mean", "identification_or_restoration_sd", "evidence_f1_mean", "evidence_f1_sd", "source"]
    writer = csv.writer(output)
    writer.writerow(fields)
    for row in data["results"]:
        for track in ("rca", "path"):
            values = [row["harness"], row["model"], track, data["tasks"][track]]
            for metric in ("accuracy", "localization", "reasoning", "evidence"):
                values.extend((row[track][metric]["mean"], row[track][metric]["sd"]))
            writer.writerow(values + [data["url"]])
    return output.getvalue()


def build(output: Path, repository: str | None = None):
    output = output.resolve()
    # This function never deletes directories, and refuses to overwrite source trees.
    if output == ROOT or output == SOURCE or ROOT.is_relative_to(output) or output.is_relative_to(SOURCE):
        raise ValueError("Choose a separate output directory, such as dist.")
    allowed = set(ASSETS) | {"data/leaderboard.json", "data/leaderboard.csv", "data/agent-details.json", ".nojekyll"}
    unexpected = [p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file() and p.relative_to(output).as_posix() not in allowed]
    if unexpected:
        raise ValueError("Build output contains unexpected files; choose a clean directory.")
    config = json.loads((SOURCE / "site-config.json").read_text(encoding="utf-8"))
    if repository:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Repository must be owner/name.")
        # The Pages source repository can differ from the evaluation framework.
        # Keep repository/repositoryUrl as the explicit framework link in site-config.json.
        config.update(siteRepository=repository, siteRepositoryUrl=f"https://github.com/{repository}")
    data = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    validate_data(data)
    details = json.loads(AGENT_DETAILS.read_text(encoding="utf-8"))
    validate_details(details, data)
    for relative in ASSETS:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)
    (output / "data").mkdir(parents=True, exist_ok=True)
    (output / "data/agent-details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "data/leaderboard.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "site-config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "data/leaderboard.csv").write_text(results_csv(data), encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {len(ASSETS) + 4} public files: {output}")
    print(f"Scores: {data['label']}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--repository", help="Pages source repository owner/name; does not override the framework link.")
    args = parser.parse_args()
    build(args.output, args.repository)
