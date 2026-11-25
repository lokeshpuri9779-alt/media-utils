"""Render the deterministic long-form trend fixture; never publish this output."""
import argparse
import json
from pathlib import Path

import longform_trends


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.fixture.read_text(encoding="utf-8"))
    if "Synthetic test data only" not in data.get("note", ""):
        raise SystemExit("Refusing to render a fixture not explicitly marked synthetic")
    title, description, report = longform_trends.render(
        args.output, data["content_id"], data["trends"]
    )
    if report.get("pacing_profile", {}).get("name") != "high-energy":
        raise SystemExit("High-energy pacing profile missing")
    report_path = args.output.with_suffix(".json")
    print("QA_TITLE=" + title)
    print("QA_DESCRIPTION_CHARACTERS=" + str(len(description)))
    print("QA_REPORT=" + str(report_path))
    print("QA_VIDEO=" + str(args.output))


if __name__ == "__main__":
    main()
