# M2-2-R1 철회 동시성·브라우저 fixture 보완

2026-10-10 한국 시간. **R1 보완 구현·지정된 자체 회귀 완료. 독립 재검증·사용자 승인 대기.** 초기 [독립 검증 FAIL](../branches-independent/README.md)·[발견 목록](../branches-independent/findings.json)과 이전 [개발 자체 검수](../branches/README.md)는 변경하지 않았다. 이번 근거는 이 폴더에만 추가한다. 다음 기능·Git 반영·배포는 진행하지 않았다. [최종 검사 요약](verification.json).

## 원인과 수정

**F01 / 동시 철회:** 설치된 Wagtail 7.4.3의 generic `UnpublishView.get_object(queryset)`는 인자를 사용하지 않고 모델을 직접 조회한다. 이전 지점 뷰가 전달한 `select_for_update()`는 실행되지 않았으며, 오래된 객체를 전체 저장하는 `UnpublishAction`이 새 초안의 최신 포인터를 되돌렸다. R1 수정 전 실제 두 HTTP 요청에서 **지점·브랜드·소식 모두** 철회 잠금 없음·새 리비전은 존재하지만 최신 포인터/현재 초안은 이전 상태로 돌아가는 것을 재현했다. 지점/브랜드 [JSON](before-fix/branch-draft-withdraw-first.json)·[브랜드 JSON](before-fix/brandcontent-draft-withdraw-first.json)·[로그](logs/before-fix.txt), 소식 [JSON](before-fix-post/post-draft-withdraw-first.json)·[로그](logs/before-fix-post.txt).

`news/wagtail_hooks.py`에 공통 `ConcurrentUnpublishView`를 추가했다. 기존 조회/유효성 경로를 거친 뒤 POST에서 `get_object_or_404(self.model.objects.select_for_update(), pk=...)`로 **최신 행을 실제 조회**한다. `ATOMIC_REQUESTS`가 조회부터 철회 완료까지 잠금을 유지한다. 지점·브랜드·소식 viewset이 이를 사용하며 기존 permission policy·CSRF·before/after/cancel hook·철회 처리는 그대로 상속한다. GET 확인 화면은 잠금을 걸지 않는다.

새 동시성 검사는 3모델 × 초안/공개 × 철회 먼저/저장 먼저 = **12가지 실제 교차 요청**을 수행한다. 먼저 조회한 요청만 잠깐 멈추고 두 번째 요청이 `pg_blocking_pids()`로 첫 요청의 잠금을 기다리는지 확인한 뒤 진행한다. 양쪽 SQL의 `FOR UPDATE`, 302 응답, 최신 포인터·본문·시설 순서/제목, 최종 공개 상태를 확인한다. 먼저 초안 저장한 경우 Wagtail이 현재 모델 행에 이전 공개 내용을 남기는 기존 동작과 최신 리비전에 보관한 새 초안의 보존을 구분한다. 새 초안은 반드시 최신 리비전에서 복원해 비교한다.

**F02 / 브랜드 fixture:** 브랜드 옵트인 테스트는 지점 없이 시작하면서 문의 바/2지점 화면을 기대했다. 공통 테스트 fixture가 소식·브랜드와 공개 본점/예시점 2곳을 준비하고, 브랜드 스크립트도 쓰기 전 두 공개 지점 조건을 명시적으로 확인한다. 기존 7개 흐름·문의 바 검사·제품의 0지점 문의 숨김은 유지했다.

**W01 / 합동 fixture:** `StaticLiveServerTestCase`의 flush는 migration으로 만든 Wagtail Collection root도 제거한다. 테스트 전용 `ensure_collection_root()`가 필요한 root를 준비한 뒤 동일 초기화 명령을 호출한다. 제품 seed·실행 DB는 수정하지 않는다. [Django의 migration 초기 데이터/TransactionTestCase 설명](https://docs.djangoproject.com/en/5.2/topics/testing/overview/#rollback-emulation)과 설치된 Django/Wagtail 소스를 확인했다. 두 클래스 모두 같은 준비 절차를 사용하며 단독·합동·반대 순서로 검사한다.

**관리자 모바일:** 제품 UI를 바꾸지 않았다. 검수 스크립트가 375px 축소 전환 후 이름 입력 x=20px·폭=335px를 기다리고 캡처하도록 했다. 과거 전환 중간 상태 캡처는 그대로 보존했다.

## 이번 실행과 결과

각 명령은 `backend/`에서 실행한다. [run_checks.py](run_checks.py)가 동일 테스트 DB를 사용하는 검사를 **직렬 실행**하고 명령·환경(비밀값 제외)·종료 코드·시간을 각 `run.json`과 `output.txt`에 저장한다. `Y3GYM_BRAND_REVIEW_DIR`·`Y3GYM_BRANCH_REVIEW_DIR`·`Y3GYM_WITHDRAWAL_REVIEW_DIR`는 모두 새 출력 폴더다. 기존 폴더가 있으면 덮어쓰지 않는다.

| 실제 검사 | 결과/근거 |
| --- | --- |
| 전체 `uv run --locked python manage.py test news.tests --noinput --verbosity 2` | 최종 **81개 중 79개 PASS·옵트인 브라우저 2개 생략**, 83.204초. 새 동시성 12개·권한/CSRF/GET/hooks 2개 포함. [실행](server-final/server/run.json)·[로그](server-final/server/output.txt)·[12가지 동시성 요약](verification.json) |
| 브랜드 단독 `Y3GYM_RUN_BRAND_BROWSER=1 … test news.tests.test_brand_browser` | 1개 PASS·기존 **7흐름 PASS**. [실행](regressions-final/brand-alone/run.json)·[로그](regressions-final/brand-alone/output.txt)·[JSON](regressions-final/brand-alone/brand/result.json) |
| 지점 단독 `Y3GYM_RUN_BRANCH_BROWSER=1 … test news.tests.test_branch_browser` | 1개 PASS·**11흐름 PASS**. [실행](regressions-final/branch-alone/run.json)·[로그](regressions-final/branch-alone/output.txt)·[JSON](regressions-final/branch-alone/branches/checks.json) |
| 두 환경변수=1 + `… test news.tests.test_brand_browser news.tests.test_branch_browser` | 브랜드 → 지점 **2개 PASS**, 기존 7+11흐름 모두 PASS. [실행](regressions-final/combined/run.json)·[로그](regressions-final/combined/output.txt) |
| 같은 합동 명령 + `--reverse` | 지점 → 브랜드 **2개 PASS**, 기존 11+7흐름 모두 PASS. [실행](regressions-final/combined-reverse/run.json)·[로그](regressions-final/combined-reverse/output.txt) |
| `uv run --locked python manage.py check`, `makemigrations --check --dry-run` | PASS·모델 변경 없음. [check](logs/check.txt)·[migration](logs/migrations.txt) |
| `uv run --locked ruff check .`, `ruff format --check news config scripts review/branches-repair` | 최종 lint PASS·대상 **36개 포맷 PASS**. [lint](logs/lint-final.txt)·[format](logs/scoped-format-final.txt) |
| `uv run --locked ruff format --check .` | 기존 `review/workflow-01/verify.py` 1개만 FAIL. [최종 로그](logs/global-format-final.txt). 이전 파일은 보존 |
| 루트에서 `node backend/review/branches-repair/verify-documents.mjs`, `git diff --check` | 문서 파일/앵커·명령·공개/관리자 경로, 변경 파일 공백/충돌 표시 검사. [결과](document-checks.json)·[문서 로그](logs/documents.txt)·[diff 공백 검사](logs/diff-check.txt) |

전체 서버와 옵트인 브라우저를 별도 실행한 수·재실행·흐름 수를 합산하지 않는다. 팝업 native 위치/크기와 공개 레이아웃 등 제품 코드가 바뀌지 않은 범위는 이번에 반복하지 않았다.

## 권한 거부와 검수 초기 실패

새 권한 검사의 첫 전체 실행은 일반 철회 요청이 항상 403이라고 단정해 3모델의 subtest에서 실패했다. 설치된 `wagtail/admin/auth.py`의 `require_admin_access`/`permission_denied`는 일반 권한 거부를 오류 메시지와 함께 **`/admin/`로 302**, AJAX는 **403**으로 처리한다. 로그인 실패나 제품의 철회 성공과 구분해야 한다. [초기 전체 로그](regressions-final/server/output.txt)

최종 검사는 비밀번호로 실제 로그인한 계정에 관리자 접근·해당 모델 조회/수정만 허용하고 publish 권한은 부여하지 않았다. 세 모델 모두 관리자 홈 200, 일반 거부 302·Location `/admin/`·권한 거부 메시지, AJAX 403·CSRF 403과 공개 상태·최신 리비전·본문/시설·이미지 해시 무변경을 확인했다. [요청/해시 결과](server-final/server/concurrency/boundary-permissions.json). 성공한 철회·GET 무잠금·404·hooks의 순서/취소도 통과했다. 처음의 403 단정은 검수 기대값 오류였으며, 실제 Location을 확인하지 않은 채 비밀번호 준비 redirect나 권한 우회로 판정하지 않았다. 제품 응답을 바꾸지 않았다.

다음 자체 검수 실패·중단도 보존한다.

- [수정 전 1차](logs/before-fix.txt): 지점/브랜드 결함 재현. 소식은 처음에 HTML을 Draftail JSON 대신 전송한 fixture 오류로 실패했고, JSON으로 보정한 [별도 재현](logs/before-fix-post.txt)에서 같은 제품 결함을 확인했다.
- [수정 후 동시성 1차](logs/concurrency-final.txt): 새 검사의 Collection root 누락과 Wagtail 공개 행/초안 리비전 구분 오류. 제품 seed는 변경하지 않고 테스트 fixture/검사 기준을 보정했다.
- [수정 후 동시성 2차](logs/concurrency-final-2.txt): fixture 객체의 modelcluster 자식 캐시가 남은 비교 오류를 보정하던 중 별도 전체 검사를 너무 일찍 시작해 임시 테스트 DB가 충돌했다. 해당 검사를 멈추고 이후 직렬 실행으로 전환했다. 실행 앱 DB를 대상으로 쓰지 않았다.
- [중단된 전체 검사](regressions/server/output.txt): 17개 시점에서 중단한 불완전 실행이다. 전체 통과 근거로 쓰지 않는다.
- [문서 검사 첫 실행](document-attempt-1.json)은 아직 생성 전인 자기 결과 파일 `document-checks.json` 링크 때문에 실패했다. 결과 파일 생성 후 다시 경로를 검사했다. 제품 코드·문서의 실제 대상 경로 결함과 구분한다.

## 직접 확인·캡처·서버

이 저장소 cwd와 실행 인자를 확인한 기존 8768 `--noreload` Python 프로세스만 종료한 뒤 **원래 명령/포트**로 새 코드를 실행했다.

```bash
uv run python manage.py runserver 127.0.0.1:8768 --noreload --insecure
```

[이전 프로세스](server-before.json)·[재시작/실제 요청](server-after.json)에 PID·명령·경로 결과를 기록했다. [홈](http://localhost:8768/?branch=main)·[지점](http://localhost:8768/branches/?branch=second)·[소식](http://localhost:8768/news/?branch=second)은 200, [관리자 지점](http://localhost:8768/admin/snippets/news/branch/)·브랜드·소식은 무로그인 302 로그인 보호를 확인했다. 실행 DB 관리자 로그인/저장·공개/철회는 수행하지 않았다. 관리자 쓰기는 모두 임시 테스트 서버/DB에서 수행했다. 기존 8767 서버는 건드리지 않았다.

안정 상태 새 모바일 캡처: [지점 관리자](regressions-final/branch-alone/branches/branch-editor-mobile.png)·[브랜드 관리자](regressions-final/brand-alone/brand/brand-editor-mobile.png). 두 캡처를 직접 열어 확인했다. 측정한 x=20px·폭=335px는 각 JSON의 `adminMobileNameBox`에 있다. 그 밖의 PC/모바일/미리보기 캡처는 각 브라우저 JSON의 목록을 따른다. 사용성·시각 승인은 별도다.

## 보존·변경·남은 범위

R1 시작 전에 849개 파일과 Git index, 소식/브랜드/지점/시설/이미지/리비전/계정/권한/Collection DB 행 해시를 접근 제한된 `/tmp/y3gym-m2-2-r1-2lzs9l2n/`에 보존했다. 최종 [보존 대조](preservation.json)·[명령 로그](logs/preservation.txt)는 **DB 15개 비교 테이블의 모든 행 해시/개수 동일**, prototype 원본/디자인/캡처 186개·기존 백엔드 검수 437개·비공개 미디어 141개·비밀 파일 2개·의존성/버전 5개·Git index의 바이트 동일을 확인했다. 비교 그룹은 겹칠 수 있어 합산하지 않는다. R1에서 실행 DB에 지점·미디어·계정·권한 등 추가/수정을 하지 않았다. 원본 행·비밀값·해시는 보고서에 싣지 않는다.

정확한 [변경 목록](changed-files.json)은 **기존 9개 수정·구현 파일 2개 추가**와 새 검수 폴더다. 제품 수정은 `news/wagtail_hooks.py`의 공통 철회 조회뿐이다. 브라우저 테스트 2개·스크립트 2개, 새 `tests/review_fixtures.py`·`test_withdrawal_concurrency.py`, 현재 상태를 기록한 루트/백엔드 README·PRD·구현 계획과 이번 검수 도구/근거를 변경했다. 모델·마이그레이션·의존성·UI·운영 정책·제품 seed는 변경하지 않았다.

독립 재검증, 사용자 시각/관리자 사용성 승인, 실제 기기·Whale·Chromium 외 브라우저·한국어 IME·운영 배포/캐시/저장소/백업, 기존 중복 이미지 업로드 오류는 미확인이다. Git index/커밋/푸시/배포·외부 변경·다음 기능은 수행하지 않는다. 최종 자체 보완 보고를 설계에 제출한 뒤 다음 지시를 기다린다.
