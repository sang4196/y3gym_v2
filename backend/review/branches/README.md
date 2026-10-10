# M2-2 지점·시설 개발 및 자체 검수

검수일: 2026-10-10 한국 시간. **로컬 구현과 개발 자체 검수 완료. 설계의 보고 검토·테스트 담당의 독립 검증·사용자 시각/관리자 사용성 승인은 대기 중이다.** Git index·커밋·푸시·배포는 변경하지 않았다. 이전 검수 결과를 이번 실행으로 합산하지 않는다.

## 구현한 동작

- 관리자 ‘지점’에서 지점명·소개·주소·운영시간·선택 전화/카카오톡 안내·표시 순서를 편집한다. 시설 사진·제목·설명·대체 설명·순서·중심은 부모 지점과 같은 클러스터 리비전으로 저장한다. 시설의 추가·삭제·재정렬 초안도 공개본에 섞이지 않는다.
- 미완성 초안을 허용하고 공개할 리비전의 지점명·주소·운영시간을 검사한다. 공백만 입력하면 공개하지 않으며 편집값을 보존한다. 이미지 없는 시설 항목은 초안에 남기고 공개 갤러리에서 제외한다.
- 실제 홈 `/`와 새 `/branches/`는 현재 공개 리비전에서 지점과 시설을 함께 복원한다. 공개 본점 `main`은 첫 순서·새 방문 기본값이며 URL/같은 탭의 유효한 명시 선택이 우선한다. 본점 비공개·알 수 없는 ID는 첫 유효 공개 지점으로 복구한다. 추가 지점은 공개 표시 순서·안정적인 ID 순이다.
- 홈·지점 안내·소식·팝업의 지점 목록과 연결 URL을 통일했다. 사진·트레이너·연락수단이 없으면 해당 영역/버튼을 숨긴다. 마지막 공개 지점도 철회 가능하며 0곳이면 준비 중 안내·브랜드/소식 탐색을 남기고 공통·모바일 문의를 숨긴다.
- 브랜드·소식·지점 시설의 공유 이미지 사용처를 함께 판정한다. 원본·초안·미사용 파일과 권한 없는 미리보기는 보호하며 마지막 공개 사용처 철회 후 새 익명 이미지 요청을 차단한다. 지점 편집에도 권한·CSRF·잠금·오래된 폼 거부·동시 저장 행 잠금을 적용했다.
- 승인된 A 화면의 CSS·탭·시설 자동 슬라이드를 재사용했다. 긴 지점명 줄바꿈과 선택 탭의 가로 위치 보정을 추가했다. 원본 HTML/스크립트/이전 캡처는 재생성하지 않았다. JS가 없으면 모든 공개 지점의 주소·운영시간·기본 링크가 남는다.

`0004_branch_facility`를 로컬 DB에 적용했다. `bootstrap_branch_review`를 두 번 실행해 본점·예시점 2곳, 시설 6항목, 공유 사진 3장을 준비하고 두 번째 실행의 콘텐츠 재생성 생략을 확인했다. 이름·주소·운영시간·연락처·가상 사진은 기존 `prototype/branch-data.js`의 임시 자료를 재사용했다. 신규 트레이너·운영 사실은 추가하지 않았다.

## 변경 파일

작업 전 해시/소스 사본과 대조한 **기존 파일 23개 수정·구현 파일 11개 추가**다. 정확한 목록은 [changed-files.json](changed-files.json)에 있다. 시작 전부터 대부분의 프로젝트가 미추적 상태였으므로 현재 Git status 전체를 이번 변경으로 취급하지 않는다.

| 파일 묶음 | 변경 내용 |
| --- | --- |
| `news/models.py`, `migrations/0004_branch_facility.py` 신규 | `Branch`·`FacilityImage`, 공개 필수값·식별자 고정·클러스터 리비전·권한 미리보기 |
| `news/wagtail_hooks.py`, `publication.py` | 지점 관리자·편집 충돌/철회·삭제 제한, 공개 리비전/시설 이미지 사용처 판정 |
| `news/branches.py` 신규, `config/urls.py`, `context.py`, `views.py`, `middleware.py` | 실제 지점 URL·공통 동적 목록·선택·캐시 경계 |
| `news/home.py`, `static/news/context.js`, `static/news/branches.css` 신규 | 홈 공개 지점 연결, 동선·문의 채널·가로 탭 위치·긴 이름 |
| `templates/news/branch_browser.html`, `branch_navigation.html`, `branches.html`, `facility_gallery.html` 신규 | 공통 지점/시설 렌더링, 0곳/0장, JS 대체 정보 |
| `templates/news/base.html`, `list.html`, `detail.html`, `popup.html`, `popup_entry.html` | 실제 홈·지점·소식·팝업 URL와 선택 유지, 없는 문의 숨김 |
| `management/commands/bootstrap_branch_review.py` 신규 | 승인된 임시 2지점 자료·기존 데이터 보존·멱등 초기화·지점 권한 4개 추가 |
| `tests/test_branches.py`, `test_branch_browser.py` 신규, `test_concurrency.py`, `test_brand.py`, `test_publication.py`, `scripts/review-branches.mjs` 신규 | 지점 공개/권한/미디어/재공개·실제 동시 요청·관리자/화면 검수, 기존 정적 경로 기대값 갱신 |
| 루트/백엔드 `README.md`, `docs/PRD.md`, `IMPLEMENTATION-PLAN.md`, `WORKFLOW.md`, `prototype/DESIGN.md` | 현재 구현·확정 정책·역할·검수 명령·승인 경계 정합성. PRD §7의 과거 본점 정책 문구도 FR-02와 일치시킴 |
| 새 `backend/review/branches/` | 이번 JSON·로그·캡처·실패 이력·보존 대조·보조 검수 스크립트 |

## 이번에 실행한 검사

아래 명령은 별도 표기가 없으면 `backend/`에서 실행했다. 전체 서버 검사는 마지막 실행 뒤 재공개 테스트 1개를 추가했으므로, 현재 소스 전체 67개를 한 번에 재실행한 결과로 보고하지 않는다.

| 실제 실행 명령 | 결과와 근거 |
| --- | --- |
| 작업 전 `uv run python manage.py test news.tests --noinput --verbosity 1` | 51개 중 50개 성공·브랜드 브라우저 1개 생략. [기준 로그](logs/baseline-tests.txt) |
| `uv run python manage.py test news.tests --noinput --verbosity 1` | 마지막 전체 실행 66개 중 **64개 성공·옵트인 브라우저 2개 생략**, 55.604초. 지점 서버 12개와 실제 동시 초안/공개 요청 2개 포함. 기존 소식·브랜드·팝업 회귀 포함. [로그](logs/server-tests-final.txt) |
| `uv run python manage.py test news.tests.test_branches.BranchTests.test_withdraw_and_republish_restore_only_the_requested_revision_and_media --noinput --verbosity 2` | 이후 추가한 재공개 **1개 성공**. 철회 시 0곳/이미지 404 → 새 리비전 재공개 시 시설 복원/이미지 200/지점 1행 유지. [로그](logs/republish-final.txt) |
| `Y3GYM_RUN_BRANCH_BROWSER=1 uv run python manage.py test news.tests.test_branch_browser --noinput --verbosity 1` | 별도 테스트 DB·임시 미디어/계정의 실제 Wagtail **1개 테스트·11개 흐름 PASS**, 55.365초. [로그](logs/browser-final.txt), [JSON](checks.json) |
| `node scripts/review-branches.mjs --live-read-only` | 실행 앱 `8768`의 공개 화면 **5개 흐름 PASS**, JS 오류 0. 터치·키보드·자동 이동·JS 없는 탐색 포함. [로그](logs/live-browser-touch.txt), [JSON](live/checks.json) |
| `node review/branches/verify-layout.mjs` | 홈/지점 안내 × 1440/900/375px **6개 측정 PASS**. 실제 카드 너비로 각각 3/2/1장을 확인, 페이지 가로 넘침 0. 동작 줄이기 상태에서 측정. [로그](logs/layout-final.txt), [JSON](layout-checks.json) |
| 아래 팝업 읽기 전용 회귀 명령 4개 | 위치 8·크기 10·재노출 8·예외 3 = **29개 항목 PASS**. 위치·크기는 화면이 표시되는 Chromium의 실제 창 경계 사용. [실행 종료코드](popups/runs.json), [위치](popups/position/checks.json), [크기](popups/sizing/checks.json), [재노출](popups/revisit/checks.json), [예외](popups/edges/edge-checks.json) |
| `uv run python manage.py check` / `makemigrations --check --dry-run` / `showmigrations news` | 시스템 오류 없음·모델 변경 없음·0004 적용 확인. [check](logs/check-final.txt), [dry-run](logs/migrations-dry-run-final.txt), [적용 상태](logs/migration-final.txt) |
| `uv run ruff check .` / `uv run ruff format --check news config scripts` | lint 통과·대상 32파일 포맷 통과. [lint](logs/lint-final.txt), [format](logs/scoped-format-final.txt) |
| `uv run ruff format --check .` | **실패:** 작업 전부터 있던 `review/workflow-01/verify.py` 1개. 해당 파일의 작업 전/후 해시 동일. 이전 검수를 수정하지 않음. [로그](logs/global-format-final.txt), [보존 근거](file-preservation.json) |
| 루트에서 `node backend/review/branches/verify-documents.mjs`, `git diff --check` | 현재 문서의 파일/앵커·명령 정의·실제 공개 경로·정책 정합성 검사. [결과](document-checks.json), [tracked diff 공백 검사](logs/diff-check.txt). 미추적 변경 파일의 공백은 별도 스크립트에서 확인 |

팝업 회귀는 기존 스크립트를 재사용하면서 새 출력 폴더만 지정했다. 기존 DB 설정·검수 폴더를 덮어쓰지 않았다.

```bash
Y3GYM_POPUP_REVIEW_DIR=review/branches/popups/position node scripts/review-popup-position.mjs
Y3GYM_POPUP_REVIEW_DIR=review/branches/popups/sizing node scripts/review-popup-sizing.mjs
Y3GYM_POPUP_REVIEW_DIR=review/branches/popups/revisit node scripts/review-popup-revisit.mjs
Y3GYM_POPUP_REVIEW_DIR=review/branches/popups/edges node scripts/review-popup-edges.mjs
```

11개 브라우저 흐름은 관리자 초안 재진입·공개본 유지, 실제 iframe 미리보기/명시적 공개, 신규 미완성 초안/공개 필수값, 3번째 지점과 홈/소식 연결, 실제 사진 선택기/중심/1장, 8개 탭/긴 탭 이름, PC·모바일 캡처, 자동 transform 변화, 동작 줄이기/키보드, CDP 터치 스와이프, JS 없는 탐색, 마지막 철회/0곳을 확인했다. 서로 연결된 동작을 JSON의 11개 항목으로 묶었다. 터치는 Chromium 입력 에뮬레이션이며 실제 휴대폰 검증은 아니다. 기본 서버 검사에서 생략한 브랜드 브라우저 검사는 이번에 별도 재실행하지 않았다.

## 직접 확인 경로와 캡처

- [실제 홈 — 본점](http://localhost:8768/?branch=main), [실제 홈 — 예시점](http://localhost:8768/?branch=second)
- [실제 지점 안내](http://localhost:8768/branches/?branch=second), [선택 유지 소식](http://localhost:8768/news/?branch=second)
- [CMS 지점·시설](http://localhost:8768/admin/snippets/news/branch/) → 본점/예시점 편집 → 시설 사진·초안·미리보기·공개. 로그인 정보는 `backend/.local-credentials`에만 있으며 문서에 출력하지 않는다.

쓰기 검수의 관리자 캡처는 임시 테스트 서버/DB에서 촬영했다. 실행 DB에서는 공개 경로를 읽기 전용으로 확인했으며 관리자 로그인/저장을 수행하지 않았다. 아래 `live/`는 실행 DB에 남은 원래 본점/예시점이고, 루트 캡처는 임시 검수에서 수정한 자료다. 팝업을 숨기는 촬영용 상태는 독립 브라우저 문맥에만 기록했다.

| 대상 | PC | 모바일 |
| --- | --- | --- |
| 실행 앱 홈 | [첫 화면](live/home-desktop-first.png) · [전체](live/home-desktop-full.png) | [첫 화면](live/home-mobile-first.png) · [전체](live/home-mobile-full.png) |
| 실행 앱 지점 안내 | [첫 화면](live/branches-desktop-first.png) · [전체](live/branches-desktop-full.png) | [첫 화면](live/branches-mobile-first.png) · [전체](live/branches-mobile-full.png) |
| 임시 DB 관리자 | [목록](branch-list.png) · [편집 전체](branch-editor-desktop.png) · [초안 미리보기](branch-draft-preview.png) | [편집 첫 화면](branch-editor-mobile.png) |
| 보조 상태 | [태블릿 홈](home-tablet.png) · [태블릿 지점](branches-tablet.png) | [8개 탭·긴 이름](many-tabs-long-name-mobile.png) · [0곳](no-public-branches-mobile.png) |

개발자가 실행 앱 홈 PC 첫 화면·지점 모바일 전체·많은 탭 모바일·관리자 모바일 캡처를 직접 열어 확인했다. 자동 검사의 가로 넘침 통과와 별개로 관리자 모바일 편집 영역이 좁다. 관리자 사용성 검토 항목으로 남기며 사용자 승인 완료로 보고하지 않는다.

## 실패 이력과 보정

- 첫 지점 서버 검사에서 클러스터 `FakeQuerySet.delete()`를 사용한 테스트 오류, 공개 후 갱신하지 않은 공유 이미지 테스트 객체 오류가 있었다. 실제 자식 테이블 삭제와 갱신된 객체로 검사하도록 수정했다. 실제 소식 breadcrumb에 남은 `8767` 링크도 발견해 `/`로 수정했다. [초기 로그](logs/branch-tests-attempt-1.txt)
- 첫 전체 서버 검사에서 이전 정적 예시점의 존재를 가정한 소식 테스트가 실패했다. 실제 공개 지점 fixture를 생성하고 유효 공개 지점 fallback을 검사하도록 갱신했다. [로그](logs/server-tests-attempt-1.txt)
- 브라우저 1차는 미리보기 iframe 이름을 잘못 가정했고, 2차는 공개 후 편집 화면에 남는다고 가정해 시간 초과했다. 실제 iframe과 공개 후 목록 이동을 확인해 검수 도구를 수정했다. [1차 JSON/캡처](attempt-1/checks.json), [2차 JSON/캡처](attempt-2/checks.json), [1차 로그](logs/browser-attempt-1.txt), [2차 로그](logs/browser-attempt-2.txt)
- 보정 후 3차 10흐름은 통과했다. 이후 선택 탭의 가로 노출 검증과 터치 항목을 추가한 마지막 실행에서 11흐름이 통과했다. [3차 JSON](attempt-3/checks.json), [마지막 JSON](checks.json)
- 실제 앱 첫 읽기 전용 검수는 검수용 초기 스크립트가 팝업의 `about:blank`에서 localStorage에 접근해 실패했다. 동일 origin에서만 초기 스크립트가 동작하도록 제한했다. 이후 4흐름, 터치 추가 후 5흐름이 통과했다. [실패 JSON/캡처](live/attempt-1/checks.json), [4흐름 이력](live/attempt-2/checks.json), [마지막 JSON](live/checks.json)
- 문서 검사 도구 첫 실행은 유효한 `docs/legacy/` 디렉터리 링크를 파일이 아니라는 이유로 거부했다. 파일과 디렉터리를 모두 허용하도록 도구를 수정한 뒤 통과했다. [초기 결과](document-attempt-1.json), [최종 결과](document-checks.json)

실패 JSON·캡처·로그는 삭제하지 않았다. 루트의 `failure-*.png`는 해당 실패 시점의 파일이며 마지막 정상 화면으로 취급하지 않는다.

## DB·파일·Git 보존

[DB 대조](db-preservation.json)는 작업 전/최종 기존 행의 정규화 JSON SHA-256을 비교했다. 기존 브랜드 1·소식 22·팝업 설정 10·계정 2·이미지 36·변환본 99·리비전 65행을 포함해 **변경/삭제된 기존 행 0**이다. 추가분은 지점 2·시설 6·이미지 3·변환본 3·리비전 2와 기존 편집자 그룹의 지점 권한 4개다. [초기화 직후 대조](seed-preservation.json)와 최종 대조를 구분한다.

[파일 대조](file-preservation.json)는 작업 전 588파일을 기준으로 원본 프로토타입/이전 캡처 185개, 기존 백엔드 검수 193개, 비공개 미디어 135개, 비밀 파일 2개, 의존성/버전 파일 5개 및 Git index의 바이트 보존을 확인했다. `prototype/DESIGN.md`만 허용된 문서 수정 예외다. 비교 그룹은 서로 겹칠 수 있으므로 합산하지 않는다. 새 지점 미디어·이번 검수 자료만 추가했다.

원본 해시/소스 사본과 DB 행 해시는 접근 제한된 로컬 `/tmp/y3gym-m2-2-5ud5sjy6/`에 있다. 문서·새 JSON에는 비밀번호·DB 접속값·원본 행 값을 싣지 않았다. 최종 DB 스냅샷 명령은 `Y3GYM_SNAPSHOT_LABEL=final uv run python manage.py shell -c "exec(open('/tmp/y3gym-m2-2-db-snapshot.py').read())"`이다. 기존 사용자 콘텐츠·비밀·파일을 초기화하지 않았다. 커밋·푸시·배포·외부 변경을 실행하지 않았다.

## 남은 확인과 범위

- 테스트 담당의 독립 검증, 설계의 개발 보고 검토, 사용자 시각/관리자 사용성 확인은 아직 완료되지 않았다.
- 실제 휴대폰·Whale·Chromium 외 브라우저, 운영 권한 구성·배포/캐시·외부 저장소·백업/복구는 미검증이다. 기존 Whale 도구 연결 실패를 이번 Chromium 결과로 해결한 것으로 취급하지 않는다.
- 이전 M1의 Wagtail 중복 이미지 업로드 탭 오류는 이번에 재현하지 않았다. 시설의 기존 사진 선택 흐름은 통과했으나 해당 업로드 오류 해결 근거는 없다.
- 실제 브랜드/지점/시설/트레이너 자료, 트레이너 CMS, 홈 최근 소식 CMS 연결, 실제 전화/카카오톡/지도, 본점 교체·지점 삭제/복원·예약게시를 구현하지 않았다. 화면 자료는 계속 임시 표시다.
- 전체 포맷 검사의 기존 파일 1개 실패와 관리자 모바일 폭은 위에 기록했다. 로컬 구현·자체 검사 통과를 전체 제품 완료나 출시 승인으로 확대하지 않는다. 이번 M2-2 보고 제출 후 다음 지시를 기다린다.
