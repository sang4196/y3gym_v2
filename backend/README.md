# 소식 CMS · 팝업 · 브랜드/홈 · 지점/시설 · 트레이너 관리

Django/Wagtail + PostgreSQL에서 소식·브랜드 소개·지점/시설·트레이너를 **초안 저장 → 미리보기 → 명시적 공개 → 수정 → 공개 철회**하고 글의 팝업 설정을 별도 적용하는 로컬 구현이다. 전체 제품·전체 관리자의 완성이 아니다. 승인된 공개 HTML·CSS·글꼴을 재사용하며 관리자 편집 경험의 사용자 확인은 아직 받지 않았다.

제품 기준은 [PRD](../docs/PRD.md), 승인된 공개 UI는 [디자인 문서](../prototype/DESIGN.md), 마일스톤과 미결정 사항은 [구현 계획](../docs/IMPLEMENTATION-PLAN.md)을 따른다.

**M2-2 종료 상태:** [초기 독립 검증 FAIL](review/branches-independent/README.md) → [R1 보완·자체 검사](review/branches-repair/README.md) → [독립 재검증 PASS_WITH_WARNINGS](review/branches-independent-recheck/README.md). F01·F02·W01은 해결됐고 차단 결함은 없다. 기존 전역 포맷 경고 1개와 사용자 시각·관리자 사용성 미승인은 구분해 남긴다. M2-3 트레이너는 [범위·완료 기준](../docs/IMPLEMENTATION-PLAN.md#다음-단위-m2-3-트레이너-관리)에 따라 로컬 구현했고 [이번 자체 검사·캡처·보존](review/trainers/README.md)에 기록한다. 이후 [초기 독립 검증 FAIL](review/trainers-independent/README.md)에서 최신 초안 이름/소개 검색 불일치를 확인해 [M2-3-R1 검색·기록 보완](review/trainers-repair/README.md)을 수행했다. 이후 [독립 재검증 PASS_WITH_WARNINGS](review/trainers-independent-recheck/README.md)로 F01/P2·W02~W04 해결·새 차단 결함 없음을 확인했다. W01 기존 전역 format 경고 1개는 유지하며 관리자 사용성 승인은 별개다. 2026-10-10 사용자가 검토한 PC/모바일 캡처의 직급·약력 배치는 “이 배치로 유지”로 승인했다.

**M2-3 종료 문서:** [독립 재검증 결과](review/trainers-independent-recheck/verification.json)는 전체 101개 중 98 PASS·3 opt-in SKIP, 트레이너 13 PASS, 원 재현 재사용 1 PASS, 신규 독립 의미 검사 3 PASS·검색 응답 81건·다음 링크 4건, 브라우저 기존 10/검색 7흐름, 실제 지점 5/관리자 GET 4건이다. 당시 [종료 문서 검사](review/m2-3-closeout/README.md)는 이 결과를 읽고 경로·상태·보존만 확인하며 제품 검사·캡처·DB 쓰기를 수행하지 않았다. 첫 체크포인트 `46ef337` push 이후 M2-3·R1/종료 문서는 설계 검토와 Git 담당 반영을 거쳐 `b517cc209f0f3ac66d7b602450cf5d9dca16d58c`으로 main → origin/main push 완료했다. 이는 설계가 전달한 Git 결과이며 개발에서 Git 쓰기·인증/영구 설정 변경을 수행하지 않았다. 이 종료 문서 작성 시점의 M2-4 변경은 미커밋이며 이후 Git 반영 결과와 구분한다. 최종 독립/승인 상태는 아래에 구분한다.

**M2-4 종료 상태:** [개발 자체 검사](review/home-news/README.md) 뒤 [독립 검증 PASS_WITH_WARNINGS](review/home-news-independent/README.md)를 완료했다. 요구사항 위반·새 제품 결함은 없으며 기존 포맷 W01만 남는다. 독립 전체 서버 110개 중 106 PASS·4 opt-in SKIP이며 홈 8건은 이 안에 포함된다. 신규 독립 의미 검사 3 PASS, 브랜드 7/지점 11/홈 8/팝업 재방문 8+edges 3·추가 팝업 6건 PC/모바일 2흐름·실제 읽기 7흐름을 확인한 보고서다. 최초 독립 2 FAIL은 미래 시각에 의한 세션 만료/공개 전 stale 지점 객체라는 검사 도구 문제로 보완했으며 초기 로그는 보존했다. 2026-10-10 사용자는 [PC 최근 소식 5건](review/home-news/live-third/home/desktop-actual-news.png)·[모바일 5건 전체](review/home-news/live-third/home/mobile-actual-news-unobscured.png)를 보고 “이 배치로 유지”로 승인했다. 이 승인은 최근 소식 5건 배치와 기존 A 색상·폰트·행 간격 유지에 한정하며 관리자 사용성·실제 기기·Whale·한국어 IME·운영 승인은 아니다. 검수 당시 자체/독립 JSON의 승인 대기는 당시 기록으로 보존한다. 이번 [종료 문서·보존 검사](review/m2-4-closeout/README.md)는 제품 검사·캡처·DB 쓰기를 재실행하지 않았다.

## 범위와 구현 구조

- Wagtail 기본 로그인·소식 목록·단일 리치 텍스트 편집기. 제목·공지/이벤트·짧은 설명·선택 대표 사진·본문을 관리한다.
- `/news/`, `/news/<숫자 ID>/`는 현재 공개한 리비전만 읽는다. 수정 초안은 기존 공개 제목·본문·사진·날짜를 바꾸지 않는다. 관리자 로그인 중에도 일반 공개 URL은 같은 규칙이다.
- 미리보기는 편집 권한을 확인한다. HTML·미디어·관리자 응답은 `no-store`로 제공한다.
- 원본 이미지는 공개하지 않는다. 변환본도 현재 공개 소식·브랜드·지점 시설·공개 지점에 소속된 공개 트레이너에서 사용하는 이미지일 때만 익명 요청에 제공한다. 초안·미사용 이미지와 관리자 썸네일은 이미지 선택 권한을 확인한다. 마지막 공개 사용처 철회 후 새 익명 요청은 차단한다. 이미 받은 파일을 회수하는 기능은 아니다.
- 기존 사진 파일을 덮어쓰는 대신 새 이미지를 등록해 글의 참조를 바꾼다. 편집 저장은 리비전 확인과 PostgreSQL 행 잠금으로 오래된 화면의 덮어쓰기를 차단한다.
- 입력 직후 저장할 때 본문이 누락되지 않도록 제출 전에 편집 값을 반영한다. 공개 UI의 기존 CSS는 그대로 두고 CMS 사진에만 원본 비율을 유지하는 반응형 높이 규칙을 추가했다.
- 게시글 작성/편집의 본문 아래 **‘팝업 설정’**에서 사용·한국 시간 시작/종료를 **‘팝업 설정 적용’**으로 별도 저장한다. 새 글은 먼저 초안 저장한다. 설정 적용은 본문 입력을 제출하거나 게시하지 않는다. 이후 본문 저장·게시도 설정을 되돌리지 않는다. 버전 충돌·게시 권한·기존 편집 잠금을 검사한다.
- 공개 홈 `/`와 `/popups/<글 ID>/`, `/popups/<글 ID>/data/`는 실제 DB·서버 시각·현재 공개 리비전을 사용한다. 중첩 전체 허용, 최초 초안 저장 순서, 전 지점 공통이다. PC 별도 창/모바일 순차 레이어, 차단/실패 시에만 수동 텍스트 링크, 한국 시간 오늘 숨김을 적용했다. 최신 사용자 확인에 따라 **일반 닫기 후 새로고침·홈 재방문 때 다시 자동 노출**한다. 예전 탭당 한 번 제한은 폐기했다. [게시글 연결 검수](review/popups/README.md) · [최신 재노출 검수](review/popup-revisit/README.md).
- PC 팝업은 `popup-sizing.js`에서 기준 폭과 내용 높이를 맞추고 비동기 창 크기 변경 뒤 다시 측정한다. `popup-window.css`는 CMS 팝업에만 적용하며 크기 변경 제한 시에도 하단 컨트롤을 내용 다음에 붙인다. 정적 프로토타입 소스는 수정하지 않았다. [실제 창 크기 검수](review/popup-sizing/README.md).
- ‘브랜드·홈’은 사이트 공통 한 묶음의 브랜드명·선택 로고·소개 제목/설명·선택 대표 사진/대체 설명/중심을 관리한다. 공개 필수값은 사용자 확인으로 브랜드명·소개 제목이며 미완성 초안 저장을 허용한다. 홈과 실제 소식/팝업의 브랜드 표시는 공개 리비전만 사용하고 초안 미리보기에서는 자동 팝업을 실행하지 않는다. [이번 검수 기록](review/brand-home/README.md).
- 지점+시설은 `Branch`/`FacilityImage`의 한 클러스터 리비전으로 초안·미리보기·공개·철회한다. 실제 `/`·`/branches/`에 공개본만 연결하고 소식·팝업도 동적 공개 지점 선택을 사용한다. `main` 본점 정체성은 고정하고 공개 본점 우선·추가 지점의 공개 표시 순서를 적용한다. 지점명·주소·운영시간만 공개 필수이며 미완성 초안은 허용한다. 0곳·없는 선택 사진/연락처/트레이너는 안내 또는 숨김 처리한다. [지점 검수 기록](review/branches/README.md). 트레이너는 M2-3에서 아래 별도 편집 단위로 연결했으며 홈 최근 소식은 M2-4에서 현재 공개 글 최대 5건에 연결했다. `prototype/` 원본과 기존 검수는 보존한다.

- 트레이너는 지점 편집의 ‘소속 트레이너 관리/등록’에서 진입한다. 신규 지점은 먼저 초안 저장하며 등록 화면에 현재 지점을 미리 선택한다. 프로필·단일 약력은 지점/시설과 별도 저장·리비전 단위다. 이름·소속만 공개 필수, 나머지는 선택·빈 영역 숨김이다. 최신 초안을 보여주는 관리자 목록과 현재 공개 리비전을 사용하는 고객 조회를 구분한다. 소속 이동·수동 순서·약력·사진 초안은 공개본을 바꾸지 않으며 프로필과 소속 지점의 이중 공개 조건을 사진 사용처에도 적용한다.

```text
backend/
├── pyproject.toml / uv.lock / .python-version
├── compose.yaml                       # M1 전용 PostgreSQL
├── config/                            # 로컬 앱 설정·URL
├── news/
│   ├── models.py / migrations/         # 소식 리비전·비공개 이미지
│   ├── publication.py / views.py       # 현재 공개본·미디어 접근 경계
│   ├── wagtail_hooks.py                # 소식 관리자·저장 충돌 처리
│   ├── templates/news/ / static/news/  # 공개 목록·상세·지점 맥락
│   └── tests/                         # 서버·실제 DB 동시 저장 검사
├── scripts/                           # 로컬 준비·브라우저 검수
└── review/                            # 이번 마일스톤 검수 결과·캡처
```

## 버전과 로컬 준비

2026-10-10 공식 호환성 문서를 확인하고 Python **3.13.15**, Django **5.2.18**, Wagtail **7.4.3**, PostgreSQL **17.11**로 실행했다. Python은 `.python-version`, Python 패키지는 `uv.lock`, DB 이미지는 Compose의 digest로 고정했다. [Python 릴리스](https://www.python.org/downloads/release/python-31315/), [Django 5.2 호환성](https://docs.djangoproject.com/en/5.2/releases/5.2/), [Django 릴리스 목록](https://www.djangoproject.com/download/), [Wagtail 7.4 호환성](https://docs.wagtail.org/en/stable-7.4.x/releases/7.4.html).

로컬에 `uv`, Docker/Compose, Python 3가 필요하다. 프로젝트 루트에서 아래 순서로 실행한다. 준비 스크립트와 초기 데이터 명령은 기존 비밀값·계정·사용자 편집을 초기화하지 않는다.

```bash
cd backend
uv sync --locked
python3 scripts/prepare_local.py
docker compose --env-file .env.local up -d --wait
uv run python manage.py migrate
uv run python manage.py bootstrap_review
uv run python manage.py bootstrap_brand_review
uv run python manage.py bootstrap_branch_review
uv run python manage.py bootstrap_trainer_review
uv run python manage.py runserver 127.0.0.1:8768 --noreload --insecure
```

DB는 M1 전용 프로젝트 `y3gym-v2-m1`, 볼륨 `y3gym-v2-m1_database-data`, `127.0.0.1:55438`을 사용한다. 작업 시작 전에 있던 `55437`의 DB/컨테이너는 변경하지 않았다. 볼륨 삭제·초기화 명령을 실행하지 않는다.

기존 정적 검수와 이전 홈 주소를 확인하려면 **프로젝트 루트의 별도 터미널**에서 실행한다. 기존 `prototype/npm start` 서버와 같은 포트를 사용하므로 동시에 실행하지 않는다.

```bash
python3 backend/scripts/serve-prototype.py
```

- [CMS 로그인](http://localhost:8768/admin/)
- [브랜드·홈 관리](http://localhost:8768/admin/snippets/news/brandcontent/) → 한 묶음 선택 → 초안 저장·미리보기·공개·공개 철회
- [지점·시설 관리](http://localhost:8768/admin/snippets/news/branch/) → 지점 작성/편집 → 시설 사진 함께 초안·미리보기·공개·철회
- [실제 지점 안내](http://localhost:8768/branches/?branch=second)
- [실제 공개 홈](http://localhost:8768/?branch=second)
- [CMS 공개 소식](http://localhost:8768/news/?branch=second)
- [이전 홈 주소](http://localhost:8767/?branch=second) — 위 서버에서 실제 홈으로 연결. `/branches.html`, `/review/` 등은 보존한 프로토타입 파일 제공

`prototype/`에서 `npm start`를 대신 실행하면 원본 정적 홈을 그대로 제공한다. 실제 팝업 검증은 `8768/`에서 해야 한다. 팝업 검토용 TEST 글 ID·기간은 [현재 검수 기록](review/popups/checks.json)에 있다. 예시 기간 종료 후에도 글은 공개되고 팝업만 사라진다. 홈의 새로고침·재방문마다 자동 노출을 다시 시도하며 오늘 숨김을 선택한 글만 제외한다.

로컬 검토 계정은 `cms-review-editor`와 `cms-review-admin`이다. 비밀번호는 **이 폴더의 `.local-credentials`**에 JSON으로 저장하며 터미널·문서·검수 결과에 출력하지 않는다. `.env.local`과 함께 Git에서 제외하고 파일 권한은 0600으로 생성한다. 운영자는 소식·브랜드·지점·트레이너의 편집·공개·철회와 이미지 등록·선택을 사용할 수 있다. 트레이너의 기존 패턴 모델 권한만 추가하며 계정·운영 권한 관리를 확대하지 않는다. 지점 작성 권한을 추가하며 삭제·본점 교체·예약게시 권한/화면을 확대하지 않는다. 브랜드 초기화 명령은 기존 그룹 권한에 필요한 권한만 추가하며 브랜드 콘텐츠가 이미 있으면 리비전·미디어를 다시 생성하지 않는다. 지점 초기화도 기존 지점이 있으면 콘텐츠·리비전·미디어를 덮어쓰지 않으며 운영자 그룹에 지점 권한 4개만 추가한다. 최초 값은 승인된 임시 소개·본점/예시점 자료이며 실제 운영 자료가 아니다. 삭제 권한은 부여하지 않았다. 시스템 관리자 계정은 로컬 구성 확인용이며 최종 운영 역할 정책을 뜻하지 않는다.

`--insecure`는 `DEBUG=False` 상태에서 로컬 정적 파일만 제공하기 위한 Django 개발 서버 옵션이다. 이 구성은 운영 서버·HTTPS·배포·백업을 구현한 것이 아니다. 미디어를 정적 서버로 별도 공개하면 접근 통제가 우회되므로 현재 미디어 요청은 앱의 보호된 경로만 사용한다.

## 검증 재현

M2-4는 `news/home.py`와 [홈 소식 행 템플릿](news/templates/news/home_news.html)에서 기존 `published_posts()`를 재사용한다. 수정 초안과 미공개 글은 홈·목록·브랜드 미리보기에 노출하지 않고 철회하면 홈에서 제거한다. 실제 사이트 읽기와 격리된 테스트 DB의 5건/빈 상태를 구분한다. 새 명령·출력 경로·실패 이력은 [홈 소식 검수](review/home-news/README.md)를 따른다. 공통 브라우저 fixture 3개·기존 검수는 보존한다.


M2-3-R1은 [새 보완 기록](review/trainers-repair/README.md)의 명령·출력 경로를 따른다. 검색은 최신 리비전 이름/소개를 사용하며 최신 리비전이 없을 때만 모델 값을 검색한다. 빈 초안 값은 이전 공개 값으로 되돌리지 않는다. 기존 Wagtail 검색 입력·공개/소속 필터·페이지 이동을 유지한다. 원 독립 FAIL/재현 도구·이전 캡처를 덮어쓰지 않는다. M2-4 홈 최대 5건/최초 공개 최신순 연결은 설계 지시로 로컬 구현했으며 [별도 자체 검수](review/home-news/README.md)에 기록한다. M2-4 독립 검증과 아래 특정 5건 배치 사용자 승인은 완료했으며 관리자 사용성/운영 검증은 별도 미완료다.

M2-3의 서버·브라우저·실제 앱 읽기·캡처는 [새 검수 기록](review/trainers/README.md)에 구분한다. 아래 재현은 새 출력 폴더를 지정하며 기존 FAIL·R1·M2-2 결과를 덮어쓰지 않는다.

```bash
# backend/에서 새 폴더 이름으로 실행
uv run --locked python review/trainers/run_checks.py --output regressions-new
Y3GYM_RUN_TRAINER_BROWSER=1 Y3GYM_TRAINER_REVIEW_DIR=review/trainers/browser-new uv run --locked python manage.py test news.tests.test_trainer_browser --noinput --verbosity 2
Y3GYM_TRAINER_REVIEW_DIR=review/trainers/live-new node scripts/review-trainers.mjs --live-read-only
```

`bootstrap_trainer_review`는 기존 main/second에 승인된 가상 A/B 각 1명·선택 사진/소개만 준비한다. 직급·약력을 만들어 넣지 않는다. 프로필이 이미 있으면 콘텐츠·리비전·미디어를 보존한다. 기존 공통 브랜드/지점 브라우저 fixture에는 트레이너 seed를 섞지 않고 새 트레이너 클래스에서만 명시적으로 추가한다.

후속 [독립 재검증의 실행 결과](review/branches-independent-recheck/verification.json)는 서버 79 PASS·옵트인 2 skip, 별도 독립 검사 13 PASS·기존 재현 1 PASS, 브랜드 7/지점 11흐름의 단독·합동·역순 PASS, 실제 앱 읽기 전용 5흐름·팝업 재노출 8흐름 PASS다. M2-2 종료 문서 작업에서는 이 검사를 재실행하지 않았다. 전역 포맷은 기존 `review/workflow-01/verify.py` 1개로 실패하고 범위 포맷·전체 lint는 통과했다. [문제·경고·미검증 목록](review/branches-independent-recheck/findings.json)과 [독립 검증 당시 DB·파일·index 보존](review/branches-independent-recheck/preservation-result.json)을 함께 읽는다. 실제 기기·Whale·한국어 IME·운영 환경·사용자 시각/사용성은 미검증이다.

M2-2-R1에서 브랜드/지점 옵트인 클래스는 공통 테스트 fixture로 소식·브랜드·공개 본점/예시점 2곳을 준비한다. 테스트 DB flush로 사라진 Wagtail Collection root도 테스트 안에서 복원하며 제품 초기화 명령은 바꾸지 않는다. 브랜드의 기존 7개 검수 흐름과 제품의 0지점 문의 숨김 정책을 유지한다. 단독·합동·반대 순서와 철회 교차 요청 결과는 [R1 검수 기록](review/branches-repair/README.md)에 있다. 이전 검수를 보존하며 지정 검사를 재현하려면 `backend/`에서 다음처럼 새 출력 폴더를 지정한다. 같은 이름의 근거는 덮어쓰지 않는다.

```bash
uv run --locked python review/branches-repair/run_checks.py --output regressions-new
```

서버 검사는 별도 테스트 DB를 만들고 끝나면 제거한다. 현재 로컬 앱 DB의 글을 초기화하지 않는다.

```bash
cd backend
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
uv run python manage.py test news.tests --noinput --verbosity 2
```

M2-2에서 `ruff check .`와 `ruff format --check news config scripts`는 통과했다. 전체 `ruff format --check .`는 작업 전부터 있던 `review/workflow-01/verify.py` 1개를 지적한다. 이전 검수 파일은 보존했으며 이 제한과 실제 실행 결과는 [M2-2 검수 기록](review/branches/README.md)에 구분한다. 현재 기본 서버 검사에서는 브랜드·지점·트레이너·홈 소식의 옵트인 브라우저 검사 4개를 건너뛴다.

브랜드 쓰기 브라우저 검수는 **별도 테스트 DB·임시 계정·임시 미디어**를 사용한다. 실행 중인 사이트의 데이터·계정과 기존 캡처는 보존하며 결과는 `review/brand-home/`에 쓴다. Node 스크립트를 단독으로 쓰기 모드 실행하면 거부한다. Playwright 준비는 아래 기존 안내와 같다.

```bash
cd backend
Y3GYM_RUN_BRAND_BROWSER=1 uv run python manage.py test news.tests.test_brand_browser --noinput --verbosity 1
node scripts/review-brand-home.mjs --live-read-only
```

둘째 명령은 실행 중인 `8768`에서 입력 화면·저장 전 미리보기·공개 홈을 확인하며 초안 저장/공개/철회를 실행하지 않는다. 결과는 `review/brand-home/live/`다. 팝업은 독립적인 브라우저 문맥에서만 임시 숨겨 소개 화면을 캡처하고 사용자 브라우저의 숨김 기록이나 DB 설정은 바꾸지 않는다. 기본 서버 검사에서는 이 브라우저 검사 1개를 건너뛰고 위 첫 명령으로 별도 실행한다.

M2-2 지점 쓰기 브라우저 검수도 별도 테스트 DB·임시 미디어·계정에서 수행한다. 실행 사이트는 읽기 전용으로 확인한다. 결과는 새 `review/branches/`에 두며 이전 검수 파일을 덮어쓰지 않는다.

```bash
cd backend
Y3GYM_RUN_BRANCH_BROWSER=1 uv run python manage.py test news.tests.test_branch_browser --noinput --verbosity 1
node scripts/review-branches.mjs --live-read-only
```

쓰기 스크립트 단독 실행·8768 대상 쓰기는 거부한다. 첫 명령은 테스트 지점의 초안·미리보기·공개·시설 재정렬/삭제/사진 선택·신규 지점·마지막 철회를 실제 관리자로 확인한다. 둘째 명령은 실행 DB를 읽어 홈/상세 PC·모바일·슬라이드·JavaScript 없는 탐색을 캡처한다. 사진 촬영용 브라우저의 팝업 숨김은 독립 문맥에만 기록하고 실제 팝업 설정을 바꾸지 않는다. 캡처·재실행 범위와 실패 이력은 [지점 검수 기록](review/branches/README.md)을 따른다.

브라우저 검수에는 두 서버와 초기 계정이 필요하다. 기존 `prototype/package-lock.json`의 Playwright를 재사용하며 프로토타입 HTML·캡처 생성 스크립트는 실행하지 않는다. 의존성이 없으면 먼저 `prototype/`에서 `npm ci`, `npx playwright install chromium`을 실행한다. 이번 팝업 연결 검증은 다음 명령이며 결과·캡처는 **`review/popups/`만 갱신**한다.

```bash
cd backend
node scripts/review-popups.mjs
node scripts/review-popup-edges.mjs
```

첫 명령은 실제 관리자 UI로 새 TEST 글 두 개를 만들고 자기 글만 저장·게시·설정·철회한다. 성공하면 그 두 글을 다시 공개하고 팝업을 24시간 검토 가능하게 남긴다. 기존 글과 프로토타입 검수 자료는 수정하지 않는다. 재실행은 새 TEST 글을 추가하며 기존 팝업도 보존한다. 둘째 명령은 현재 노출 가능한 예시를 읽어 짧은 모바일 화면·크기 전환·저장소 제한을 검사하고 DB는 변경하지 않는다. 현재 검토 대상의 ID·기간과 실제 결과는 [JSON](review/popups/checks.json)에 기록한다.

아래는 **기존 M1 브라우저 검수 명령**이다. 이번 팝업 작업에서는 M1 캡처를 보존하기 위해 재실행하지 않았다.

```bash
cd backend
node scripts/review-cms.mjs
```

이 명령은 테스트 글·이미지를 추가하고 해당 글을 마지막에 철회한다. 기존 글·이미지는 삭제하지 않는다. 실패 시 중간 상태가 남을 수 있으므로 [검수 JSON](review/checks.json)의 글 ID와 실패 단계를 확인한다. 재실행은 **`backend/review/`의 같은 이름 결과·캡처를 갱신**하며 기존 `prototype/review/`에는 쓰지 않는다.

실제 실행 결과와 캡처 목록, 미검증 항목은 [검수 기록](review/README.md)에 구분한다. 자동 통과는 관리자 사용성이나 디자인의 사용자 승인을 대신하지 않는다.

팝업 크기 회귀는 기존 DB를 읽기만 하며, 기간 내 공개 팝업 예시가 두 개 이상 필요하다. 화면이 표시되는 Chromium을 사용하므로 그래픽 세션(`DISPLAY`)이 필요하다. `viewport:null`과 브라우저의 실제 창 경계로 크기를 검증한다. 결과는 **`review/popup-sizing/`만 갱신**하며 과거 검수를 덮어쓰지 않는다.

```bash
cd backend
node scripts/review-popup-sizing.mjs
```

`--noreload` 서버에서 템플릿을 변경했다면 서버를 재시작해야 한다. 크기 수정에서는 재시작 후 새 CSS가 실제 응답에 포함되는 것을 확인했다. 현재는 일반 닫기 후 같은 탭에서 홈을 새로고침해도 다시 노출된다. 오늘 숨김만 한국 시간 다음 날 00시까지 유지하며, 이전 자동 시도 플래그는 지울 필요가 없다.

최신 재노출 회귀는 앱 DB를 읽기만 하며 브라우저 숨김은 별도 검수 컨텍스트에서만 설정한다. 아래 명령은 결과를 `review/popup-revisit/`에 저장해 이전 캡처·검수 기록을 보존한다.

```bash
cd backend
node scripts/review-popup-revisit.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-revisit/edges node scripts/review-popup-edges.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-revisit/sizing node scripts/review-popup-sizing.mjs
```

M1 당시 브라우저 결과는 `PASS_WITH_WARNINGS`다. 중복 이미지 업로드 확인에서 Wagtail 기본 탭 오류가 관측됐으며 해당 이미지 선택·공개 동작은 완료됐다. 이번 팝업 브라우저 9개 + 추가 3개 흐름은 `PASS`이며 업로드를 재현하지 않았으므로 당시 문제를 해결한 것으로 보고하지 않는다. 기존 CMS 17개를 포함한 서버 33개도 재실행해 통과했다. 자세한 발생 기록과 검증 한계는 각각의 검수 JSON에 남긴다.

PC 중앙 랜덤 배치 검수는 현재 공개 팝업을 읽기만 한다. 실제 창 경계와 시작 좌표 요청을 구분하며, 결과·캡처는 `review/popup-position/`에 저장한다. 아래 회귀 명령도 별도 출력 경로를 지정해 과거 기록을 보존한다. 위치·크기 명령은 화면이 표시되는 Chromium과 그래픽 세션이 필요하다.

```bash
cd backend
node scripts/review-popup-position.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-position/sizing node scripts/review-popup-sizing.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-position/revisit node scripts/review-popup-revisit.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-position/edges node scripts/review-popup-edges.mjs
```

이번 실행 결과와 이동 제한·실제 다른 브라우저의 미검증 항목은 [위치 검수 기록](review/popup-position/README.md)에 기록한다. 정적 원본 프로토타입과 이전 검수는 재생성하지 않는다.

## 이번 단계에서 하지 않은 일

프로필 삭제/복원·운영 계정 확대, 팝업용 별도 문구·사진 입력, 실제 로고·사진·연락처, 지도·전화·카카오톡 연동, 운영 배포·외부 저장소·CDN·백업은 미구현이다. 지점의 본점 우선·표시 순서·공개 필수값·마지막 철회는 사용자 답변으로 확정했다. 본점 교체·지점 삭제/복원, 소식 공개일 변경·목록 페이지당 10건의 운영 확정·삭제/복원·최종 운영 권한은 미결정이다. 홈 최대 5건·홈/목록 최초 공개 최신순·수정/재공개 순위 유지와 팝업 최초 등록 빠른순은 확정·구현했다. 브랜드는 공개 필수값만 이번에 확정했으며 삭제/복원 동작을 추가하지 않았다. 실제 기기와 Chromium 이외 브라우저, 한국어 IME 조합 입력, 운영 환경의 캐시·미디어 제공 경로는 별도 확인이 필요하다.
