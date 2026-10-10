"""Verify no writes outside the new evidence folder and preserve the live app."""

import json
import os
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent
before, after = [
    json.loads((OUTPUT / f"snapshot-{label}.json").read_text())
    for label in ["before", "after"]
]
changed = sorted(
    p
    for p in set(before["files"]) | set(after["files"])
    if before["files"].get(p) != after["files"].get(p)
)
changed_tables = sorted(
    t
    for t in set(before["db"]) | set(after["db"])
    if before["db"].get(t) != after["db"].get(t)
)
scopes = {
    "all_previous_backend_reviews": lambda p: p.startswith("backend/review/"),
    "all_prototype_including_design": lambda p: p.startswith("prototype/"),
    "private_media": lambda p: p.startswith("backend/.private-media/"),
    "secrets": lambda p: p in {"backend/.env.local", "backend/.local-credentials"},
    "dependencies_and_config": lambda p: (
        p
        in {
            "backend/uv.lock",
            "backend/pyproject.toml",
            "backend/compose.yaml",
            "prototype/package.json",
            "prototype/package-lock.json",
        }
    ),
}
protected = {}
for label, predicate in scopes.items():
    paths = sorted(p for p in before["files"] if predicate(p))
    protected[label] = {
        "files": len(paths),
        "unchanged": all(before["files"][p] == after["files"].get(p) for p in paths),
        "no_additions": not any(
            predicate(p) for p in set(after["files"]) - set(before["files"])
        ),
    }
fixtures = [
    "backend/news/tests/review_fixtures.py",
    "backend/news/tests/test_brand_browser.py",
    "backend/news/tests/test_branch_browser.py",
]
per_file = [
    {
        "path": p,
        "before_sha256": before["files"][p],
        "after_sha256": after["files"].get(p),
        "unchanged": before["files"][p] == after["files"].get(p),
    }
    for p in fixtures
]
reference = json.loads((OUTPUT / "process-reference.json").read_text())
processes = {}
for port, record in reference["processes"].items():
    base = Path("/proc") / str(record["pid"])
    try:
        now = {
            "pid": record["pid"],
            "cwd": os.readlink(base / "cwd"),
            "command": (base / "cmdline")
            .read_bytes()
            .replace(bytes([0]), b" ")
            .decode()
            .strip(),
        }
    except (OSError, FileNotFoundError):
        now = None
    processes[port] = {"reference": record, "current": now, "unchanged": record == now}
checks = {
    "outside_evidence_all_files_unchanged_no_additions": not changed,
    "all_58_live_database_tables_and_rows_unchanged": not changed_tables
    and len(before["db"]) == len(after["db"]) == 58,
    "index_unchanged": before["index_sha256"] == after["index_sha256"],
    "all_protected_scopes_unchanged": all(
        d["unchanged"] and d["no_additions"] for d in protected.values()
    ),
    "all_three_common_fixtures_unchanged": all(d["unchanged"] for d in per_file),
    "both_existing_servers_unchanged": all(d["unchanged"] for d in processes.values()),
}
result = {
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "before_files": len(before["files"]),
    "after_files": len(after["files"]),
    "changed_files": changed,
    "database_tables": len(before["db"]),
    "changed_tables": changed_tables,
    "protected": protected,
    "common_fixture": per_file,
    "processes": processes,
}
with (OUTPUT / "preservation-result.json").open("x") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps({"status": result["status"], "checks": checks}))
raise SystemExit(result["status"] != "PASS")
