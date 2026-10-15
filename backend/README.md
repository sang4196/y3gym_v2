# 소식 CMS · 팝업 · 브랜드/홈 · 지점/시설 · 트레이너 관리

**2026-10-14 기존 잔여물 정리:** 사용자 승인으로 완료 서버7개, legacy DB31개, 임시 폴더63개와 과거 bulk 결과물을 정리했다. 현재8776·원본성8769·canonical8767과 제품/현행 도구·원본 데이터는 보호했다. 과거 자료 링크의 ‘정리됨’은 결과 변경이 아니며 [현재 검증·원실패·한계 요약](review/README.md)과 [실제 정리·보류](review/cleanup-residue-01/README.md)를 따른다. 좁은 독립 확인을 완료했으며 기존 경고·관측 한계는 유지한다.

Django/Wagtail + PostgreSQL에서 소식·브랜드 소개·지점/시설·트레이너를 **초안 저장 → 미리보기 → 명시적 공개 → 수정 → 공개 철회**하고 글의 팝업 설정을 별도 적용하는 로컬 구현이다. 전체 제품·전체 관리자의 완성이 아니다. 승인된 공개 HTML·CSS·글꼴을 재사용하며 관리자 편집 경험의 사용자 확인은 아직 받지 않았다.

제품 기준은 [PRD](../docs/PRD.md), 승인된 공개 UI는 [디자인 문서](../prototype/DESIGN.md), 마일스톤과 미결정 사항은 [구현 계획](../docs/IMPLEMENTATION-PLAN.md)을 따른다.

**M2-2 종료 상태:** [초기 독립 검증 FAIL · 정리됨](review/README.md#정리-후-유지한-검증-요약) → [R1 보완·자체 검사 · 정리됨](review/README.md#정리-후-유지한-검증-요약) → [독립 재검증 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약). F01·F02·W01은 해결됐고 차단 결함은 없다. 기존 전역 포맷 경고 1개와 사용자 시각·관리자 사용성 미승인은 구분해 남긴다. M2-3 트레이너는 [범위·완료 기준](../docs/IMPLEMENTATION-PLAN.md#다음-단위-m2-3-트레이너-관리)에 따라 로컬 구현했고 [이번 자체 검사·캡처·보존 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 기록한다. 이후 [초기 독립 검증 FAIL · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 최신 초안 이름/소개 검색 불일치를 확인해 [M2-3-R1 검색·기록 보완 · 정리됨](review/README.md#정리-후-유지한-검증-요약)을 수행했다. 이후 [독립 재검증 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)로 F01/P2·W02~W04 해결·새 차단 결함 없음을 확인했다. W01 기존 전역 format 경고 1개는 유지하며 관리자 사용성 승인은 별개다. 2026-10-10 사용자가 검토한 PC/모바일 캡처의 직급·약력 배치는 “이 배치로 유지”로 승인했다.

**M2-3 종료 문서:** [독립 재검증 결과 · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 전체 101개 중 98 PASS·3 opt-in SKIP, 트레이너 13 PASS, 원 재현 재사용 1 PASS, 신규 독립 의미 검사 3 PASS·검색 응답 81건·다음 링크 4건, 브라우저 기존 10/검색 7흐름, 실제 지점 5/관리자 GET 4건이다. 당시 [종료 문서 검사 · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 이 결과를 읽고 경로·상태·보존만 확인하며 제품 검사·캡처·DB 쓰기를 수행하지 않았다. 첫 체크포인트 `46ef337` push 이후 M2-3·R1/종료 문서는 설계 검토와 Git 담당 반영을 거쳐 `b517cc209f0f3ac66d7b602450cf5d9dca16d58c`으로 main → origin/main push 완료했다. 이는 설계가 전달한 Git 결과이며 개발에서 Git 쓰기·인증/영구 설정 변경을 수행하지 않았다. 이 종료 문서 작성 시점의 M2-4 변경은 미커밋이며 이후 Git 반영 결과와 구분한다. 최종 독립/승인 상태는 아래에 구분한다.

**M2-4 종료 상태:** [개발 자체 검사 · 정리됨](review/README.md#정리-후-유지한-검증-요약) 뒤 [독립 검증 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)를 완료했다. 요구사항 위반·새 제품 결함은 없으며 기존 포맷 W01만 남는다. 독립 전체 서버 110개 중 106 PASS·4 opt-in SKIP이며 홈 8건은 이 안에 포함된다. 신규 독립 의미 검사 3 PASS, 브랜드 7/지점 11/홈 8/팝업 재방문 8+edges 3·추가 팝업 6건 PC/모바일 2흐름·실제 읽기 7흐름을 확인한 보고서다. 최초 독립 2 FAIL은 미래 시각에 의한 세션 만료/공개 전 stale 지점 객체라는 검사 도구 문제로 보완했으며 초기 로그는 보존했다. 2026-10-10 사용자는 [PC 최근 소식 5건](review/home-news/live-third/home/desktop-actual-news.png)·[모바일 5건 전체](review/home-news/live-third/home/mobile-actual-news-unobscured.png)를 보고 “이 배치로 유지”로 승인했다. 이 승인은 최근 소식 5건 배치와 기존 A 색상·폰트·행 간격 유지에 한정하며 관리자 사용성·실제 기기·Whale·한국어 IME·운영 승인은 아니다. 검수 당시 자체/독립 JSON의 승인 대기는 당시 기록으로 보존한다. 이번 [종료 문서·보존 검사 · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 제품 검사·캡처·DB 쓰기를 재실행하지 않았다.

## 범위와 구현 구조

- Wagtail 기본 로그인·소식 목록·단일 리치 텍스트 편집기. 제목·공지/이벤트·짧은 설명·선택 대표 사진·본문을 관리한다.
- `/news/`, `/news/<숫자 ID>/`는 현재 공개한 리비전만 읽는다. 수정 초안은 기존 공개 제목·본문·사진·날짜를 바꾸지 않는다. 관리자 로그인 중에도 일반 공개 URL은 같은 규칙이다.
- 미리보기는 편집 권한을 확인한다. HTML·미디어·관리자 응답은 `no-store`로 제공한다.
- 원본 이미지는 공개하지 않는다. 변환본도 현재 공개 소식·브랜드·지점 시설·공개 지점에 소속된 공개 트레이너에서 사용하는 이미지일 때만 익명 요청에 제공한다. 초안·미사용 이미지와 관리자 썸네일은 이미지 선택 권한을 확인한다. 마지막 공개 사용처 철회 후 새 익명 요청은 차단한다. 이미 받은 파일을 회수하는 기능은 아니다.
- 기존 사진 파일을 덮어쓰는 대신 새 이미지를 등록해 글의 참조를 바꾼다. 편집 저장은 리비전 확인과 PostgreSQL 행 잠금으로 오래된 화면의 덮어쓰기를 차단한다.
- 입력 직후 저장할 때 본문이 누락되지 않도록 제출 전에 편집 값을 반영한다. 공개 UI의 기존 CSS는 그대로 두고 CMS 사진에만 원본 비율을 유지하는 반응형 높이 규칙을 추가했다.
- 게시글 작성/편집의 본문 아래 **‘팝업 설정’**에서 사용·한국 시간 시작/종료를 **‘팝업 설정 적용’**으로 별도 저장한다. 새 글은 먼저 초안 저장한다. 설정 적용은 본문 입력을 제출하거나 게시하지 않는다. 이후 본문 저장·게시도 설정을 되돌리지 않는다. 버전 충돌·게시 권한·기존 편집 잠금을 검사한다.
- 공개 홈 `/`와 `/popups/<글 ID>/`, `/popups/<글 ID>/data/`는 실제 DB·서버 시각·현재 공개 리비전을 사용한다. 중첩 전체 허용, 최초 초안 저장 순서, 전 지점 공통이다. PC 별도 창/모바일 순차 레이어, 차단/실패 시에만 수동 텍스트 링크, 한국 시간 오늘 숨김을 적용했다. 최신 사용자 확인에 따라 **일반 닫기 후 새로고침·홈 재방문 때 다시 자동 노출**한다. 예전 탭당 한 번 제한은 폐기했다. [게시글 연결 검수 · 정리됨](review/README.md#정리-후-유지한-검증-요약) · [최신 재노출 검수 · 정리됨](review/README.md#정리-후-유지한-검증-요약).
- PC 팝업은 `popup-sizing.js`에서 기준 폭과 내용 높이를 맞추고 비동기 창 크기 변경 뒤 다시 측정한다. `popup-window.css`는 CMS 팝업에만 적용하며 크기 변경 제한 시에도 하단 컨트롤을 내용 다음에 붙인다. 정적 프로토타입 소스는 수정하지 않았다. [실제 창 크기 검수 · 정리됨](review/README.md#정리-후-유지한-검증-요약).
- ‘브랜드·홈’은 사이트 공통 한 묶음의 브랜드명·선택 로고·소개 제목/설명·선택 대표 사진/대체 설명/중심을 관리한다. 공개 필수값은 사용자 확인으로 브랜드명·소개 제목이며 미완성 초안 저장을 허용한다. 홈과 실제 소식/팝업의 브랜드 표시는 공개 리비전만 사용하고 초안 미리보기에서는 자동 팝업을 실행하지 않는다. [이번 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약).
- 지점+시설은 `Branch`/`FacilityImage`의 한 클러스터 리비전으로 초안·미리보기·공개·철회한다. 실제 `/`·`/branches/`에 공개본만 연결하고 소식·팝업도 동적 공개 지점 선택을 사용한다. `main` 본점 정체성은 고정하고 공개 본점 우선·추가 지점의 공개 표시 순서를 적용한다. 지점명·주소·운영시간만 공개 필수이며 미완성 초안은 허용한다. 0곳·없는 선택 사진/연락처/트레이너는 안내 또는 숨김 처리한다. [지점 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약). 트레이너는 M2-3에서 아래 별도 편집 단위로 연결했으며 홈 최근 소식은 M2-4에서 현재 공개 글 최대 5건에 연결했다. `prototype/` 원본과 기존 검수는 보존한다.

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

## 개발과 운영 설정 — OPS-01

현재 설정은 [runtime.py](config/runtime.py)에서 읽고 [settings.py](config/settings.py)에 연결한다. **기본은 기존 development 동작**이며 이때만 `.env.local`을 읽는다. 운영은 프로세스 환경에 `Y3GYM_ENV=production`을 명시하고 필요한 값을 별도로 주입한다. production은 `.env.local`을 읽지 않으며, 그 파일로 모드를 production으로 바꾸려 해도 오류로 중단한다. 값이 빠지거나 잘못되면 값 자체를 출력하지 않고 환경변수 이름/오류 종류를 알린다.

[.env.example](.env.example)은 비밀값 없는 참고 목록이며 자동 로딩/바로 실행하는 운영 설정이 아니다. 필수 값은 의도적으로 비워 두었다. 실제 도메인·인프라·DB 배치·secret 공급 방식·운영 계정·백업/복구를 선택한 뒤 값을 확정해야 한다. 개발/QA secret과 DB를 재사용하지 않는다. 운영 로더가 실제 개발 비밀값을 읽어 비교하는 방식은 사용하지 않는다.

| production 필수 값 | 확인하는 경계 |
| --- | --- |
| `DJANGO_SECRET_KEY` | 50자 이상·서로 다른 문자5개 이상, Django insecure prefix/명백한 개발·템플릿 값 거절. 새 운영 secret을 공급 |
| `Y3GYM_DB_NAME`, `Y3GYM_DB_USER`, `Y3GYM_DB_PASSWORD`, `Y3GYM_DB_HOST`, `Y3GYM_DB_PORT` | 누락·템플릿 값/잘못된 host·port 거절. `test_` 이름과 `y3gym_m1`/`y3gym_v2_m1` 거절. 명시한 loopback DB host 자체는 허용하며 외부 DB 배치를 강제하지 않음 |
| `Y3GYM_ALLOWED_HOSTS` | 쉼표로 나눈 정확한 host. wildcard·scheme/path/port·localhost/loopback/testserver 거절. IPv6 host는 대괄호 사용 |
| `Y3GYM_ADMIN_ORIGIN` | 허용 host에 속한 정확한 HTTPS 원점. 경로·query·fragment·userinfo 거절. `WAGTAILADMIN_BASE_URL`에 연결 |
| `Y3GYM_MEDIA_ROOT`, `Y3GYM_STATIC_ROOT` | 전용 절대 경로. 서로 같거나 포함하는 경로·symlink로 숨긴 중첩·소스/QA 전체를 포함하는 root 거절. private media가 정적 소스에 들어가는 설정도 거절 |

선택 값은 `Y3GYM_PROTOTYPE_URL`(production의 빈 값은 같은 사이트 상대 경로), `Y3GYM_CSRF_TRUSTED_ORIGINS`(명시한 HTTPS 원점만), `Y3GYM_LOG_LEVEL`(기본INFO·콘솔 Django 로그), `Y3GYM_KAKAO_MAP_JS_KEY`다. `DEBUG=False`를 유지한다. production은 HTTPS redirect·secure session/CSRF cookie를 사용한다. 개발 cookie 이름은 유지하고 운영 이름을 분리한다. 실제 로그 수집/보관 서비스는 정하지 않았다.

`Y3GYM_TRUST_PROXY_HTTPS=0`이 기본이다. **실제 신뢰 프록시가 클라이언트 header를 제거하고 HTTPS 상태를 올바르게 설정함을 확인한 뒤에만** `1`로 설정한다. 이때만 `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https")`를 적용한다. `Y3GYM_SECURE_HSTS_SECONDS=0`, subdomain/preload=False는 미결정 상태이며 HSTS 기간·하위 도메인 정책을 이번에 확정하지 않았다.

운영 환경을 주입한 뒤 backend에서 사용하는 Django 명령은 다음과 같다. `.env.example`을 그대로 적용하면 필수 값 오류가 나며, 아래 검증을 실제 운영 설치/제공 완료로 해석하지 않는다.

```bash
Y3GYM_ENV=production .venv/bin/python -B manage.py check --deploy
Y3GYM_ENV=production .venv/bin/python -B manage.py collectstatic --noinput --verbosity 0 \
  --ignore node_modules --ignore review --ignore templates --ignore scripts \
  --ignore '*.md' --ignore 'package*.json'
```

기존 `STATICFILES_DIRS`의 prototype 입력에는 개발 자료도 있으므로 **위 실제 검증한 ignore 인자를 포함한다.** 기본 collectstatic을 무조건 운영 수집으로 사용하지 않는다. 앱은 계속 backend와 형제 `prototype/`의 실행 HTML·JS/CSS·assets를 읽으므로 두 소스의 배치 관계를 유지한다. 실제 정적 서버는 수집한 `STATIC_ROOT`만 제공해야 한다. **`/media`·`MEDIA_ROOT`·저장소 루트·`.local/qa`를 별도 공개 mount하지 않는다.** 원본과 변환 이미지는 기존 권한 view를 계속 통한다. 서버/프록시 설정 파일·배포 도구·새 의존성을 추가하지 않았다.

### 이번 실제 검증과 남은 선택

[OPS-01 개발 근거](review/ops-01/README.md): 경계12 PASS, owned DB의 migrate/연결·로그인·공개/비공개 이미지·권한10확인 PASS, production 설정 로딩/deploy check exit0, 정적263파일 수집과 관리자 로그인 직접 assets18개 존재 확인. source/QA/private 자료와 node_modules/review/templates/scripts sentinel은 수집되지 않았다. 기본 GET은 자기 run에만 수행했다.

production은 `test_` DB를 거절하므로 **production은 설정 로딩·deploy checks·collectstatic만**, 실제 DB 연결/실행·이미지는 **development의 고유 owned DB**로 구분했다. production 검사의 비-test DB 이름은 생성/접속하지 않았다. deploy 경고 W004(HSTS 미정)·W019(기존 SAMEORIGIN/미리보기 정책)는 원 상태로 기록하며 숨기지 않는다.

최종 `news.tests`는 **1회164/164 PASS·4opt-in 실행·skip0**다. 이전148/148·142/142와 합산하지 않는다. 별도 새 venv의 `uv sync --locked --no-python-downloads --link-mode copy`와 버전/Django check도 PASS이며 원본 `.venv`·lock은 sync/변경하지 않았다. 새 venv/cache는 자기 run 안에서 검증 후 제거하고 기존 CLI로 own4run·생성 DB6개·프로세스를 정리했다. 정확한 명령·구분·원 후처리 오류는 [verification](review/ops-01/verification.json)에 있다.

이는 격리 runserver와 수집 검증이다. 실제 WSGI/ASGI 서버·TLS·DNS·신뢰 프록시·정적/미디어 제공·운영 DB 연결/권한·실자료·백업/복구·배포는 미검증이다. 해당 인프라와 도메인/secret/계정 정책을 결정하고 운영 전 검증할 때 사용자 선택이 필요하다. [독립 최종 PASS_WITH_DEPLOYMENT_LIMITS](review/ops-01/independent-verification.json)·설계 검토를 완료했다. 독립 선택16/16·후속 설정8/HTTP16 PASS, 정적263파일/private·QA 제외와 own2run/DB4개 DELETED를 확인했다. 개발 전체164/164·새 설치는 근거 읽기이며 독립 재실행/합산이 아니다. 초기 metadata Boolean-vs-SHA 가정·RequestFactory 초기화 순서 관찰 오류2건은 원기록과 후속을 유지하며 새 제품/설정 결함은0이다. W004/W019/W01과 위 실제 운영 미검증은 유지한다.

## 버전과 로컬 준비

2026-10-10 공식 호환성 문서를 확인하고 Python **3.13.15**, Django **5.2.18**, Wagtail **7.4.3**, PostgreSQL **17.11**로 실행했다. Python은 `.python-version`, Python 패키지는 `uv.lock`, DB 이미지는 Compose의 digest로 고정했다. [Python 릴리스](https://www.python.org/downloads/release/python-31315/), [Django 5.2 호환성](https://docs.djangoproject.com/en/5.2/releases/5.2/), [Django 릴리스 목록](https://www.djangoproject.com/download/), [Wagtail 7.4 호환성](https://docs.wagtail.org/en/stable-7.4.x/releases/7.4.html).

로컬에 `uv`, Docker/Compose, Python 3가 필요하다. 프로젝트 루트에서 아래 순서로 실행한다. 준비 스크립트와 초기 데이터 명령은 기존 비밀값·계정·사용자 편집을 초기화하지 않는다.

아래는 최초 로컬 앱 준비 안내다. 이미 준비된 환경에서 **새 QA 환경을 만들 때는 이 준비/seed 명령을 반복하지 않고 [관리 CLI](#qa-환경-생성실행정리)를 사용한다.** 기존 검토 서버의 재시작·초기화·데이터 변경을 허용하는 안내가 아니다.

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

`prototype/`에서 `npm start`를 대신 실행하면 원본 정적 홈을 그대로 제공한다. 실제 팝업 검증은 `8768/`에서 해야 한다. 팝업 검토용 TEST 글 ID·기간은 [현재 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 있다. 예시 기간 종료 후에도 글은 공개되고 팝업만 사라진다. 홈의 새로고침·재방문마다 자동 노출을 다시 시도하며 오늘 숨김을 선택한 글만 제외한다.

로컬 검토 계정은 `cms-review-editor`와 `cms-review-admin`이다. 비밀번호는 **이 폴더의 `.local-credentials`**에 JSON으로 저장하며 터미널·문서·검수 결과에 출력하지 않는다. `.env.local`과 함께 Git에서 제외하고 파일 권한은 0600으로 생성한다. 운영자는 소식·브랜드·지점·트레이너의 편집·공개·철회와 이미지 등록·선택을 사용할 수 있다. 트레이너의 기존 패턴 모델 권한만 추가하며 계정·운영 권한 관리를 확대하지 않는다. 지점 작성 권한을 추가하며 삭제·본점 교체·예약게시 권한/화면을 확대하지 않는다. 브랜드 초기화 명령은 기존 그룹 권한에 필요한 권한만 추가하며 브랜드 콘텐츠가 이미 있으면 리비전·미디어를 다시 생성하지 않는다. 지점 초기화도 기존 지점이 있으면 콘텐츠·리비전·미디어를 덮어쓰지 않으며 운영자 그룹에 지점 권한 4개만 추가한다. 최초 값은 승인된 임시 소개·본점/예시점 자료이며 실제 운영 자료가 아니다. 삭제 권한은 부여하지 않았다. 시스템 관리자 계정은 로컬 구성 확인용이며 최종 운영 역할 정책을 뜻하지 않는다.

`--insecure`는 `DEBUG=False` 상태에서 로컬 정적 파일만 제공하기 위한 Django 개발 서버 옵션이다. 이 구성은 운영 서버·HTTPS·배포·백업을 구현한 것이 아니다. 미디어를 정적 서버로 별도 공개하면 접근 통제가 우회되므로 현재 미디어 요청은 앱의 보호된 경로만 사용한다.

## 검증 재현

현재 새 서버/브라우저 QA의 기본 생성·실행·정리 경로는 아래 관리 CLI다. `news.tests`와 기존 opt-in 클래스·fixture·Playwright helper를 재사용하고, 현재 dirty/untracked 소스를 run 내부에 복사한다. 이번 문서 마감에서는 제품 검사나 명령을 재실행하지 않았다. 과거 bare `manage.py test`·`/tmp` 스크립트·고정 출력 경로는 뒤의 당시 재현 자료로 구분한다.

### QA 환경 생성·실행·정리

**전제:** Linux/WSL의 procfs와 pidfd, 기존 `backend/.venv`, 준비된 로컬 PostgreSQL compose 서비스와 `backend/.env.local`, Node 및 기존 Playwright 패키지/브라우저 설치가 필요하다. 도구는 기존 의존성·브라우저 바이너리를 읽기 전용으로 재사용하며 설치/다운로드하지 않는다. 기존 compose의 loopback PostgreSQL만 사용하고 DB 생성·COMMENT·정리 권한이 필요하다. 실제 배포 환경을 준비하는 명령이 아니다.

관리 코드는 [qa_lifecycle.py](scripts/qa_lifecycle.py), [Django runner](scripts/qa_test_runner.py), [비밀값 제거](scripts/qa_redaction.py), [브라우저 loader](scripts/qa_browser_loader.mjs)·[resolver](scripts/qa_browser_resolver.mjs)·[guard](scripts/qa_browser_guard.mjs)다. 아래 명령은 모두 **프로젝트 루트** 기준이며 `uv sync`, 원본 seed, 기존 서버 제어를 포함하지 않는다.

```bash
# 기본 서버 검사. 기존 opt-in 4개는 별도 지정하지 않으면 건너뛴다.
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py auto --purpose '서버 QA' --tests news.tests
# 선택한 기존 브라우저 검사만 함께 실행
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py auto --purpose '헤더·지점 QA' --tests news.tests.test_header_home news.tests.test_branch_browser --browser branch
# 등록된 run과 소유 프로세스·DB 관찰·보존 사유
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py status
```

`--browser`는 `brand`, `branch`, `trainer`, `home_news` 중 필요한 값만 반복 지정한다. 이것이 검사 라벨을 추가하지는 않으므로 해당 기존 테스트도 `--tests`에 지정한다. `auto --command <실행파일> <인자...>`는 shell 없이 argv를 실행하는 경로이며, DB 검사용 자동 provision은 `--tests` 경로에서 수행한다.

기본 경로는 프로젝트 `.local/qa/<run-id>`다. 관리 디렉터리는 0700, 제어/비밀 파일은 0600이며 현재 소스 복사본·고유 설정·계정·미디어·캐시·쿠키 이름·TMPDIR·브라우저 프로필·출력을 이 run에 둔다. `source-manifest.json`이 복사한 소스를 기록한다. 원본 `.env.local`, `.local-credentials`, `.private-media`, `.git`, `.local`, 의존성 디렉터리 및 과거 캡처를 복사하지 않는다. 기존 DB 접속 비밀값은 원본 설정에서 메모리로 읽고, 앱 DB 이름은 관리 환경에서 run 전용으로 지정한다. 생성 설정을 CLI 밖에서 직접 실행하는 방식은 지원 안내에 포함하지 않는다.

PostgreSQL **물리 파일은 기존 서비스 볼륨에 남는 예외**를 manifest에 명시한다. 논리 본 DB와 Django runner DB는 각각 고유 이름·OID·소유 토큰 COMMENT로 관리한다. 원본 DB 대체나 기존 이름 채택은 거절하며 클러스터·볼륨 정책은 바꾸지 않는다. marker/registry·canonical 경로·inode/UID·토큰, PID/starttime/cwd/exe/argv hash/boot ID를 확인하고 조회 불가·symlink·다른 run·소유권 불일치는 정리를 거절한다.

수동 검토 환경은 다음 순서로 준비한다. 생성 결과의 실제 ID를 `QA_RUN_ID`에 넣으며 아래 자리표시자를 그대로 실행하지 않는다. fixture는 합성 TEST 자료이며 실제 영업 정보가 아니다.

```bash
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py create --mode manual --purpose '수동 검토'
QA_RUN_ID='<생성 결과의 실제 run-id>'
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py initialize "$QA_RUN_ID" --fixtures
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py start "$QA_RUN_ID"
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py status "$QA_RUN_ID"
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py stop "$QA_RUN_ID"
```

초기화는 한 번만 허용한다. `start` 결과의 origin을 사용하고 고정 포트나 기존 서버로 우회하지 않는다. 준비 완료는 소유 listener의 실제 `/admin/login/` HTTP 200 확인이다. 첫 공개 페이지의 cold rendition 완료까지 보장하지 않는다. 동일 환경 재시작은 `stop` → 종료/상태 확인 → `start`이며 DB·계정·미디어를 다시 초기화하지 않는다. 자격은 해당 run의 `.local-credentials`에서만 확인하고 비밀번호·키·쿠키·토큰은 문서/대화/캡처에 옮기지 않는다. `owner.json`, `secret-key`, 생성 설정과 raw 로그/DB/미디어/프로필도 private 자료다.

`MANUAL_PENDING`은 실행 중과 정지 후 모두 자동 삭제하지 않는다. `retain`은 이유와 해제 조건을 명시한다. 검토 완료·미사용 확인 후에만 `complete`, 새 dry-run, 정확한 plan 실행 순서로 정리한다. live driver/프로세스·DB 연결이 있거나 DB 소유권이 다르면 거절한다.

```bash
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py retain "$QA_RUN_ID" --reason '재현 검토 대기' --cleanup-condition '독립 검토 완료 후 미사용 확인'
# 검토가 끝난 해당 run에만 실행
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py complete "$QA_RUN_ID" --reason '검토 완료 및 미사용 확인'
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py cleanup "$QA_RUN_ID" --dry-run
QA_PLAN_ID='<직전 dry-run의 실제 plan_id>'
backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py cleanup "$QA_RUN_ID" --plan "$QA_PLAN_ID"
```

파일/상태가 바뀌면 이전 계획은 거절된다. 삭제 완료는 registry tombstone에 남기며 중복 정리는 no-op이다. `auto`는 성공·실패·예외 때 비밀값을 제거한 메시지·스택·검사 ID·실제 경로 근거를 `backend/review/qa-lifecycle/runs/<run-id>/`에 먼저 보존하고 소유 프로세스·두 DB·폴더를 정리한다. 원 실행 실패 exit를 유지하고 정리 실패를 별도 보고한다. 원 실행 성공 후 정리 실패는 exit 3이다. 의도적 실패 재현 보존은 `--retain-on-failure '이유' --cleanup-condition '해제 조건'`을 함께 지정한다. 강제 중단·일부 정리 실패는 status와 남은 자원을 확인하고 검토한 뒤 새 정확한 계획으로 처리한다.

실행 담당 보고에는 **실제 명령·검사 결과·원실패/후속 구분·두 DB/폴더/프로세스 정리 결과**, 또는 **보존 ID·이유·해제 조건**을 포함한다. 기존 `/tmp` 환경은 이번 관리 소유권으로 채택하지 않으며 별도 승인 없이 정지·삭제·DB drop하지 않는다. 앞선 수명주기 구현 당시 인벤토리의 조건부 후보4개·기존 환경 삭제0개는 그 시점 이력이다. 이후 사용자 승인으로 완료 잔여물을 선별 정리했으며 현재 결과는 검증 요약을 따른다.

2026-10-14 현재 [개발 인계·원실패 · 정리됨](review/README.md#정리-후-유지한-검증-요약)와 독립 [자체 검사 12/12](review/qa-lifecycle-independent/unittest-result.json), [헤더 4/4](review/qa-lifecycle-independent/auto-header.json), [브라우저 1/1·내부 11](review/qa-lifecycle-independent/auto-browser.json), [수동 9 PASS](review/qa-lifecycle-independent/manual-result.json), [새 Python4 Ruff lint/format·JS3 syntax](review/qa-lifecycle-independent/static-checks.json)를 설계가 검토했다. 브라우저 실제 Chrome identity·종료와 두 DB/폴더 정리를 확인했으며 [독립 보존 metadata 대조 PASS](review/qa-lifecycle-independent/preservation.json)까지 설계 검토를 완료했고 최종 독립 판정은 [PASS_WITH_OBSERVATION_LIMIT](review/qa-lifecycle-independent/verification.json)이며 [독립 보고](review/qa-lifecycle-independent/README.md)를 설계가 검토했다. 독립 [자기 run23개](review/qa-lifecycle-independent/own-runs-final.json)는 모두 DELETED·예약 DB 부재다. 기존 4,022파일 누락0·허용 failures 문서1변경, 보호75경로/68tmp의15,622파일 stat·15process identity·DB 이름/OID/comment hash·HEAD/index 동일 범위이며 raw DB 행·미디어 내용 재대조는 아니다. 개발 두 disposable fixture는 [원로그 archive 후 정리](review/qa-lifecycle/developer-fixture-closeout.json)했고 기존 `/tmp` 환경은 제어하지 않았다. [OBS01](review/qa-lifecycle-independent/failures.json)은 완료된 브라우저 로그의 origin 정규식 부재로 후처리 AssertionError가 난 원실패다. 실제 검사 재실행은 없었으며 새 origin 차단 negative·실제 중단 Chrome의 조회 거절 강제 시나리오는 미실행이다. 동적 브라우저 HTTP origin은 export에 없어 예약 origin과 실제 Chrome identity 근거를 구분한다. 개발의 최초 공개 GET TimeoutError와 별도 후속 PASS도 그대로 구분한다. 제품 전체 회귀·W01 수정·실기기/운영 검증으로 확대하지 않는다.

`.local/qa/`는 Git에서 제외한다. 실제 배포 도구는 없으며, 향후 배포 패키징에서는 `.local/qa`, 비밀 설정/계정, raw DB·미디어·브라우저 프로필 등 QA 실행 자료를 제외해야 한다. 배포 제외 검증을 완료했다는 뜻은 아니다.

### 이전 마일스톤의 실행·검사 기록

아래 명령·고정 출력 경로는 해당 당시 구현과 검사 이력이다. 신규 QA 생성의 기본 명령이 아니며, 원 환경·원 캡처를 대상으로 그대로 실행하지 않는다. 현재 신규 검사는 위 관리 CLI를 사용한다. 과거 수치·FAIL·제한을 최신 전체 통과로 재해석하지 않는다.

<details>
<summary>이전 bare test·브라우저 실행 이력 펼치기</summary>

완료 one-off review 코드와 결과물은 이번 선별 정리로 제거했으므로 아래 옛 review 명령은 당시 실행 기록이며 현재 재실행 안내가 아니다. 현재 명령은 위 관리 CLI를 따른다.

M2-4는 `news/home.py`와 [홈 소식 행 템플릿](news/templates/news/home_news.html)에서 기존 `published_posts()`를 재사용한다. 수정 초안과 미공개 글은 홈·목록·브랜드 미리보기에 노출하지 않고 철회하면 홈에서 제거한다. 실제 사이트 읽기와 격리된 테스트 DB의 5건/빈 상태를 구분한다. 새 명령·출력 경로·실패 이력은 [홈 소식 검수 · 정리됨](review/README.md#정리-후-유지한-검증-요약)를 따른다. 공통 브라우저 fixture 3개·기존 검수는 보존한다.


M2-3-R1은 [새 보완 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)의 명령·출력 경로를 따른다. 검색은 최신 리비전 이름/소개를 사용하며 최신 리비전이 없을 때만 모델 값을 검색한다. 빈 초안 값은 이전 공개 값으로 되돌리지 않는다. 기존 Wagtail 검색 입력·공개/소속 필터·페이지 이동을 유지한다. 원 독립 FAIL/재현 도구·이전 캡처를 덮어쓰지 않는다. M2-4 홈 최대 5건/최초 공개 최신순 연결은 설계 지시로 로컬 구현했으며 [별도 자체 검수 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 기록한다. M2-4 독립 검증과 아래 특정 5건 배치 사용자 승인은 완료했으며 관리자 사용성/운영 검증은 별도 미완료다.

M2-3의 서버·브라우저·실제 앱 읽기·캡처는 [새 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 구분한다. 아래 재현은 새 출력 폴더를 지정하며 기존 FAIL·R1·M2-2 결과를 덮어쓰지 않는다.

```bash
# backend/에서 새 폴더 이름으로 실행
uv run --locked python review/trainers/run_checks.py --output regressions-new
Y3GYM_RUN_TRAINER_BROWSER=1 Y3GYM_TRAINER_REVIEW_DIR=review/trainers/browser-new uv run --locked python manage.py test news.tests.test_trainer_browser --noinput --verbosity 2
Y3GYM_TRAINER_REVIEW_DIR=review/trainers/live-new node scripts/review-trainers.mjs --live-read-only
```

`bootstrap_trainer_review`는 기존 main/second에 승인된 가상 A/B 각 1명·선택 사진/소개만 준비한다. 직급·약력을 만들어 넣지 않는다. 프로필이 이미 있으면 콘텐츠·리비전·미디어를 보존한다. 기존 공통 브랜드/지점 브라우저 fixture에는 트레이너 seed를 섞지 않고 새 트레이너 클래스에서만 명시적으로 추가한다.

후속 [독립 재검증의 실행 결과 · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 서버 79 PASS·옵트인 2 skip, 별도 독립 검사 13 PASS·기존 재현 1 PASS, 브랜드 7/지점 11흐름의 단독·합동·역순 PASS, 실제 앱 읽기 전용 5흐름·팝업 재노출 8흐름 PASS다. M2-2 종료 문서 작업에서는 이 검사를 재실행하지 않았다. 전역 포맷은 기존 `review/workflow-01/verify.py` 1개로 실패하고 범위 포맷·전체 lint는 통과했다. [문제·경고·미검증 목록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)과 [독립 검증 당시 DB·파일·index 보존 · 정리됨](review/README.md#정리-후-유지한-검증-요약)을 함께 읽는다. 실제 기기·Whale·한국어 IME·운영 환경·사용자 시각/사용성은 미검증이다.

M2-2-R1에서 브랜드/지점 옵트인 클래스는 공통 테스트 fixture로 소식·브랜드·공개 본점/예시점 2곳을 준비한다. 테스트 DB flush로 사라진 Wagtail Collection root도 테스트 안에서 복원하며 제품 초기화 명령은 바꾸지 않는다. 브랜드의 기존 7개 검수 흐름과 제품의 0지점 문의 숨김 정책을 유지한다. 단독·합동·반대 순서와 철회 교차 요청 결과는 [R1 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 있다. 이전 검수를 보존하며 지정 검사를 재현하려면 `backend/`에서 다음처럼 새 출력 폴더를 지정한다. 같은 이름의 근거는 덮어쓰지 않는다.

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

M2-2에서 `ruff check .`와 `ruff format --check news config scripts`는 통과했다. 전체 `ruff format --check .`는 작업 전부터 있던 `review/workflow-01/verify.py` 1개를 지적한다. 이전 검수 파일은 보존했으며 이 제한과 실제 실행 결과는 [M2-2 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 구분한다. 현재 기본 서버 검사에서는 브랜드·지점·트레이너·홈 소식의 옵트인 브라우저 검사 4개를 건너뛴다.

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

쓰기 스크립트 단독 실행·8768 대상 쓰기는 거부한다. 첫 명령은 테스트 지점의 초안·미리보기·공개·시설 재정렬/삭제/사진 선택·신규 지점·마지막 철회를 실제 관리자로 확인한다. 둘째 명령은 실행 DB를 읽어 홈/상세 PC·모바일·슬라이드·JavaScript 없는 탐색을 캡처한다. 사진 촬영용 브라우저의 팝업 숨김은 독립 문맥에만 기록하고 실제 팝업 설정을 바꾸지 않는다. 캡처·재실행 범위와 실패 이력은 [지점 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)을 따른다.

브라우저 검수에는 두 서버와 초기 계정이 필요하다. 기존 `prototype/package-lock.json`의 Playwright를 재사용하며 프로토타입 HTML·캡처 생성 스크립트는 실행하지 않는다. 의존성이 없으면 먼저 `prototype/`에서 `npm ci`, `npx playwright install chromium`을 실행한다. 이번 팝업 연결 검증은 다음 명령이며 결과·캡처는 **`review/popups/`만 갱신**한다.

```bash
cd backend
node scripts/review-popups.mjs
node scripts/review-popup-edges.mjs
```

첫 명령은 실제 관리자 UI로 새 TEST 글 두 개를 만들고 자기 글만 저장·게시·설정·철회한다. 성공하면 그 두 글을 다시 공개하고 팝업을 24시간 검토 가능하게 남긴다. 기존 글과 프로토타입 검수 자료는 수정하지 않는다. 재실행은 새 TEST 글을 추가하며 기존 팝업도 보존한다. 둘째 명령은 현재 노출 가능한 예시를 읽어 짧은 모바일 화면·크기 전환·저장소 제한을 검사하고 DB는 변경하지 않는다. 현재 검토 대상의 ID·기간과 실제 결과는 [JSON · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 기록한다.

아래는 **기존 M1 브라우저 검수 명령**이다. 이번 팝업 작업에서는 M1 캡처를 보존하기 위해 재실행하지 않았다.

```bash
cd backend
node scripts/review-cms.mjs
```

이 명령은 테스트 글·이미지를 추가하고 해당 글을 마지막에 철회한다. 기존 글·이미지는 삭제하지 않는다. 실패 시 중간 상태가 남을 수 있으므로 [검수 JSON · 정리됨](review/README.md#정리-후-유지한-검증-요약)의 글 ID와 실패 단계를 확인한다. 재실행은 **`backend/review/`의 같은 이름 결과·캡처를 갱신**하며 기존 `prototype/review/`에는 쓰지 않는다.

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

이번 실행 결과와 이동 제한·실제 다른 브라우저의 미검증 항목은 [위치 검수 기록 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에 기록한다. 정적 원본 프로토타입과 이전 검수는 재생성하지 않는다.

</details>

## 카카오맵 연결과 격리 검수

이 절의 `/tmp`·고정 포트·PID는 당시 지도 작업의 보호 환경 기록이다. 현재 신규 환경 생성·정리 절차는 [관리 CLI](#qa-환경-생성실행정리)를 따르며 아래 환경의 제어 승인을 대신하지 않는다.

사용자가 2026-10-11 카카오맵·지점 안내 페이지 내 지도+외부 지도 열기 링크를 선택했다. 카카오맵 페이지 내 지도·마커와 외부 지도 열기 링크를 로컬 구현했다. 개발 자체 검사에서 서버4·모의16·로컬 상태/좁은 회귀5개를 통과했고 테스트 주소 두 곳의 최종 실제 SDK 검수6개를 완료했다. `real-run05`는 폐기된 타일 취소3건을 보존한 통과이며 미해결 네트워크 오류는0이다. 초기403·도구 가정 실패는 이력으로 보존한다. [독립 검증 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약) 후 주소 도움말 F01/P3를 [한 문자열로 보완 · 정리됨](review/README.md#정리-후-유지한-검증-요약)했고 [도움말 한정 독립3 PASS · 정리됨](review/README.md#정리-후-유지한-검증-요약)로 해결했다. 원 F01·도구 FAIL은 당시 이력으로 보존하며 주소 필드·스키마·저장/공개 정책은 유지한다. 지도 시각 승인·실제 Y3GYM 위치·실기기/Whale/한국어 IME·운영은 미완료이며 그 검수 당시 이미지 탭 오류·포맷 W01은 미해결이었으며 현재 상태는 아래 종료 기록을 따른다. 이번 단위는 여기서 마친다. 독립 실행은 별도 서버4·관리자 폼의 초안→공개·실제 지도·외부 클릭·대체 안내·좁은 회귀를 확인했다. 외부 새 탭의302→200은 확인했으나 외부 페이지 전체 UI/telemetry는 미검증이고 정확한 opener URL 불변식은 미재검증이다. 검사 수는 실행별로 구분하며 합산하지 않는다. [명령·새 캡처·원 실패·진단·보존·제한 · 정리됨](review/README.md#정리-후-유지한-검증-요약)을 따른다. 기존 공개 주소 입력/리비전·권한 미리보기·명시적 공개를 재사용하며 홈·전화/카카오톡 모의 안내·프로토타입 원본은 유지한다.

`Y3GYM_KAKAO_MAP_JS_KEY`는 선택 환경변수다. 브라우저용 JavaScript 키만 사용하고 값은 저장소·로그·보고·캡처에 남기지 않는다. 미설정/실패 시 페이지의 주소와 정상 HTML 외부 검색 링크가 남는다. 이 로컬 구현에는 새 의존성·스키마·좌표 저장 캐시가 없다.

수동 검토 주소는 [지점 안내](http://localhost:8769/branches/)·[관리자 로그인](http://localhost:8769/admin/login/)이다. 실제8768·사용자34471·과거52949와 분리한 DB `test_y3gym_kakao_map_6a8c1ada2d3b`, 미디어 `/tmp/y3gym-kakao-map-iq9yoy7v/media`를 사용했다. 관리자 `cms-review-editor`의 비밀번호는 `/tmp/y3gym-kakao-map-iq9yoy7v/.local-credentials` 로컬 파일에서만 확인한다. 키 입력 파일 `/tmp/y3gym-kakao-map-iq9yoy7v/kakao-map-js-key`는0600이며 값은 출력하지 않는다. 2026-10-12 상세주소 AddField 적용 후 기존8769를 가드로 재시작하고 관리자/공개 읽기를 확인했다. 이번 이미지 템플릿 종료 적용 후 마지막 확인 PID3650456이며 지속 가동은 보장하지 않는다. 현재 적용·보존 범위는 아래 주소 분리 기록을 따른다.

카카오 앱의 **카카오맵 사용 설정 ON**, JavaScript 키의 `http://localhost:8769`·`http://localhost:8770` 도메인 등록, 무료 쿼터 적용 앱·유료 API OFF를 사용자가 확인한다. 초기 준비 답변 이후 SDK403 비활성 응답을 받았고, 사용자가 같은 앱의 ON 저장을 재확인한 뒤 실제 인증·검색200과 최종 전체 검수 통과를 확인했다. 원 실패는 보존하며 외부 설정을 코드에서 바꾸지 않았다. [공식 절차](https://developers.kakao.com/docs/ko/kakaomap/common).

독립 검증은 새 `/tmp/y3gym-kakao-map-independent-nrzSbqfL`에서 `review/kakao-map/prepare.py NEW_SCRATCH --port 8770 --real-sdk-confirmed`를 실행해 고유 DB/계정/미디어/쿠키를 준비하고 실제 검수한 뒤8770 서버를 종료했다. 도움말 한정 재확인은 같은 독립 settings/DB의 Django Client GET으로 수행해 서버·SDK를 재가동하지 않았다. `review/kakao-map/control.py SCRATCH status|stop|start`는 지정 인스턴스의 PID·cwd·port·환경을 확인하며, F01 개발 보완에서 본인8769의 stop/start가 실제 성공했다. 기존8769 환경을 초기화하거나 공유 DB를 재사용하지 않았다. 실제 키는 값을 출력/인자로 전달하지 않고0600 파일에서 자식 서버 환경으로만 읽었다. 당시 지도 단위의 종료 작업은 문서만 갱신했고 제품 검사·서버 조작·DB 쓰기·다음 기능을 수행하지 않았다.

## 2026-10-12 도로명주소·상세주소 분리

사용자가 상세주소 별도 입력을 승인해 기존 `Branch.address`는 관리자에서 도로명주소(건물 번호까지)로 안내하고 선택 `address_detail`(200자·기본 빈 값)을 추가했다. `0006_branch_address_detail`은 AddField만 수행하며 기존 주소값·리비전 JSON은 자동 분리·재작성하지 않는다. 구 공개 리비전의 누락 상세는 빈 값으로 복원한다. 두 값의 초안·권한 미리보기·명시적 공개/철회·충돌 정책은 동일하며 주소 공개 필수 조건은 유지한다. 상세는 기존 주소 영역의 다음 줄에 표시하고 지도 SDK·외부 주소 검색은 도로명주소만 사용한다. 위 지도 단위의 필드 추가 없음은2026-10-11 당시 범위다.

[새 자체 검사·명령·캡처·실패 이력·한계 · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 새 `http://localhost:8771`·DB `test_y3gym_address_detail_95f138c693b9`·별도 runner/미디어/계정/쿠키에서 수행했다. 설정/미디어/0600 자격 파일은 `/tmp/y3gym-address-detail-yunol4e7`에만 있다. 실제 SDK 키는 비어 있고 해당 브라우저의 모의 응답만 사용했으며 실제 SDK 호출은 하지 않았다. 개발 당시 기존8769/8768/34471/52949는 변경하지 않았다. 이후 [독립 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 서버18 PASS·실제 SDK·실제 PC/모바일 viewport를 확인했다. core19·edges11 뒤 도구 중단·finish5는 각각의 기록으로 보존하며 자체/독립 검사 수를 합산하지 않는다.

[사용자8769 적용·비공개 백업·보존·읽기 확인 · 정리됨](review/README.md#정리-후-유지한-검증-요약)을 완료했다. 기존 `/tmp/y3gym-kakao-map-iq9yoy7v` settings/DB/media/계정/쿠키를 유지하고 news0006 AddField1개만 적용한 뒤 기존 control 가드로 재시작했다. 적용 직후 대조에서 기존 주소·지점의 다른 컬럼·공개/최신 리비전·raw JSON·미디어는 그대로였으며 당시 상세는 빈 값이었다. 관리자 로그인/편집 GET의 인증·편집 세션 부수 효과는 콘텐츠/마이그레이션 메타데이터와 구분한다. 적용 중 fixtures·재시드·주소 자동 분리·초안 저장·게시·철회는 하지 않았다. 현재 검토는 위8769 URL과 `/tmp/y3gym-kakao-map-iq9yoy7v/.local-credentials`의 기존 계정을 사용한다. 개발8771 모의 서버는 종료했으며 독립8770 종료는 독립 보고서에서 확인했다. 다른 서버는 건드리지 않았고 이번에는 제품 검사를 반복하지 않았다. 2026-10-12 사용자가 “상세주소 따로 입력해도 지도 정상적으로 나옴. 이대로 유지”라고 직접 확인했으므로 주소 분리 구조와 해당 실제 지도 연결의 유지 승인을 기록한다. 전체 지도 경계·실기기/IME/Whale·관리자 전체 사용성·실제 영업 위치·운영 승인은 별도이며 원 QA의 당시 승인 대기·FAIL은 보존한다. 원 ADMIN-W01은 아래 자체·독립 확인 범위에서 해소됐다. 해당 종료 당시 W02/P3·기존 포맷 W01은 미해결이었으며 최신 W02 상태는 아래 별도 단위를 따른다. 새 기능은 시작하지 않는다.

## 이번 단계에서 하지 않은 일

프로필 삭제/복원·운영 계정 확대, 팝업용 별도 문구·사진 입력, 운영 배포·외부 저장소·CDN·백업은 미구현이다. 실제 로고·사진·영업 연락처의 최종 운영 자료 확인은 미완료다. 개발환경의 선택 지점 전화·본점 카카오 연결은 반영됐고 사용자가 직접 확인한 연결 범위를 승인했다. 실제 상담/메시지 송수신·실통화 성공·기기/OS별 동작·운영환경 연결은 별도 미검증이다. 지점의 본점 우선·표시 순서·공개 필수값·마지막 철회는 사용자 답변으로 확정했다. 본점 교체·지점 삭제/복원, 소식 공개일 변경·목록 페이지당 10건의 운영 확정·삭제/복원·최종 운영 권한은 미결정이다. 홈 최대 5건·홈/목록 최초 공개 최신순·수정/재공개 순위 유지와 팝업 최초 등록 빠른순은 확정·구현했다. 브랜드는 공개 필수값만 이번에 확정했으며 삭제/복원 동작을 추가하지 않았다. 실제 기기와 Chromium 이외 브라우저, 한국어 IME 조합 입력, 운영 환경의 캐시·미디어 제공 경로는 별도 확인이 필요하다.

### 관리자 이미지 중복 업로드 탭 오류 보완 — 2026-10-12

**2026-10-12 사용자 한정 사용성 승인:** 관리자 소식의 중복 업로드에서 기존 이미지 사용·새 사용·닫기·작성 내용 유지가 정상임을 사용자가 확인해 이번 수정 범위를 승인했다. 이 사용자 확인 당시 W02/P3 초기 모달 포커스 경합과 기존 Ruff 포맷 W01은 별도 미해결이었으며 최신 W02 상태는 아래 별도 단위를 따른다. 전체 회귀·실기기/Whale/한국어 IME·운영 승인은 아니다. 승인된 A 디자인·브랜드/지점 저장·공개·상세주소·지도는 유지한다. 과거 QA의 FAIL·당시 승인 대기는 보존한다.

**2026-10-12 이미지 선택기 종료:** [자체 재현·보완 · 정리됨](review/README.md#정리-후-유지한-검증-요약)과 [독립 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 원 ADMIN-W01/P3 missing-panel JS 오류 해소와 대표/본문 중복 선택·닫기·한글 보존·초안/권한 미리보기·공개/철회·미디어 경계·브랜드/시설을 확인했다. 독립 `core-03`14개 확인 뒤 초기 모달 포커스 FAIL을 W02/P3로 관찰했고, 실제 `shown.bs.modal` 이후 `finish-01` 남은10개와 선정 서버8 PASS를 별도 기록하며 합산하지 않는다. [기존8769 종료 적용 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 지정 가드 재시작·fresh loader origin·로그인 GET200만 확인했다. 해당 종료 당시 초기 모달 포커스 경합 W02/P3와 기존 전역 Ruff 포맷 W01은 미해결이었으며 최신 W02 상태는 아래 별도 단위를 따른다. 순정 upstream A/B는 미실행이다. 전체 관리자·실기기/Whale/한국어 IME·운영 승인은 아니다. 과거 자체/독립 FAIL·독립 대기는 당시 기록으로 보존한다.

### 선택 지점의 전화 문의 연결 — 2026-10-12

**2026-10-12 선택 지점 전화 — 독립 검증·8769 종료 적용:** [이번 전화 단위·지원 문법·캡처·원 실패·한계 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 실제 지점 상세의 전화 버튼만 해당 공개 리비전 번호의 native `tel:` 앵커로 연결했다. 번호/자유 안내문은 읽고 복사할 텍스트로 유지하며 공백뿐인 상세 전화 행·지원하지 않는 형식의 전화 링크는 만들지 않는다. 홈 공통 CTA·모바일 문의 바·트레이너 문의는 선택 지점 contact 이동을 유지하고 전화 종료 적용 당시 카카오톡은 모의 안내였으며 현재 연결 범위는 아래 카카오톡 단위를 따른다. 저장 문자열/리비전 자동 정규화·필드/스키마·게시 필수 조건·스타일·정적 프로토타입은 변경하지 않았다. [독립 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 서버8 PASS·별도 문법66 PASS와 지점별 native 링크·공개/초안·철회/0곳을 확인했다. `browser-01/02/finish-01`의 도구 가정 FAIL과 `cms-01`의 남은8확인 PASS는 합산하지 않는다. [기존8769 종료 적용 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 가드 재시작·로그인/두 지점 HTML GET·fresh source·현재 DB/미디어의 전후 읽기 전용 보존 확인까지 수행했다. 전화 연결 확인·현 상태 유지에 대한 사용자 한정 승인은 아래 기록을 따른다. 전체 시각/경계조건·전체 회귀/관리자·실기기/OS/Whale/한국어 IME·실제 영업번호/다이얼러/통화/국제 통신·운영은 별도 미검증이다. PHONE-OBS01(기존 공백 전화의 JS-off 공통 CTA 원문 판정 차이)은 전화 종료 당시 독립 재현된 미해결 관찰이었으며 당시 W02/P3·Ruff W01도 남았다. 각각의 최신 상태는 아래 후속 단위를 따른다. 자체/독립 원 실패와 당시 승인 대기는 보존한다.

**2026-10-12 사용자 한정 확인·전화 유지 승인:** 사용자가 전화 연결을 확인하고 “이대로 유지”를 승인했다. 직접 확인한 전화 연결·현 상태 유지에 한정하며 사용자 기기나 실통화 성공을 추정하지 않는다. 전체 시각/경계조건·전체 회귀/관리자·실기기/OS/Whale/한국어 IME·운영 확인으로 확대하지 않는다. 그 확인 당시 W02/P3·Ruff W01·PHONE-OBS01은 미해결이었으며 PHONE-OBS01의 후속 상태는 아래 별도 단위를 따른다. 과거 전화 자체/독립/적용 QA의 당시 승인 대기·원 FAIL은 보존한다.

**2026-10-12 선택 지점 카카오톡 1:1 채팅 — 독립 검증·8769 스키마/코드 적용:** [이번 범위·원 실패·실행·캡처·한계 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 선택 `kakao_chat_url`(500자·기본 빈 값)과 additive `0007`을 추가했다. 기존 `channel` 안내 문구는 별도로 보존하며 정확한 HTTPS `pf.kakao.com/_공개ID/chat`만 입력·게시/공개 helper에서 허용한다. 홈 주소/공백/추가 경로·query/fragment 등은 자동 변환하지 않는다. 실제 상세의 같은 secondary 스타일을 native 새 창 앵커(`noopener noreferrer`)로 연결하고 URL만 있는 지점의 공통·모바일·트레이너 문의는 선택 지점 contact 내부 이동을 유지했다. 안내만 있으면 문구만 표시하고 URL/번호 없는 문의 동작은 숨긴다. 구 리비전의 URL 누락은 빈 값이며 최신 초안/base URL을 빌려오지 않는다. 자기8771/새 DB에서 변경 전 서버2·브라우저2 PASS, 서버 첫11=10 PASS+검수 가정 FAIL 후 해당1 PASS, 브라우저 첫 실행의 모바일 팝업 준비 FAIL 뒤 남은10확인 PASS·공백 안내 표시 한정 서버1 PASS를 각각 보존하며 합산하지 않는다. [독립 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 첫 서버12 PASS+마이그레이션 fixture 도구1 ERROR, 도구 보완 뒤 해당1 PASS·브라우저12 PASS를 구분한다. [기존8769 종료 적용 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 현재 자료의 비공개 백업 후0007 한 건과 새 코드를 적용하고 로그인/홈/두 지점 GET200·읽기 전용 전후 보존을 확인했다. 이번 비교 도구의 튜플/JSON 형식 오류와 TIME_WAIT 시작 거절2회도 적용 보고에 남겼다. 이후 사용자의 카카오 연결 한정 확인은 아래 승인 기록을 따른다. 구체 기기/OS·로그인/메시지·전체 관리자/회귀·IME·운영 확인으로 확대하지 않는다. 카카오 종료 당시 W02/P3·Ruff W01·PHONE-OBS01은 미해결이었고 PHONE-OBS01 후속 보완은 별도 단위다. 사용자 제공 본점 입력 예시는 `https://pf.kakao.com/_VPnVxj/chat`이며 **본점만 배정 확정**, 추가지점 URL은 미제공·fallback 금지다. 8769 종료 적용 당시 두 지점 새 URL은 빈 값이었고 개발은 실제 URL을 입력/게시하지 않았다. 이후 사용자 확인과 당시 QA를 구분한다. PHONE 자체/독립 단계에서는8769를 조회하지 않았고, 아래 종료 적용에서 현재 자료를 새로 읽어 보존했다. 추가지점 URL은 미제공이며 본점 fallback은 금지다.

**2026-10-12 사용자 카카오 연결 한정 확인:** 사용자가 “확인완료. 다음마일스 톤진행하”라고 하여 방금 직접 확인한 카카오 연결 범위를 승인하고 다음 작은 단위를 지시했다. 정확한 기기/OS·로그인/메시지·전체 관리자/회귀·한국어 IME·운영까지 확인한 것으로 추정하지 않는다. 과거 QA의 빈 URL·승인 대기·원 FAIL은 촬영/실행 당시 기록으로 보존한다. 현재8769의 URL이 여전히 비어 있다고 단정하지 않는다. PHONE 자체/독립 단계는 그 환경을 조회하지 않았고 이번 종료 적용은 아래 기록처럼 현재 공개본을 새로 읽어 보존했다.

**2026-10-12 PHONE-OBS01 — 독립 해결·8769 코드 적용:** [이번 구현·원 재현·실행·캡처·한계 · 정리됨](review/README.md#정리-후-유지한-검증-요약). 공개 지점의 `has_phone_contact` 읽기 전용 판정을 metadata·상세·홈·공통/모바일·트레이너에서 재사용했다. 빈 값·ASCII/Unicode 공백 전용 전화와 유효 Kakao URL 없음은 서버 HTML부터 문의를 숨기며 JS-on/off가 일치한다. 비어 있지 않은 자유 안내문·유효 번호·URL-only의 내부 문의/지점별 대상과 원문·공개/초안·철회/0곳·기본 탐색은 유지한다. 수정 전 브라우저4확인 PASS(문제 재현), 새 서버5+관련2 PASS, 수정 후 브라우저 첫1확인 뒤 상대/절대 href 도구 가정 FAIL·도구만 보완한 남은27확인 PASS를 구분하며 합산하지 않는다. [독립 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 서버7(새5+독립2)·브라우저30 PASS로 해결을 확인했다. 독립 정적 QA의 합성 URL 접두어 오탐과 도구만 보완한 후속 PASS를 보존한다. [지정8769 종료 적용 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 현재 사용자 자료를 읽기 전용 스냅샷으로 보호한 뒤 같은 가드로 코드만 재시작하고 최소 GET/보존을 확인했다. 이후 사용자가 “확인완료”로 직접 확인한 빈 연락처 표시 범위를 승인했다. 실기기/OS·IME·전체 회귀·운영 승인은 별도다. 이 PHONE-OBS01 단위 당시 W02/P3·전역 Ruff W01은 미해결·미재검이었으며 최신 W02 상태는 아래 별도 단위를 따른다. CSS/프로토타입/스키마/전화 지원 문법·과거 QA는 변경하지 않았다. 자체/독립 당시8769 미접근과 이번 지정8769 종료 반영을 구분하며 다른 보호 환경은 유지했다.


**2026-10-12 W02/P3 — 자체·독립 검증·지정 개발환경 코드 반영:** [원 재현·최소 보완·실행·캡처·한계 · 정리됨](review/README.md#정리-후-유지한-검증-요약). 새 격리8771에서 변경 전 원 조건4회 중3회 포커스 유실을 재현했고 최종 보완 후 같은4회는 모두 통과했다. 이미지 모달의 늦은 초기 focus만 사용자 내부 포커스가 있을 때 생략하며 탭 활성화/aria/panel 동작은 유지한다. 정상 열기·열리는 중 입력창/버튼·실제 닫기 후 hidden 전 재열기·복원·다른 모달·대표/본문 기존/새/취소·한글 직렬화 보존의 관련10확인을 통과했고 본문 취소의 같은 collapsed 선택 위치·원문·실제 한글 이어 입력을 별도 확인했다. 모달 밖 첫 Tab의 검색창 진입은 프로그램 탐색 시작점 설정과 실제 키 입력을 구분해 전후 확인했다. 빠른 재열기의 프로그램 setup·이전 이벤트 합성 probe·원 FAIL은 새 QA에서 구분한다. [독립 PASS_WITH_WARNINGS · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 원4시도 중 유효3 PASS·조건미충족1, 별도 한정1 PASS(합산 금지), 밖 첫 Tab2·관련11·별도 보강2·본문 선택/이어 입력 PASS와 새 차단 제품 문제 없음을 확인했다. [지정8769 코드 반영 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 기존 가드로 적용 당시 PID709395→1020914만 재시작하고 fresh loader hook·JS 응답 일치와 익명 로그인/JS GET200만 확인했다. 적용 당시58테이블 전체655행·스키마/시퀀스·리비전24·이미지4·미디어11·설정·키/자격 metadata는 동일했다. 인증 관리자 UI는 독립 환경의 결과이며 이번 최소 읽기 적용 검사와 구분한다. 이후 사용자가8769 조작·작성 내용 보존을 직접 확인해 “수정·독립 검증 완료 및 사용자 확인 범위 승인”으로 확정했다. 직접 확인 범위에 한정하며 전체 회귀·실기기/Whale/OS 한국어 IME·운영 승인은 아니다. W02 적용 당시 전역 Ruff W01은 미해결·미재검이었으며 이후 통합 최초 실행에서 전역 Ruff78 lint/40 format FAIL을 실제 확인했고 이번 마감에서는 재실행하지 않았다. 과거 QA의 당시 승인 대기·FAIL·ERROR는 보존한다. 다른 보호 환경·vendor/스키마/공개CSS/과거 QA는 유지했다.

**2026-10-12 dev-integration-01 — 실행·한정 보완 반영 및 잔여 확인:** [최초 독립 실행 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은142건114 PASS/1 FAIL/27 ERROR/0 SKIP, [보완 뒤 전체 재실행 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은142건141 PASS/1 FAIL/0 ERROR/0 SKIP다. 남은 지점 FAIL은 JS 초기 all-visible HTML을 통과하는 검사 준비조건 누락이었으며, 실제 요청 탭의 role/aria-controls/aria-selected를 기다리는2줄을 보완한 별도 fresh 지점 opt-in1건은 PASS·브라우저11검사 PASS다. 독립 실행본과 같은2줄만 canonical QA helper에 반영했고142 clean PASS로 합산하지 않는다. 팝업 관리자10·headed 크기10·위치8 PASS다. 정상 hash fixture 뒤 W02early1시도는 입력 전에 이미 shown이어서 유효0/조건미충족1(ERROR)이며 조기Escape도 미확인 한계로 유지한다. 기존 W02 사용자 한정 승인은 유지한다. CMS8·W02 밖Tab2/본문 보존·Django check/migration dry-run·8769 기본 연결은 최초 실제 결과를 인계했고 재검증에서 반복하지 않았다. 8769 트레이너302는 기존 편집자 권한 제한이다. 전역 Ruff78 lint/40 format FAIL은 최초 실제 관찰로 보존하며 수정5파일 한정 PASS와 구분한다. [마감 반영·보존·원자료 · 정리됨](review/README.md#정리-후-유지한-검증-요약)는 이번 문서·동등성 검사와 제품 재실행을 구분한다. 소식/트레이너 관리자 전체 사용성·시설 사진0/1건·순서/교체/누락/경계·실기기/Whale/OS 한국어 IME·운영은 미검증이며 기존 승인 범위를 다시 열지 않는다. 운영 도메인·실자료·hosting/DB/uploads·backup/restore·secret/권한·배포는 미결정·미검증이다.

**2026-10-13 최종 개발 회귀·수동 준비:** [최종 독립 실행 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 fresh 환경의 `news.tests` 전체1회142 수집/실행·142 PASS/0 FAIL/0 ERROR/0 SKIP,exit0·4opt-in 실행을 확인했다. 위 과거141 PASS/1 FAIL+후속1 PASS와 합산하지 않는다. Ruff a47 lint/format PASS, b10은 I001 1건·format2개 FAIL이며 원본 전역78/40 보존·전역 미재실행·설정 미변경이다. 테스트 담당은 기존 격리8772를 기동하고 실제 headed 로그인·편집 필드 접근 및 정상/빈 자료를 확인해 실행 중으로 남겼다. [접속·실제 ID·잔여 수동 확인 · 정리됨](review/README.md#정리-후-유지한-검증-요약)을 따른다. 기존 한정 승인은 유지하며 사용자 사용성·실기기/Whale/OS IME·W02 특정 조기 재열기/Escape·실제 SDK·운영 준비 완료로 확대하지 않는다. 이번 마감은 문서만 갱신하고 검사를 재실행하지 않았다.

**2026-10-13 수동 한정 승인·시설 사진 보완 종료:** 사용자의 “수동 검수에서 직접 확인한 나머지 범위 승인, 시설 세로 잘림 제외”는 유지한다. [개발 자체17 PASS · 정리됨](review/README.md#정리-후-유지한-검증-요약)와 [독립17 PASS · 정리됨](review/README.md#정리-후-유지한-검증-요약),각 홈·지점 PC1440/모바일375의12사진 전체 표시·1/0건/순서·교체 초안/접근 통제를 확인했다. [기존 사용자8772 반영 · 정리됨](review/README.md#정리-후-유지한-검증-요약)에서 기존 가드 재시작 후 실제 사진5/6의 contain·중앙·비율/전체 내용과 원자료 보존을 확인했다. **시설 contain 표시의 사용자 시각 승인은 완료**이며 구체 기기·Whale·OS IME·W02 정확한 조기 조건·운영 승인으로 확대하지 않는다. 기존142/142는 수정 전 단일 기준선이며 자체17·독립17과 합산하지 않는다. 8769·8773·8774는 이번에 제어하지 않았다.

**2026-10-13 공개 사진 전체 표시·공통 확대 구현:** 사용자 지시에 따라 대표·시설·트레이너·소식 대표/본문·PC/모바일 팝업의 전체 사진과 원본 비율을 보존하고, 클릭한 한 사진을 현재 문서의 공통 라이트박스에서 표시한다. [이번 구현·실행·전후 화면·한계 · 정리됨](review/README.md#정리-후-유지한-검증-요약). 기존 시설 contain 승인은 유지한다. [독립 검증 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 완료(PASS_WITH_WARNINGS)했으며 사용자가 공개 콘텐츠 사진·라이트박스를 직접 확인한 범위에서 승인 완료했다. 원 픽셀 FAIL과 QA 이력은 보존하며 기기·전체 픽셀·운영 승인으로 확대하지 않는다. 독립 서버14/14, 기본 브라우저23항목·확대29사진, 별도 실제 비율23항목·일반/확대 각21사진을 확인했다. 엄격 픽셀76/77·별도39/42 및 작은 popup DPR2 0/3 FAIL은 원 판정을 유지하며 카운터 원 FAIL과 후속은 구분한다. 사용자 검토 기본 환경은 합성 TEST 자료의 [새8776](http://localhost:8776/?branch=main)이다. 기존8769·8772에는 이번 공통 확대를 재시작 반영하지 않았으며8773·8774·개발8775도 제어하지 않았다. 기존 수동 승인·실기기/Whale/OS IME·W02·운영 경계는 확대하지 않는다. **개발 자체 완료:** 최종 전체148/148 PASS(4opt-in·신규5 포함), 실제 브라우저23 PASS·확대29사진. 최초 전체146/148·두 한정 후속 및 엄격1x픽셀76/77·별도DPR2 근거는 각각 보존하며 합산하지 않는다.

**2026-10-13 NAV01 헤더 공통 홈 이동:** 공개 CMS 헤더의 브랜드명·선택 로고는 지점 쿼리 없는 named `home`으로 일반 링크 이동한다. 루트에 `branch` 없이 들어오면 저장된 선택·표시 콘텐츠는 유지하고 주소에 지점을 강제로 추가하지 않는다. 명시 지점·탭 선택·다른 지점 전달 링크는 기존대로다. 푸터·breadcrumb·팝업 브랜드, 정적 프로토타입 동작·레이아웃·이미지·관리자·운영은 변경하지 않는다. [이번 구현·재현·검사·보존 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 개발 자체 완료이며 [독립 검증 완료(PASS_WITH_WARNINGS) · 정리됨](review/README.md#정리-후-유지한-검증-요약)·신규 제품 결함 없음으로 검토됐다. 개발 최초 서버16건15 PASS/1 FAIL·별도 후속1 PASS와 독립 서버11/11·텍스트40/로고40·카운터 원 실패/별도 후속은 각각 보존하며 전체148/152로 합산하거나 재실행하지 않았다. [기존 사용자8776 반영 · 정리됨](review/README.md#정리-후-유지한-검증-요약)은 기존 guard stop/start 각1회와 실제 공개 DOM의 PC1440/모바일375 각6경로 헤더 클릭·새로고침/선택 지점·문의 유지 및 사진 확대의 한정 확인을 완료했다. 실제 자료에 없는 로고·second 트레이너·카카오 URL은 이번 확인 범위 밖이다. **NAV01은 사용자가 직접 확인한 헤더 이동 범위에서 승인 완료**이며 기존 사진·라이트박스 한정 승인과 실기기/Whale/OS IME·운영 경계는 유지한다.
