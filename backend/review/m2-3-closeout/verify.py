"""Closeout document semantics and preservation only; no product test or HTTP."""

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "backend/review/m2-3-closeout"
DOCUMENTS = [
    "README.md",
    "backend/README.md",
    "docs/PRD.md",
    "docs/IMPLEMENTATION-PLAN.md",
    "docs/WORKFLOW.md",
    "prototype/DESIGN.md",
]
FIXTURES = [
    "backend/news/tests/review_fixtures.py",
    "backend/news/tests/test_brand_browser.py",
    "backend/news/tests/test_branch_browser.py",
]


def slug(text):
    text = re.sub(r"<[^>]*>", "", text).lower()
    return re.sub(
        r"\s",
        "-",
        "".join(
            c
            for c in text
            if unicodedata.category(c)[0] in "LN" or c in "_-" or c.isspace()
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Preserve prior evidence; use a new output."
    before, after = [
        json.loads((args.archive / f"snapshot-{label}.json").read_text())
        for label in ["before", "after"]
    ]
    sources = {name: (ROOT / name).read_text() for name in DOCUMENTS}
    checks = []

    def check(name, condition, detail=None):
        checks.append(
            {"name": name, "result": "PASS" if condition else "FAIL", "detail": detail}
        )

    recheck = ROOT / "backend/review/trainers-independent-recheck"
    findings = json.loads((recheck / "findings.json").read_text())
    check(
        "Independent final status and resolved findings read accurately",
        findings["status"] == "PASS_WITH_WARNINGS"
        and not findings["blocking_findings"]
        and {f["id"] for f in findings["resolved_initial_findings"]}
        == {"F01", "W02", "W03", "W04"}
        and [w["id"] for w in findings["warnings"]] == ["W01"],
    )
    link_count = anchor_count = 0
    errors = []
    for name in DOCUMENTS + ["backend/review/m2-3-closeout/README.md"]:
        source = (ROOT / name).read_text()
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", source):
            if urlsplit(target).scheme:
                continue
            relative, _, anchor = target.partition("#")
            dest = (ROOT / name).parent / unquote(relative) if relative else ROOT / name
            link_count += 1
            if not dest.exists() and dest.resolve() != args.output.resolve():
                errors.append(f"{name}: {target}")
            elif anchor and dest.suffix == ".md":
                anchor_count += 1
                if unquote(anchor) not in {
                    slug(h)
                    for h in re.findall(r"^#{1,6}\s+(.+)$", dest.read_text(), re.M)
                }:
                    errors.append(f"{name}: {target}")
        if re.search(r"[\t ]+$|^(?:<{7}|={7}|>{7})(?: |$)", source, re.M):
            errors.append(f"{name}: whitespace/conflict marker")
    check("Document/report paths anchors and whitespace", not errors, errors)
    check(
        "All six current docs link completed independent recheck",
        all(
            "trainers-independent-recheck/README.md" in s and "PASS_WITH_WARNINGS" in s
            for s in sources.values()
        ),
    )
    check(
        "No current M2-3 independent pending status left",
        all(
            not re.search(r"독립 (?:재검증|검증)(?:은)? 대기", s)
            for s in sources.values()
        ),
    )
    prd = sources["docs/PRD.md"]
    current = prd.split("## 2.", 1)[1].split("## 3.", 1)[0]
    row = next(
        line for line in current.splitlines() if line.startswith("| 실제 CMS·DB |")
    )
    check(
        "Current CMS table matches FR03 and final independent status",
        all(t in row for t in ["M2-3", "구현", "PASS_WITH_WARNINGS", "W01"])
        and not re.search(r"트레이너[^|]*미구현", row),
        row,
    )
    check(
        "User layout approval remains limited and usability pending",
        all(
            "이 배치로 유지" in sources[n] and "관리자 사용성" in sources[n]
            for n in [
                "README.md",
                "docs/PRD.md",
                "docs/WORKFLOW.md",
                "prototype/DESIGN.md",
            ]
        )
        and "별개다" in prd,
    )
    news = prd.split("### FR-05", 1)[1].split("### FR-06", 1)[0]
    plan = sources["docs/IMPLEMENTATION-PLAN.md"]
    next_plan = plan.split("### 다음 미완료 단위: M2-4", 1)[1].split("## 7.", 1)[0]
    check(
        "M2-4 confirmed policies remain plan only and not started",
        all(
            t in news
            for t in [
                "최대 5건",
                "홈과 소식 목록은 최초 공개 최신순",
                "수정·재공개로 순위를 올리지",
                "최초 등록 빠른순",
                "미착수",
            ]
        )
        and all(
            t in next_plan
            for t in [
                "후속 계획만 기록·미착수",
                "명시적으로 다음 구현을 지시하기 전에는 시작하지 않는다",
                "0건",
                "실제 소식 상세 링크",
                "선택 지점 유지",
                "JavaScript 없는",
                "초안",
                "철회",
                "재공개",
            ]
        ),
    )
    check(
        "Remaining operational decisions remain open",
        all(t in news for t in ["페이지당 10건", "초기 표시값", "확정하지 않는다"])
        and all(t in plan for t in ["공개일 편집", "삭제/복원", "미결정"]),
    )
    check(
        "Historical M1/M2 records retained",
        "**M1 제외:**" in plan
        and "**M2-2 종료 이력:**" in plan
        and "M2-2 당시에는 트레이너 CMS를 제외했다" in prd,
    )
    check(
        "Checkpoint push complete separated from current uncommitted changes",
        all("46ef337" in s and "미커밋" in s for s in sources.values())
        and "46ef337423fb89c1eb7f9000762f32e67802bc57" in sources["docs/WORKFLOW.md"],
    )
    check(
        "Current work explicitly states no product reruns",
        all(
            "종료" in s
            and ("제품 검사" in s or "제품 테스트" in s or "제품 UI·캡처" in s)
            for s in sources.values()
        ),
    )
    modified = sorted(
        p for p, h in before["files"].items() if after["files"].get(p) != h
    )
    added = sorted(set(after["files"]) - set(before["files"]))
    check(
        "Exactly six current document changes no outside additions",
        set(modified) == set(DOCUMENTS) and not added,
        {"modified": modified, "added": added},
    )
    protected = {}
    for label, paths in {
        "old_backend_reviews_including_all_FAIL_R1_recheck": [
            p for p in before["files"] if p.startswith("backend/review/")
        ],
        "prototype_except_approved_design_document_edit": [
            p
            for p in before["files"]
            if p.startswith("prototype/") and p != "prototype/DESIGN.md"
        ],
        "private_media": [
            p for p in before["files"] if p.startswith("backend/.private-media/")
        ],
        "secrets": ["backend/.env.local", "backend/.local-credentials"],
        "common_fixtures": FIXTURES,
        "dependencies_config": [
            "backend/uv.lock",
            "backend/pyproject.toml",
            "prototype/package.json",
            "prototype/package-lock.json",
            "backend/compose.yaml",
        ],
        "all_product_source_tests_scripts": [
            p
            for p in before["files"]
            if p.startswith(("backend/news/", "backend/config/", "backend/scripts/"))
        ],
    }.items():
        protected[label] = {
            "files": len(paths),
            "paths": paths if label == "common_fixtures" else None,
            "unchanged": all(
                after["files"].get(p) == before["files"][p] for p in paths
            ),
        }
    check(
        "Product and all prior evidence media secrets fixture dependencies preserved",
        all(d["unchanged"] for d in protected.values()),
        protected,
    )
    check(
        "All 58 database tables and rows unchanged",
        before["db"] == after["db"] and len(after["db"]) == 58,
    )
    check("Git index unchanged", before["index_sha256"] == after["index_sha256"])
    expected_processes = json.loads((recheck / "preservation-result.json").read_text())[
        "processes"
    ]
    process_checks = {}
    for port, meta in expected_processes.items():
        reference = meta["current"]
        proc = Path("/proc") / str(reference["pid"])
        current_process = {
            "pid": reference["pid"],
            "cwd": str((proc / "cwd").resolve()),
            "command": (proc / "cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode()
            .strip(),
        }
        process_checks[port] = {
            "unchanged": current_process == reference,
            "current": current_process,
        }
    check(
        "Existing 8767 and 8768 processes unchanged",
        all(d["unchanged"] for d in process_checks.values()),
        process_checks,
    )
    diff = subprocess.run(
        ["git", "--no-optional-locks", "diff", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    check("git diff --check", diff.returncode == 0, diff.stdout + diff.stderr)
    patches = []
    for name in DOCUMENTS:
        old = (args.archive / "documents-before" / name).read_text()
        patches.extend(
            difflib.unified_diff(
                old.splitlines(True),
                sources[name].splitlines(True),
                fromfile="closeout-before/" + name,
                tofile="closeout-after/" + name,
            )
        )
    with (REVIEW / "document-diff.patch").open("x") as handle:
        handle.write("".join(patches))
    current_hashes_match = all(
        (ROOT / p).is_file()
        and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
        for p, h in after["files"].items()
    )
    check("Current files still equal final snapshot", current_hashes_match)
    result = {
        "status": "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL",
        "documents": DOCUMENTS,
        "checks": checks,
        "local_links": link_count,
        "anchors": anchor_count,
        "before_files": len(before["files"]),
        "after_files": len(after["files"]),
        "product_tests_reexecuted": False,
        "capture_regeneration": False,
        "HTTP_requests": False,
        "actual_database_writes": False,
        "database_preservation_queries": "SET TRANSACTION READ ONLY; SELECT row hashes only",
        "git_mutations": False,
        "independent_product_results": "Read from trainers-independent-recheck; not executed by this closeout.",
    }
    with args.output.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        result["status"],
        link_count,
        "links",
        anchor_count,
        "anchors",
        len(checks),
        "checks",
    )
    for c in checks:
        if c["result"] != "PASS":
            print(c["name"], c["detail"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
