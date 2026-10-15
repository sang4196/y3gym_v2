# QA-LIFECYCLE-01 독립 검증

이 보고서의 실행·보존 상태는 독립 검증 당시 기록이다. 이후 사용자 승인에 따른 잔여물 선별 정리로 일부 자료/일회성 코드가 제거됐으며 현재 남긴 근거와 접속 상태는 [유지 요약](../README.md)·[정리 결과](../cleanup-residue-01/README.md)를 따른다. 아래 원 판정과 실행 수는 변경하지 않았다.

2026-10-14 KST. **요청한 수명주기 검증 완료, 새 도구 코드 결함 없음.** 원 후처리 관찰 실패1건과 관측 한계를 유지한다. 제품/설정/의존성/기존 도구·검수 원본은 수정하지 않았다. 이 폴더의 독립 보고/관찰 스크립트와 허용된 표준 경로의 **새 고유 ID 근거**만 추가했다. Git commit/push·배포는 하지 않았다.

## 기준과 동결

[AGENTS](../../../AGENTS.md), [README](../../../README.md), 최신 [PRD](../../../docs/PRD.md)·[기술 설계](../../../docs/IMPLEMENTATION-PLAN.md)의 제품 경계를 확인했다. 이 작업은 공개 UI 재구현이나 전체 제품 회귀가 아닌 QA 환경 소유권·실행·보존·정리 단위다. 개발 README가 작성 중인 시점에는 실제 CLI `--help`·소스·test 상단을 기준으로 시작했고, 완성된 [개발 인계 · 정리됨](../README.md#정리-후-유지한-검증-요약)도 읽었다. 개발의 원 실패/후속은 이번 실행과 합산하지 않는다.

[source-freeze.json](source-freeze.json)에 `qa_lifecycle.py`, `qa_redaction.py`, `qa_test_runner.py`, `qa_browser_guard/loader/resolver.mjs`, `tests/test_qa_lifecycle.py` **7파일의 초기·최종 SHA-256**을 기록했다. 중간 확인과 최종 비교에서 모두 같았고 `.gitignore`도 기준 hash와 같았다. HEAD는 `32ade6ba627f49a521bd7efdf0f482f7f7e1aa7b`다. 관찰된 소스 변경은 없다.

실제 CLI/test는 `backend/review/qa-lifecycle/runs/<새 ID>/`에 증거를 생성한다. 이 고정 경로의 **자기 새 ID 생성은 설계와 사용자가 명시 허용**했다. 기존 ID/파일을 덮어쓰지 않았으며 경로 설정·소스를 바꾸지 않았다.

## 직접 실행 결과

| 실행 | 실제 결과 | 근거 |
| --- | --- | --- |
| fresh baseline의 지정 unittest, 1회 | **12 실행/12 PASS/FAIL·ERROR·SKIP0**,19.024초 | [결과·실행 ID](unittest-result.json) |
| 실제 CLI auto header, 1회 | **4/4 PASS**,skip0, 두 DB·폴더 정리 | [CLI/서버 결과](auto-header.json) |
| 실제 CLI auto browser branch, 1회 | **1/1 PASS**,skip0, 내부 **11 PASS/errors0**, 두 DB·폴더 정리 | [CLI/브라우저/runtime 결과](auto-browser.json) |
| fresh manual 실제 수명주기 | **9항목 PASS**: 한 번 초기화·시작/정지·같은 환경 재시작·완료/정리 | [실제 CLI argv/결과](manual-result.json), [도구 · 정리됨](../README.md#정리-후-유지한-검증-요약) |
| 지정 범위 정적 검사 | Python4 Ruff lint/format PASS, JS3 syntax PASS | [결과](static-checks.json) |
| 자체 baseline 최종 정리 | 완료→dry plan→동일 exact plan→중복 no-op PASS | [원 결과 · 정리됨](../README.md#정리-후-유지한-검증-요약) |

**12·4·1/내부11·manual9는 서로 다른 실행 수다.** unittest의 의도한 명령 exit7/9·실행 예외·정리 실패 주입은 해당 검사에서 기대한 fixture 결과다. 실제 CLI header/browser는 각각 한 번만 실행했고 실패 통과를 위한 반복 실행은 없다. 전체148/152는 실행하지 않았다. [정확한 명령 · 정리됨](../README.md#정리-후-유지한-검증-요약).

12개는 정상/실패 archive 후 정리, 실패 재현 보존, manual pending/명시 완료, 실제 plan drift/duplicate, root·중첩/루트 symlink·다른 run, DB OID/이름·CREATE-before-comment gap, PID 토큰/starttime·조회 거절·서명 불일치, 부분 DB drop/폴더 삭제 실패, 원 종료 코드와 정리 실패 분리, 강제 controller 중단 잔재 발견·소유 child 종료, credential redaction·evidence symlink·0700/0600을 실행했다. 새 baseline `qa-20261013T151215Z-aa300e83d93f`의 private0600 `.local-credentials`에 임의 redaction fixture를 준비했고 값은 출력/보고하지 않았다. DEV baseline을 재사용하지 않았다.

기존 unittest에서 직접 실행이 부족한 **활성 DB 접속·틀린 소유권 COMMENT**는 자기 manual run에서 추가했다. 활성 접속 동안 dry/actual cleanup을 거부했고, 임의 comment 불일치 때도 거부했다. 원 OID를 확인하며 정확한 comment를 복원한 뒤에만 새 plan으로 정리했다. 도구·제품 코드·기존 기대는 수정하지 않았다.

## 실제 manual과 자원 결과

manual ID는 **`qa-20261013T151922Z-a5aa54d1eb7b`**였다. 실제 시작의 `/admin/login/` HTTP200을 두 번 확인했다. 당시 origin은 `http://localhost:47649`였으며 **현재 이 서버는 정리되어 접속 대상이 아니다.** 로그인 POST·기존 서버 HTTP·공개 cold rendition 요청은 하지 않았다.

실행 중 pending은 dry/actual cleanup 및 이른 complete를 거부했고, stop 후 pending도 dry/actual cleanup을 거부했다. 재시작은 새 PID였고 같은 DB OID/comment·전체 자기 DB 행·미디어·계정 파일·source manifest가 같았다. 비교 데이터는 메모리에만 두었다. 두 server PID의 종료를 확인하고 미사용 complete 뒤 정확한 plan으로 두 DB와 폴더를 삭제했다. 중복 cleanup은 no-op이었다. 초기화는 한 번, 두 번째 start는 요청된 계획상 재시작이며 실패 재시도가 아니다.

[own-runs-final.json](own-runs-final.json)에 **자기 생성 23개 run 각각**의 목적·DELETED 상태·폴더 부재·예약 DB 두 이름의 부재·실제 final cleanup drop 목록·표준 증거 경로를 기록했다. 19개 unittest child fixture, header/browser/manual3개, baseline1개다. DB를 만들지 않은 fixture와 부분 정리에서 먼저 drop된 DB는 final drop 수에 더하지 않았다. **독립 잔존 환경은 없다.** raw 계정·토큰·DB·미디어·프로필·private metadata/log 폴더도 자기 baseline 정리와 함께 제거했다.

DEV 보존 **`qa-20261013T133525Z-1d7ae0edf181` MANUAL_PENDING**, **`qa-20261013T135421Z-384a05dad18c` RETAINED**는 운영/정리하지 않았다. 원 로그·before 자료와 identity 실패 이력의 보존 이유/해제 조건은 [개발 인계 · 정리됨](../README.md#정리-후-유지한-검증-요약)를 따른다. 이번 독립 검증이 이 두 환경의 정리 권한은 아니다.

## 실행 경계와 보안 증거

dirty/untracked 제품·검사 소스는 run/source로 복사됐고 unit에서 실제 untracked `backend/news/content_images.py` hash를 확인했다. `.local` 재귀·`.git`·원본 `.env`/계정·원본 media·node_modules 복사는 제외됐다. run별 MEDIA_ROOT·TMPDIR·설정/cache/cookie identity를 사용했다. 브라우저의 실제 프로필/TMPDIR은 own run/tmp 아래였다. 기존 Playwright 바이너리 cache와 동결된 canonical transport guard는 원 경로에서 읽기 전용으로 참조한다.

[browser-live-observation.json](browser-live-observation.json): 실제 Chromium **PID3146039**의 signed birth를 private token으로 검증했고 실제 `/proc` exe·UID·kernel starttime이 기록과 같았다. `auto-browser.json`에서 현재 해당 Chromium이 종료했음과 exported `exe` 필드를 확인했다. signature/token/완전 argv/environment는 저장하지 않았다. [강제 중단 fixture · 정리됨](../README.md#정리-후-유지한-검증-요약)는 실제 sleeping child를 고아로 만든 뒤 안전 종료한 unit 근거다. PID read denial·invalid birth signature는 unit fixture이며 실제 Chromium의 identity 읽기 불가 중단 상태를 새로 강제하지 않았다.

origin 검토 수준을 구분한다. frozen guard는 own localhost origin을 설정하고 브라우저/API 요청 및 redirect를 검사하며 기존 검토 포트를 차단한다. 실제 managed branch helper도 실행됐다. 그러나 **정리 후 sanitized export에는 실제 Django live-server HTTP origin 문자열이 없었다.** lifecycle의 예약 origin은 그 실제 HTTP port로 대체해 보고하지 않는다. 새 origin 차단 음성/네트워크 검사는 실행하지 않았다.

[redaction-check.json](redaction-check.json): baseline 정리 직후 새 공개 텍스트78파일에서 fixture·owner secret·설정의 알려진 비밀값이 없음을 정확한 값으로 검사했고 JSON을 파싱했다. 값은 메모리에서만 검사했다. unit의 의도한 오류 종류/스택은 남고 비밀값은 제거됐다. raw credential/DB/media/profile을 review로 옮기지 않았다.

PostgreSQL 물리 파일은 기존 선언된 loopback compose 서비스에 두는 호환성 예외다. 관리 대상은 새 논리 DB의 이름/OID/comment뿐이며 cluster/volume·기존 DB를 채택하거나 변경하지 않았다. `.local/qa/`는 실제 check-ignore에 적용됐고 git ls-files 추적은0이다. 배포 제외 검증을 수행한 것은 아니다.

## 원 관찰 실패와 한계

**OBS01 — 후처리 관찰 가정 오류:** [당시 inline 소스 보존](archive-summary-observer-initial.py)의 9행은 exported sanitized log에서 `http://localhost:<port>` regex가 있어야 한다고 단언했다. 기대는 비어 있지 않은 origin 목록, 실제는 **0개와 AssertionError**였다. [원 오류·재현 조건](failures.json)을 유지했다.

재현은 `auto-browser.json`의 CLI.evidence 경로에 있는 `evidence-auto-result-*.json`의 sanitized_logs를 읽고 같은 regex 결과에 non-empty 단언을 적용하는 읽기 전용 절차다. 당시 private CLI log는 baseline 정리로 삭제됐으며 보존 소스는 촬영 당시 실행 기록이다. 이미 실행된 browser CLI의 exit0/DELETED·1/내부11 PASS·Chromium identity/종료 증거는 그대로다. 이 누락을 실제 transport 실패로 추정하지 않았고 browser를 재실행하거나 실제 검사를 완화하지 않았다. 후속은 [지원되는 field/관측 한계를 구분한 요약](auto-browser.json)이다.

개발의 최초 Django import/0실행, managed5=4PASS/1browserFAIL, 개별 FAIL/후속 PASS, 여러 자체 unittest 배치와 cold 공개 rendition 10초 Timeout은 [개발 실패 이력](../qa-lifecycle/failures.json)이다. 이번 결과로 합산/해결 처리하지 않는다. 공개 제품 성능 수정·대기 확대·무한 재시도는 하지 않았다.

## 보존 범위

[preservation.json](preservation.json)은 검사 뒤·자기 baseline 삭제 전의 metadata 대조다. **75항목(기존68/tmp+내부7)**의 기존 파일 stat, 원본 DB 이름/OID/comment hash, inventory의 기존 PID 기록15개 identity, HEAD/index·민감 파일 metadata가 같았다. 원본 DB table/revision 행이나 media bytes를 재수집한 검사가 아니며 개발의 미실행 최종 after와 구분한다.

기준 공개파일4022개는 누락0이고, 대조 시점 변경1개 `qa-lifecycle/failures.json`은 설계가 승인한 DEV 총괄 문서 마감이다. 이후 AGENTS·루트/backend README·PRD/IMPLEMENTATION-PLAN·DESIGN·최신 수동표/QA 총괄 문서의 동시 마감도 설계 허용 범위로 구분한다. 독립 검증이 이 파일들을 수정한 것은 아니다. 제품 소스·이전 QA 원본 JSON/캡처의 변경은 대조에서 없었다.

기존8767/8769/8772/8773/8774/8775/8776/8780/8781 및 **34471/PID3142748**을 포함한 모든 legacy 환경에 stop/delete/adopt/drop·HTTP write를 하지 않았다. [inventory 표본 · 정리됨](../README.md#정리-후-유지한-검증-요약)은 기존 snapshot75의 삭제 허용0·조건부 후보4와 그중 exit 파일2곳을 확인한 것이다. 일부 exit0은 전체 환경 완료/삭제 승인이 아니다. 옛45 근거 재분석·새 전수 inventory는 하지 않았다.

전체 제품148/152·전역 W01 정리·실제 기기/Whale/OS IME·운영/배포는 미검증이다. [전체 판정](verification.json)을 제출한 뒤 종료하며 다음 기능·기존 사용자 서버 적용·DEV 보존 run 정리는 시작하지 않는다.
