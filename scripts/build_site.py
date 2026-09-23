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
ASSETS = ("index.html", "assets/styles.css", "assets/app.js", "assets/favicon.svg", "citation.bib", "site-config.json")


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
    allowed = set(ASSETS) | {"data/leaderboard.json", "data/leaderboard.csv", ".nojekyll"}
    unexpected = [p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file() and p.relative_to(output).as_posix() not in allowed]
    if unexpected:
        raise ValueError("Build output contains unexpected files; choose a clean directory.")
    config = json.loads((SOURCE / "site-config.json").read_text(encoding="utf-8"))
    if repository:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Repository must be owner/name.")
        config.update(repository=repository, repositoryUrl=f"https://github.com/{repository}", repositoryAvailable=True)
    data = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    validate_data(data)
    for relative in ASSETS:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)
    (output / "data").mkdir(parents=True, exist_ok=True)
    (output / "data/leaderboard.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "site-config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "data/leaderboard.csv").write_text(results_csv(data), encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {len(ASSETS) + 3} public files: {output}")
    print(f"Scores: {data['label']}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--repository", help="Public repository owner/name; enables repository links in the build.")
    args = parser.parse_args()
    build(args.output, args.repository)
