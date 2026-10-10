"""M2-4 closeout: documents and preservation only; no product tests or HTTP."""

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
REVIEW = ROOT / "backend/review/m2-4-closeout"
DOCS = [
    "README.md",
    "backend/README.md",
    "docs/PRD.md",
    "docs/IMPLEMENTATION-PLAN.md",
    "docs/WORKFLOW.md",
    "prototype/DESIGN.md",
]
CAPTURES = [
    "backend/review/home-news/live-third/home/desktop-actual-news.png",
    "backend/review/home-news/live-third/home/mobile-actual-news-unobscured.png",
]
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
        for label in ("before", "after")
    ]
    sources = {name: (ROOT / name).read_text() for name in DOCS}
    checks = []

    def check(name, passed, detail=None):
        checks.append(
            {"name": name, "result": "PASS" if passed else "FAIL", "detail": detail}
        )

    independent = ROOT / "backend/review/home-news-independent"
    findings = json.loads((independent / "findings.json").read_text())
    result = json.loads((independent / "verification.json").read_text())
    check(
        "Read independent final outcome without rerunning product checks",
        findings["status"] == "PASS_WITH_WARNINGS"
        and not findings["blocking_findings"]
        and not findings["product_defects_found"]
        and [w["id"] for w in findings["warnings"]] == ["W01"]
        and result["whole_server_rerun"]
        == {"collected": 110, "passed": 106, "skipped_opt_in": 4}
        and result["home_server_rerun"] == {"collected": 8, "passed": 8}
        and result["independent_new_server_final"]
        == {"collected": 3, "passed": 3, "initial_failures": 2},
    )
    errors, links, anchors = [], 0, 0
    for name in DOCS + ["backend/review/m2-4-closeout/README.md"]:
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
    check("Current document/report paths and anchors", not errors, errors)
    check(
        "All six current documents link completed M2-4 independent outcome",
        all(
            "home-news-independent/README.md" in s and "PASS_WITH_WARNINGS" in s
            for s in sources.values()
        ),
    )
    stale = (
        "독립 검증은 대기다",
        "독립 검증 대기다",
        "독립 검증 대기이며",
        "독립 검증 대기·미커밋",
        "독립 검증과 새 화면의 사용자 시각 승인 대기",
        "마치고 독립 검증을 기다린다",
        "현재 자체 검수와 독립 검증 대기를",
    )
    check(
        "No current M2-4 independent/visual pending statement remains",
        all(not any(text in s for text in stale) for s in sources.values()),
    )
    check(
        "Specific explicit user approval with exact two capture references in all six docs",
        all(
            all(Path(p).name in s for p in CAPTURES)
            and "이 배치로 유지" in s
            and "5건 배치" in s
            and "행 간격" in s
            and "한정" in s
            for s in sources.values()
        ),
    )
    check(
        "Administrator usability real devices Whale IME and operational approval remain separate",
        all(
            all(
                t in s
                for t in (
                    "관리자 사용성",
                    "실제 기기",
                    "Whale",
                    "한국어 IME",
                    "운영 승인은 아니다",
                )
            )
            for s in sources.values()
        ),
    )
    check(
        "Historical approval-pending JSON is retained as a dated record",
        all("당시 기록으로 보존" in s for s in sources.values())
        and all(before["files"][p] == after["files"][p] for p in CAPTURES),
    )
    cms_row = next(
        line
        for line in sources["docs/PRD.md"].splitlines()
        if line.startswith("| 실제 CMS·DB |")
    )
    technical_row = next(
        line
        for line in sources["docs/PRD.md"].splitlines()
        if line.startswith("| 후속 기술 구현 |")
    )
    fr05 = (
        sources["docs/PRD.md"]
        .split("### FR-05 공통 소식", 1)[1]
        .split("### FR-06", 1)[0]
    )
    check(
        "PRD current CMS/FR05/future technical table agree",
        all(
            all(t in block for t in ("M2-4", "PASS_WITH_WARNINGS", "5건", "승인"))
            for block in (cms_row, fr05, technical_row)
        ),
    )
    check(
        "Approved max-five and first-publication/edit-republish/popup-order policies retained",
        all(
            t in fr05
            for t in (
                "최대 5건",
                "최초 공개 최신순",
                "수정·재공개로 순위를 올리지 않는다",
                "최초 등록 빠른순",
            )
        ),
    )
    check(
        "Historical M2-3/M2-4 headings and anchors retained",
        all(
            t in sources["docs/IMPLEMENTATION-PLAN.md"]
            for t in (
                "### 다음 단위: M2-3 트레이너 관리",
                "### 다음 미완료 단위: M2-4 홈 최근 소식 실제 공개 글 연결",
                "처음 계획을 기록한 당시 제목",
            )
        ),
    )
    before_prd = (args.archive / "documents-before/docs/PRD.md").read_text()

    def pending_rows(source):
        section = source.split("## 6. 이후 진행과 미결정 사항", 1)[1].split("## 7.", 1)[
            0
        ]
        return [
            line
            for line in section.splitlines()
            if line.startswith("|") and not line.startswith("| 후속 기술 구현 |")
        ]

    check(
        "All existing undecided policy rows retained without expansion",
        pending_rows(before_prd) == pending_rows(sources["docs/PRD.md"])
        and "운영 저장소/캐시는 미구현" in technical_row,
        {"unchanged_table_lines": len(pending_rows(before_prd))},
    )
    check(
        "Previous b517 push and current M2-4 uncommitted state distinguished",
        all(
            "46ef337" in s and "b517cc2" in s and "M2-4" in s and "미커밋" in s
            for s in sources.values()
        ),
    )
    check(
        "Uncommitted state is dated to closeout and separate from subsequent Git results",
        all(
            "이 종료 문서 작성 시점의 M2-4 변경은 미커밋이며 이후 Git 반영 결과와 구분한다."
            in s
            for s in sources.values()
        ),
    )
    changed = sorted(
        p for p, h in before["files"].items() if after["files"].get(p) != h
    )
    added = sorted(set(after["files"]) - set(before["files"]))
    check(
        "Only six current documents changed; no additions outside new closeout",
        set(changed) == set(DOCS) and not added,
        {"changed": changed, "added": added},
    )
    scopes = {
        "all_previous_reviews": lambda p: p.startswith("backend/review/"),
        "prototype_UI_except_design_document": lambda p: (
            p.startswith("prototype/") and p != "prototype/DESIGN.md"
        ),
        "private_media": lambda p: p.startswith("backend/.private-media/"),
        "secrets": lambda p: p in ("backend/.env.local", "backend/.local-credentials"),
        "common_browser_fixtures": lambda p: p in FIXTURES,
        "all_product_source_tests_scripts_config_dependencies": lambda p: (
            p.startswith(("backend/news/", "backend/scripts/", "backend/config/"))
            or p
            in (
                "backend/pyproject.toml",
                "backend/uv.lock",
                "backend/compose.yaml",
                "prototype/package.json",
                "prototype/package-lock.json",
            )
        ),
    }
    protected = {}
    for name, predicate in scopes.items():
        previous = {p: h for p, h in before["files"].items() if predicate(p)}
        current = {p: h for p, h in after["files"].items() if predicate(p)}
        protected[name] = {"files": len(previous), "unchanged": previous == current}
    check(
        "Code all old reviews prototype UI media secrets fixtures and config unchanged",
        all(item["unchanged"] for item in protected.values()),
        protected,
    )
    check(
        "All 58 database tables and row hashes unchanged with read-only capture",
        len(before["db"]) == len(after["db"]) == 58 and before["db"] == after["db"],
    )
    check(
        "Git index and HEAD unchanged",
        before["index_sha256"] == after["index_sha256"]
        and subprocess.check_output(
            ["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        == "b517cc209f0f3ac66d7b602450cf5d9dca16d58c",
    )
    baseline = json.loads((REVIEW / "baseline.json").read_text())
    processes = []
    for record in baseline["servers"]:
        proc = Path("/proc") / str(record["pid"])
        current = {
            "pid": record["pid"],
            "cwd": str((proc / "cwd").resolve()),
            "command": (proc / "cmdline")
            .read_bytes()
            .decode()
            .replace("\0", " ")
            .strip(),
        }
        processes.append(
            {"reference": record, "current": current, "unchanged": record == current}
        )
    check(
        "8767 and 8768 PID command and root preserved without restart",
        all(row["unchanged"] for row in processes),
        processes,
    )
    diff = subprocess.run(
        ["git", "--no-optional-locks", "diff", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    check("Git diff whitespace", diff.returncode == 0, diff.stdout + diff.stderr)
    check(
        "Current files still equal final snapshot",
        all(
            (ROOT / p).is_file()
            and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
            for p, h in after["files"].items()
        ),
    )
    report = (REVIEW / "README.md").read_text()
    check(
        "Closeout report explicitly distinguishes read product results and current document-only checks",
        "제품 테스트·캡처를 재실행하지 않았다" in report
        and "보고서 확인" in report
        and "문서·보존" in report,
    )
    patch = "".join(
        "".join(
            difflib.unified_diff(
                (args.archive / "documents-before" / name)
                .read_text()
                .splitlines(keepends=True),
                (ROOT / name).read_text().splitlines(keepends=True),
                fromfile="before/" + name,
                tofile="after/" + name,
            )
        )
        for name in DOCS
    )
    with (REVIEW / "document-diff.patch").open("x") as handle:
        handle.write(patch)
    payload = {
        "status": "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL",
        "local_links": links,
        "anchors": anchors,
        "checks": checks,
        "before_files": len(before["files"]),
        "after_files": len(after["files"]),
        "changed_documents": changed,
        "protected": protected,
        "database_tables": len(after["db"]),
        "product_checks_rerun": False,
        "capture_regeneration": False,
        "HTTP_requests": False,
        "actual_database_writes": False,
        "git_mutations": False,
        "independent_results": "Read from home-news-independent; not executed by this closeout.",
    }
    with args.output.open("x") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(payload["status"] != "PASS")


if __name__ == "__main__":
    main()
