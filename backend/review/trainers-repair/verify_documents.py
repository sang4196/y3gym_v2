"""Validate current R1 state and M2-4 plan without rewriting historical evidence."""

import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS = [
    "README.md",
    "backend/README.md",
    "docs/PRD.md",
    "docs/IMPLEMENTATION-PLAN.md",
    "docs/WORKFLOW.md",
    "prototype/DESIGN.md",
    "backend/review/trainers-repair/README.md",
]


def slug(text):
    text = re.sub(r"<[^>]*>", "", text).lower()
    return re.sub(
        r"\s",
        "-",
        "".join(
            char
            for char in text
            if unicodedata.category(char)[0] in "LN" or char in "_-" or char.isspace()
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new evidence path; existing reports are preserved.")
    sources = {name: (ROOT / name).read_text() for name in DOCUMENTS}
    checks = []

    def check(name, success, detail=None):
        checks.append(
            {"name": name, "result": "PASS" if success else "FAIL", "detail": detail}
        )

    link_count = anchor_count = 0
    errors = []
    for name, source in sources.items():
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", source):
            if urlsplit(target).scheme:
                continue
            relative, _, anchor = target.partition("#")
            destination = (
                (ROOT / name).parent / unquote(relative) if relative else ROOT / name
            )
            link_count += 1
            if (
                not destination.exists()
                and destination.resolve() != args.output.resolve()
            ):
                errors.append(f"{name}: {target}")
            elif anchor and destination.suffix == ".md":
                anchor_count += 1
                headings = {
                    slug(h)
                    for h in re.findall(
                        r"^#{1,6}\s+(.+)$", destination.read_text(), re.M
                    )
                }
                if unquote(anchor) not in headings:
                    errors.append(f"{name}: {target}")
    check("Local document/report paths and anchors", not errors, errors)
    check(
        "Whitespace/conflict markers",
        all(
            not re.search(r"[\t ]+$|^(?:<{7}|={7}|>{7})(?: |$)", s, re.M)
            for s in sources.values()
        ),
    )
    prd = sources["docs/PRD.md"]
    current_status = prd.split("## 2.", 1)[1].split("## 3.", 1)[0]
    cms_row = next(
        line
        for line in current_status.splitlines()
        if line.startswith("| 실제 CMS·DB |")
    )
    check(
        "W04 current CMS table agrees with implemented trainer/R1 state",
        all(token in cms_row for token in ["M2-3", "구현", "R1", "독립 재검증 대기"])
        and not re.search(r"트레이너[^|]*미구현", cms_row),
        cms_row,
    )
    trainer = prd.split("### FR-03", 1)[1].split("### FR-04", 1)[0]
    check(
        "R1 draft search contract and independent review are explicit",
        all(
            token in trainer
            for token in [
                "초기 독립 검증 FAIL",
                "M2-3-R1",
                "독립 재검증 대기",
                "최신 초안",
                "최신 리비전이 없을 때만",
                "빈 값",
                "소속 필터",
                "페이지 이동",
            ]
        ),
    )
    check(
        "Confirmed profile requirements unchanged",
        all(
            token in trainer
            for token in [
                "이름·소속 지점만 필수",
                "사진·한줄 소개·직급·약력",
                "미완성 초안",
                "단일 목록",
                "CMS에서 수동 지정",
                "4:5",
            ]
        ),
    )
    check(
        "All five current operational docs link initial FAIL and R1",
        all(
            "trainers-independent/" in sources[name]
            and "trainers-repair/README.md" in sources[name]
            and "독립 재검증" in sources[name]
            for name in DOCUMENTS[:5]
        ),
    )
    check(
        "Specific approved layout remains separate from administrator usability",
        all(
            "이 배치로 유지" in sources[name] and "관리자 사용성" in sources[name]
            for name in ["docs/PRD.md", "docs/WORKFLOW.md", "prototype/DESIGN.md"]
        ),
    )
    news = prd.split("### FR-05", 1)[1].split("### FR-06", 1)[0]
    check(
        "New home/news ordering and limit decisions documented",
        all(
            token in news
            for token in [
                "최대 5건",
                "홈과 소식 목록은 최초 공개 최신순",
                "수정·재공개로 순위를 올리지",
                "최초 등록 빠른순",
                "M2-4",
                "미착수",
            ]
        ),
    )
    pending = prd.split("## 6.", 1)[1].split("## 7.", 1)[0]
    check(
        "Remaining news operational decisions exclude newly confirmed policies",
        "홈 최대 5건" in pending
        and "목록 페이지당 10건 운영 확정" in pending
        and "삭제/복원·운영자 권한은 미결정" in pending,
    )
    plan = sources["docs/IMPLEMENTATION-PLAN.md"]
    next_plan = plan.split("### 다음 미완료 단위: M2-4", 1)[1].split("## 7.", 1)[0]
    check(
        "M2-4 is only the next unstarted plan with limited completion criteria",
        all(
            token in next_plan
            for token in [
                "후속 계획만 기록·미착수",
                "명시적으로 다음 구현을 지시하기 전",
                "최대 5건",
                "0건",
                "실제 소식 상세 링크",
                "선택 지점 유지",
                "JavaScript 없는",
                "초안",
                "철회",
                "재공개",
                "페이지당 10건",
                "미결정",
            ]
        ),
    )
    check(
        "Historical M1/M2 boundaries remain as historical records",
        "**M1 제외:**" in plan
        and "**M2-2 종료 이력:**" in plan
        and "M2-2 당시에는 트레이너 CMS를 제외했다" in prd,
    )
    fixtures = [
        "backend/news/tests/review_fixtures.py",
        "backend/news/tests/test_brand_browser.py",
        "backend/news/tests/test_branch_browser.py",
    ]
    check(
        "W02 exact three shared fixture paths exist",
        all((ROOT / p).is_file() for p in fixtures),
        fixtures,
    )
    check(
        "R1 verification and implementation paths exist",
        all(
            (ROOT / p).is_file()
            for p in [
                "backend/news/tests/test_trainer_search.py",
                "backend/review/trainers-repair/audit_search.py",
                "backend/review/trainers-repair/browser_search.py",
                "backend/review/trainers-repair/review-search.mjs",
            ]
        ),
    )
    diff = subprocess.run(
        ["git", "--no-optional-locks", "diff", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    check("git diff --check", diff.returncode == 0, diff.stdout + diff.stderr)
    result = {
        "status": "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL",
        "documents": DOCUMENTS,
        "local_links": link_count,
        "anchors": anchor_count,
        "checks": checks,
        "http_or_database_writes": False,
        "historical_documents_not_subject_to_current_status_regex": True,
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
    for item in checks:
        if item["result"] != "PASS":
            print(item["name"], item["detail"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
