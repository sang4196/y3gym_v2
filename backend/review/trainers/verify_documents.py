"""Check current M2-3 document paths and consistency without HTTP/DB access."""

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
        parser.error("Use a new output file; existing review evidence is preserved.")
    sources = {name: (ROOT / name).read_text() for name in DOCUMENTS}
    report = {
        "status": "RUNNING",
        "documents": DOCUMENTS,
        "local_links": 0,
        "anchors": 0,
        "checks": [],
        "errors": [],
        "http_or_db_access": False,
    }

    def check(name, success, detail=None):
        report["checks"].append(
            {"name": name, "result": "PASS" if success else "FAIL", "detail": detail}
        )
        if not success:
            report["errors"].append(name)

    errors = []
    for name, source in sources.items():
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", source):
            if urlsplit(target).scheme:
                continue
            relative, _, anchor = target.partition("#")
            destination = (
                (ROOT / name).parent / unquote(relative) if relative else ROOT / name
            )
            report["local_links"] += 1
            if not destination.exists():
                errors.append(f"{name}: {target}")
            elif anchor and destination.suffix == ".md":
                report["anchors"] += 1
                if unquote(anchor) not in {
                    slug(heading)
                    for heading in re.findall(
                        r"^#{1,6}\s+(.+)$", destination.read_text(), re.M
                    )
                }:
                    errors.append(f"{name}: {target}")
    check("Local paths and Markdown anchors", not errors, errors)
    check(
        "Current document whitespace and conflict markers",
        all(
            not re.search(r"[\t ]+$|^(?:<{7}|={7}|>{7})(?: |$)", source, re.M)
            for source in sources.values()
        ),
    )
    check(
        "M2-3 actual implementation and independent review separated",
        all(
            "M2-3" in source
            and "독립 검증" in source
            and "trainers/README.md" in source
            for source in sources.values()
        ),
    )
    check(
        "No stale M2-3 not-started or trainer-CMS-unimplemented status",
        all(
            not re.search(
                r"M2-3[^.\n]*미착수|트레이너 (?:CMS|테이블·관리)[^.\n]*미구현", source
            )
            for source in sources.values()
        ),
    )
    prd = (
        sources["docs/PRD.md"]
        .split("### FR-03 트레이너", 1)[1]
        .split("### FR-04", 1)[0]
        .replace("**", "")
    )
    check(
        "Confirmed required/optional fields and single-list manual order",
        all(
            token in prd
            for token in [
                "이름·소속 지점만 필수",
                "사진·한줄 소개·직급·약력",
                "미완성 초안 저장",
                "단일 목록",
                "분류하지 않는다",
                "CMS에서 수동 지정",
                "4:5",
            ]
        ),
    )
    check(
        "Dual publication and draft affiliation isolation",
        all(
            token in prd
            for token in [
                "공개 프로필과 공개 소속 지점 조건을 함께 적용",
                "소속 이동 초안은 현재 공개 소속에 영향을 주지",
                "별도 저장 단위",
            ]
        ),
    )
    check(
        "Specific visual approval and pending independent/usability review separated",
        all(
            "이 배치로 유지" in sources[name]
            and "관리자 사용성" in sources[name]
            and "독립 검증" in sources[name]
            for name in ["docs/PRD.md", "prototype/DESIGN.md", "docs/WORKFLOW.md"]
        )
        and "독립 검증·관리자 사용성 승인은 대기" in prd,
    )
    plan = sources["docs/IMPLEMENTATION-PLAN.md"]
    check(
        "Excluded scope remains unimplemented",
        all(
            token in plan
            for token in [
                "프로필 삭제/복원",
                "운영 계정",
                "홈 최근 소식 CMS화",
                "실제 지도·전화·카카오톡",
                "기술 스택 변경",
            ]
        ),
    )
    check(
        "Checkpoint push recovery is separate from current uncommitted work",
        all(
            token in sources["docs/WORKFLOW.md"]
            for token in [
                "46ef337423fb89c1eb7f9000762f32e67802bc57",
                "최초 HTTPS",
                "재사용",
                "M2-3은 제외",
            ]
        ),
    )
    paths = [
        "backend/news/trainers.py",
        "backend/news/migrations/0005_trainer_trainerbiography.py",
        "backend/news/management/commands/bootstrap_trainer_review.py",
        "backend/news/tests/test_trainer_browser.py",
        "backend/news/tests/test_trainers.py",
        "backend/scripts/review-trainers.mjs",
        "backend/review/trainers/run_checks.py",
        "backend/news/templates/news/trainer_card.html",
        "backend/news/static/news/trainers.css",
    ]
    check(
        "New documented commands and implementation paths exist",
        all((ROOT / name).is_file() for name in paths),
        paths,
    )
    diff = subprocess.run(
        ["git", "--no-optional-locks", "diff", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    check(
        "git diff --check",
        diff.returncode == 0,
        {"exit_code": diff.returncode, "output": diff.stdout + diff.stderr},
    )
    report["status"] = "PASS" if not report["errors"] else "FAIL"
    with args.output.open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        report["status"],
        report["local_links"],
        "local links",
        report["anchors"],
        "anchors",
        len(report["checks"]),
        "checks",
    )
    for error in report["errors"]:
        print(error)
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
