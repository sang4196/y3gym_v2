"""Run trainer/server and three browser fixtures sequentially with fresh evidence."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True)
parser.add_argument("--only", choices=["server", "combined", "reverse"])
options = parser.parse_args()
output = Path(__file__).resolve().parent / options.output
output.mkdir(exist_ok=False)
command = ["uv", "run", "--locked", "python", "manage.py", "test"]
labels = [
    "news.tests.test_brand_browser",
    "news.tests.test_branch_browser",
    "news.tests.test_trainer_browser",
]
flags = ["--noinput", "--verbosity", "2"]
results = []
for name, tests in [
    ("server", ["news.tests"]),
    ("combined", labels),
    ("reverse", labels + ["--reverse"]),
]:
    if options.only and options.only != name:
        continue
    destination = output / name
    destination.mkdir()
    environment = os.environ.copy()
    overrides = {}
    for kind in ["BRAND", "BRANCH", "TRAINER"]:
        environment.pop(f"Y3GYM_RUN_{kind}_BROWSER", None)
        overrides[f"Y3GYM_{kind}_REVIEW_DIR"] = str(destination / kind.lower())
        if name != "server":
            overrides[f"Y3GYM_RUN_{kind}_BROWSER"] = "1"
    overrides["Y3GYM_WITHDRAWAL_REVIEW_DIR"] = str(destination / "concurrency")
    environment.update(overrides)
    args = command + tests + flags
    start = time.monotonic()
    print("START", name, flush=True)
    with (destination / "output.txt").open("x") as handle:
        result = subprocess.run(
            args, cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT
        )
    record = {
        "name": name,
        "cwd": str(root),
        "command": args,
        "environment_overrides": overrides,
        "exit_code": result.returncode,
        "elapsed_seconds": round(time.monotonic() - start, 3),
    }
    results.append(record)
    (destination / "command.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print("END", name, result.returncode, flush=True)
    if result.returncode:
        break
(output / "results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2) + "\n"
)
raise SystemExit(0 if all(result["exit_code"] == 0 for result in results) else 1)
