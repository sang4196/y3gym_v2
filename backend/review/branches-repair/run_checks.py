"""Run R1 regressions sequentially without overwriting previous evidence."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--output", default="regressions-final")
parser.add_argument(
    "--only",
    choices=["server", "brand-alone", "branch-alone", "combined", "combined-reverse"],
)
options = parser.parse_args()
output = Path(__file__).resolve().parent / options.output
output.mkdir(exist_ok=True)
command = ["uv", "run", "--locked", "python", "manage.py", "test"]
flags = ["--noinput", "--verbosity", "2"]
cases = [
    ("server", ["news.tests"], {}),
    (
        "brand-alone",
        ["news.tests.test_brand_browser"],
        {"Y3GYM_RUN_BRAND_BROWSER": "1"},
    ),
    (
        "branch-alone",
        ["news.tests.test_branch_browser"],
        {"Y3GYM_RUN_BRANCH_BROWSER": "1"},
    ),
    (
        "combined",
        ["news.tests.test_brand_browser", "news.tests.test_branch_browser"],
        {"Y3GYM_RUN_BRAND_BROWSER": "1", "Y3GYM_RUN_BRANCH_BROWSER": "1"},
    ),
    (
        "combined-reverse",
        [
            "news.tests.test_brand_browser",
            "news.tests.test_branch_browser",
            "--reverse",
        ],
        {"Y3GYM_RUN_BRAND_BROWSER": "1", "Y3GYM_RUN_BRANCH_BROWSER": "1"},
    ),
]
results = []
for name, labels, overrides in cases:
    if options.only and options.only != name:
        continue
    directory = output / name
    directory.mkdir()
    environment = os.environ.copy()
    environment.pop("Y3GYM_RUN_BRAND_BROWSER", None)
    environment.pop("Y3GYM_RUN_BRANCH_BROWSER", None)
    environment.update(overrides)
    environment.update(
        Y3GYM_BRAND_REVIEW_DIR=str(directory / "brand"),
        Y3GYM_BRANCH_REVIEW_DIR=str(directory / "branches"),
        Y3GYM_WITHDRAWAL_REVIEW_DIR=str(directory / "concurrency"),
    )
    args = command + labels + flags
    start = time.monotonic()
    print("START", name, flush=True)
    with (directory / "output.txt").open("x") as handle:
        result = subprocess.run(
            args, cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT
        )
    record = {
        "name": name,
        "cwd": str(root),
        "command": args,
        "environment": {
            key: environment[key]
            for key in [
                *overrides,
                "Y3GYM_BRAND_REVIEW_DIR",
                "Y3GYM_BRANCH_REVIEW_DIR",
                "Y3GYM_WITHDRAWAL_REVIEW_DIR",
            ]
        },
        "exitCode": result.returncode,
        "elapsedSeconds": round(time.monotonic() - start, 3),
    }
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    results.append(record)
    (output / "runs.json").write_text(json.dumps(results, indent=2) + "\n")
    print("END", name, result.returncode, record["elapsedSeconds"], flush=True)
raise SystemExit(any(record["exitCode"] for record in results))
