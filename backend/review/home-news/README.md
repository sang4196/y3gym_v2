# M2-4 홈 최근 소식 실제 공개 글 연결 — 개발 자체 검수

2026-10-10, local `/home/shlee/Workspace/ai/01.codex/y3gym_v2`. 설계가 명시적으로 지시한 M2-4만 구현했다. **로컬 구현·자체 검수와 독립 검증 대기**를 구분한다. 새 캡처의 사용자 시각 승인·관리자 사용성·실제 기기·운영 검증은 완료하지 않았다.

## 구현과 변경 파일

홈은 승인된 `prototype/index.html` 원본을 계속 읽고 최근 소식 행만 현재 공개 글 최대 5건으로 교체한다. 기존 `published_posts()`의 `live=True` + `live_revision.as_object()`와 최초 공개 최신순/동률 pk 순을 재사용한다. 수정·재공개로 최초 공개 날짜/순위를 올리지 않는다. 최초 등록 빠른순인 팝업 조회·기간·설정·닫기/오늘 숨김·창/모바일 동작은 바꾸지 않았다.

기존 A 행의 분류·h3 제목·선택 요약·날짜·구분선, PC/모바일 밀도·색상·Pretendard·간격을 그대로 쓴다. 0건이면 기존 “등록된 소식이 없습니다.” 안내를 표시한다. 상세는 `get_absolute_url()`, 모두 보기는 `/news/`이며 `data-news-link`/기존 `context.js`로 선택 지점을 유지한다. 행에는 `data-branch-page`를 중복 적용하지 않아 서버 href에 branch가 두 번 붙지 않는다. 목록의 all/1 초기값과 본문 복귀 동선은 유지한다. 관련 안내는 로컬 CMS 검토 자료로 교체했다. 브랜드 미리보기에도 다른 소식의 초안을 노출하지 않는다.

| 파일 | 변경 |
| --- | --- |
| [news/home.py](../../news/home.py) | 공개 소식 최대 5건 조회와 행 교체·임시 자료 안내 |
| [news/templates/news/home_news.html](../../news/templates/news/home_news.html) — 신규 | 기존 A 행과 빈 상태, 선택 요약·최초 공개 날짜·상세/지점 링크, 자동 이스케이프 |
| [news/tests/test_home_news.py](../../news/tests/test_home_news.py) — 신규 | 새 의미 있는 서버 검사 8개 |
| [news/tests/test_home_news_browser.py](../../news/tests/test_home_news_browser.py) — 신규 | 격리 DB·계정·미디어의 홈/탐색/철회·팝업 브라우저 검수 |
| [scripts/review-home-news.mjs](../../scripts/review-home-news.mjs) — 신규 | PC 1440·모바일 375·JS 없는 탐색·마지막 행 읽기/클릭·0건 및 실제 앱 읽기 검수 |
| [루트 README](../../../README.md), [backend README](../../README.md) | 현재 구현·재현·이전 Git 완료/이번 미커밋·한계 |
| [PRD](../../../docs/PRD.md), [구현 계획](../../../docs/IMPLEMENTATION-PLAN.md), [작업 흐름](../../../docs/WORKFLOW.md), [디자인 문서](../../../prototype/DESIGN.md) | 확정 정책·M2-4 구현/독립 검증 대기·기존 승인/검수/Git 이력 구분 |
| 이 `backend/review/home-news/` 폴더 — 신규 | 실제 명령·출력·실패·새 캡처·읽기/보존 근거. 기존 검수는 덮어쓰지 않음 |

새 모델/마이그레이션·관리 메뉴·CSS/제품 JavaScript·홈 전체 구조·팝업 설정/정책·자료·스택·외부 서비스를 추가하거나 변경하지 않았다. 실제 DB에 seed/검수 글을 쓰지 않았다.

## 이번에 실행한 검사

| 검사 | 실제 결과·근거 |
| --- | --- |
| 변경 전 관련 baseline | 소식 공개/브랜드/팝업 서버 **48 PASS**. [명령](baseline-server-command.json), [출력](baseline-server.txt) |
| 신규 홈 서버 | **8 PASS**. [명령](home-server-second-command.json), [출력](home-server-second.txt) |
| 전체 `news.tests` | **110 collected / 106 PASS / 4 opt-in SKIP**, exit 0. [이번 실행 출력](all-server.txt), [명령/종료 코드](all-server-command.json) 참조 |
| 기존 브랜드 브라우저 | **1 test / 7 flows PASS**. [기존 fixture 그대로 실행](browser-first/brand/result.json) |
| 기존 지점 브라우저 | **1 test / 11 flows PASS**. [지점 탐색·0곳·JS off 등](browser-first/branches/checks.json) |
| 신규 홈 + 팝업 브라우저 | **1 test PASS**, 홈 **8 flows** + 팝업 재방문 **8** + edges **3**. [명령](home-browser-third-command.json), [출력](home-browser-third.txt), [홈](browser-third/home/checks.json), [재방문](browser-third/popup-revisit/checks.json), [edges](browser-third/popup-edges/edge-checks.json) |
| 실제 8768 홈 읽기 | **7 flows PASS**, 로그인/관리자 쓰기 없음. [명령](live-home-third-command.json), [결과](live-third/home/checks.json) |
| 실제 공개 리비전 대조 | **PASS**, 기존 공개 6건의 최근 5건·날짜/제목/URL을 DB 읽기 전용 트랜잭션과 익명 HTTP로 대조. [결과](live-state-final.json), [명령](live-state-final-command.json) |
| Django check / migration dry run | **PASS / No changes detected**. [check](django-check-command.json), [migration](migration-check-command.json) |
| 전체 lint / 범위 format / Node syntax | **PASS**. [lint](lint-final-command.json), [format](format-final-command.json), [Node](node-final-command.json) |
| 전역 format | **기존 경고 W01 유지 / exit 1**. `review/workflow-01/verify.py` 1개만 지적, 원 파일 보존. [출력](format-global.txt) |

새 서버 검사는 0~6건(0/1/5/6+)·최초 공개와 등록 순서의 차이·정렬 동률·최초 날짜의 한국 시간 표시·수정 초안 제목/분류/요약/본문/사진/날짜 비노출·새 글 초안/리비전 없는 행 제외·현재 공개 snapshot·게시/철회/재공개·상세 404·HTML 이스케이프·빈 요약 숨김·선택/잘못된/0지점·JS 없이 유효한 서버 링크·브랜드 미리보기 공개 경계를 확인했다. 관리자 로그인 중인 일반 공개 URL도 포함했다.

기존 브랜드·지점 브라우저는 원본 공통 fixture 3파일을 그대로 실행하고 새 출력 폴더만 지정했다. 초기 합동 명령의 두 기존 브라우저 test는 통과했으나 신규 home test의 도구 import 오류 때문에 전체 명령은 FAIL이다. 이를 합동 전체 PASS로 보고하지 않는다. 신규 홈은 수정 후 별도 test로 PASS했으며 전체 서버 검사는 별도 실행이다.

팝업은 기존 재방문/edges 도구를 새 폴더에 복사하고 import/root/output/격리 origin guard만 조정했다. 기존 제품/검수 도구·단언은 보존한다. [원본 해시·복사 범위](popup-adaptation.json). 별도 테스트 DB의 공개 팝업 2건으로 PC 창 재사용·등록순·일반 닫기 재노출·오늘 숨김/만료·모바일 순차·차단 복구·짧은 화면·크기 전환·저장소 제한을 실행했다. `pageshow.persisted`는 합성 이벤트 분기 검사이며 실제 브라우저 BFCache 복원을 새로 입증한 것은 아니다.

## 실제 앱과 격리 시나리오·캡처

실제 앱에는 작업 전부터 공개 글 **6건**이 있었다. 익명 읽기 캡처의 최근 5건은 **21 → 22 → 17 → 18 → 2**이며 실제 공개 날짜는 모두 2026-10-10이다. 기존 제목에 포함된 과거 테스트 작성 시간이 그대로 보일 수 있으며 이 작업에서 새로 만든 영업 정보나 글이 아니다. [최종 DB/HTTP 대조](live-state-final.json)가 정확한 원본이다. 이전 [읽기 결과](live-state.json)의 `five_post_scenario` 문구는 통제한 fixture를 뜻하며, 실제 앱도 기존 6건 중 5건이 표시된다는 점을 최종 결과에 명확히 구분했다.

격리 브라우저는 임시 계정/미디어와 별도 test DB에 공개 6건·수정 초안·새 미공개 글·기간 내 팝업 2건을 준비했다. 홈에는 최근 5건만 표시하고 실제 관리자 UI로 6건을 철회해 0건 화면과 상세 404를 확인했다. 이 데이터·날짜·철회는 실제 앱 데이터와 구분한다.

| 대상 | 실제 화면 |
| --- | --- |
| 실제 앱 PC 1440 | [최근 소식](live-third/home/desktop-actual-news.png), [전체](live-third/home/desktop-actual-full.png) |
| 실제 앱 모바일 375×812 | [마지막 제목·요약이 문의 바 위에서 보이는 화면](live-third/home/mobile-actual-last-row-visible.png) |
| 실제 앱 모바일 긴 viewport | [5건 전체가 보이는 새 구역 캡처](live-third/home/mobile-actual-news-unobscured.png) |
| 격리 DB PC 5건 | [최근 소식](browser-third/home/desktop-five-news.png) |
| 격리 DB 모바일 5건 | [긴 viewport의 전체 행](browser-third/home/mobile-five-news-unobscured.png), [375×812 마지막 행](browser-third/home/mobile-five-last-row-visible.png) |
| 격리 DB 0건 | [PC](browser-third/home/desktop-empty-news.png), [모바일](browser-third/home/mobile-empty-news.png) |

설계의 캡처 보완 요청에 따라 **375×812에서 마지막 행으로 스크롤 → 제목/요약 끝이 문의 바 위인지 → 실제 hit target과 상세 클릭**을 단언했다. 실제 앱은 제목 top 407.25px·요약 bottom 450.94px·문의 바 top 740px이며 제목 hit target도 확인했다. 긴 화면 높이는 2686px이다. 긴 viewport에서는 문의 바가 푸터 아래에 위치해 행과 겹치지 않는지도 단언했다. 위 PC/모바일 5건·모바일 빈 상태 이미지를 개발이 직접 열어 확인했다. 기존 [짧은 구역 캡처](live-second/home/mobile-actual-news.png)의 마지막 요약 가림은 촬영 조건의 한계이며 UI 결함으로 처리하거나 레이아웃을 바꾸지 않았다. 기존 캡처는 그대로 보존한다.

## 실패 이력과 보완

[전체 실패/경고 기록](failure-history.json)과 실제 command JSON·원 로그를 보존했다. 신규 테스트의 popup JSON selector/수정 날짜 fixture, 신규 import 정렬, 새 복사 도구의 상대 import, 스크린샷 init의 opaque origin 저장소 접근, Wagtail mutable fixture와 기대값 공유를 수정했다. 제품 변경은 홈 연결과 새 행 템플릿에 한정했다. 최초 실패 로그·캡처와 이후 성공을 구분한다. 문서·보존 1차 검사의 2 FAIL은 단순 literal 검사 오류가 아니라 현재 문서의 의미 누락/불명확성이다. backend README는 독립 검증이 별개라는 설명만 있어 대기 상태를 명시했고, backend README와 DESIGN에는 현재 Git 문단 교체 때 빠진 첫 `46ef337` 체크포인트 이력을 복원했다. 원 FAIL·도구/스냅샷을 보존하고 문서 보완 뒤 새 최종 결과로 구분한다. M2-4 제목은 처음 계획 당시 제목임을 명시하고 기존 앵커는 보존했다. 탐색 중 없는 파일 경로를 바로잡은 읽기 기록은 [별도 메모](reconnaissance-notes.json)에 있다.

## 보존·Git·남은 범위

사전 [스냅샷 실행](baseline-snapshot-command.json)은 **1931파일·DB 58테이블**의 해시를 수집했다. DB는 `SET TRANSACTION READ ONLY` 안의 SELECT만 사용했고 원 데이터/비밀번호를 출력하지 않았다. 비공개 원본 스냅샷은 `/tmp/y3gym-m2-4-chvghqww/`에 권한 0700/0600으로 보존한다. 최종 [문서·보존 검사](preservation-report-final.json) **14 PASS**, 링크 290개·앵커 24개를 확인했다. 파일은 1931 → 1935개이며 기존 변경은 허용된 7파일, 제품/테스트 신규는 4파일이다. 과거 검수 1502·프로토타입 원본 185·미디어 145·비밀 2·공통 fixture 3·의존성/설정 8·그 밖의 제품 소스/테스트/스크립트 77파일과 DB 58테이블 전체 행 해시·Git index/HEAD를 보존했다. 8767 보존·8768 허용 재시작도 확인했다. [최종 스냅샷 명령](report-final-snapshot-command.json)과 [검사 명령](preservation-report-final-command.json), [구조화한 최종 결과](verification.json)를 따른다. 이 문서에 최종 근거 링크를 추가한 뒤 [마지막 보고 감사](final-audit.json)에서 최종 링크 298개·앵커 24개 PASS를 확인했다. 첫 [문서 2항목 FAIL](preservation.json)과 [보완 뒤 PASS](preservation-final.json)는 당시 결과로 보존한다. [기존 비밀값 비노출 검사](secret-check.json)도 통과했다.

8768은 `--noreload`에서 새 `home.py`를 읽도록 정확한 프로젝트 루트·동일 Python/인수로 한 번 재시작했다. [재시작 근거](server-restart.json). 기존 8767 서버는 유지했다. 새 8768은 실행 상태로 남긴다.

첫 체크포인트 `46ef337`과 M2-3 종료 당시 미커밋 기록은 역사로 보존했다. 설계가 전달한 Git 담당 완료는 **b517cc209f0f3ac66d7b602450cf5d9dca16d58c main → origin/main push exit 0·실제 원격 해시 일치·ahead/behind 0·작업 트리/index 깨끗함**이다. 개발은 시작 시 실제 HEAD/깨끗한 작업 트리를 확인했다. 현재 M2-4는 **미커밋**이며 stage/commit/push·인증/전역 설정·배포를 하지 않았다. M2-3-R1 독립 재검증 PASS_WITH_WARNINGS와 사용자의 특정 직급/약력 배치 승인도 유지하며 M2-4 자체 검사를 독립 검증·새 화면 승인으로 확대하지 않는다.

실제 기기·Whale/다른 브라우저·한국어 IME·관리자 사용성·실제 브랜드/연락처·지도/전화/카카오톡·운영 저장소/캐시/백업/배포는 미검증/미구현이다. 과거 Wagtail 중복 업로드 문제는 재현하지 않아 해결로 보고하지 않는다. 트레이너 opt-in 브라우저·합동 역순·실제 headed 창 크기/위치 전체 검수는 이번 홈 연결에 관련 실패/변경 근거가 없어 반복하지 않았다. 전체 서버 회귀에는 기존 트레이너·저장/철회 동시성 검사가 포함된다. 개발 최종 보고 후 멈추며 설계가 diff/화면/보고를 검토한 뒤 독립 검증을 별도 지시한다.

## 재현 안내

`backend/`에서 실행한다. 기본 검사는 격리 test DB를 생성하고 제거하며 실제 앱 DB를 초기화하지 않는다.

```bash
uv run --locked python manage.py test news.tests.test_home_news --noinput --verbosity 1
uv run --locked python manage.py test news.tests --noinput --verbosity 1
```

브라우저 재검수는 **새 출력 폴더**를 지정한다. 기존 결과를 덮어쓰지 않는다. 기존 `prototype/node_modules` Playwright/Chromium을 재사용했고 의존성 설치·변경은 하지 않았다.

```bash
Y3GYM_RUN_HOME_NEWS_BROWSER=1 Y3GYM_HOME_NEWS_REVIEW_DIR=review/home-news/review-new uv run --locked python manage.py test news.tests.test_home_news_browser --noinput --verbosity 1
Y3GYM_HOME_NEWS_REVIEW_DIR=review/home-news/live-new node scripts/review-home-news.mjs --live-read-only
```

쓰기 스크립트 단독 실행과 8767/8768 대상 쓰기는 거부한다. 실제 앱 읽기 명령은 로그인하지 않고 DB를 수정하지 않는다. 스크린샷용 팝업 숨김은 별도 브라우저 컨텍스트에만 저장하며 실제 설정·사용자 브라우저 상태를 바꾸지 않는다. 정확한 이번 명령/환경/종료 코드/시각은 각각의 `*-command.json`, 실행 중 실패 로그는 같은 이름의 `.txt`에 있다.
