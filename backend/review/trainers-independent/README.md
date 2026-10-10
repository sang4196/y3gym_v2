# M2-3 트레이너 관리 독립 검증 — 2026-10-10

**최종 판정: FAIL / 수정 필요.** 최신 초안 이름·소개를 관리자 목록에서 검색하지 못하는 **F01/P2 결함 1건**을 실제 관리자 로그인과 HTTP 저장·조회로 재현했다. 나머지 공개·미디어·권한·동시성·브라우저 검사는 아래 범위에서 통과했다. 기능 결함과 별개로 경고 4건 및 미검증 항목이 남는다.

기계 판독용 결과는 [verification.json](verification.json), 문제·경고는 [findings.json](findings.json), 요구사항별 근거는 [requirements-evidence.json](requirements-evidence.json)에 있다. 개발자 완료 보고와 기존 PASS는 참고로 읽었으며 이번 독립 실행 건수에 합산하지 않았다.

**판정 근거와 실행 환경**

- [현행 AGENTS.md](../../../AGENTS.md), [프로젝트 README](../../../README.md), [PRD FR-03](../../../docs/PRD.md#fr-03-트레이너), [구현 계획 M2-3](../../../docs/IMPLEMENTATION-PLAN.md#다음-단위-m2-3-트레이너-관리), [디자인 기준](../../../prototype/DESIGN.md), [작업 흐름](../../../docs/WORKFLOW.md), [백엔드 안내](../../README.md)를 확인했다. 과거 legacy 문서는 현행 지침으로 적용하지 않았다.
- 실제 작업 루트는 `/home/shlee/Workspace/ai/01.codex/y3gym_v2`다. 기존 작업 변경 16파일과 신규 구현 10파일의 범위를 실제 파일 및 해시와 대조했다. 목록은 [historical-preservation.json](historical-preservation.json)과 [개발자의 변경 목록](../trainers/changed-files.json)에 있다.
- 승인된 로컬 PostgreSQL `127.0.0.1:55438`, 잠긴 의존성의 Python 3.13.15·Django/Wagtail·Chromium을 사용했다. 쓰기 검사는 `test_y3gym_m1` 및 임시 미디어·계정에서 직렬 실행했다. 테스트가 만드는 DB의 마이그레이션을 실제 앱 DB 적용으로 해석하지 않는다.
- 실행 중인 로컬 앱 `127.0.0.1:8768`과 정적 서버 `127.0.0.1:8767`은 재시작하지 않았다. 실제 `y3gym_m1`은 읽기 및 읽기 전용 트랜잭션 대조만 수행했다. 실제 관리자 저장·시드 재실행은 하지 않았다.
- 검증자가 생성·수정한 파일은 이 `review/trainers-independent/`의 테스트 도구·로그·JSON·새 캡처·본 보고서뿐이다. 프로덕션 코드·기존 문서·기존 검수 자료·프로토타입·비밀 파일·Git index는 보존했다. commit, push, 배포, 인증·Git 설정 변경은 하지 않았다.

**F01 — P2: 관리자 검색이 최신 초안 이름·소개를 찾지 못함**

요구사항 근거는 구현 계획 M2-3의 “관리자 목록은 최신 초안의 이름·소속·순서” 기준과 추가 검증 지시의 최신 이름·소개 검색 일치 확인이다. PRD에 별도 검색 기능 요구가 있다고 확대하지 않는다. 구현은 [TrainerIndexView/TrainerViewSet](../../news/wagtail_hooks.py) 162~197행과 [Trainer 편집 표시 속성](../../news/models.py) 543~555행에 있다.

재현 절차:

1. 이름 `공개 이름`, 소개 `공개 소개`인 트레이너를 공개한다.
2. 실제 관리자 계정으로 로그인해 이름을 `독립 새 이름`, 소개를 `독립 새 소개`로 변경하고 초안 저장한다. 재현 검사에서는 소속도 두 번째 지점으로 이동했다. 저장 응답은 302다.
3. 현재 초안 소속의 트레이너 목록을 연다. 검색 없는 목록에는 `독립 새 이름`이 표시된다.
4. 같은 목록에서 새 이름·새 소개로 각각 검색하고 이전 이름·이전 소개 검색과 비교한다. 모든 조회 응답은 200이다.

| 검색 조건 | 기대 결과 | 실제 결과 |
| --- | --- | --- |
| 검색 없음, 현재 초안 소속 | 저장한 프로필과 새 이름 표시 | 해당 프로필에 `독립 새 이름` 표시 |
| `독립 새 이름` | 해당 프로필 반환 | 해당 프로필 없음 |
| `독립 새 소개` | 해당 프로필 반환 | 해당 프로필 없음 |
| `공개 이름` / `공개 소개` | 최신 편집본 기준 검색과 일치 | 이전 값으로 새 이름의 동일 프로필이 검색됨 |

`search_fields = ["name", "intro"]`는 현재 모델 행의 이전 값을 검색하고 목록의 `editing_name`과 소속 필터는 최신 리비전을 사용한다. 검사 당시 모델 행의 이름·소개는 이전 값이고 최신 리비전은 새 값이었다. 목록에 소개 열이 있다고 주장하는 것은 아니다. 소개 검색의 기대값은 같은 최신 편집본의 소개다.

운영자가 방금 저장한 이름·소개로 프로필을 찾지 못하며 공개하기 전까지 이전 값을 기억하거나 목록을 수동 탐색해야 한다. 이 재현에서 공개 화면 누출·데이터 소실은 관측되지 않았다. 우선순위는 P2다.

증거: [검색 결과 JSON](trainer-search-result.json), [실행 로그](trainer-search.txt), [명령·종료 코드](trainer-search.json), [독립 재현 도구](audit_search.py). JSON의 `rows`는 대상 프로필의 이름/수정 링크이므로 두 링크를 두 프로필로 집계하지 않았다. 입력 칸이나 알림 문구 대신 실제 목록 테이블의 해당 편집 링크를 판정했다.

승인된 로컬 테스트 환경에서 `backend/`를 작업 디렉터리로 다음 명령으로 재현한다. 이 검사는 현재 코드에서 1건 실패하며 실제 앱 데이터는 수정하지 않는다. 재실행 시 기존 검색 결과 JSON은 덮어쓰지 않는다.

```sh
uv run --locked python review/trainers-independent/audit_search.py
```

**이번에 실제 실행한 검사**

각 실행의 정확한 명령·작업 디렉터리·종료 코드·시간은 같은 이름의 JSON과 [통합 결과](verification.json)에 보존했다. 아래 수치는 실행별 수치이며 중복 테스트를 합산한 고유 테스트 수가 아니다.

| 검사 | 실제 결과 | 새 실행 증거 |
| --- | --- | --- |
| `manage.py test news.tests` | 97건 수집, 94 통과, opt-in 브라우저 3 제외 | [server-tests.txt](server-tests.txt), [json](server-tests.json) |
| 독립 경계·동시성 검사 | 20 통과 = 새 독립 검사 11 + 함께 수집된 기존 트레이너 검사 9 | [additional-tests.txt](additional-tests.txt), [json](additional-tests.json), [도구](audit_trainers.py) |
| 트레이너 브라우저 단독 | 1테스트·10흐름 통과 | [trainer-alone.txt](trainer-alone.txt), [흐름](trainer-alone/trainer/checks.json) |
| 브랜드 → 지점 → 트레이너 결합 | 3테스트, 각각 7·11·10흐름 통과 | [combined.txt](combined.txt), [json](combined.json) |
| 트레이너 → 지점 → 브랜드 역순 | 3테스트, 각각 10·11·7흐름 통과 | [reverse.txt](reverse.txt), [json](reverse.json) |
| 긴 이름·약력 12항목·빈 선택 영역 추가 브라우저 | 1테스트, 1440·900·375px 3검사 통과 | [로그](long-biography-browser.txt), [치수](long-biography/checks.json) |
| 최신 초안 이름·소개 검색 | **1테스트 실패 — F01** | [trainer-search.txt](trainer-search.txt) |
| 실제 앱 읽기: 트레이너 | 4흐름 통과, 지점별 A/B 각 1명 | [로그](live-trainers.txt), [흐름](live-trainers/checks.json) |
| 실제 앱 읽기: 지점·시설 | 5흐름 통과; 로그 이름 경고 W03 | [로그](live-branches.txt), [흐름](live-branches/checks.json) |
| 실제 앱 읽기: 팝업 재방문 | 8흐름 통과 | [로그](popup-revisit.txt), [흐름](popup-revisit/checks.json) |
| 실제 앱 추가 구역 검사 | 두 지점 × PC/모바일 4검사 통과 | [최종 로그](live-sections-final.txt), [결과](live-sections-final/checks.json) |
| `manage.py check` / 마이그레이션 dry-run | 문제 없음 / 추가 모델 변경 없음 | [check](system-check.txt), [migration](migration-check.txt) |
| 최신 문서 자동 검사 | 6문서·194링크·20앵커·11검사 통과; 수동 문서 경고 W04 | [결과](document-checks.json), [로그](documents.txt) |
| 전체 Ruff lint | 통과 | [lint-report-tools.txt](lint-report-tools.txt) |
| 구현·이번 검수 범위 Ruff format | 48파일 통과 | [scoped-format-report-final.txt](scoped-format-report-final.txt) |
| 전체 Ruff format | **실패: 기존 파일 1개 — W01** | [global-format-complete.txt](global-format-complete.txt) |
| `git diff --check` | 통과 | [diff-check.txt](diff-check.txt) |

서버 검사에서 제외된 opt-in 3종은 각각 별도의 단독/결합/역순 브라우저 실행으로 수행했다. 97건 전부 통과로 보고하지 않는다. 추가 검사에서 기존 9건을 다시 수집한 사실도 독립 신규 20건으로 확대하지 않는다.

독립 검사는 공개 리비전의 소속·순서·사진·이름·소개·직급·단일 약력을 함께 대조했다. 테스트 DB의 mutable 행과 자식을 바꿔도 익명/로그인 고객 URL은 같은 공개본을 유지했고, 이동을 공개하면 같은 ID 1개가 새 지점에만 표시됐다. 공개 필수 이름·소속 각각의 오류, 미완성 초안 저장, 선택 블록 숨김, 두 지점의 등록 초기 소속과 새 지점 먼저 저장 안내도 확인했다.

미리보기는 권한 및 `private, no-store`를 확인했고 공개 지점의 수정 초안·비공개/미지정 소속의 주소·운영시간·시설 누출을 검사했다. 사진은 프로필과 지점의 이중 공개, 소식·브랜드·시설 공유의 마지막 공개 사용처, 초안·원본·변환본·관리자 썸네일의 권한 경계를 확인했다. 실제 제한 계정 로그인·CSRF·GET·삭제 거부·오래된 폼·잠금에서 전체 행/리비전/약력/이미지 상태 보존도 확인했다. 일반 요청의 302 거부와 AJAX 403을 구분했다.

추가 동시성 6건은 실제 로그인·요청·서로 다른 연결의 두 스레드로 실행했다. 저장/공개와 철회의 4가지 순서는 `pg_blocking_pids`의 실제 잠금 대기를 확인했고 두 경로의 `FOR UPDATE` 및 최신 내용 보존을 대조했다. 동시 초안 저장/동시 공개 2건은 1요청 성공·1요청 오래된 폼 거부 및 리비전의 필드 묶음 일치를 검사했다. 상세 증거는 [추가 증거 디렉터리](additional/), 기존 서버의 교차 요청 증거는 [server-concurrency](server-concurrency/)에 있다.

브라우저에서는 시설 다음·위치 이전의 트레이너, 홈 제외·새 공개 메뉴/프로필 페이지 없음, JS 없는 전체 공개 지점/프로필, 지점 선택·문의 대상, 4:5 사진, PC/태블릿 2열·모바일 1열·가로 넘침을 확인했다. 별도 공개 트레이너 URL은 404, 기존 소식/지점 URL은 200이었다([경로 결과](public-route-scope.json)). 모바일 긴 약력 마지막 문장과 프로필 문의를 각각 스크롤해 고정 문의 바 위에서 읽고 조작할 수 있음을 치수와 새 캡처로 확인했다.

새 캡처 예시: [실제 A 모바일](live-sections-final/main-375-section.png), [최신 약력 PC](trainer-alone/trainer/short-biography-desktop-section.png), [최신 약력 모바일](trainer-alone/trainer/short-biography-mobile-section.png), [관리자 모바일 긴 이름](trainer-alone/trainer/trainer-editor-mobile.png), [긴 약력 마지막 항목](long-biography/last-biography-mobile-viewport.png), [문의 링크](long-biography/profile-inquiry-mobile-viewport.png). 실제 A/B에는 직급·약력이 없으며 해당 선택 정보 사례는 테스트 DB에서만 만들었다. 합성 인물/사진은 임시 자료다.

기존 사용자의 “이 배치로 유지” 승인은 개발자 `regressions-final/combined/trainer/`의 짧은 약력 PC·모바일 구역 2장에 한정된다. 이번 단독 실행에서 생성한 대응 2장은 그 승인 캡처와 바이트가 동일했다([대조 결과](visual-capture-comparison.json)). 이 사실을 관리자 사용성·실제 기기·운영 배포 승인으로 확대하지 않는다.

검증 도구의 실패 이력도 보존했다. 첫 실제 구역 캡처는 lazy 이미지에 대한 `decode()` 대기로 중단했다([최초 로그](live-sections.txt), [최초 결과](live-sections/checks.json)). 해당 검증자의 Node 프로세스만 종료하고 검증 도구에서 이미지를 로드한 뒤 새 디렉터리로 재실행해 위 최종 4건이 통과했다. 앱 서버는 종료하지 않았다. 검수 도구 포맷 검사 1회 실패도 [최초 로그](format-report-tools.txt)에 남겼으며 해당 도구만 정리한 최종 48파일 검사는 통과했다. 이를 제품 기능 실패로 집계하지 않는다.

**보존 검사와 이전 이력의 한계**

이번 검증 시작/종료를 직접 수집한 해시에서 **기존 파일 1,446개, 실제 DB 58테이블 전체 행, 비밀 파일 2개, 비공개 미디어 145파일, Git index가 동일**했다. 범위 밖 신규 파일도 없었다. [preservation-result.json](preservation-result.json), `snapshot-before.json`·`snapshot-after.json`에 근거를 보존했다. 스냅샷은 원본 행 값 대신 해시를 기록하고 접근 권한을 0600으로 제한했다.

개발자의 M2-3 이전 보관 스냅샷 1,199파일·56테이블도 현재 파일/DB를 직접 재계산해 대조했다. 기존 변경은 보고된 16파일과 일치하며 기존 DB 행 변경/삭제는 없다. 트레이너 2행·약력 0행, 사진/변환본 각 2행, 리비전/로그 각 2행, 참조 6행·검색 색인 2행과 권한 추가가 이번 시드에 귀속되는지 확인했다. 시드 → 반복 시드 → 최종 → 현재의 58테이블 전체 해시는 동일했다. 이는 보관된 단계의 멱등성 근거이며 이번에 실제 앱 시드를 재실행한 결과는 아니다.

공통 fixture 3파일(`review_fixtures.py`, `test_brand_browser.py`, `test_branch_browser.py`)은 모두 이전 해시와 같고 트레이너 자료를 주입하거나 기존 0명 단언을 제거하지 않았다. 기존 검수 785파일·디자인 문서를 제외한 프로토타입 185파일·기존 비공개 미디어 141파일도 이전 해시와 같았다. 새 미디어 4파일은 A/B 원본 2개와 변환본 2개다([범위](file-scope.json), [이전 대조](historical-preservation.json)). **과거 스냅샷의 취득 자체는 개발자가 제공한 보관 자료이며 이번에 과거 시점 수집을 독립 재현한 것은 아니다.** 현재 해시·DB 조회와 대조는 직접 수행했다.

**남은 경고 — 통과 항목과 분리**

- **W01/P3 — 기존 전역 포맷:** `backend/review/workflow-01/verify.py` 1파일로 전역 format 검사가 종료 1이다. 이번 구현/검수 범위 48파일과 전체 lint는 통과했다. 기존 파일은 수정하지 않았다.
- **W02/P3 — 보존 메타데이터 범위 설명:** 개발자 README는 공통 fixture 3파일을 설명하지만 `preservation-final.json`의 `protected.common_browser_fixture.files`는 2다. 독립 대조에서는 3파일 모두 불변이다. 두 파일 카운터의 범위 설명이 없어 그 값만으로 3파일 전체의 보존을 입증했다고 인용하지 않는다.
- **W03/P3 — 읽기 검사 로그 문구:** `backend/scripts/review-branches.mjs` 191행의 PASS 이름은 “0명 트레이너 숨김”으로 남지만 실제 읽기 모드의 단언은 지점당 1명이다. 실제 A/B 각 1명을 확인했고 쓰기 fixture의 0명 검사는 보존했다. 실행 결과와 로그 이름의 불일치다.
- **W04/P3 — PRD 현재 상태 모순:** [PRD](../../../docs/PRD.md) 32행의 현재 상태 표는 “트레이너 관리는 미구현”, 같은 문서 FR-03 75행과 M2-3 계획/코드는 “로컬 구현”이다. 두 부분을 비교해 재현할 수 있다. 기대는 구현 상태와 남은 검토 상태의 일관된 표기이며 실제는 서로 모순이다. 자동 링크·앵커 검사의 통과가 이 수동 검토 경고를 해소하지 않는다.

**실행하지 못했거나 이번 범위에서 제외한 검사**

Whale 및 Chromium 외 브라우저, 실제 휴대폰·한국어 IME, 운영 배포/캐시/저장소/백업, 관리자 사용성의 사용자 승인은 검증하지 않았다. 기존 Wagtail 중복 이미지 업로드 오류와 변경 없는 native 팝업의 실제 좌표·창 크기 검사도 재실행하지 않았다. 이번 팝업의 `pageshow` 이벤트 주입 검사는 실제 OS의 BFCache 복원 검증을 대신하지 않는다. 외부 지도·전화·카카오톡의 실제 연동과 제품 제외 범위는 완료로 판정하지 않는다.

F01의 수정과 해당 검색 재검증이 필요하다. 본 검증에서는 문제를 수정하거나 다음 기능을 시작하지 않았다.
