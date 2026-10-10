"""Run only one temporary database consumer at a time."""

import subprocess
import sys
from pathlib import Path

runner = Path(__file__).resolve().parent / "run.py"
base = "review/branches-independent-recheck"
for name, labels, reverse in [
    ("brand-alone", ["news.tests.test_brand_browser"], False),
    ("branch-alone", ["news.tests.test_branch_browser"], False),
    (
        "combined",
        ["news.tests.test_brand_browser", "news.tests.test_branch_browser"],
        False,
    ),
    (
        "combined-reverse",
        ["news.tests.test_brand_browser", "news.tests.test_branch_browser"],
        True,
    ),
]:
    flags = ["--reverse"] if reverse else []
    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            name,
            "env",
            "Y3GYM_RUN_BRAND_BROWSER=1",
            "Y3GYM_RUN_BRANCH_BROWSER=1",
            f"Y3GYM_BRAND_REVIEW_DIR={base}/{name}/brand",
            f"Y3GYM_BRANCH_REVIEW_DIR={base}/{name}/branches",
            "uv",
            "run",
            "--locked",
            "python",
            "manage.py",
            "test",
            *labels,
            "--noinput",
            "--verbosity",
            "2",
            *flags,
        ]
    )
    if result.returncode:
        raise SystemExit(result.returncode)
