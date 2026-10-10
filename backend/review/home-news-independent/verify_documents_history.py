"""Verify current documents and scoped preservation; never write product data."""

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "backend/review/home-news"
DOCS = [
    "README.md",
    "backend/README.md",
    "docs/PRD.md",
    "docs/IMPLEMENTATION-PLAN.md",
    "docs/WORKFLOW.md",
    "prototype/DESIGN.md",
]
CHANGED = set(DOCS + ["backend/news/home.py"])
ADDED = {
    "backend/news/templates/news/home_news.html",
    "backend/news/tests/test_home_news.py",
    "backend/news/tests/test_home_news_browser.py",
    "backend/scripts/review-home-news.mjs",
}
FIXTURES = [
    "backend/news/tests/review_fixtures.py",
    "backend/news/tests/test_brand_browser.py",
    "backend/news/tests/test_branch_browser.py",
]


def slug(text):
    return re.sub(
        r"\s",
        "-",
        "".join(
            c
            for c in re.sub(r"<[^>]*>", "", text).lower()
            if unicodedata.category(c)[0] in "LN" or c in "_-" or c.isspace()
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before, after = [
        json.loads((args.archive / f"snapshot-{label}.json").read_text())
        for label in ("before", "final")
    ]
    checks = []

    def check(name, condition, detail=None):
        checks.append(
            {"name": name, "result": "PASS" if condition else "FAIL", "detail": detail}
        )

    errors, links, anchors = [], 0, 0
    sources = {name: (ROOT / name).read_text() for name in DOCS}
    for name in DOCS + ["backend/review/home-news/README.md"]:
        source = (ROOT / name).read_text()
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", source):
            if urlsplit(target).scheme:
                continue
            relative, _, anchor = target.partition("#")
            dest = (ROOT / name).parent / unquote(relative) if relative else ROOT / name
            links += 1
            if not dest.exists() and dest.resolve() != args.output.resolve():
                errors.append(f"{name}: {target}")
            elif anchor and dest.suffix == ".md":
                anchors += 1
                if unquote(anchor) not in {
                    slug(h)
                    for h in re.findall(r"^#{1,6}\s+(.+)$", dest.read_text(), re.M)
                }:
                    errors.append(f"{name}: {target}")
        if re.search(r"[\t ]+$|^(?:<{7}|={7}|>{7})(?: |$)", source, re.M):
            errors.append(f"{name}: whitespace/conflict marker")
    check("Current document/report links and anchors", not errors, errors)
    check(
        "All six documents link new review and distinguish independent pending",
        all(
            "home-news/README.md" in s
            and "M2-4" in s
            and "독립 검증" in s
            and "대기" in s
            for s in sources.values()
        ),
    )
    check(
        "Confirmed max-five/first-publication and separate popup policies",
        all(
            t in sources["docs/PRD.md"]
            for t in (
                "최대 5건",
                "최초 공개 최신순",
                "수정·재공개로 순위를 올리지 않는다",
                "최초 등록 빠른순",
            )
        ),
    )
    check(
        "M2-3 previous independent outcome and limited approval retained",
        all(
            "PASS_WITH_WARNINGS" in s and "이 배치로 유지" in s
            for s in sources.values()
        ),
    )
    check(
        "Previous checkpoint history/new pushed checkpoint/current uncommitted separated",
        all(
            "46ef337" in s and "b517cc2" in s and "M2-4" in s and "미커밋" in s
            for s in sources.values()
        ),
    )
    check(
        "Current status does not say M2-4 unstarted",
        all(
            not re.search(r"M2-4[^\n]*(?:계획만|미착수|후속 계획만)", s)
            for s in sources.values()
        ),
    )
    changed = sorted(
        p for p in before["files"] if before["files"][p] != after["files"].get(p)
    )
    added = sorted(set(after["files"]) - set(before["files"]))
    check(
        "Exactly seven authorized existing files and four product/test additions",
        set(changed) == CHANGED and set(added) == ADDED,
        {"changed": changed, "added": added},
    )
    scopes = {
        "previous_backend_reviews": lambda p: p.startswith("backend/review/"),
        "prototype_except_design_document": lambda p: (
            p.startswith("prototype/") and p != "prototype/DESIGN.md"
        ),
        "private_media": lambda p: p.startswith("backend/.private-media/"),
        "secrets": lambda p: p in ("backend/.env.local", "backend/.local-credentials"),
        "common_browser_fixtures": lambda p: p in FIXTURES,
        "dependencies_and_config": lambda p: (
            p
            in (
                "backend/pyproject.toml",
                "backend/uv.lock",
                "backend/compose.yaml",
                "prototype/package.json",
                "prototype/package-lock.json",
            )
            or p.startswith("backend/config/")
        ),
        "other_product_source_tests_and_scripts": lambda p: (
            p.startswith(("backend/news/", "backend/scripts/")) and p not in CHANGED
        ),
    }
    protected = {}
    for name, predicate in scopes.items():
        previous = {p: h for p, h in before["files"].items() if predicate(p)}
        current = {
            p: h for p, h in after["files"].items() if predicate(p) and p not in ADDED
        }
        protected[name] = {"files": len(previous), "unchanged": previous == current}
    check(
        "All protected file scopes unchanged",
        all(item["unchanged"] for item in protected.values()),
        protected,
    )
    check(
        "All 58 local database tables and row hashes unchanged",
        len(before["db"]) == len(after["db"]) == 58 and before["db"] == after["db"],
    )
    check("Git index unchanged", before["index_sha256"] == after["index_sha256"])
    check(
        "HEAD is previous pushed b517 checkpoint",
        subprocess.check_output(
            ["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        == "b517cc209f0f3ac66d7b602450cf5d9dca16d58c",
    )
    baseline = json.loads((REVIEW / "baseline.json").read_text())
    static = baseline["servers"][0]
    path = Path("/proc") / str(static["pid"])
    static_same = (
        str((path / "cwd").resolve()) == static["cwd"]
        and (path / "cmdline").read_bytes().decode().replace("\0", " ").strip()
        == static["args"]
    )
    processes = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            command = (path / "cmdline").read_bytes().decode().strip("\0").split("\0")
            cwd = (path / "cwd").resolve()
            if command[1:] == [
                "manage.py",
                "runserver",
                "127.0.0.1:8768",
                "--noreload",
                "--insecure",
            ]:
                processes.append(
                    {
                        "pid": int(path.name),
                        "cwd": str(cwd),
                        "command": command,
                        "canonical_executable": str((cwd / command[0]).resolve()),
                    }
                )
        except (OSError, UnicodeError):
            continue
    expected = ROOT / "backend/.venv/bin/python"
    # resolve() dereferences the venv symlink on both sides consistently.
    dynamic_same = (
        len(processes) == 1
        and processes[0]["cwd"] == str(ROOT / "backend")
        and processes[0]["canonical_executable"] == str(expected.resolve())
    )
    check(
        "Historical server baseline comparison; restart itself not independently reenacted",
        static_same and dynamic_same,
        processes,
    )
    result = subprocess.run(
        ["git", "--no-optional-locks", "diff", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    check("Git diff whitespace", result.returncode == 0, result.stdout + result.stderr)
    check(
        "Current files still match after snapshot",
        all(
            (ROOT / p).is_file()
            and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
            for p, h in after["files"].items()
        ),
    )
    payload = {
        "status": "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL",
        "local_links": links,
        "anchors": anchors,
        "checks": checks,
        "before_files": len(before["files"]),
        "after_files": len(after["files"]),
        "database_tables": len(after["db"]),
        "protected": protected,
        "actual_database_writes": False,
        "git_mutations": False,
        "product_and_test_file_changes": changed + added,
    }
    with args.output.open("x") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(payload["status"] != "PASS")


if __name__ == "__main__":
    main()
