"""Static document checks only: no product imports, HTTP, DB, or server actions."""

import argparse
import json
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
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
    text = "".join(
        char
        for char in text
        if unicodedata.category(char)[0] in "LN" or char in "_-" or char.isspace()
    )
    return re.sub(r"\s", "-", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; specify a new result path.")
    report = {
        "run": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING",
        "scope": "Static document paths, anchors, command definitions and consistency",
        "documents": DOCUMENTS,
        "local_links": 0,
        "markdown_anchors": 0,
        "checks": [],
        "errors": [],
        "product_tests_rerun": False,
        "http_or_database_access": False,
    }

    def check(name, condition, detail=None):
        entry = {"name": name, "result": "PASS" if condition else "FAIL"}
        if detail is not None:
            entry["detail"] = detail
        report["checks"].append(entry)
        if not condition:
            report["errors"].append(name)

    sources = {name: (ROOT / name).read_text() for name in DOCUMENTS}
    link_errors = []
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
                link_errors.append(f"{name}: missing {target}")
            elif anchor and destination.suffix == ".md":
                headings = {
                    slug(text)
                    for text in re.findall(
                        r"^#{1,6}\s+(.+)$", destination.read_text(), re.M
                    )
                }
                report["markdown_anchors"] += 1
                if unquote(anchor) not in headings:
                    link_errors.append(f"{name}: missing anchor {target}")
    check("Local links and Markdown anchors exist", not link_errors, link_errors)
    check(
        "Whitespace and conflict markers",
        all(
            not re.search(r"[\t ]+$|^(?:<{7}|={7}|>{7})(?: |$)", source, re.M)
            for source in sources.values()
        ),
    )

    latest = {
        name: source
        for name, source in sources.items()
        if name != "prototype/DESIGN.md"
    }
    check(
        "Five current documents record FAIL -> R1 -> PASS_WITH_WARNINGS with evidence",
        all(
            all(
                token in source
                for token in [
                    "branches-independent/README.md",
                    "branches-repair/README.md",
                    "branches-independent-recheck/README.md",
                    "FAIL",
                    "PASS_WITH_WARNINGS",
                ]
            )
            for source in latest.values()
        ),
    )
    check(
        "No stale independent-recheck-pending status in current documents",
        all(
            not re.search(r"독립 재검증[^.\n]*대기|독립 검증/사용자 확인 전", source)
            for source in latest.values()
        ),
    )
    check(
        "M2-3 remains unstarted behind Git checkpoint and separate design instruction",
        all(
            all(
                token in source
                for token in ["M2-3", "미착수", "Git 체크포인트", "별도"]
            )
            for source in latest.values()
        ),
    )
    prd = sources["docs/PRD.md"]
    fr03 = prd.split("### FR-03 트레이너\n", 1)[1].split("### FR-04", 1)[0]
    plan = sources["docs/IMPLEMENTATION-PLAN.md"]
    m23 = plan.split("### 다음 단위: M2-3 트레이너 관리\n", 1)[1].split("## 7.", 1)[0]
    plain_fr03 = fr03.replace("**", "")
    plain_m23 = m23.replace("**", "")
    for name, tokens in [
        (
            "Confirmed trainer required and optional fields",
            [
                "이름·소속 지점만 필수",
                "사진·한줄 소개·직급·약력",
                "선택",
                "미완성 초안 저장",
            ],
        ),
        (
            "One biography list without classifications, manual CMS ordering",
            ["단일 목록", "경력·자격·수상", "분류", "CMS에서 수동 지정"],
        ),
        (
            "Profile and biography revision unit, separate branch-entry save unit",
            [
                "편집·리비전 단위",
                "별도 저장 단위",
                "지점에서 소속 트레이너 관리로 진입",
            ],
        ),
        (
            "Authorized preview, explicit publication and withdrawal",
            ["초안 저장 → 권한 있는 미리보기 → 명시적 공개·철회"],
        ),
        (
            "Draft affiliation move does not change public affiliation",
            [
                "소속 이동 초안은 현재 공개 소속에 영향을 주지",
                "명시적 공개 후 새 소속에만",
            ],
        ),
        (
            "Approved 4:5 photos and hidden empty optional areas",
            ["4:5", "선택 영역", "숨긴다", "임시 자료"],
        ),
    ]:
        check(name, all(token in plain_fr03 and token in plain_m23 for token in tokens))
    check(
        "Selected branch profiles require both profile and branch publication",
        all(
            token in plain_fr03
            for token in ["선택 지점", "공개 프로필과 공개 소속 지점 조건을 함께 적용"]
        )
        and all(
            token in plain_m23
            for token in ["선택 지점의 공개 프로필만", "프로필과 소속 지점이 모두 공개"]
        ),
    )
    check(
        "M2-3 reuses and regression-checks image boundaries and row locks",
        all(
            token in m23
            for token in [
                "이미지 공개 사용처 판정",
                "행 잠금",
                "회귀 검증",
                "마지막 공개 사용처 철회",
                "저장/공개/철회 교차 요청",
            ]
        ),
    )
    exclusions = m23.split("**제외·미구현:**", 1)[1]
    check(
        "M2-3 exclusions stay explicit",
        all(
            token in exclusions
            for token in [
                "프로필 삭제/복원",
                "운영 계정",
                "홈 트레이너",
                "새로운 고객 메뉴",
                "별도 공개 프로필 페이지",
                "홈 최근 소식 CMS화",
                "실제 지도·전화·카카오톡",
                "운영 배포",
                "기술 스택 변경",
            ]
        ),
    )
    findings = json.loads(
        (ROOT / "backend/review/branches-independent-recheck/findings.json").read_text()
    )
    evidence = json.loads(
        (
            ROOT / "backend/review/branches-independent-recheck/verification.json"
        ).read_text()
    )
    check(
        "Latest status agrees with independent evidence; warnings and approval limits retained",
        findings["status"] == evidence["status"] == "PASS_WITH_WARNINGS"
        and not findings["blocking_findings"]
        and {item["id"] for item in findings["resolved"]} >= {"F01", "F02", "W01"}
        and all(
            all(
                token in source
                for token in ["workflow-01/verify.py", "사용자 시각", "관리자 사용성"]
            )
            for source in latest.values()
        ),
    )
    check(
        "Copied counts agree with independent execution, not a fresh product test run",
        evidence["server"] == {"collected": 81, "passed": 79, "skipped_opt_in": 2}
        and evidence["independent_additional"]["passed"] == 13
        and evidence["original_reproduction"]["passed"] == 1
        and evidence["read_only_live_flows"] == 5
        and evidence["popup_revisit_flows"] == 8
        and all(item["exit_code"] == 0 for item in evidence["browser_matrix"])
        and all(
            flow["status"] == "PASS"
            and flow["count"] == {"brand": 7, "branches": 11}[kind]
            for item in evidence["browser_matrix"]
            for kind, flow in item["flows"].items()
        )
        and "재실행하지 않았다" in sources["backend/README.md"],
    )
    command_paths = [
        "backend/manage.py",
        "backend/pyproject.toml",
        "backend/uv.lock",
        "backend/compose.yaml",
        "backend/scripts/prepare_local.py",
        "backend/scripts/serve-prototype.py",
        "backend/review/branches-repair/run_checks.py",
        "backend/news/management/commands/bootstrap_review.py",
        "backend/news/management/commands/bootstrap_brand_review.py",
        "backend/news/management/commands/bootstrap_branch_review.py",
        "backend/news/tests/__init__.py",
        "backend/news/tests/test_brand_browser.py",
        "backend/news/tests/test_branch_browser.py",
    ]
    command_paths.extend(
        "backend/" + path
        for path in sorted(
            set(
                re.findall(
                    r"\b(scripts/review-[\w-]+\.mjs)\b", sources["backend/README.md"]
                )
            )
        )
    )
    check(
        "Existing documented local command/test paths exist (not executed)",
        all((ROOT / name).is_file() for name in command_paths),
        command_paths,
    )
    diff_check = subprocess.run(
        ["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True
    )
    check(
        "git diff --check (read only; tracked diff only)",
        diff_check.returncode == 0,
        {
            "exit_code": diff_check.returncode,
            "output": diff_check.stdout + diff_check.stderr,
        },
    )
    report["status"] = "PASS" if not report["errors"] else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        f"{report['status']}: {report['local_links']} local links, {report['markdown_anchors']} anchors, {len(report['checks'])} checks"
    )
    for error in report["errors"]:
        print(error)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
