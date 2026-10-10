"""Run opt-in browser fixtures serially with fresh output paths."""

import subprocess
import sys
from pathlib import Path

runner = Path(__file__).resolve().parent / "run.py"
base = "review/trainers-independent"
labels = [
    "news.tests.test_brand_browser",
    "news.tests.test_branch_browser",
    "news.tests.test_trainer_browser",
]
for name, tests, reverse in [
    ("trainer-alone", [labels[2]], False),
    ("combined", labels, False),
    ("reverse", labels, True),
]:
    env = ["Y3GYM_RUN_TRAINER_BROWSER=1"]
    if name != "trainer-alone":
        env += ["Y3GYM_RUN_BRAND_BROWSER=1", "Y3GYM_RUN_BRANCH_BROWSER=1"]
    for kind in ["BRAND", "BRANCH", "TRAINER"]:
        env.append(f"Y3GYM_{kind}_REVIEW_DIR={base}/{name}/{kind.lower()}")
    command = [
        sys.executable,
        str(runner),
        name,
        "env",
        *env,
        "uv",
        "run",
        "--locked",
        "python",
        "manage.py",
        "test",
        *tests,
        "--noinput",
        "--verbosity",
        "2",
    ]
    if reverse:
        command.append("--reverse")
    result = subprocess.run(command)
    if result.returncode:
        raise SystemExit(result.returncode)
