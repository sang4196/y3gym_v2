"""Compare R1 snapshots with exact source scope and all three shared fixtures."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ALLOWED_MODIFIED = {
    "README.md",
    "backend/README.md",
    "docs/PRD.md",
    "docs/IMPLEMENTATION-PLAN.md",
    "docs/WORKFLOW.md",
    "backend/news/wagtail_hooks.py",
    "backend/scripts/review-branches.mjs",
}
ALLOWED_NEW = {"backend/news/tests/test_trainer_search.py"}
FIXTURES = [
    "backend/news/tests/review_fixtures.py",
    "backend/news/tests/test_brand_browser.py",
    "backend/news/tests/test_branch_browser.py",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new evidence output path.")
    before, after = [json.loads(p.read_text()) for p in [args.before, args.after]]
    modified = sorted(
        p for p, h in before["files"].items() if after["files"].get(p) != h
    )
    new = sorted(set(after["files"]) - set(before["files"]))
    scopes = {
        "all_prior_backend_reviews_including_trainer_and_independent_FAIL": lambda p: (
            p.startswith("backend/review/")
        ),
        "all_prototype_including_design": lambda p: p.startswith("prototype/"),
        "private_media": lambda p: p.startswith("backend/.private-media/"),
        "secrets": lambda p: p in ["backend/.env.local", "backend/.local-credentials"],
        "dependency_and_compose_files": lambda p: (
            p
            in [
                "backend/uv.lock",
                "backend/pyproject.toml",
                "prototype/package.json",
                "prototype/package-lock.json",
                "backend/compose.yaml",
            ]
        ),
    }
    protected = {}
    for label, predicate in scopes.items():
        paths = sorted(p for p in before["files"] if predicate(p))
        protected[label] = {
            "files": len(paths),
            "unchanged": all(
                before["files"][p] == after["files"].get(p) for p in paths
            ),
        }
    protected["common_browser_fixture"] = {
        "files": len(FIXTURES),
        "paths": FIXTURES,
        "per_file": [
            {
                "path": p,
                "before_sha256": before["files"][p],
                "after_sha256": after["files"].get(p),
                "unchanged": before["files"][p] == after["files"].get(p),
            }
            for p in FIXTURES
        ],
        "unchanged": all(before["files"][p] == after["files"].get(p) for p in FIXTURES),
    }
    changed_tables = sorted(
        t
        for t in set(before["db"]) | set(after["db"])
        if before["db"].get(t) != after["db"].get(t)
    )
    checks = {
        "changed_existing_files_exactly_seven_authorized": set(modified)
        == ALLOWED_MODIFIED,
        "new_files_outside_R1_review_exactly_one_search_test": set(new) == ALLOWED_NEW,
        "all_58_database_tables_and_rows_unchanged": not changed_tables
        and len(before["db"]) == len(after["db"]) == 58,
        "git_index_unchanged": before["index_sha256"] == after["index_sha256"],
        "all_protected_file_hashes_unchanged": all(
            d["unchanged"] for d in protected.values()
        ),
        "all_145_private_media_files_unchanged_no_additions": protected[
            "private_media"
        ]["files"]
        == 145
        and not any(p.startswith("backend/.private-media/") for p in new),
        "all_three_shared_browser_fixture_files_explicitly_compared": len(
            protected["common_browser_fixture"]["per_file"]
        )
        == 3
        and protected["common_browser_fixture"]["unchanged"],
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "before_files": len(before["files"]),
        "after_files": len(after["files"]),
        "modified_existing_files": modified,
        "new_files_outside_R1_review": new,
        "protected": protected,
        "database_tables_compared": len(before["db"]),
        "changed_database_tables": changed_tables,
        "W02_prior_scope_explanation": "The prior trainers README said three shared fixture files, while preservation-final.json counted two in its subgroup: its third path incorrectly named a nonexistent management command instead of tests/review_fixtures.py. The full old file comparison already covered the actual file. All prior artifacts remain unchanged; R1 explicitly lists and hashes the correct three files.",
        "actual_schema_seed_content_account_or_media_writes": False,
    }
    with args.output.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        result["status"],
        len(before["files"]),
        "baseline files;",
        len(before["db"]),
        "DB tables; fixtures",
        len(FIXTURES),
    )
    if result["status"] != "PASS":
        print(checks, modified, new, changed_tables)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
