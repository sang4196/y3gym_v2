"""Future test-role entrypoint. Preparation never calls this with --execute."""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / ".venv/bin/python"
RUFF = BACKEND / ".venv/bin/ruff"


def execute(work, recheck=False):
    os.umask(0o077)
    work = work.resolve()
    assert work.parent == Path("/tmp") and work.name.startswith(
        "y3gym-dev-integration-"
    )
    assert work.stat().st_mode & 0o777 == 0o700
    plan = json.loads((work / "plan.json").read_text())
    assert plan["work"] == str(work)
    mirror = Path(plan["mirror"])
    assert mirror == work / "source"
    marker = work / "execution-started"
    marker.open("x").close()  # Never overwrite/rerun a previous campaign.
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith("Y3GYM_") and (
            "REVIEW" in key or "ORIGIN" in key or "PASSWORD" in key or "RUN_" in key
        ):
            environment.pop(key)
    environment.update(
        PYTHONDONTWRITEBYTECODE="1",
        DJANGO_SETTINGS_MODULE="dev_integration_settings",
        PYTHONPATH=os.pathsep.join([str(work), str(HERE), str(BACKEND)]),
        Y3GYM_KAKAO_MAP_JS_KEY="",
        Y3GYM_INTEGRATION_ORIGIN="http://localhost:8772",
        Y3GYM_INTEGRATION_WORK=str(work),
    )
    for flag in plan["flags"]:
        environment[f"Y3GYM_RUN_{flag}_BROWSER"] = "1"
        environment[f"Y3GYM_{flag}_REVIEW_DIR"] = str(work / "evidence" / flag.lower())
    environment["Y3GYM_WITHDRAWAL_REVIEW_DIR"] = str(work / "evidence/withdrawal")
    results = []
    omitted = []
    if recheck:
        omitted = [
            {
                "commands": [
                    "django-check",
                    "migration-check",
                    "ruff-lint",
                    "ruff-format",
                ],
                "status": "NOT_RUN_PRIOR_RESULTS_RETAINED",
            },
            {
                "commands": ["cms", "w02-outside", "w02-body"],
                "status": "NOT_RUN_PRIOR_PASS_EVIDENCE_ONLY",
            },
            {
                "commands": ["w02-supplement"],
                "status": "NOT_RUN_EARLY_ESCAPE_CONDITION_LIMIT_RETAINED",
            },
        ]

    def run(label, argv, cwd=BACKEND, extra=None, timeout=2400):
        env = environment | (extra or {})
        with (work / f"{label}.log").open("xb") as log:
            try:
                code = subprocess.run(
                    [str(arg) for arg in argv],
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                ).returncode
            except subprocess.TimeoutExpired:
                code = "TIMEOUT"
        results.append(
            {"command": label, "exit": code, "log": str(work / f"{label}.log")}
        )
        print(json.dumps(results[-1]), flush=True)
        return code == 0

    def sandbox(action):
        return run(
            "sandbox-" + action, [PYTHON, "-B", work / "sandbox.py", work, action]
        )

    started = False
    try:
        if not sandbox("configure"):
            return
        spec = json.loads((work / "instance.json").read_text())
        assert spec["database"].startswith("test_y3gym_dev_integration_")
        assert spec["test_database"] == spec["database"] + "_runner"
        with (work / "dev_integration_settings.py").open("a") as settings:
            settings.write(
                f'\nPROTOTYPE_DIR = Path({str(mirror / "prototype")!r})\nSTATICFILES_DIRS = [("prototype", PROTOTYPE_DIR)]\nTEST_RUNNER = "result_runner.Runner"\nSTATIC_ROOT = BASE_DIR / "static"\n'
            )
        # Original full campaign gates stay available; recheck omits prior work.
        if not recheck:
            run("django-check", [PYTHON, "-B", "manage.py", "check"])
            run(
                "migration-check",
                [PYTHON, "-B", "manage.py", "makemigrations", "--check", "--dry-run"],
            )
            run("ruff-lint", [RUFF, "check", "--no-cache", "."])
            run("ruff-format", [RUFF, "format", "--check", "--no-cache", "."])
        run(
            "news-tests-all-four-optins",
            [
                PYTHON,
                "-B",
                "manage.py",
                "test",
                "news.tests",
                "--noinput",
                "--verbosity",
                "2",
            ],
        )
        if not sandbox("initialize"):
            return
        # One new synthetic fixture in this sandbox, never copied from old media.
        seed = "from fixtures import seed_w02, validate_seed_and_permissions; print(seed_w02()); print(validate_seed_and_permissions())"
        if not run(
            "seed-own-w02-image", [PYTHON, "-B", "manage.py", "shell", "-c", seed]
        ):
            return
        started = sandbox("start")
        if not started:
            return
        private_backend = mirror / "backend"
        if not recheck:
            run("cms", ["node", "scripts/review-cms.mjs"], cwd=private_backend)
        popup_passed = run(
            "popups", ["node", "scripts/review-popups.mjs"], cwd=private_backend
        )
        popup_handoff = popup_passed and run(
            "popup-fixture-handoff",
            [
                PYTHON,
                "-B",
                "manage.py",
                "shell",
                "-c",
                "from fixtures import validate_popup_handoff; print(validate_popup_handoff())",
            ],
        )
        for name in ("popup-sizing", "popup-position"):
            if not popup_handoff:
                results.append(
                    {"command": name, "exit": "BLOCKED_POPUP_FIXTURE", "log": None}
                )
                continue
            extra = {"Y3GYM_POPUP_REVIEW_DIR": str(work / "evidence" / name)}
            run(
                name,
                ["node", "scripts/review-" + name + ".mjs"],
                cwd=private_backend,
                extra=extra,
            )
        focus = private_backend / "review/image-chooser-focus-independent"
        for name, args in (
            ("w02-early", ["reproduce.mjs", work, "final", "w02-early", "1"]),
            (
                "w02-outside",
                ["edges.mjs", work, "with", "w02-outside", "Tab", "outside-tab"],
            ),
            ("w02-supplement", ["supplement.mjs", work, "w02-supplement"]),
            ("w02-body", ["body-close.mjs", work, "w02-body", "with"]),
        ):
            if recheck and name != "w02-early":
                continue
            run(name, ["node", *args], cwd=focus)
    finally:
        # Even a partial start is cleaned up by the reused process identity guard.
        if started or (work / "server.pid").exists():
            sandbox("stop")
        summary = {
            "stage": "EXECUTED_RESULTS_REQUIRE_REVIEW",
            "scope": "RECHECK_SUITE_POPUPS_W02_EARLY"
            if recheck
            else "ORIGINAL_FULL_CAMPAIGN",
            "commands": results,
            "omitted_not_pass": omitted,
            "suite": None,
            "browser_reports": [],
        }
        if (work / "suite-result.json").exists():
            summary["suite"] = json.loads((work / "suite-result.json").read_text())
        for path in sorted((work / "evidence").rglob("*.json")):
            if path.name not in {"checks.json", "result.json"}:
                continue
            value = json.loads(path.read_text())
            summary["browser_reports"].append(
                {
                    "private_path": str(path),
                    "status": value.get("status"),
                    "checks": len(value.get("checks", [])),
                    "errors": len(value.get("errors", [])),
                    "warnings": len(value.get("warnings", [])),
                    "attempt_statuses": [
                        row.get("status") for row in value.get("attempts", [])
                    ],
                }
            )
        # Raw logs/reports remain private. Review this safe summary before promotion.
        with (work / "campaign-summary.json").open("x") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    assert len(sys.argv) == 3 and sys.argv[2] in {"--execute", "--recheck"}, (
        "Test-role execution authorization required"
    )
    execute(Path(sys.argv[1]), recheck=sys.argv[2] == "--recheck")
