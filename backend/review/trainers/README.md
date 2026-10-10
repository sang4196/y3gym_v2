# M2-3 트레이너 관리 — 개발 자체 검사

2026-10-10, `/home/shlee/Workspace/ai/01.codex/y3gym_v2`의 로컬 구현 결과다. **개발 자체 검사 PASS_WITH_WARNINGS, 독립 검증 대기**다. 기존 전역 포맷 경고 1개를 보존했다. 관리자 사용성·실제 기기·운영 배포 승인은 완료로 보고하지 않는다.

**후속 사용자 시각 승인:** 사용자가 아래 합동 검수의 PC·모바일 구역 캡처를 보고 직급·약력 배치를 **“이 배치로 유지”**로 승인했다. 설계가 이 승인 범위를 전달했다. 이 선택정보 배치 승인과 독립 검증·관리자 사용성·실제 기기/배포 승인은 별개다. 촬영 당시 JSON·캡처를 승인 이후 상태로 재작성하지 않았다.

## 구현과 변경 파일

- `Trainer`와 `TrainerBiography(Orderable, ParentalKey)`를 하나의 프로필 리비전으로 저장한다. 공개 시 이름·소속 지점만 필수이며 미완성 초안과 빈 선택 정보를 허용한다. 약력은 분류 없는 단일 목록이다.
- 지점 편집의 ‘소속 트레이너 관리/등록’에서 진입하고 현재 지점을 미리 선택한다. 지점·시설과 별도 저장 단위임을 안내하고 아직 저장하지 않은 지점은 초안 저장을 먼저 안내한다. 지점 내 표시 순서는 CMS에서 수동 지정한다.
- 초안 → 권한 있는 미리보기 → 명시적 공개/철회 흐름과 기존 `ConcurrentEditView`·R1 `ConcurrentUnpublishView`를 재사용한다. 권한·CSRF·편집 잠금·오래된 폼 및 실제 PostgreSQL 저장/공개/철회 교차 요청을 검사했다.
- 고객 화면의 소속·순서·사진·약력·선택 정보는 같은 `live_revision`에서 읽는다. 프로필과 소속 지점이 모두 공개여야 노출하며 지점 철회는 프로필 원본·자체 공개 상태를 보존한다. 같은 프로필의 이동 초안은 현재 공개 소속에 영향을 주지 않고 공개 후 새 지점에만 나타난다.
- 비공개/소속 미지정 미리보기는 프로필과 상태만 보여 주며 비공개 지점의 초안 주소·운영시간·시설을 포함하지 않는다. 프로필 사진도 같은 이중 공개 조건과 기존 마지막 공개 이미지 사용처 판정을 적용한다.
- 실제 지점 상세의 시설 → 트레이너 → 위치 순서, 기존 A 카드·4:5 사진·PC/태블릿 2열·모바일 1열·Pretendard/색상/간격을 유지한다. 약력 카드 내부와 같은 행의 시작점을 위로 맞춘 CSS만 추가했다. 짧은 소개 카드의 기존 내부 정렬을 유지한다. 비어 있는 블록과 0명 구역은 숨긴다.

기존 파일 **16개**를 수정하고 구현 파일 **10개**를 추가했다. 정확한 목록은 [changed-files.json](changed-files.json)에 있다.

| 파일 묶음 | 내용 |
| --- | --- |
| [models.py](../../news/models.py), [0005 migration](../../news/migrations/0005_trainer_trainerbiography.py) | 프로필·단일 약력, 공개 필수값, 리비전·잠금·미리보기 |
| [panels.py](../../news/panels.py), [wagtail_hooks.py](../../news/wagtail_hooks.py), [관리 패널](../../news/templates/news/admin/trainer_management.html) | 지점에서 진입·소속 미리 선택·초안 기준 목록·기존 저장/철회 보호 |
| [publication.py](../../news/publication.py), [branches.py](../../news/branches.py), [trainers.py](../../news/trainers.py) | 공개 리비전 기반 소속/순서, 미디어 사용처, 안전한 미리보기 |
| [base.html](../../news/templates/news/base.html), [branch_browser.html](../../news/templates/news/branch_browser.html), [카드](../../news/templates/news/trainer_card.html), [미리보기](../../news/templates/news/trainer_preview.html), [CSS](../../news/static/news/trainers.css) | 실제 지점 카드·선택 블록·반응형·상단 정렬 |
| [초기 자료 명령](../../news/management/commands/bootstrap_trainer_review.py) | 승인된 가상 A/B·사진/소개만 각 1명, 기존 자료 미덮어쓰기, 로컬 그룹의 필요한 프로필 권한 4개 |
| [서버 검사](../../news/tests/test_trainers.py), [동시 저장](../../news/tests/test_concurrency.py), [철회 교차](../../news/tests/test_withdrawal_concurrency.py) | 공개본/권한/사진 경계와 실제 DB 동시성 |
| [명시적 opt-in fixture](../../news/tests/test_trainer_browser.py), [트레이너 브라우저](../../scripts/review-trainers.mjs), [지점 브라우저](../../scripts/review-branches.mjs) | 분리된 쓰기 검수, 기존 0명 fixture 검사 유지, 실제 앱 A/B 읽기 검사 |
| [루트 README](../../../README.md), [백엔드 README](../../README.md), [PRD](../../../docs/PRD.md), [구현 계획](../../../docs/IMPLEMENTATION-PLAN.md), [WORKFLOW](../../../docs/WORKFLOW.md), [DESIGN](../../../prototype/DESIGN.md) | 구현/자체 검사/독립 검증/후속 배치 승인·미검증 범위 구분 |

공유 브랜드·지점 fixture 3개는 수정하지 않았다. 트레이너 fixture는 기존 브라우저 준비 명령 뒤 새 명령을 **명시적으로** 호출하는 별도 opt-in이다. 이전 지점 0명 검사를 유지하고 실제 읽기 모드만 승인된 A/B 각 1명을 검사한다.

## 이번에 수행한 검증

이 표는 이번 개발에서 직접 실행한 결과다. 이전 M2-2 독립 보고서를 읽은 것과 구분하며 반복 실행의 테스트/흐름 수를 합산하지 않는다. 명령·환경·종료 코드는 [verification.json](verification.json), [최종 회귀 메타데이터](regressions-final/results.json), [정적 검사](static-checks.json), [실제 앱 명령](live-commands.json)에 있다.

| 검사 | 이번 결과 | 근거 |
| --- | --- | --- |
| 변경 전 `manage.py test news.tests` | 81개 중 79 PASS, opt-in 2 SKIP | [baseline-server.txt](baseline-server.txt) |
| 트레이너 전용 서버 | 9 PASS | [trainer-server-second.txt](trainer-server-second.txt) |
| 트레이너 + 동시 저장 + 철회 교차 | 33 PASS | [concurrency-final.txt](concurrency-final.txt), [교차 요청 JSON](concurrency-final/trainer-publish-edit-first.json) |
| 최종 전체 `news.tests` | **97개 중 94 PASS, opt-in 3 SKIP** | [최종 전체 로그](regressions-final/server/output.txt) |
| 트레이너 브라우저 단독 | 1 PASS / 10흐름 | [browser-second.txt](browser-second.txt), [checks.json](browser-second/checks.json) |
| 브랜드 → 지점 → 트레이너 합동 | **3 PASS**, 각각 7·11·10흐름 | [로그](regressions-final/combined/output.txt), [브랜드](regressions-final/combined/brand/result.json), [지점](regressions-final/combined/branch/checks.json), [트레이너](regressions-final/combined/trainer/checks.json) |
| 트레이너 → 지점 → 브랜드 역순 | **3 PASS**, 각각 10·11·7흐름 | [로그](regressions-final/reverse/output.txt), [브랜드](regressions-final/reverse/brand/result.json), [지점](regressions-final/reverse/branch/checks.json), [트레이너](regressions-final/reverse/trainer/checks.json) |
| 실제 8768 읽기 전용 트레이너 / 지점 / 팝업 재노출 | **4 / 5 / 8흐름 PASS** | [트레이너](live-trainers/checks.json), [지점](live-branches/checks.json), [팝업](live-popup-revisit/checks.json) |
| 실제 A/B 구역 PC/모바일 캡처 | 4장 PASS | [captures.json](live-sections/captures.json) |
| Django check / migration drift / 전체 Ruff lint | PASS / 추가 migration 없음 / PASS | [check](system-check.txt), [migration](migration-check.txt), [lint](lint-final.txt) |
| 변경 관련 Ruff format | 40파일 PASS | [format-scoped.txt](format-scoped.txt) |
| 전역 Ruff format | 기존 `review/workflow-01/verify.py` 1개 경고 | [format-global.txt](format-global.txt) |
| 최신 6문서 경로·앵커·정합성·diff | **194링크·20앵커·11항목 PASS** | [최종 결과](document-checks-final.json), [검사 도구](verify_documents.py) |
| 기존 파일/DB 행/비밀/index·서버 보존 | **최종 PASS** | [preservation-final.json](preservation-final.json), [새 DB 행의 범위](new-database-rows.json) |

최종 전체 회귀는 소식·팝업·브랜드·지점·이미지·동시 저장/철회를 포함한다. 트레이너 4가지 철회 교차 시나리오는 실제 `pg_blocking_pids` 대기를 관측하고 두 요청의 최신 리비전·소속/순서/사진/단일 약력·파일 바이트와 응답을 함께 검사한다. 비공개 사진·원본·변환본·썸네일, 공유 이미지의 마지막 공개 사용처, 익명/읽기/편집/게시 권한·CSRF·GET 부작용·삭제 거부·오래된 폼을 확인했다.

[마지막 보고 도구 검사](report-tool-checks.json)에서도 새 Python 도구 2개 포맷/lint와 트레이너/캡처 JavaScript 문법이 통과했다. 제품 회귀 이후 변경은 보고·최신 문서와 문서 검사 도구에 한정했으므로 제품 테스트를 불필요하게 반복하지 않았다.

쓰기 브라우저는 별도 테스트 DB·임시 계정/미디어와 임시 localhost 포트에서만 실행했다. 실제 8768은 승인된 migration·초기 A/B 자료 외에 읽기 요청만 수행했다. 팝업 검수의 localStorage/창 동작은 서버 DB 쓰기가 아니다. 기존 팝업 `pageshow` 검사는 이벤트를 주입한 분기 검증이며 실제 OS BFCache 검증으로 확대하지 않는다.

## 화면 근거와 승인 범위

**실제 8768:** 본점 A·예시점 B 각 1명, 기존 가상 사진/한줄 소개만 있다. 직급·약력은 비어 있다. 아래는 읽기 전용으로 촬영한 구역 캡처이며 전체 캡처는 [live-trainers/checks.json](live-trainers/checks.json)의 목록에 있다.

- 본점: [PC 1440](live-sections/main-1440-section.png) · [모바일 375](live-sections/main-375-section.png)
- 예시점: [PC 1440](live-sections/second-1440-section.png) · [모바일 375](live-sections/second-375-section.png)

**별도 테스트 DB:** 직급, 짧은 약력 2항목과 사진/선택 정보 없는 옆 카드를 함께 만든 표시 검사다. 경력·자격·실적을 주장하는 실제 자료가 아니다. **사용자가 “이 배치로 유지”로 승인한 캡처는 이 두 장이다.**

- [PC 직급·짧은 약력·사진 없음 구역](regressions-final/combined/trainer/short-biography-desktop-section.png)
- [모바일 직급·짧은 약력·사진 없음 구역](regressions-final/combined/trainer/short-biography-mobile-section.png)

긴 이름/약력 12항목과 관리자도 별도 테스트 DB 자료다: [긴 카드 PC](regressions-final/combined/trainer/long-profile-desktop.png), [태블릿 900](regressions-final/combined/trainer/long-profile-900.png), [모바일 375](regressions-final/combined/trainer/long-profile-375.png), [관리자 PC](regressions-final/combined/trainer/trainer-editor-desktop.png), [관리자 모바일](regressions-final/combined/trainer/trainer-editor-mobile.png). 관리자 모바일 이름 입력 폭도 검사했으나 실제 기기/한국어 IME·관리자 사용성 사용자 승인은 별개다.

## 실패 이력과 수정

실패 로그·JSON·캡처는 삭제하거나 덮어쓰지 않았다. 다음은 성공 결과와 별개인 개발 중 기록이다.

1. [최초 전용 서버 검사](trainer-server-first.txt): 2 FAIL + 1 ERROR. fixture의 오래된 객체 상태와 지점 chooser를 일반 select로 가정한 검사를 수정했다. 실제 새 객체/hidden chooser 값을 검사하고 전용 9개가 통과했다.
2. [최초 동시성 검사](concurrency-first.txt): 5 FAIL. 4건은 읽기 포인터가 끝에 있던 파일 해시 비교, 1건은 modelcluster 자식 캐시였다. 파일 경로에서 바이트를 읽고 새 Trainer 객체에서 자식을 다시 조회했다. 실제 잠금·리비전 단언을 줄이지 않고 33개가 통과했다.
3. [최초 브라우저](browser-first.txt): 사진 chooser의 선택 상태 메뉴를 열지 않고 숨겨진 지우기 버튼을 클릭한 locator timeout이었다. 이후 소속 이동 검사를 수행하기 전의 **검사 도구 실패**이며 소속 이동 제품 결함으로 보고하지 않는다. 메뉴를 열어 실행한 단독 10흐름과 합동/역순이 모두 통과했다.
4. 최초 브라우저 캡처에서 긴 약력 카드의 사진/본문과 옆 카드가 수직 가운데에 놓이는 배치 문제를 별도로 확인했다. 설계가 지시한 최소 상단 정렬 CSS를 적용하고 새 캡처·정렬 측정으로 확인했다. 이후 사용자의 위 두 캡처 배치 승인을 별도 기록했다.
5. [최초 보존 판정](preservation.json): 개별 보존 조건은 정상이지만 추가 허용 테이블 목록에서 Wagtail 자동 참조 인덱스 6행·이미지 검색 인덱스 2행이 빠져 최상위 FAIL이었다. 단계별 snapshot과 `SET TRANSACTION READ ONLY` 조회로 모두 새 A/B 프로필·사진에 속함을 확인했다. 기존 행 변경·삭제는 없다. 최초 FAIL을 그대로 두고 [근거를 포함한 최종 PASS](preservation-final.json)를 추가했다.

6. [최초 문서 검사](document-checks.json): 경로·앵커는 모두 정상이었으나 PRD의 여러 문장을 한 줄로 검색해 현재 M2-3 구현과 과거 “미착수” 이력을 잘못 연결했다. 문장 경계 안에서 현재 상태를 검사하도록 도구를 수정하고 [최종 문서 검사](document-checks-final.json)로 구분했다. 보고서의 재현 예시도 출력 디렉터리 이름만 전달하도록 바로잡았다. 제품 코드는 변경하지 않았다.

## 실제 데이터·파일·서버 보존

[실제 schema/seed 실행 기록](schema-seed.json): `migrate --noinput`·`bootstrap_trainer_review`·같은 seed 재실행이 모두 성공했다. 재실행 전후 **58개 전체 테이블이 동일**하다. 실제 자료는 승인된 임시 A/B·기존 사진/소개만이며 직급/약력은 넣지 않았다.

[최종 보존 검사](preservation-final.json)는 작업 전 1,199파일·56테이블과 최종 상태를 대조했다. 기존 DB 행 변경/삭제 0건, 과거 검수 785파일·DESIGN을 제외한 프로토타입 185파일·비공개 미디어 141파일·비밀 2파일·의존성/구성 5파일·공유 browser fixture 3파일의 해시가 동일하다. Git index도 동일하다. 실제 읽기 검수 이후 58테이블 전체가 seed 직후와 동일하다.

승인된 실제 추가분은 프로필 테이블 2행·약력 테이블 0행, 모델 기본/게시/잠금 권한 정의 11행·기존 로컬 그룹의 add/change/view/publish trainer 연결 4행, content type 2행·migration 1행, 사진/변환본/리비전/공개 로그 각 2행, Wagtail 참조 인덱스 6행·이미지 검색 인덱스 2행이다. 삭제 권한 정의가 Django에 생성된 것과 그룹에 삭제 권한을 부여한 것은 구분한다. 프로필 삭제 화면/권한은 열지 않았다. 기존 미디어는 보존하고 새 원본 2·변환본 2파일만 추가했다.

정확한 cwd/명령을 확인해 기존 8768만 재시작했다. 새 실제 앱 PID는 **1149215**, 기존 8767 PID **714159**는 유지한다. 기존 체크포인트 `46ef337423fb89c1eb7f9000762f32e67802bc57`의 원격 push는 Git 담당의 별도 작업이다. 개발은 이번 M2-3의 stage/commit/push·인증·영구 Git 설정·배포를 수행하지 않았다. ref 변화와 코드/index 보존을 구분한다.

## 재현과 남은 확인

[백엔드 검증 안내](../../README.md#검증-재현)와 [run_checks.py](run_checks.py)를 따른다. 새 출력 디렉터리를 지정하면 전체 서버 → 합동 → 역순을 순차 실행한다. 기존 검수 경로를 재사용하거나 원본 프로토타입을 재생성하지 않는다.

```bash
cd backend
uv run --locked python review/trainers/run_checks.py --output recheck-new
```

실제 실행한 명령은 `--output regressions-final`이며 도구가 `review/trainers/` 아래로 해석한다. 쓰기 검수에 실제 8768 포트를 사용하지 않는다. 실제 읽기 명령도 기존 출력 폴더를 다시 지정하면 캡처/JSON을 덮어쓸 수 있으므로 새 경로를 지정한다.

- **대기:** 테스트 담당의 독립 검증, 관리자 사용성 사용자 확인. 사용자 시각 승인은 위 선택정보 배치 캡처에 한정된다.
- **미검증/한계:** 실제 휴대기기·Whale 등 다른 브라우저·한국어 IME, 실제 브랜드/지점/인물 자료, 운영 저장소/캐시/백업/배포. Wagtail 기존 중복 업로드 흐름의 운영 사용성도 이번 범위에서 해결/승인으로 확대하지 않는다.
- **제외·미구현:** 프로필 삭제/복원, 운영 계정 관리 확대, 홈 트레이너·새 고객 메뉴/별도 공개 프로필 페이지, 홈 최근 소식 CMS화, 실제 지도·전화·카카오톡, 새 외부 서비스/기술 스택/비용.

이번 개발 단위는 여기서 멈춘다. 설계가 보고를 검토한 뒤 독립 검증을 지시한다.
