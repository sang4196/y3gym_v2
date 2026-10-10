"""Summarize completed local runs and compare before/after preservation hashes."""

import json
from pathlib import Path

output = Path(__file__).resolve().parent


def read(name):
    return json.loads((output / name).read_text())


def write(name, value):
    with (output / name).open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


runs = [
    "server-tests",
    "independent-concurrency",
    "original-reproduction",
    "brand-alone",
    "branch-alone",
    "combined",
    "combined-reverse",
    "live-read-only",
    "popup-revisit",
    "system-check",
    "migration-check",
    "lint-final",
    "scoped-format-final",
    "documents",
    "diff-check",
]
commands = {name: read(f"{name}.json") for name in runs}
assert all(value["exit_code"] == 0 for value in commands.values()), commands
before, after = read("snapshot-before.json"), read("snapshot-after.json")
files = sorted(set(before["files"]) | set(after["files"]))
changed = [
    name for name in files if before["files"].get(name) != after["files"].get(name)
]
tables = sorted(set(before["db"]) | set(after["db"]))
changed_tables = [
    name for name in tables if before["db"].get(name) != after["db"].get(name)
]
preservation = {
    "status": "PASS"
    if not changed
    and not changed_tables
    and before["index_sha256"] == after["index_sha256"]
    else "FAIL",
    "before_files": len(before["files"]),
    "after_files": len(after["files"]),
    "changed_existing_or_added_outside_audit": changed,
    "db_tables_compared": len(tables),
    "changed_db_tables": changed_tables,
    "index_unchanged": before["index_sha256"] == after["index_sha256"],
    "secrets_unchanged": all(
        before["files"].get(name) == after["files"].get(name)
        for name in ["backend/.env.local", "backend/.local-credentials"]
    ),
    "private_media_files_compared": sum(
        name.startswith("backend/.private-media/") for name in files
    ),
}
write("preservation-result.json", preservation)
assert preservation["status"] == "PASS", preservation
cases = [
    json.loads(path.read_text())
    for path in sorted((output / "independent-concurrency").glob("*-first.json"))
]
assert len(cases) == 12
browsers = []
for name in ["brand-alone", "branch-alone", "combined", "combined-reverse"]:
    row = {"name": name, "exit_code": commands[name]["exit_code"], "flows": {}}
    for kind, report in [
        ("brand", "brand/result.json"),
        ("branches", "branches/checks.json"),
    ]:
        if (output / name / report).exists():
            result = read(f"{name}/{report}")
            row["flows"][kind] = {
                "status": result["status"],
                "count": len(result["checks"]),
                "errors": result.get("errors", []),
                "adminMobileNameBox": result.get("adminMobileNameBox"),
            }
    browsers.append(row)
verification = {
    "status": "PASS_WITH_WARNINGS",
    "date": "2026-10-10",
    "work_unit": "M2-2-R1 independent recheck",
    "server": {"collected": 81, "passed": 79, "skipped_opt_in": 2},
    "independent_additional": {"collected": 13, "passed": 13},
    "original_reproduction": {"collected": 1, "passed": 1},
    "concurrency_cases": cases,
    "browser_matrix": browsers,
    "read_only_live_flows": len(read("live/checks.json")["checks"]),
    "popup_revisit_flows": len(read("popups/revisit/checks.json")["checks"]),
    "commands": commands,
    "preservation": preservation,
    "global_format": read("global-format-final.json"),
    "previous_results_counted_as_rerun": False,
    "user_visual_approval": "NOT_ESTABLISHED_BY_AUTOMATED_CHECKS",
}
write("verification.json", verification)
findings = {
    "status": "PASS_WITH_WARNINGS",
    "blocking_findings": [],
    "resolved": [
        {
            "id": "F01",
            "evidence": ["independent-concurrency/", "original-repro-result.json"],
        },
        {
            "id": "F02",
            "evidence": ["brand-alone/brand/result.json", "reviewed-source.diff"],
        },
        {"id": "W01", "evidence": ["combined.json", "combined-reverse.json"]},
        {
            "id": "W03",
            "qualification": "Stable capture fixed; production UI unchanged. Previous transitional captures preserved.",
            "evidence": [
                "brand-alone/brand/result.json",
                "branch-alone/branches/checks.json",
            ],
        },
    ],
    "warnings": [
        {
            "id": "W02",
            "priority": "P3",
            "title": "Existing global format warning",
            "file": "backend/review/workflow-01/verify.py",
            "evidence": "global-format-final.txt",
            "unchanged": True,
        }
    ],
    "unverified": [
        "Whale / browsers other than Chromium",
        "Physical phones and Korean IME composition",
        "Unchanged native popup position and sizing tests not rerun",
        "All six prior tablet/layout combinations not rerun; current PC/mobile flows executed",
        "Prior Wagtail duplicate image upload error not retested",
        "Production deployment, cache, storage and backups",
        "User visual / administrator usability approval",
    ],
    "preservation": "preservation-result.json",
}
write("findings.json", findings)
print(
    json.dumps(
        {
            "status": verification["status"],
            "preservation": preservation,
            "browser_matrix": browsers,
        },
        ensure_ascii=False,
    )
)
