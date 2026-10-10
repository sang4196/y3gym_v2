# M2-2-R1 독립 재검증

검증일: 2026-10-10 한국 시간. **판정: PASS_WITH_WARNINGS — 지정한 R1 완료 기준 통과, 기존 전역 포맷 경고 1개 유지.** 이전 F01·F02와 W01은 실제 재실행에서 해결을 확인했다. W03은 UI 변경 없이 안정 상태를 촬영하도록 보완됐으며 새 캡처를 직접 확인했다. 새 차단 결함은 발견하지 않았다. 사용자 시각·관리자 사용성 승인과 운영 배포 완료를 뜻하지 않는다.

작업 루트는 `/home/shlee/Workspace/ai/01.codex/y3gym_v2`다. 최신 AGENTS·루트/백엔드 README·PRD·IMPLEMENTATION-PLAN·DESIGN·WORKFLOW, [이전 독립 FAIL](../branches-independent/README.md)·[문제 목록](../branches-independent/findings.json), [개발 보완 보고](../branches-repair/README.md)·[변경 목록](../branches-repair/changed-files.json)·[자체 검사](../branches-repair/verification.json)·[보존 기록](../branches-repair/preservation.json)을 읽고 실제 소스·설치된 Wagtail 코드·이번 실행과 대조했다. 개발자의 PASS나 과거 결과를 이번 재실행으로 합산하지 않았다.

제품 코드·제품 문서·원본 prototype·이전 검수는 수정하지 않았다. 이 폴더에만 새 도구·로그·JSON·캡처·보고를 추가했다. Git index·commit·push·배포·서버 재시작·다음 기능은 수행하지 않았다.

## 문제별 해결 근거

### F01 / P1 — 동시 철회의 최신 초안 덮어쓰기: 해결 확인

- **요구:** [PRD FR-06](../../../docs/PRD.md#fr-06-공개-흐름과-미디어), [구현 계획 M2-2/R1](../../../docs/IMPLEMENTATION-PLAN.md#이번-단위-m2-2-지점시설-관리)의 초안/공개 리비전 분리·행 잠금·동시 저장 보호와 기존 콘텐츠 보존.
- **관련 코드:** [ConcurrentUnpublishView](../../news/wagtail_hooks.py) 39~47행, Post/Brand의 공통 뷰 연결과 BranchUnpublishView 상속. 설치된 Wagtail의 원래 조회를 거친 뒤 POST에서 최신 행을 `select_for_update()`로 직접 조회한다. 기존 권한·CSRF·hooks·철회 처리는 상속한다. GET 확인은 잠금을 추가하지 않는다.
- **기존 재현 재실행:** 이전 [재현 소스](../branches-independent/withdrawal_concurrency.py)를 [새 경로](original_repro.py)로 복사하고 import 위치·출력 경로만 적응했다. 철회가 조회 후 대기하는 동안 초안 저장을 요청하는 원래 순서를 유지했다. **1개 PASS**. 철회 SQL 잠금 true, 최신 포인터 2·새 주소 보존·live=false. [실행 로그](original-reproduction.txt)·[결과](original-repro-result.json).
- **추가 독립 재현:** [audit_concurrency.py](audit_concurrency.py)를 이번 검증자가 작성했다. 3모델 × 초안/공개 × 저장 먼저/철회 먼저의 **12가지 실제 HTTP 교차 요청**을 수행했다. 실제 조회 뒤 동기화 대기만 추가하며 객체 값이나 제품 로직을 인위적으로 바꾸지 않았다. 두 번째 요청이 첫 PostgreSQL 세션의 잠금을 기다리는 것을 `pg_blocking_pids()`로 확인한 뒤 해제했다.
- **기대:** 양쪽 요청에 실제 행 잠금 적용, 최신 리비전 포인터/내용·본문·시설 순서/교체 사진 보존, 직렬 처리 순서에 맞는 공개 상태·공개 미디어 접근.
- **실제:** **12/12에서 실제 잠금 대기·양쪽 FOR UPDATE·302/302·최신 포인터·리비전 2개·본문·시설 제목/순서/이미지 ID·원본 이미지 바이트 보존을 확인**했다. 마지막 작업이 공개이면 live=true·그 리비전이 공개되고 마지막 작업이 철회이면 live=false다. 최종 공개 이미지의 변환본만 익명 200, 나머지 변환본과 모든 원본은 404였다. [13개 추가 검사 로그](independent-concurrency.txt)·[12가지 상세 JSON](independent-concurrency/)·[명령/종료 코드](independent-concurrency.json).

공개 상태에서 초안 저장을 먼저 한 경우 Wagtail은 현재 모델 행/시설에 이전 공개 내용을 남기고 새 초안은 최신 리비전에 보관한다. 따라서 이 순서의 기대는 현재 행을 무조건 새 내용으로 바꾸는 것이 아니라 **최신 초안·포인터를 잃지 않는 것**이다. 철회 먼저 → 초안 저장이면 새 내용이 현재 행에도 남는다. 두 경우를 별도로 검사했다. 원래 재현의 기존 4초 대기 동안 새 구현에서는 저장 요청이 잠금을 기다려 순서가 직렬화되며, 실제 대기 증명은 별도 12가지 검사에 있다.

### 권한·CSRF·GET·404·hooks: 유지 확인

독립 추가 검사 1개에서 세 모델을 각각 확인했다. [독립 결과](independent-concurrency/independent-boundaries.json)와 전체 서버에서 직접 재실행한 [기존 경계 결과](server-concurrency/boundary-permissions.json)를 구분해 남겼다.

- 실제 비밀번호로 제한 계정 로그인 성공·관리자 홈 200·publish 권한 없음 확인.
- 일반 거부는 **302 + Location `/admin/` + 권한 거부 메시지**, AJAX는 403. 성공한 철회의 302와 실제 Location을 구분했다.
- 관리자 계정의 CSRF 없는 요청은 403. 거부/GET/없는 ID/취소를 거친 뒤 모델·최신 리비전·리비전 목록·본문/시설·이미지 바이트 해시가 동일했다.
- GET 확인은 200이며 대상 행 `FOR UPDATE` 없음. 없는 ID의 POST는 404.
- before hook 취소 409일 때 after hook 미호출·공개/초안/이미지 상태 유지. 정상 철회에서는 before(live=true) → after(live=false) 순서와 최종 비공개 확인.

### F02 / P2 — 공식 브랜드 브라우저 회귀 실패: 해결 확인

- **요구:** 공식 단독 명령의 기존 브랜드 7흐름 유지, [FR-02](../../../docs/PRD.md#fr-02-지점시설)의 0지점 문의 숨김 정책 유지.
- **관련 코드:** [공통 fixture](../../news/tests/review_fixtures.py) 11~18행, [브랜드 테스트](../../news/tests/test_brand_browser.py), [브랜드 스크립트](../../scripts/review-brand-home.mjs).
- **재현:** 기존 테스트 라벨 `news.tests.test_brand_browser`를 옵트인 환경·새 출력 경로에서 단독 실행했다. 보조 fixture로 대체하지 않았다.
- **기대/실제:** 공개 본점/예시점 2곳을 준비하고 기존 문의 바·두 지점·초안/공개·사진 제거·철회의 **7개 흐름이 모두 통과**했다. JS 오류 0. [단독 로그](brand-alone.txt)·[7흐름 JSON](brand-alone/brand/result.json)·[전체 명령](brand-alone.json).
- **검사 축소 여부:** 개발 전 보관 소스의 해시가 이전 독립 스냅샷과 일치함을 확인하고 실제 diff를 읽었다. 기존 7개 check·문의 바·두 패널 assertions는 삭제되지 않았다. [대조 근거](reviewed-source.json)·[실제 diff](reviewed-source.diff). 0지점 문의 숨김은 서버 검사와 지점 브라우저의 마지막 철회 흐름에서 계속 통과했다.

### W01 / P3 — flush 뒤 합동 fixture 오류: 해결 확인

[ensure_collection_root](../../news/tests/review_fixtures.py) 5~8행은 테스트 DB에서 flush로 사라진 migration 초기 dependency를 복원한다. 제품 seed는 바뀌지 않았다.

브랜드 단독 **1 PASS/7흐름**, 지점 단독 **1 PASS/11흐름**, 브랜드 → 지점 합동 **2 PASS/7+11흐름**, `--reverse` 지점 → 브랜드 **2 PASS/11+7흐름**을 모두 직접 실행했다. 두 번째 클래스도 정상 초기화됐고 Collection NULL 오류가 없었다. 실제 실행 순서는 로그의 테스트 시작 순서로 확인했다. [합동 로그](combined.txt)·[역순 로그](combined-reverse.txt).

### W03 / P3 — 전환 중 모바일 캡처: 촬영 보완 확인

제품 UI를 바꾸지 않았으며 축소 후 이름 입력이 x=20px·폭=335px가 될 때까지 기다리는 부분만 두 검수 스크립트에 추가됐다. 기존 개발 전 전환 중 캡처와 이전 독립 A/B 결과는 그대로 남아 있다.

이번 단독·합동·역순의 두 관리자 측정값은 모두 **x=20px·폭=335px**다. 개발 R1 캡처 두 개와 이번 독립 단독 캡처 두 개를 직접 열어 정상적인 입력 폭을 확인했다. 브랜드 JSON의 y=-178.55px는 `scrollIntoViewIfNeeded` 전 측정값이며 실제 캡처는 이후 스크롤한 화면이다. x/폭과 캡처를 확인하되 y를 화면 내 위치의 근거로 쓰지 않는다.

- 새 [지점 관리자 모바일](branch-alone/branches/branch-editor-mobile.png)·[브랜드 관리자 모바일](brand-alone/brand/brand-editor-mobile.png).
- [지점 측정 JSON](branch-alone/branches/checks.json)·[브랜드 측정 JSON](brand-alone/brand/result.json).
- [공개 지점 모바일](live/branches-mobile-full.png)·[홈 PC](live/home-desktop-first.png)·[0지점 상태의 소식/문의 숨김](branch-alone/branches/no-public-branches-mobile.png).

이전 독립 검증에서 수행한 새 모바일 진입·리로드·미리보기·사이드바·실제 모바일 입력/사진 선택/정렬/저장/공개의 전체 A/B 조작은 이번에 반복하지 않았다. UI 소스는 동일하며 이번에는 안정 촬영과 기존 관리자 브라우저 흐름을 재실행했다. 시각·관리자 사용성의 사용자 승인은 별도다.

## 이번 실제 명령과 결과

cwd는 `backend/`다. [run.py](run.py)가 실제 명령·환경 인자·종료 코드·시간을 같은 이름의 JSON에, 출력을 TXT에 남겼다. 테스트 DB를 사용하는 서버·추가·원래 재현·브라우저 네 실행은 **직렬로 수행**했다. [browser_matrix.py](browser_matrix.py)의 실제 네 명령은 각 실행 기록에서 확인할 수 있다. 브라우저 결과는 모두 `Y3GYM_BRAND_REVIEW_DIR`·`Y3GYM_BRANCH_REVIEW_DIR`의 이번 전용 새 하위 폴더에 저장했다.

| 이번 실행 | 실제 결과 / 명령 기록 |
| --- | --- |
| `uv run --locked python manage.py test news.tests --noinput --verbosity 2` + 전용 `Y3GYM_WITHDRAWAL_REVIEW_DIR` | **81개: 79 PASS·옵트인 2 skip**, 82.965초. 새 동시성 12개·기존 권한/hooks 2개 포함. [로그](server-tests.txt)·[명령](server-tests.json) |
| `uv run --locked python review/branches-independent-recheck/audit_concurrency.py` | **13 PASS**, 46.911초. 독립 교차 요청 12개·세 모델 경계 1개. [로그](independent-concurrency.txt)·[명령](independent-concurrency.json) |
| `uv run --locked python review/branches-independent-recheck/original_repro.py` | 이전 재현 **1 PASS**, 6.247초. [로그](original-reproduction.txt)·[명령](original-reproduction.json) |
| 옵트인 `manage.py test news.tests.test_brand_browser --noinput --verbosity 2` | 브랜드 단독 **1 PASS·7흐름**, 24.810초. [로그](brand-alone.txt)·[명령](brand-alone.json) |
| 옵트인 `manage.py test news.tests.test_branch_browser --noinput --verbosity 2` | 지점 단독 **1 PASS·11흐름**, 52.239초. [로그](branch-alone.txt)·[명령](branch-alone.json) |
| 두 옵트인 `manage.py test news.tests.test_brand_browser news.tests.test_branch_browser --noinput --verbosity 2` | 합동 **2 PASS·7+11흐름**, 97.125초. [로그](combined.txt)·[명령](combined.json) |
| 같은 합동 명령 + `--reverse` | 역순 **2 PASS·11+7흐름**, 76.538초. [로그](combined-reverse.txt)·[명령](combined-reverse.json) |
| 전용 경로로 `node scripts/review-branches.mjs --live-read-only` | 실제 8768 읽기 전용 **5흐름 PASS·JS 오류 0**: PC/모바일·자동 슬라이드·동작 줄이기/키보드·터치·JS 없음. [JSON](live/checks.json)·[로그](live-read-only.txt)·[명령](live-read-only.json) |
| 전용 경로로 `node scripts/review-popup-revisit.mjs` | 실제 8768 읽기 전용 **8흐름 PASS**: 일반 닫기/재방문·열린 창 재사용·소식 경유·pageshow·한국 시간 오늘 숨김/만료·모바일·차단 복구. [JSON](popups/revisit/checks.json)·[로그](popup-revisit.txt)·[명령](popup-revisit.json) |
| `uv run --locked python manage.py check` | PASS. [로그](system-check.txt)·[명령](system-check.json) |
| `uv run --locked python manage.py makemigrations --check --dry-run` | PASS·변경 없음. [로그](migration-check.txt)·[명령](migration-check.json) |
| `uv run --locked ruff check .` | 최종 PASS. [로그](lint-final.txt)·[명령](lint-final.json) |
| `uv run --locked ruff format --check news config scripts review/branches-repair review/branches-independent-recheck` | PASS·42파일. [로그](scoped-format-final.txt)·[명령](scoped-format-final.json) |
| `uv run --locked ruff format --check .` | **FAIL·기존 경고**: `review/workflow-01/verify.py`만 해당. 48파일은 이미 포맷됨. [로그](global-format-final.txt)·[명령](global-format-final.json) |
| `node review/branches-independent-recheck/verify-documents.mjs` | PASS·기존 현재 문서 **199개 로컬 링크·앵커 12개·검사항목 10개**. [JSON](document-checks.json)·[명령](documents.json) |
| `git diff --check` | PASS. [로그](diff-check.txt)·[명령](diff-check.json) |

서로 다른 실행의 테스트 수·동일 흐름 재실행·브라우저 세부 항목 수를 하나로 합산하지 않는다. 기본 서버에서 skip한 옵트인 두 개는 위 별도 실행으로 확인했다. 전체 서버에는 공개 지점 0곳·공유 미디어·초안 분리·소식/팝업/브랜드 회귀가 포함돼 실제 재실행됐다. 과거 native 팝업 29 PASS나 이전 반응형 6 PASS를 이번 결과로 계산하지 않는다.

## 경고·실패 이력과 미검증

- **W02 유지:** 전역 format 명령은 기존 `review/workflow-01/verify.py` 1개 때문에 종료 코드 1이다. 이번 전후 해시가 동일하며 원본을 고치지 않았다. 범위 포맷·전체 lint 통과와 구분한다.
- **검증 도구 준비:** 최초 보존 도구 복사 때 backend cwd에서 경로를 한 번 중복 지정해 파일을 찾지 못했다. 제품/DB 쓰기 없이 경로를 고친 뒤 테스트 전 스냅샷을 취득했다. 원래 재현 소스를 복사한 뒤의 import 순서 lint 1개는 새 복사본만 정렬해 최종 lint/포맷을 통과했다. 검사 대상 제품의 실패로 판정하지 않는다.
- **미재실행:** 변경 없는 native 팝업 좌표/크기·이전 태블릿 포함 레이아웃 6조합·전체 모바일 A/B 조작. 현재 공개 PC/모바일·슬라이드·팝업 재노출과 해당 관리자 흐름은 위에 구분했다. [UI 해시 대조](unchanged-ui.json)의 209파일은 이전 독립 이후 동일하다.
- **미검증:** Whale/Chromium 외 브라우저·실제 휴대폰·한국어 IME·기존 Wagtail 중복 이미지 업로드 오류·운영 배포/캐시/저장소/백업·사용자 시각/관리자 사용성 승인.
- **제외 범위 유지:** 트레이너 CMS·홈 최근 소식 CMS화·실제 전화/카카오톡/지도·본점 교체·삭제/복원·외부 서비스·새 기술/정책은 이번 보완 검증으로 완료 처리하지 않는다.

개발 자체 검수의 초기 fixture/권한 기대값/DB 충돌 실패와 중단 기록은 [개발 R1 보고](../branches-repair/README.md)에 그대로 있다. 이번 독립 검사에서 실제 재현되지 않은 과거 실패를 이번 실패나 이번 PASS로 재작성하지 않았다.

## 시작·종료 보존과 변경 범위

[snapshot.py](snapshot.py)는 실제 `127.0.0.1:55438` 앱 DB의 **READ ONLY 트랜잭션**에서 56개 테이블의 행 수·정규화 행 해시를 취득했다. 원본 행·비밀값은 보고하지 않았고 해시 스냅샷은 mode 0600이다. 쓰기·로그인·계정·사진·저장/공개/철회는 별도 `test_y3gym_m1`·임시 미디어·임시 계정에서만 수행했다. 실제 8768에서는 관리자 로그인·저장·철회를 하지 않고 독립 브라우저 문맥으로 읽었다.

- 이번 시작/종료 **기존 파일 1,019개 동일**, 기존 파일 변경·폴더 밖 추가 0. 비공개 미디어 **141파일**, 비밀 설정/계정 **2파일**, 이전 개발/독립/보완 검수 전체 포함.
- 실제 앱 DB **56개 테이블의 모든 행 수/행 해시 동일**, Git index 해시 동일. [보존 결과](preservation-result.json).
- 이전 독립 종료 스냅샷과 이번 시작 DB도 **56테이블 동일·index 동일**이다. 개발 완료 보고에만 의존하지 않고 이전 독립 값으로 대조했다. [이전/현재 비교](prior-independent-preservation.json).
- 이전 독립 종료 때의 707파일 중 변경된 기존 파일은 개발 R1이 보고한 **9개와 일치**한다. [변경 대조](change-comparison.json). 실제 검토한 5개 코드/검수 소스의 개발 전 보관본도 이전 독립 해시와 일치했다. 새 테스트/fixture 2개를 직접 읽고 새 서버 검사를 수행했다.
- `.venv`·node_modules·컴파일 캐시 같은 무시된 런타임 파일 전체의 보존을 주장하지 않는다. 코드/문서/기존 검수·의존성 정의·비밀·비공개 미디어·DB 행·Git index가 이번 비교 대상이다.

새 파일은 이 독립 재검증 폴더 안의 6개 Python 도구·문서 검사 도구·새 로그/캡처/JSON·이 보고서다. [검사 요약](verification.json)·[문제/경고 목록](findings.json)·[요구 대조](requirements-evidence.json)에 근거를 연결했다. 재실행 시 새 폴더와 모든 출력 경로를 지정해야 하며 이 검수 도구의 기존 로그/JSON에 덮어쓰지 않는다. 이번 요청을 마쳤으며 설계의 보고 검토를 기다린다.
