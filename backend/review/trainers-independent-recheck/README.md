# M2-3-R1 독립 재검증 — 2026-10-10

**판정: PASS_WITH_WARNINGS.** 초기 독립 검증의 **F01/P2 검색 결함과 W02~W04 보완을 확인**했다. 이번 범위에서 새 기능 결함은 발견하지 않았다. **W01 — 기존 전역 포맷 경고 1개는 남으며 전역 format 검사를 통과로 처리하지 않는다.**

[초기 FAIL](../trainers-independent/README.md), [원 실패 JSON](../trainers-independent/trainer-search-result.json), [개발 R1 보고](../trainers-repair/README.md)는 당시 기록으로 보존했다. 개발자의 PASS는 참고 자료다. 아래 결과는 현재 소스·이번 독립 실행·직접 수집한 현재 DB/파일 해시로 판정했다. [findings.json](findings.json), [verification.json](verification.json)에 기계 판독용 결과를 남겼다.

**확인한 요구사항과 변경 범위**

[AGENTS.md](../../../AGENTS.md), [루트 README](../../../README.md), [백엔드 안내](../../README.md), [PRD FR-03](../../../docs/PRD.md#fr-03-트레이너), [구현 계획 M2-3](../../../docs/IMPLEMENTATION-PLAN.md#다음-단위-m2-3-트레이너-관리), [WORKFLOW](../../../docs/WORKFLOW.md), [디자인 문서](../../../prototype/DESIGN.md)와 R1 보고를 읽었다. 최신 사용자 결정·기능 구현·개발 자체 검사·독립 검증·사용자 배치 승인을 구분했다.

R1 이전 보관 스냅샷과 직접 수집한 현재 상태를 대조해 기존 **7파일 변경과 신규 검색 테스트 1파일**, 새 trainers-repair 근거만 확인했다([history-comparison.json](history-comparison.json)).

| 개발의 R1 변경 파일 | 독립 검토 결과 |
| --- | --- |
| backend/news/wagtail_hooks.py | TrainerIndexView.get_search_form() 164행의 숨은 branch 필드와 search_queryset() 175행의 최신 리비전 검색. 빈 초안 값의 이전 공개 값 fallback 금지, 리비전이 없을 때만 모델 fallback |
| backend/news/tests/test_trainer_search.py — 신규 | 실제 로그인/초안 저장·목록/fragment·한글/대소문자·소속/공개 상태/페이지·공개본 보존의 4테스트를 읽고 재실행 |
| backend/scripts/review-branches.mjs | 191행의 읽기 라벨 수정; 쓰기 fixture 0명 단언/라벨 유지 |
| README.md, backend/README.md, docs/PRD.md, docs/IMPLEMENTATION-PLAN.md, docs/WORKFLOW.md | 초기 FAIL → R1 → 독립 재검증 대기, 현재 구현 표기와 M2-4 미착수 계획, 확정 정책과 미결정 운영 범위 구분 |

그 외 공개 카드·레이아웃·모델/마이그레이션·의존성/구성·공통 fixture 3파일·프로토타입·소식 공개 코드는 R1 이전 해시와 같다. 설치된 Wagtail 7.4.3의 실제 BaseListingView 소스에서 정렬 → 필터 → 검색 순서와 기존 OR icontains/SearchForm 처리를 확인했다([로컬 API 근거](installed-api-review.json)). 검색 구현이 공개 리비전이나 모델 행을 검색 값에 맞춰 덮어쓰지 않는지도 확인했다.

검증자가 작성한 소스·근거는 **이 backend/review/trainers-independent-recheck 폴더만**이다. 새 독립 의미 검사 audit_semantics.py, 복사한 원 재현/fixture harness, 검색 브라우저·문서·읽기·보존 도구 및 이번 로그/JSON/캡처/보고서를 추가했다. 제품 코드·최신 문서·기존 FAIL/repair/캡처는 수정하지 않았다.

**F01/P2 재현의 기대/실제 결과 — 해결 확인**

근거는 PRD FR-03의 최신 초안 이름/소개 검색·최신 소속, 리비전 없는 경우만 모델 fallback, 빈 값·소속 필터·공개 상태·페이지 유지 기준이다. 관련 구현은 [wagtail_hooks.py](../../news/wagtail_hooks.py) 164~205행, 편집 표시 속성은 [models.py](../../news/models.py) 543~555행이다.

재현은 기존과 같은 실제 관리자 로그인 → 공개 프로필의 이름/소개/소속을 변경 → 초안 저장 → 현재 초안 소속 목록에서 새 값과 이전 공개 값을 검색하는 순서로 수행했다. 저장은 302, 조회는 모두 200이다.

| 조건 | 기대 결과 | 이번 실제 결과 |
| --- | --- | --- |
| 검색 없는 최신 소속 목록 | 독립 새 이름의 동일 프로필 표시 | 일치 |
| 새 이름: 독립 새 이름 | 동일 프로필 검색 | 검색됨 |
| 새 소개: 독립 새 소개 | 동일 프로필 검색 | 검색됨 |
| 이전 공개 이름 / 공개 소개 | 최신 편집본 기준으로 제외 | 대상 링크 0 |
| 초안 이름/소개가 빈 값 | 이전 초안/공개 값으로 검색하지 않음 | 목록/fragment·실제 브라우저 모두 제외 |
| 최신 리비전 없음 | 현재 모델 이름/소개 검색 | 한글·대소문자 검색 및 소속 격리 확인 |
| 검색·소속 이동 초안 저장 후 고객 화면 | 원 소속의 같은 공개본 유지 | 공개 리비전 전체·카드 HTML·사진 바이트 동일 |

원 [audit_search.py](../trainers-independent/audit_search.py)와 [audit_trainers.py](../trainers-independent/audit_trainers.py)를 **바이트 동일하게 복사한 뒤 원 재현 1개를 실행**했다. 보조 harness는 fixture로 재사용했다([동일성](original-tools-identity.json)). 새 원 재현은 1 PASS이며 [결과 JSON](trainer-search-result.json), [로그](original-reproduction.txt), [명령](original-reproduction.json)에 보존했다. JSON의 이름/수정 링크 2개는 프로필 2개를 뜻하지 않는다. 소개 열을 표시한다고 주장하는 것은 아니며 소개 검색은 같은 최신 편집본 기준이다.

승인된 로컬 환경에서 backend를 작업 디렉터리로 재현한다. 아래 도구는 별도 테스트 DB를 사용하며 기존 결과를 덮어쓰지 않는다.

~~~sh
uv run --locked python review/trainers-independent-recheck/audit_search.py
~~~

이번에 새로 작성한 [audit_semantics.py](audit_semantics.py)는 **3개 독립 검사만 수집**했다. 두 지점의 동명 초안, 이름/소개 OR 검색, 한글/대소문자·따옴표, 전역/잘못된 소속, 공개 상태, 공백 검색, 빈 초안과 무리비전 fallback을 목록/fragment의 실제 편집 행 링크로 판정했다. 검색 응답 81건과 실제 다음 페이지 링크 응답 4건을 대조했다. 43개 미공개 대상의 20+20+3 페이지와 공개 13개를 조회하며 q/branch/live 보존·중복/누락 없음을 확인했다([최신 값/공개본](semantics/latest-and-public.json), [빈 값/fallback](semantics/empty-and-fallback.json), [페이지](semantics/pagination.json)).

**이번 실제 실행 결과 — 실행별 건수를 합산하지 않음**

정확한 명령·cwd·종료 코드·시간은 각 명령 JSON과 [verification.json](verification.json)에 있다. 쓰기 테스트는 공유 테스트 DB를 직렬로 사용했다. 기존 테스트를 다시 실행한 수를 새 독립 테스트 수로 보고하지 않는다.

| 실행 | 이번 결과 | 증거 |
| --- | --- | --- |
| 초기 독립 원 재현의 동일 복사본 | 1 PASS — 재사용 검사 | [로그](original-reproduction.txt) |
| 기존 트레이너 9 + 개발 신규 검색 4 | 13 PASS — 재수집/재실행 | [로그](trainer-server.txt), [명령](trainer-server.json) |
| 이번 신규 독립 의미 검사 | 3 PASS — 기존 테스트 추가 수집 0 | [로그](independent-semantics.txt), [명령](independent-semantics.json) |
| 전체 news.tests | 101 수집, **98 PASS·opt-in 3 SKIP** | [로그](all-server.txt), [명령](all-server-command.json) |
| 기존 트레이너 opt-in 브라우저 | 1 PASS / 10흐름 | [로그](trainer-browser.txt), [결과](trainer-browser/checks.json) |
| 새 검색 실제 브라우저 도구 재실행 | 1 PASS / 7흐름·검색 응답 13건 200·JS 오류 0 | [로그](search-browser.txt), [결과](search-browser/checks.json) |
| 실제 8768 지점 읽기 | 5흐름 PASS·수정된 A/B 라벨 일치 | [로그](live-branches.txt), [결과](live-branches/checks.json) |
| 실제 8768 관리자 읽기 | 기존 세션으로 GET 4건 PASS·새 로그인/세션 생성 없음 | [로그](live-admin-search.txt), [결과](live-admin-search.json) |
| Django system check | 문제 없음 | [로그](system-check.txt) |
| migration check/dry-run | 추가 모델 변경 없음 | [로그](migration-check.txt) |
| 현재 문서 자동/의미 검사 | 7문서·274링크·25앵커·14검사 PASS | [결과](document-checks.json), [로그](documents.txt) |
| lint / 범위 format / 검색 JS 구문 | PASS, 최종 도구 추가 후 결과도 별도 기록 | [최종 lint](final-lint.txt), [최종 범위 65파일](final-format-scoped.txt), [JS](node-search.txt) |
| 전역 format | **기존 1파일로 종료 1 — W01** | [최종 로그](final-format-global.txt) |
| 실제 DB·파일·서버 보존 | PASS | [결과](preservation-result.json) |

전체 서버의 opt-in 3개 중 **트레이너는 이번에 별도 실행**했다. 변경되지 않은 브랜드·지점 브라우저는 이번에 다시 실행하지 않았으며 SKIP을 PASS로 바꾸지 않는다. 전체 서버에서는 기존 소식·브랜드·지점·미디어·권한·오래된 폼/행 잠금·실제 동시 저장/공개/철회 회귀를 실행했다. 그 교차 요청 근거는 [server-concurrency](server-concurrency/)에 있다.

새 검색 브라우저는 테스트 서버에서 실제 운영자 로그인과 이름/소개/소속 초안 저장 후 입력 이벤트에 따른 trainer/results 요청을 기다려 행 링크·branch를 확인했다. 다른 지점의 동명 프로필 제외, 이전 값 제외, 검색어 비우기, 빈 값 제외와 공개 카드 동일성을 확인했다. 개발 도구를 읽고 경로만 이번 새 출력으로 바꿔 실행했으며 이 브라우저 1개를 검증자가 새로 만든 검사로 집계하지 않는다. [새 이름 검색 캡처](search-browser/draft-name.png)와 [빈 초안/이전 값 0건](search-browser/empty-draft-no-old-result.png)을 실제로 열어 확인했다.

트레이너 브라우저는 공개 필수/선택 정보, 단일 약력, 등록 진입/초기 소속, 미리보기/공개 분리, 이동/수동 순서/사진 제거/철회, 4:5·PC/태블릿 2열·모바일 1열·긴 이름과 12항목·JS 없는 공개 본문·문의 대상을 확인했다. [관리자 모바일 캡처](trainer-browser/trainer-editor-mobile.png)와 [짧은 약력 PC](trainer-browser/short-biography-desktop-section.png)를 열어 확인했다.

사용자의 “이 배치로 유지” 승인은 기존 지정 짧은 약력 PC·모바일 배치에 한정된다. 이번에 생성한 대응 2장은 승인 캡처와 바이트가 동일하다([대조](approved-capture-comparison.json)). 관리자 사용성·실제 기기·배포 승인을 뜻하지 않는다. 실제 A/B에는 직급/약력이 없고 선택 정보 검수 자료는 테스트 DB에서만 만들었다.

**W02~W04 — 보완 확인과 이전 기록 보존**

- **W02:** 새 R1 보존 근거의 공통 fixture 3개 실제 경로·전후 해시를 직접 수집한 해시와 대조해 모두 일치했다([scope-evidence.json](scope-evidence.json)). 과거 2파일 카운터/FAIL은 그대로 보존하고 새 보충으로 범위를 설명했으므로 해결로 판정한다. 실제 fixture를 수정하거나 트레이너를 공통 fixture에 주입하지 않았다.
- **W03:** 실제 읽기 5흐름의 첫 라벨이 “홈 트레이너 숨김·실제 지점별 A/B 각 1명”으로 바뀌었고 실제 단언도 일치한다. 소스에서 쓰기 fixture의 0명 단언과 라벨은 유지돼 있다.
- **W04:** PRD 32행 현재 CMS 표와 FR-03는 M2-3 구현·R1 보완·독립 재검증 대기로 일치한다. 새 의미 검사는 해당 행을 직접 추출했다. 과거 M1/M2 제외 기록은 현재 상태와 구분해 보존했다.

홈 최대 5건·홈/소식 목록 최초 공개 최신순·수정/재공개로 순위 올리지 않음·팝업 최초 등록 빠른순의 새 확정 정책도 현재 문서에서 대조했다. **M2-4는 미착수 계획**이며 이번 코드에 구현된 것으로 판정하지 않는다. 페이지당 10건 운영 확정·공개일 편집·삭제/복원·운영 권한·지도/문의/운영 저장소·배포는 미결정/미구현으로 구분돼 있다.

**남은 W01/P3 — 기존 전역 포맷 경고**

파일: backend/review/workflow-01/verify.py. 재현: backend에서 uv run --locked ruff format --check . 기대는 전역 포맷 필요 파일 0개지만 실제는 이 기존 파일 1개로 종료 1이다. 범위 format과 전체 lint는 통과했다. 기능 결함은 아니며 기존 기록 보존 지시로 수정하지 않았다. 이 경고를 통과 항목에 포함하지 않는다.

**로컬 실행·보존 근거와 한계**

실제 루트는 /home/shlee/Workspace/ai/01.codex/y3gym_v2이며 잠긴 Python 3.13.15/Django 5.2.18/Wagtail 7.4.3·로컬 PostgreSQL 127.0.0.1:55438·Chromium을 사용했다. 모든 로그인/저장/공개/시드 테스트는 test_y3gym_m1과 임시 계정·미디어에서만 수행했다. 실제 y3gym_m1은 읽기 전용 트랜잭션의 해시 조회와 기존 세션을 이용한 GET만 수행했다. 쿠키/비밀번호를 기록하지 않았고 실제 관리자 POST·새 로그인/세션·schema/seed 실행은 하지 않았다.

독립 수집한 비교 대상 **1,795파일·실제 DB 58테이블 전체 행·비공개 미디어 145파일·비밀 2파일·Git index가 동일**하며 범위 밖 신규/변경도 없다. 프로토타입 186파일과 이전 backend 검수 1,366파일(초기 FAIL과 repair 포함), 공통 fixture 3개도 보존했다. [snapshot-before.json](snapshot-before.json)·[snapshot-after.json](snapshot-after.json)은 원본 DB 값 대신 행 해시를 기록하고 0600으로 저장했다. [최종 보존 결과](preservation-result.json)와 [R1 이전 대조](history-comparison.json)에 근거가 있다.

R1 시작/종료의 보관 자료와 현재를 대조한 DB 58테이블 전체 해시 및 index도 같고, 보고된 7파일/신규 검색 테스트 외 변경은 없다. **과거 R1 스냅샷 취득 자체는 개발자가 제공한 보관 자료이며 그 과거 수집을 독립 재현한 것은 아니다.** 현재 파일/DB 해시는 직접 수집했다. 기존 8768 PID 1221566과 8767 PID 714159의 cwd/명령/프로세스도 유지했다. 개발 R1에서의 과거 재시작과 구분하며 검증자는 서버를 재시작하지 않았다.

검증 도구의 오류는 [tool-failures.json](tool-failures.json)에 별도로 남겼다. 시작 snapshot과 실제 관리자 GET 도구는 데이터 JSON 저장 후 명령 기록의 파일명이 겹쳐 wrapper가 종료 1이었다. 원 데이터·stdout의 읽기/GET 판정은 보존됐고 덮어쓰기는 없었다. 이후 명령 메타데이터를 -command.json으로 구분했다. 사전 도구 정리의 잘못된 상대 경로 1회와 실행 전 거절된 JS 호출도 실제 제품 검사 실패와 구분했다. 누락된 wrapper 성공 종료 코드/시간을 만들어 기록하지 않았다.

실제 휴대폰·Whale/Chromium 외 브라우저·한국어 IME, 관리자 사용성 사용자 승인, 운영 배포/캐시/저장소/백업·실제 지도/전화/카카오톡은 미검증이다. 기존 Wagtail 중복 이미지 업로드 오류도 재검증하지 않았다.

초기 독립 검증의 brand/branch/trainer 합동·역순, 긴 약력 하단 조작 추가 검사와 팝업 재방문 결과는 [초기 보고](../trainers-independent/README.md)의 당시 결과로만 인용한다. 이번 변경 범위와 파일 보존을 근거로 그 합동/역순 및 native 팝업 실제 위치·크기 전체 검사는 반복하지 않았다. 이번 R1에서 pageshow/BFCache 재방문 브라우저도 재실행하지 않았다. 이전 pageshow 주입을 실제 OS BFCache 검증으로 확대하지 않는다.

제품 코드·최신 문서·Git index·인증/설정·외부 서비스는 변경하지 않았다. commit/push/배포, 개발 담당에게 직접 전달, 다음 기능 착수 없이 이 재검증 보고에서 멈춘다.
