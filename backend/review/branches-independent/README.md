# M2-2 지점·시설 독립 검증

검증일: 2026-10-10 한국 시간. **판정: 수정 필요(FAIL).** 기존 전체 서버 검사와 주요 화면 흐름은 통과했지만, 공개 철회가 동시에 저장된 새 초안을 이전 상태로 덮어쓰는 결함을 재현했다. 문서에 안내한 브랜드 브라우저 회귀도 지점 초기 데이터 누락으로 실패한다. 자동 검사·이번 독립 검증·사용자 시각/관리자 사용성 승인은 구분한다.

작업 루트는 `/home/shlee/Workspace/ai/01.codex/y3gym_v2`다. AGENTS·README·PRD·구현 계획·디자인·WORKFLOW·백엔드 안내와 실제 변경 코드를 읽고 대조했다. 이전 개발자의 PASS나 과거 캡처를 이번 재실행 결과로 합산하지 않았다. 제품/정책 문서·원본 프로토타입·기존 검수·실행 DB를 수정하지 않았으며 Git index·commit·push·배포도 변경하지 않았다. 이 폴더에만 새 검수 도구·로그·캡처·보고를 추가했다.

## 수정이 필요한 문제

### F01 / P1 — 공개 철회가 동시에 저장된 최신 초안을 덮어씀

- **요구 근거:** [구현 계획 M2-2 공개 경계](../../../docs/IMPLEMENTATION-PLAN.md#이번-단위-m2-2-지점시설-관리)의 행 잠금·오래된 폼·동시 저장 보호, 기존 콘텐츠 보존 요구.
- **관련 파일:** [BranchUnpublishView](../../news/wagtail_hooks.py) 113~117행. 설치된 `wagtail.admin.views.generic.models.UnpublishView.get_object`는 전달받은 `queryset` 인자를 사용하지 않고 모델을 직접 조회한다. 따라서 현재 `select_for_update()` QuerySet은 실행되지 않는다.
- **재현 절차:** 공개 지점의 철회 요청이 기존 객체를 읽은 직후 대기 → 다른 요청으로 같은 지점의 주소를 바꿔 초안 저장 → 저장 완료 뒤 철회 요청을 진행한다. 새 [재현 검사](withdrawal_concurrency.py)는 실제 조회 뒤에 동기화 대기만 추가하며, 제품 로직이나 객체 값을 인위적으로 바꾸지 않는다. Django 별도 테스트 DB의 실제 두 HTTP 요청으로 검사했다.
- **재현 명령:** `backend/`에서 `uv run --locked python review/branches-independent/withdrawal_concurrency.py`. 종료 코드 1이 현재 결함의 예상 재현 결과다. 기존 결과 파일이 있으면 새 이름으로 보존한다.
- **기대:** 철회 후 공개 상태는 false이고, 이미 성공한 새 초안의 주소·최신 리비전 포인터는 유지된다.
- **실제:** 초안 저장과 철회 모두 HTTP 302. 새 리비전 2가 만들어졌지만 `latest_revision_id`는 1로 되돌아가고 현재 주소도 이전 값이다. 철회 조회에 `news_branch ... FOR UPDATE`가 없다. 리비전 2의 기록 자체는 남아 있지만 다음 일반 편집의 기준 초안은 이전 내용으로 돌아간다.
- **근거:** [요청·DB 결과](withdrawal-concurrency-result.json), [실행 로그](withdrawal-concurrency.txt), [명령·종료 코드](withdrawal-concurrency.json).
- **영향/후속:** 저장 성공을 확인한 운영자의 수정이 현재 초안에서 소실된다. 실제 철회 조회에 행 잠금이 적용되도록 수정하고 초안 저장/공개와 철회의 교차 요청을 재검증해야 한다. 이번 검증에서는 제품 코드를 수정하지 않았다.

### F02 / P2 — 안내된 브랜드 브라우저 회귀 명령이 실패

- **요구 근거:** 이번 작업의 기존 브랜드 브라우저 회귀 수행 요구, [FR-02](../../../docs/PRD.md#fr-02-지점시설)의 공개 지점 0곳일 때 문의 숨김 정책, 문서 명령 재현 가능성.
- **관련 파일:** [브랜드 브라우저 테스트](../../news/tests/test_brand_browser.py) 25~26행, [브랜드 검수 스크립트](../../scripts/review-brand-home.mjs) 117~118행과 127행.
- **재현 명령:** `backend/`에서 `Y3GYM_RUN_BRAND_BROWSER=1 Y3GYM_BRAND_REVIEW_DIR=review/branches-independent/brand-repro-new uv run --locked python manage.py test news.tests.test_brand_browser --noinput --verbosity 2`. 재실행 시 출력 폴더는 새 이름을 사용한다.
- **기대:** 검수가 필요한 공개 지점 fixture를 준비하거나 지점 0곳의 유효한 조건을 검사해 브랜드 흐름을 끝까지 수행한다.
- **실제:** 테스트는 소식·브랜드만 초기화하므로 공개 지점이 0곳이다. 제품은 요구대로 문의 바를 숨기지만 스크립트는 바의 표시를 필수로 검사해 `boundingBox() == null`에서 실패한다. 뒤에도 공개 지점 패널이 2개라는 고정 기대가 남아 있다.
- **근거:** [단독 실행 로그](brand-browser-separate.txt), [실패 JSON](brand-browser-separate/result.json), [실행 정보](brand-browser-separate.json).
- **구분:** 제품의 문의 숨김을 결함으로 판정한 것이 아니다. 검수 준비와 기대값의 회귀 문제다. 제품·기존 테스트 소스는 그대로 두고 [별도 임시 fixture 검사](brand_fixture_regression.py)에서 공개 지점 2곳을 추가하자 기존 브랜드 스크립트의 7개 흐름이 통과했다. [보조 결과](brand-browser-with-branches/result.json)·[로그](brand-fixture-adapted.txt)는 원래 명령의 실패를 대체하지 않는다.

## 이번에 실제 실행한 검사

아래 명령의 cwd는 `backend/`다. 각 `*.json` 실행 기록에는 실제 명령·종료 코드·경과 시간이 있고 같은 이름의 `*.txt`에는 출력을 보존했다. [run.py](run.py)는 이미 존재하는 로그에 덮어쓰지 않는다. 성공한 재실행과 초기 실패를 모두 보존했다.

| 검사와 실제 명령 | 이번 결과 / 근거 |
| --- | --- |
| `uv run --locked python manage.py test news.tests --noinput --verbosity 2` | **67개 중 65개 성공·옵트인 2개 생략**, 테스트 시간 53.824초. 신규 재공개 검사 포함. [로그](server-tests.txt)·[실행](server-tests.json) |
| 두 옵트인 플래그·각 새 출력 경로로 `manage.py test news.tests.test_branch_browser news.tests.test_brand_browser --noinput --verbosity 2` | **2개 중 지점 1개 성공·브랜드 준비 1개 ERROR**. 지점 브라우저 **11개 흐름 PASS**·JS 오류 0. [지점 JSON](branch-browser/checks.json)·[합동 로그](browser-regressions.txt) |
| `Y3GYM_RUN_BRAND_BROWSER=1` 및 새 출력 경로로 브랜드 테스트 단독 실행 | **1개 FAIL**, F02. [로그](brand-browser-separate.txt) |
| `uv run --locked python review/branches-independent/brand_fixture_regression.py` | 임시 지점 fixture를 추가한 보조 브랜드 **1개 테스트·7개 흐름 PASS**. [로그](brand-fixture-adapted.txt)·[JSON](brand-browser-with-branches/result.json) |
| `uv run --locked python review/branches-independent/test_independent.py`와 새 `Y3GYM_INDEPENDENT_PROBE_DIR` | 마지막 실행 **4개 PASS**: 필수값별 공백 공개 거부, 철회 권한/CSRF, 지점 0곳의 홈·지점·소식·팝업, 모바일/세 번째 지점 맥락. 브라우저 세부 **11항목 PASS_WITH_WARNINGS**. [로그](independent-mobile-final.txt)·[JSON](mobile-probe-final/checks.json) |
| `uv run --locked python review/branches-independent/withdrawal_concurrency.py` | **1개 FAIL**, F01. [결과](withdrawal-concurrency-result.json) |
| `Y3GYM_BRANCH_REVIEW_DIR=review/branches-independent/live node scripts/review-branches.mjs --live-read-only` | 실행 앱 **5개 흐름 PASS**, JS 오류 0. PC/모바일 캡처·자동 이동·동작 줄이기/키보드·CDP 터치·JS 없는 탐색. [JSON](live/checks.json)·[로그](live-browser.txt) |
| `node review/branches-independent/verify-layout.mjs` | 홈/지점 × 1440/900/375px **6개 PASS**, 시설 3/2/1장·가로 넘침 0. [JSON](layout-checks.json)·[로그](responsive-layout.txt) |
| `Y3GYM_POPUP_REVIEW_DIR=review/branches-independent/popups/revisit node scripts/review-popup-revisit.mjs` | **8개 PASS**, 일반 닫기 재노출·재방문·창 재사용·한국 시간 오늘 숨김/만료·차단 복구. [JSON](popups/revisit/checks.json)·[로그](popup-revisit.txt) |
| `Y3GYM_POPUP_REVIEW_DIR=review/branches-independent/popups/edges node scripts/review-popup-edges.mjs` | **3개 PASS**, 짧은 화면·포커스·크기 전환·세션 저장소 제한. [JSON](popups/edges/edge-checks.json)·[로그](popup-edges.txt) |
| `uv run --locked python manage.py check` | PASS, 시스템 오류 없음. [로그](system-check.txt) |
| `uv run --locked python manage.py makemigrations --check --dry-run` | PASS, 미생성 모델 변경 없음. [로그](migration-check.txt) |
| `uv run --locked ruff check .` | 최종 PASS. [로그](lint-complete.txt). 최초 검사에서 이번 검증 도구의 미사용 import 1개를 지적해 새 도구만 수정했다. [초기 로그](lint.txt) |
| `uv run --locked ruff format --check news config scripts` | PASS, 제품 범위 32개 파일. [로그](scoped-format.txt) |
| `uv run --locked ruff format --check .` | **FAIL**, 기존 `review/workflow-01/verify.py` 1개만 해당. 이전 파일은 그대로 보존했다. [로그](global-format-final.txt) |
| `node review/branches-independent/verify-documents.mjs`, `git diff --check` | PASS. 현재 문서 링크 **204개·앵커 12개**, 변경 34파일 공백/충돌 표시·명령·실제 공개 URL·로그인 필요 경계. [JSON](document-checks.json)·[로그](documents.txt) |

서로 다른 실행·재실행·브라우저 세부 흐름 수를 하나의 테스트 수로 합산하지 않는다. 제품 전체가 통과했다는 판정도 하지 않는다. 문서/레이아웃 도구는 개발 도구를 이 폴더에 복사해 새 출력 경로로 실제 재실행했다. 추가 경계·모바일·동시 철회 검사는 이번 검증자가 작성했다.

## 기능·경계별 확인

- **본점/선택:** 전체 서버의 본점 우선·공개 순서·무효/철회 ID fallback 검사가 통과했다. 추가 브라우저에서는 3번째 지점의 홈·지점·소식 목록·소식 상세·PC 팝업 URL/문의 채널과 같은 탭 재방문을 실제 확인했다. 서로 다른 지점으로 연결되지 않았다.
- **초안/공개:** 지점+시설의 동일 공개 리비전 복원, 시설 삭제/재정렬/새 사진/주소/순서의 수정 초안 분리, 권한 미리보기, 명시 공개·철회·재공개가 기존 13개 지점 서버 검사 및 실제 관리자 11흐름에서 통과했다. 다만 F01의 철회 교차 동시성은 별도로 실패했다.
- **권한/미디어:** 기존 전체 검사에서 원본·초안·관리자 썸네일 권한, 브랜드/소식/지점 공유 이미지의 마지막 공개 사용처 철회, 모델 권한·CSRF·편집 잠금·오래된 폼, 실제 동시 초안/공개가 통과했다. 추가 검사에서도 필수값 각각의 공백 입력, 철회 공개 권한·CSRF를 확인했다.
- **선택 콘텐츠/0곳:** 사진/트레이너/없는 채널 숨김, 마지막 공개 지점 철회, 0곳 준비 중과 문의 숨김·브랜드/소식 탐색 유지가 통과했다. 추가로 소식 상세와 팝업의 0곳 동작도 검사했다.
- **공개 UI:** 홈/지점 첫 화면·전체·900px 2열을 캡처하고 PC 첫 화면·모바일 지점 전체·관리자 모바일 안정 상태·공개 조작 화면을 직접 열어 확인했다. 자동 슬라이드·동작 줄이기·키보드·터치 에뮬레이션·JS 없는 탐색은 실제 실행 결과다. 사용자 시각 승인을 대신하지 않는다.

## 관리자 모바일 검증

개발 캡처의 큰 왼쪽 여백을 보고 추가 검증했다. A는 **처음부터 375×812인 새 컨텍스트·새 로그인·직접 편집 URL**, B는 **1440px 편집 후 375px로 축소**다. B의 즉시/600ms 후/리로드/미리보기 열림·닫힘/사이드바 전환을 구분했다.

최종 실행에서 A와 B의 안정 상태 모두 이름 입력은 **x=20px, 폭=335px**, 페이지 가로 넘침은 없다. B 축소 직후는 폭 226.45px(이전 시도 141.59px)였고 600ms 후 복구됐다. 미리보기/사이드바 상태를 닫은 뒤 양쪽 모두 실제 이름·주소·시설 제목 입력, 사진 선택기·시설 정렬, 초안 저장·재진입·공개를 완료했다. 따라서 지속적으로 편집을 막는 결함은 재현되지 않았다. 즉시 축소 캡처는 정상 모바일 화면의 근거로 쓰지 않으며 전환 중간 상태와 관리자 사용성 경고로 남긴다. [측정/동작 결과](mobile-probe-final/checks.json)

| 새 캡처 | 링크 |
| --- | --- |
| 실행 홈 PC / 모바일 | [PC 첫 화면](live/home-desktop-first.png) · [PC 전체](live/home-desktop-full.png) · [모바일 첫 화면](live/home-mobile-first.png) · [모바일 전체](live/home-mobile-full.png) |
| 실행 지점 PC / 모바일 | [PC 첫 화면](live/branches-desktop-first.png) · [PC 전체](live/branches-desktop-full.png) · [모바일 첫 화면](live/branches-mobile-first.png) · [모바일 전체](live/branches-mobile-full.png) |
| 900px 두 열 | [홈](home-tablet.png) · [지점](branches-tablet.png) |
| 관리자 A/B | [A 새 모바일](mobile-probe-final/A-fresh-mobile-direct.png) · [B 축소 직후](mobile-probe-final/B-desktop-resize.png) · [B 600ms 후](mobile-probe-final/B-desktop-resize-settled.png) · [리로드](mobile-probe-final/B-mobile-reload.png) |
| 실제 조작 | [A 사진 선택](mobile-probe-final/A-image-chooser.png) · [A 저장](mobile-probe-final/A-save-controls.png) · [B 공개](mobile-probe-final/B-publish-controls.png) · [미리보기](mobile-probe-final/B-preview-open.png) · [사이드바](mobile-probe-final/B-sidebar-toggled.png) |

한글 이름 캡처의 URL 파일명이 인코딩되어 ASCII 링크 사본 6개를 같은 폴더에 추가했다. 원본을 덮어쓰지 않았고 바이트는 동일하다. [원본/사본 해시](mobile-probe-final/screenshot-aliases.json)

## 실패·경고 이력

- **합동 브라우저 fixture 오류:** 두 StaticLiveServerTestCase를 같은 명령으로 실행하면 첫 클래스의 flush 뒤 Wagtail Collection root가 없어 두 번째 초기화가 `collection_id NULL`로 실패한다. 이는 P3 테스트 격리 경고이며 [합동 로그](browser-regressions.txt)에 보존했다. 문서의 단독 브랜드 명령 실패 F02와 구분한다.
- **검증 도구 초기 실패:** [1차 추가 검사](independent-boundaries-and-mobile.txt)는 기존 사진 선택기의 숨겨진 빈 상태 버튼을 눌러 시간 초과했다. [2차](independent-mobile-attempt-2.txt)는 모바일에서 숨겨진 PC 사이드바 버튼을 선택했다. 실제 표시되는 사진 교체 메뉴·모바일 사이드바 버튼으로 새 도구만 고친 뒤 마지막 실행 4개가 통과했다. 초기 캡처/JSON은 `mobile-probe/`와 `mobile-probe-attempt-2/`에 보존했다. 이 실패들을 제품 결함으로 보고하지 않는다.
- **전체 포맷:** 기존 WORKFLOW 검증 파일 1개 실패는 숨기거나 범위 밖 코드를 고치지 않았다. 새 검증 Python 도구는 포맷/최종 lint에 문제가 없다.
- **사용성 승인:** 모바일 조작 성공은 최종 관리자 사용성 승인이나 한국어 IME 검증이 아니다.

## DB·파일·Git 보존

[snapshot.py](snapshot.py)는 승인된 `127.0.0.1:55438`에서 **READ ONLY 트랜잭션**으로 행 값을 읽어 정규화 SHA-256만 저장했다. 비밀번호·접속 비밀·원본 행 값은 출력하지 않았다. 현재 실제 DB에 대해 검증 전/후를 직접 취득했다. 계정 로그인·업로드·저장/공개 등 쓰기는 모두 Django 별도 테스트 DB·임시 미디어·임시 계정에서만 수행했다. 실행 앱 8768과 팝업 검사는 독립 브라우저 문맥에서 읽기 전용으로 실행했다.

- 이번 독립 검사 전후 **기존 파일 707개 동일**, 비공개 미디어 141개와 비밀 설정/계정 파일 2개 포함. 새 파일은 이 독립 검수 폴더 안에만 있다.
- 실제 앱 DB **56개 테이블의 행 수/행 해시 동일**, Git index SHA-256 동일. [보존 결과](preservation-result.json)
- 개발 전 588개 파일 기록과 현재 해시를 독립 대조한 수정 파일은 개발이 보고한 기존 23개와 일치한다. 개발 전 기존 DB 행의 변경/삭제는 0이며 개발 최종 DB 스냅샷과 현재값도 같다. [대조 요약](developer-baseline-comparison.json)
- 과거 개발 전 스냅샷의 취득 시점·완전성은 개발 제공 자료에 의존한다. 이번 검증 전후 값과 현재 값 재계산은 독립 수행했다. 이 구분 없이 과거 보존 주장을 확장하지 않는다.

## 미구현·미결정·미검증과 후속

트레이너 CMS·홈 최근 소식 CMS 연결·실제 전화/카카오톡/지도·본점 교체·지점 삭제/복원·운영 배포는 승인 범위 밖이거나 미구현이다. 운영 자료·운영 권한·배포 저장소/캐시/백업은 확정·검증하지 않았다. Whale 및 Chromium 외 브라우저·실제 휴대폰·한국어 IME·기존 Wagtail 중복 이미지 업로드 오류도 이번에 확인하지 않았다.

native 팝업 위치/크기 코드는 개발 전과 동일하며 이번 수정은 공통 지점 목록/연결 맥락이다. 이번에는 재노출·차단·숨김·모바일·지점 전달 회귀를 실행했고 화면이 표시되는 브라우저의 native 좌표·창 경계는 재실행하지 않았다. 과거/개발의 29개 PASS를 이번 결과로 합산하지 않는다.

F01의 동시성 결함과 F02의 공식 회귀 준비를 수정한 뒤 관련 재검증이 필요하다. 이번 검증자는 수정이나 다음 기능을 시작하지 않고 설계의 보고 검토를 기다린다. 기계 판독용 문제 목록은 [findings.json](findings.json)에 있다.
