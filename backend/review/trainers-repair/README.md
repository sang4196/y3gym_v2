# M2-3-R1 — 관리자 최신 초안 검색·기록 보완

2026-10-10 로컬 개발 보완의 **자체 판정 PASS_WITH_WARNINGS / 독립 재검증 대기**다. [초기 독립 FAIL](../trainers-independent/README.md)의 F01/P2와 W02~W04만 보완했다. W01의 기존 전역 포맷 경고 1개는 보존한다. 이번 결과를 독립 재검증 완료나 관리자 사용성 승인으로 보고하지 않는다.

사용자가 “이 배치로 유지”로 승인한 직급·약력 [PC](../trainers/regressions-final/combined/trainer/short-biography-desktop-section.png)·[모바일](../trainers/regressions-final/combined/trainer/short-biography-mobile-section.png) 배치는 유지했다. 모든 프로토타입과 기존 캡처/JSON·초기 독립 FAIL·원 재현 도구를 보존했다. 관리자 사용성·실제 기기·운영 배포 승인은 별개다. **M2-4는 후속 계획만 기록·미착수**이며 홈/소식 공개 코드는 수정하지 않았다.

## 변경 파일과 필요성

R1 시작 시 기존 M2-3 변경 16파일·신규 구현 10파일 및 검수 자료가 있었다. 이를 보존하며 이번에는 기존 **7파일**을 수정하고 검색 회귀 **1파일**과 이 `review/trainers-repair/`의 새 근거만 추가했다. [R1 보존 결과](preservation-final.json)의 목록은 첫 M2-3 전체 변경 목록과 구분한다.

| 이번 파일 | 변경 이유·결과 |
| --- | --- |
| [wagtail_hooks.py](../../news/wagtail_hooks.py) | `TrainerIndexView.search_queryset()`만 최신 리비전 이름/소개를 검색한다. 최신 리비전이 없을 때만 현재 모델 값을 사용하며 빈 초안 값은 이전 공개 값으로 되돌리지 않는다. 기존 Wagtail 검색 form에 숨은 branch 값만 전달해 검색 시 현재 소속 진입을 유지한다. |
| [test_trainer_search.py](../../news/tests/test_trainer_search.py) — 신규 | 실제 로그인→편집 GET/POST→목록/결과 fragment 응답의 행 링크로 최신 검색·빈 값·리비전 없는 fallback·한글/대소문자·소속/공개 상태/페이지 조합 및 공개본 보존을 검사한다. |
| [review-branches.mjs](../../scripts/review-branches.mjs) | W03: 쓰기 fixture의 0명 단언/라벨을 유지하고 실제 읽기 라벨만 홈 숨김·지점별 A/B 각 1명으로 구분했다. |
| [루트 README](../../../README.md), [백엔드 README](../../README.md), [PRD](../../../docs/PRD.md), [구현 계획](../../../docs/IMPLEMENTATION-PLAN.md), [WORKFLOW](../../../docs/WORKFLOW.md) | 초기 독립 FAIL→R1 자체 검사→독립 재검증 대기, 제한된 배치 승인과 관리자 사용성 별도 상태를 반영했다. W04 현재 CMS 표를 바로잡고 새로운 홈/소식 확정 정책과 M2-4 미착수 계획을 기록했다. |

설치된 Wagtail 7.4.3의 `BaseListingView.get_queryset()`은 기본 queryset → 정렬 → 공개 상태 필터 → 검색 순서다. 기존 Trainer view의 소속 필터는 그 결과에 적용된다. 비색인 모델의 기존 OR `icontains` 의미와 `SearchForm`의 공백 처리·`is_searching`·결과/페이지 흐름을 유지하고 검색 처리 지점에서 JSON 필드를 조회하도록 한정했다. [설치 소스·API 근거](wagtail-search-api.json)에 경로·해시·순서를 기록했다.

모델 이름/소개·게시 상태·현재 공개 리비전을 검색에 맞춰 저장하거나 덮어쓰지 않았다. 소식·지점·브랜드 검색, 검색어 입력 UI, 공개 카드/레이아웃, fixture, 의존성·스택·외부 서비스는 바꾸지 않았다.

## 원 독립 재현과 실제 실행 결과

[원 audit_search.py](../trainers-independent/audit_search.py)·[보조 harness](../trainers-independent/audit_trainers.py)를 바이트 동일한 복사본으로 실행했다. 원 파일·FAIL 결과는 수정하지 않았다. 명령은 backend에서 다음과 같다.

```bash
uv run --locked python review/trainers-repair/audit_search.py
```

- 수정 전: **1 FAIL**. 새 이름/소개 검색 링크 0, 이전 이름/소개 검색은 최신 이름 행을 반환했다([baseline 로그](search-baseline.txt), [baseline 결과](trainer-search-result.json)).
- 수정 후: **1 PASS**. 새 이름/소개 검색에서 해당 프로필이 나타나고 이전 이름/소개는 링크 0이다([실행 로그](original-reproduction-fixed.txt), [수정 후 원 결과](trainer-search-result-2e6c2cb4.json), [복사 동일성/전후 요약](original-reproduction-results.json)). 원 도구의 링크 수 2는 제목 링크와 ‘수정’ 링크이며 프로필 2개를 뜻하지 않는다.

다음은 이번 R1에서 직접 재실행했다. 실행별 테스트·흐름 수를 합산하지 않는다. [regression-commands.json](regression-commands.json), [검색 보정 명령](search-correction-commands.json), [최종 검색 브라우저 명령](search-browser-second-command.json), [정적 검사 명령](static-checks.json)에 정확한 인자·cwd·환경·종료 코드·시간이 있다.

| 검사 | 결과 | 이번 근거 |
| --- | --- | --- |
| 검색 전용 서버 | **4 PASS** | [search-tests-second.txt](search-tests-second.txt) |
| 기존 트레이너 9 + 새 검색 4 | **13 PASS** | [trainer-server.txt](trainer-server.txt) |
| 전체 `news.tests` | **101개 중 98 PASS, opt-in 3 SKIP** | [all-server.txt](all-server.txt), [기존 동시성 새 출력](server-concurrency/) |
| 기존 트레이너 브라우저 | **1 PASS / 기존 10흐름 유지** | [로그](trainer-browser.txt), [checks.json](trainer-browser/checks.json) |
| 신규 실제 검색 브라우저 | **1 PASS / 7흐름, 검색 응답 13건 200** | [로그](search-browser-second.txt), [checks.json](search-browser-second/checks.json) |
| 실제 8768 지점 읽기 | **5흐름 PASS, 실제 A/B 라벨 확인** | [로그](live-branches.txt), [checks.json](live-branches/checks.json) |
| 실제 8768 관리자 검색 GET | **4건 PASS** | [live-admin-search.json](live-admin-search.json), [로그](live-admin-search.txt) |
| Django check / migration dry-run | PASS / 추가 migration 없음 | [check](system-check.txt), [migration](migration-check.txt) |
| 전체 Ruff lint / 범위 format | PASS / **46파일 PASS** | [lint](lint-final.txt), [format](format-scoped.txt) |
| 전역 Ruff format | 기존 `review/workflow-01/verify.py` 1개 경고 | [format-global.txt](format-global.txt) |
| 트레이너·지점·새 검색 JS 문법 | PASS | [트레이너](node-trainer.txt), [지점](node-branch.txt), [검색](node-search.txt) |
| 문서 경로/앵커/현재 상태/계획/diff | **273링크·25앵커·14항목 PASS** · [최종 결과](document-checks-final.json) | [R1 검사 도구](verify_documents.py) |
| 실제 DB/미디어/프로토타입/기존 검수/비밀/index | **PASS** | [preservation-final.json](preservation-final.json) |

마감 문서 도구 수정 후에도 [R1 도구 lint/format](report-tool-checks.json)은 7파일 모두 통과했다. 제품 회귀 이후 수정은 보고·문서 검사 도구뿐이어서 제품 검사를 추가 반복하지 않았다.

새 서버 검사는 실제 편집 저장 후 공개 리비전의 이름·소개·소속·순서·사진·직급/대체 설명·단일 약력과 사진 바이트가 그대로인지 확인한다. 기존 공개 URL도 원래 지점에만 같은 공개 이름/소개·약력을 유지한다. 페이지 검사는 최신 초안 소속의 25건을 공개 상태·q와 함께 조회하고 실제 페이지 링크의 query·branch·live 보존, 첫/다음 페이지 20+5건·중복/누락 없음·결과 0건을 확인한다.

새 브라우저는 별도 테스트 DB·임시 계정/미디어에서 실제 검색어 입력과 Wagtail 결과 요청을 사용했다. 다른 지점의 동명 초안을 추가해 소속이 빠지면 실패하도록 했다. 이름·소개·소속 초안 저장, 영문 대소문자·한글, 이전 공개 이름/소개 제외, 검색어 비우기, 빈 초안 값 제외, 공개 카드 HTML 동일성·JS 오류 0을 확인했다. [최신 초안 검색 화면](search-browser-second/draft-name.png)과 [빈 초안/이전 값 결과 0](search-browser-second/empty-draft-no-old-result.png)은 이번 테스트 DB 자료다.

실제 앱에서는 기존 로컬 검토 운영자 세션을 읽어 **GET 4건만** 수행했고 새 로그인/세션 생성·편집 POST는 하지 않았다. 쿠키·비밀번호는 기록하지 않았다. 실제 지점 검수도 읽기 전용이다. 실제 schema/seed·사용자 콘텐츠·계정/권한·사진/변환본은 추가/수정하지 않았다.

fixture·레이아웃·소식 공개 코드가 그대로여서 지시대로 합동/역순·native 팝업의 전체 창 검사는 반복하지 않았다. 해당 이전 결과를 이번 재실행으로 집계하지 않는다. 전체 서버의 기존 소식/브랜드/지점/미디어/권한/동시 저장/철회 검사는 이번에 실행했다.

## W02~W04와 문서 보완

- **W02:** 이전 `trainers/preservation-final.json`의 common fixture 소그룹은 2개였고 당시 README는 3개였다. 실제 공통 함수는 `news/tests/review_fixtures.py`인데 이전 소그룹의 세 번째 경로가 존재하지 않는 management command를 가리켜 집계에서 빠졌다. 상위 전체 파일 해시 대조에는 실제 파일이 포함됐고 독립 검증에서도 세 파일 보존을 확인했다. 과거 README/JSON은 그대로 두고 이번 [보존 결과](preservation-final.json)에 다음 **3개 모두의 경로·전후 해시·판정**을 명시했다: `news/tests/review_fixtures.py`, `news/tests/test_brand_browser.py`, `news/tests/test_branch_browser.py`.
- **W03:** 실제 읽기 PASS 라벨에 남은 “0명”을 모드별로 고쳤다. 새 [실제 읽기 출력](live-branches/checks.json)의 첫 항목은 “홈 트레이너 숨김·실제 지점별 A/B 각 1명”이다. 쓰기 fixture의 실제 0명 단언과 라벨은 유지했다.
- **W04:** PRD §2 현재 CMS 표의 “트레이너 관리는 미구현”을 실제 M2-3/R1 상태로 고쳤다. 새 문서 검사는 이 행을 직접 추출해 FR-03와 현재 구현·독립 재검증 상태를 대조한다. 과거 M1/M2 제외 문장을 현재 상태 문자열 검사에 넣거나 삭제하지 않는다.

**새 후속 결정만 기록:** 홈 최근 소식 최대 5건, 홈/소식 목록 최초 공개 최신순, 수정·재공개로 순위 올리지 않음, 팝업 최초 등록 빠른순 유지다. [M2-4 첫 계획](../../../docs/IMPLEMENTATION-PLAN.md#다음-미완료-단위-m2-4-홈-최근-소식-실제-공개-글-연결)은 승인 A 목록/구조·공개 리비전 최대 5/0건·실제 상세 링크·선택 지점·JS 없는 탐색·초안 분리/철회/재공개 순위 검증을 완료 기준으로 기록했다. **명시적 다음 구현 지시 전 미착수**다. 목록 페이지당 10건은 초기값이며 삭제/복원·공개일 편집·운영 정책·지도·실서비스·배포를 이번에 확정하지 않았다.

## 실패 이력·보존·한계

이번 실패도 새 경로에 보존했다.

1. 수정 전 원 독립 재현 1 FAIL은 F01의 baseline이다.
2. [최초 새 서버 검사](search-tests-first.txt)는 2 FAIL·12 ERROR였다. Wagtail 제목 ID를 링크 자체에 있다고 가정해 실제 행 링크를 수집하지 못한 검사 도구 오류였다. 실제 편집 href를 읽도록 수정한 4개가 통과했고 원 독립 재현도 별도로 통과했다. 검색/공개본 단언을 줄이지 않았다.
3. [최초 새 브라우저](search-browser.txt), [JSON](search-browser/checks.json), [캡처](search-browser/failure.png)는 지점 chooser 갱신 전에 이전 지점 ID를 읽어 본점의 동명 초안을 찾은 뒤 timeout이었다. 응답은 요청한 본점 범위를 정확히 유지했다. 선택 완료를 기다리는 검수 도구만 고쳐 새 `search-browser-second/`에서 7흐름이 통과했다.
4. [첫 문서 검사](document-checks.json)는 생성 전 결과 파일의 자기 링크와 독립 README 대신 findings.json을 연결한 계획 문서를 검사 도구가 거부한 실패였다. 자신의 예정 출력 파일과 유효한 독립 findings 링크를 구분하도록 고치고 [최종 문서 검사](document-checks-final.json)로 확인했다. 현재 상태 표·확정 정책·미착수 검사 자체는 처음에도 통과했다.
5. 새 snapshot 도구의 초기 import 위치 lint 경고와 잘못된 루트 cwd에서 시도한 도구 실행을 바로잡았다. [도구 시행 이력](tool-failures.json)에 구분한다. 최종 전체 lint·범위 format은 통과했다.

[최종 보존 결과](preservation-final.json)는 R1 시작의 **1,690파일·실제 DB 58테이블 전체 행**과 완료 상태를 대조했다. 새 근거는 이 폴더에만 썼으며 기존 7파일의 승인된 수정과 새 검색 테스트 1파일 외 변화는 없다. 실제 58테이블 전체 행·145개 비공개 미디어·모든 프로토타입·이전 backend 검수(초기 FAIL 포함)·비밀 2파일·의존성/구성·Git index·공통 fixture 3개가 동일하다. 시작/끝 snapshot은 읽기 전용 트랜잭션으로 수집해 비공개 `/tmp` 보관 폴더에 0600으로 저장했다.

정확한 cwd/명령을 대조한 기존 8768 PID 1149215만 종료하고 같은 명령으로 재시작했다([재시작 기록](server-restart.json), [최종 서버 상태](server-final.json)). 8767 PID 714159는 유지했다. 새 서버가 검색 코드를 반영한 뒤 실제 GET을 확인했다. 개발에서 Git stage/commit/push·인증/전역 설정·외부 서비스·비용·배포를 수행하지 않았다.

**남음:** 테스트 담당의 독립 재검증, 관리자 사용성 사용자 확인, 실제 휴대기기/Whale/다른 브라우저/한국어 IME, 운영 저장소·캐시·백업/배포는 미검증이다. 기존 Wagtail 중복 이미지 업로드 오류를 해결/승인했다고 보고하지 않는다. 기존 전역 format 경고 파일을 고치지 않았다. M2-4를 시작하지 않고 이번 보고에서 멈춘다.
