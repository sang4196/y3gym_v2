# M2-4 홈 최근 소식 독립 검증

판정: **PASS_WITH_WARNINGS**. 요구사항 위반 또는 새 제품 결함을 발견하지 않았다. W01 기존 전체 포맷 경고 1건을 유지한다. 사용자 시각 승인·관리자 사용성·실제 기기·운영 승인은 별도다.

## 기준·범위

현재 AGENTS, 루트 README, PRD FR-05, IMPLEMENTATION-PLAN M2-4, DESIGN M2-4, backend README와 WORKFLOW를 읽고 실제 코드 및 이번 실행 결과로 판단했다. 개발자의 완료 보고·실패 로그·보존 보고는 참고 자료로 읽었으며 PASS 수에 합치지 않았다. HEAD는 b517cc209f0f3ac66d7b602450cf5d9dca16d58c이며 로컬 origin/main과 같다. 원격 push 재실행 또는 원격 확인은 하지 않았다.

검증 대상은 기존 7개 변경(README.md, backend/README.md, backend/news/home.py, docs/PRD.md, docs/IMPLEMENTATION-PLAN.md, docs/WORKFLOW.md, prototype/DESIGN.md)과 새 4개 제품/검사 파일(home_news.html, test_home_news.py, test_home_news_browser.py, review-home-news.mjs)이다. 기능 목표·현 구현·과거 검수·현재 독립 검증 대기를 구분한 문서를 확인했다. 과거 M2-4 미완료 제목은 기존 앵커 유지용이며 본문 현재 상태는 구현·자체 검수로 명시되어 있다.

검증 담당이 추가·수정한 파일은 이 home-news-independent 폴더의 검사 코드·명령 로그·JSON·새 캡처·보고서뿐이다. 프로덕션/기존 테스트/문서/프로토타입은 수정하지 않았다. commit, push, 배포, 서버 재시작은 하지 않았다.

## 이번에 직접 실행한 검사

| 검사 | 결과 | 이번 증거 |
|---|---|---|
| 기능 서버 검사 | 8/8 PASS | [로그](home-server.txt) |
| 전체 서버 | 110 수집, 106 PASS, opt-in 4 SKIP | [로그](all-server.txt) |
| 새 독립 서버 검사 | 최종 3/3 PASS. 최초 1 PASS·2 FAIL은 검사 코드 구성 문제로 수정 | [초기 실패](independent-semantics.txt), [재실행](independent-semantics-rerun.txt), [각 단계](semantics-rerun/CMS-lifecycle.json) |
| 관련 브랜드·지점 opt-in | Django 2건 PASS / 흐름 7·11 PASS | [로그](related-brand-branch.txt), [브랜드](browser/brand/result.json), [지점](browser/branches/checks.json) |
| 홈 opt-in 및 팝업 회귀 | Django 1건 PASS / 홈 8·재방문 8·경계 3 PASS | [로그](home-browser-and-popups.txt), [홈](browser/home/checks.json), [재방문](browser/popup-revisit/checks.json), [경계](browser/popup-edges/edge-checks.json) |
| 추가 팝업 6건 브라우저 | PC·모바일 2흐름 PASS | [증거](browser/all-popups/checks.json) |
| 실제 8768 익명 읽기 | 독립 DB/HTTP 비교 PASS, Chromium 7흐름 PASS | [DB/HTTP](live-state.json), [브라우저](live/home/checks.json) |
| 문서·과거 스냅샷 비교 | 298개 로컬 링크·24개 앵커 및 정합성 PASS | [결과](documents-history.json) |
| 시스템·마이그레이션·lint·변경 범위 format·diff | 모두 exit 0 | [전체 명령](verification.json) |
| 전체 format | exit 1 / 기존 W01만 유지 | [로그](global-format.txt) |

기능 8건은 전체 서버에 포함되어 있으며 중복 합산하지 않는다. 전체 서버에서 제외된 opt-in 중 브랜드·지점·홈은 위 별도 실행으로 확인했다. 트레이너 opt-in은 이번 재실행 범위 밖이다. 공유 test_y3gym_m1을 사용하는 서버·브라우저 검사는 순차 실행했다.

명령마다 *-command.json에 정확한 argv·cwd·exit·실행 시간을, 같은 이름의 .txt에 출력을 저장했다. 이 둘과 [종합 JSON](verification.json)이 재현 근거다. 실행 경로는 backend이며 uv run --locked를 사용한다. 재실행은 새 출력 폴더를 지정해야 기존 증거를 보존할 수 있다. 이 폴더의 검사 결과 파일은 exclusive 생성하므로 같은 이름을 덮어쓰지 않는다.

## 요구사항과 실제 결과

| 확정 요구사항 근거 | 독립 재현·기대 | 실제 결과 |
|---|---|---|
| PRD FR-05: 최대 5건·최초 공개 최신순·수정/재공개 순위 유지 | 공개 8건을 등록순과 다른 최초 공개일로 만들고 같은 날짜 2건도 포함. seed 스칼라 manifest를 시각 내림차순/ID 오름차순으로 정렬해 홈5·목록8을 각각 비교 | PASS. 목록을 기대값으로 삼아 홈과 목록의 동시 오정렬을 놓치지 않음 |
| 공개 리비전만 표시 | 실제 비밀번호 로그인·CMS edit GET/POST로 제목·분류·요약·본문·사진 초안 변경. 익명/로그인 홈·목록·상세는 기존 공개본, 새 사진 익명 404 기대 | PASS. 명시적 공개 후에만 반영. CMS 철회 후 홈/목록 제외·상세404. 이후 실제 재공개에서도 최초 날짜·원 순위 유지 |
| 팝업 최초 등록 빠른순 유지 | 8개 공개/팝업 대상의 홈5 밖 3개도 payload·data route 유지. 추가 브라우저에서 6개 활성 팝업과 홈5를 비교 | PASS. PC 자동 열기/ready 6건·모바일 순차 표시/닫기 6건. 홈에서 빠진 가장 오래된 글 포함 |
| 0건·선택 요약·한국 날짜·비공개 제외 | 0/1/5/6/8건, 한국 날짜 경계, 빈 요약, 새 초안, live revision 없는 행, 브랜드 preview, 제목/요약/본문 악성 마크업 | PASS. 행/빈 상태·날짜·분류 일치, 빈 요약 태그 없음, 공개 HTML에 실행 요소 없음. preview도 공개 글만 사용·팝업 없음 |
| 지점·탐색·A 행 유지 | 무지정/잘못된 지점/0곳, JS 없는 실제 링크, PC/모바일 탭·뒤로가기·새로고침·상세·모두 보기 | PASS. 선택 지점 query 1개, 유효 서버 링크, 가로 넘침 없음. PC/모바일 패딩10/8px·h3 18/16px·구분선1px 확인. CSS/글꼴/context.js 원본 해시 보존 |

세부 manifest·단계별 결과는 [정렬/팝업](semantics-rerun/order-and-popup.json), [실제 CMS lifecycle](semantics-rerun/CMS-lifecycle.json), [경계](semantics-rerun/boundaries.json)에 둔다. 새 독립 테스트 3건이며 기존 개발자 검사 8건과 구분한다.

실제 DB는 공개 6건이며 자체 Python 정렬 기대 ID는 **21→22→17→18→2→1**, 홈 기대는 앞 5건이다. 익명 홈·목록·5개 상세의 공개 제목/분류/요약/최초 날짜/URL과 일치했다. 실제 8768에는 로그인·POST·seed·업로드를 실행하지 않았다.

## 새 화면 확인

다음 실제 캡처를 검증 담당이 열어 확인했다. 과거 개발자 모바일 구역 캡처는 촬영 당시 위치에서 고정 문의 바가 마지막 요약을 덮은 자료이며 보존했다. 이번 375×812 스크롤 검사에서는 마지막 제목 top407.25·요약 bottom450.94·문의 바 top740px이며 hit test와 실제 상세 클릭이 통과했다. 긴 viewport 구역 캡처는 5건 전체 표시용이며 실제 휴대폰 크기 검사로 대체하지 않는다.

- [실제 PC 5개 행](live/home/desktop-actual-news.png)
- [실제 375×812 마지막 행 읽기/클릭 위치](live/home/mobile-actual-last-row-visible.png)
- [실제 모바일 폭의 5개 행 전체](live/home/mobile-actual-news-unobscured.png)
- [격리 PC 5건](browser/home/desktop-five-news.png)
- [격리 모바일 5건 전체](browser/home/mobile-five-news-unobscured.png)
- [격리 모바일 빈 상태](browser/home/mobile-empty-news.png)
- [홈5 밖 가장 오래된 팝업의 모바일 표시](browser/all-popups/mobile-oldest-outside-home.png)

기존 A 디자인 승인 및 트레이너 선택 직급/약력 배치 승인은 유지하며 새 M2-4 캡처의 사용자 승인을 뜻하지 않는다.

## 남은 경고·실행하지 않은 범위

**W01/P3 — 기존 전체 Ruff 포맷 경고**

- 근거: AGENTS 검증·보고의 남은 경고 구분 및 기존 검수 이력 보존.
- 관련 파일: backend/review/workflow-01/verify.py.
- 재현: backend에서 uv run --locked ruff format --check . 실행.
- 기대: exit 0. 실제: exit 1, 해당 1개 파일 재포맷 필요.
- 이번 제품 변경 밖의 기존 검사 파일이며 전후 해시 동일. 수정하지 않았다. 이번 변경/독립 도구의 scoped format 및 전체 lint는 통과했다.

미실행·미확정은 [findings.json](findings.json)에 별도로 기록했다. 실제 휴대폰/Whale/타 브라우저/한국어 IME, 관리자 사용성·새 화면 사용자 승인, 운영 배포/스토리지/CDN/캐시/백업 및 실제 전화·카카오톡·지도 연동은 검증하지 않았다. 기존 native 팝업 전체 위치/크기 검사는 이번에 재실행하지 않았다. persisted pageshow 분기는 이벤트를 주입해 검사했으며 OS 실제 BFCache 입증과 구분한다. 트레이너 opt-in·브랜드/지점 역순/단독 전체 조합은 재실행하지 않았다. 개발자 과거 실패·획득 경위·서버 재시작은 기록을 읽은 것이며 독립 재현한 것으로 세지 않는다.

## 검사 도구 실패와 보존

새 독립 서버 검사의 최초 실패 2건은 미래 시각 고정에 따른 기본 세션 만료와 공개 전 객체의 stale live 값 사용이었다. 검증 코드에서 세션 만료를 늘리고 철회 전 refresh_from_db()를 추가해 재실행 3건 PASS를 확인했다. 최초 로그/명령/그때의 성공 결과를 보존했다. 기타 도구 준비 오류와 read-only live JSON의 최초 잘못된 저장 위치 복구는 [tool-notes.json](tool-notes.json)에 기록했다. 프로덕션 코드를 고치지 않았다.

[검증 전후 보존 결과](preservation-result.json): 독립 폴더 밖 **2,101개 파일**, 실제 DB **58개 테이블의 모든 행 해시**, private media **145개 파일**, Git index/HEAD, 실제 두 서버 PID/명령/cwd가 동일하다. 개발자 home-news 전체 166개 파일(실패 로그/초기·최종 캡처/보고서 포함), 이전 검수, 프로토타입, 3개 공통 fixture, 의존성·설정·비밀 파일을 보존했다.

[별도 과거 비교](documents-history.json)는 제공된 개발 전1931개/개발 후1935개 스냅샷으로 7개 변경+4개 추가만 확인했다. 이것은 이번 검증 시작/종료 snapshot 비교와 구분한다. 이전 검수1502개·DESIGN 제외 프로토타입185개·미디어145개·비밀2개·fixture3개·설정8개 보존을 현재 파일 해시와 다시 비교했다. 개발 시점의 행위를 독립적으로 재연한 것은 아니다.

요청한 M2-4 검증을 마쳤으며 후속 기능·Git 작업을 시작하지 않는다.
