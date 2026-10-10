# Y3GYM

헬스장 브랜드와 지점·시설·트레이너를 소개하고 방문자를 **선택한 지점의 전화·카카오톡 문의**로 연결하는 공식 홈페이지 프로젝트다. 운영자는 정해진 화면의 콘텐츠를 직접 관리한다. PT 운영관리 서비스와는 별개다.

## 현재 상태

2026-10-10 실제 파일과 사용자 결정을 대조한 기준이다.

- **공개 화면 디자인 검토 완료:** 밝고 정돈된 A 방향, 홈과 별도 지점 안내, 지점별 탭, 공통 시설 자동 슬라이드, 소식 목록, PC·모바일 팝업을 기준으로 진행한다. 상세 승인 범위와 개별 확인이 없는 항목은 [디자인 문서](prototype/DESIGN.md)에 구분했다.
- **공개 UI:** `prototype/`의 독립적인 정적 HTML·CSS·JavaScript. 기본 예시는 본점·예시점 두 지점이다. 가상 시설·인물 사진, 주소·운영시간·연락처를 사용한다.
- **첫 백엔드 구현:** `backend/`에 Django 5.2.18 / Wagtail 7.4.3 + PostgreSQL 17.11로 소식 작성·초안·미리보기·명시적 공개·수정·철회를 구현했다. 실제 공개 리비전·이미지 접근 통제·저장 충돌을 검증하는 로컬 마일스톤이다. Python 3.13.15와 의존성을 고정했고 실행법은 [백엔드 README](backend/README.md)에 있다.
- **게시글 연동 팝업:** 소식 편집 화면의 ‘팝업 설정’에서 사용 여부와 한국 시간 시작·종료 일시를 별도로 적용한다. 실제 DB 설정과 현재 공개한 글을 홈에 연결했다. 중첩은 모두 허용하고 등록이 빠른 글부터 전체 자동 노출한다. PC는 별도 창, 모바일은 순차 레이어다. 평소 ‘알림 보기’는 없으며 차단·실패 시에만 수동 복구 링크를 제공한다. [실행·검증·캡처](backend/review/popups/README.md).
- **팝업 크기 보정:** 실제 복수 창의 폭 불일치·하단 과도한 여백을 수정했다. 모든 창에 기준 폭을 요청하고 내용 높이를 재측정한다. 기존 headless 검수와 구분해 [화면이 표시되는 브라우저의 실제 창 크기·새 캡처](backend/review/popup-sizing/README.md)를 기록한다. Whale 직접 검사는 도구 연결 오류로 미실행이다.
- **최신 재노출 정책:** 일반 닫기 후 같은 탭 새로고침·홈 재방문 때 다시 자동 표시한다. ‘오늘 하루 보지 않기’를 선택한 글만 한국 시간 다음 날 00시까지 숨긴다. 예전 탭당 한 번 제한은 폐기하고 열린 PC 창은 재사용한다. [재노출·크기 회귀 검증](backend/review/popup-revisit/README.md).
- **PC 팝업 위치:** 화면 중앙 주변의 서로 다른 구역에서 랜덤하게 배치한다. 시작 좌표를 지정하고 내용에 맞춰 크기를 조절한 뒤 실제 창 위치를 보정한다. 가장자리 기본 여백은 48px이며 모바일 레이어는 유지한다. [실제 좌표·크기·재노출 검수와 제한](backend/review/popup-position/README.md). 사용자 ‘ok 다음으로 넘어가자’로 후속 진행을 확인했다. 이를 Whale 직접 검증으로 취급하지 않는다.
- **M2-1 브랜드·홈 소개:** 관리자 ‘브랜드·홈’에서 공통 브랜드명·선택 로고·소개 제목/설명·선택 대표 사진과 중심을 초안 저장 → 미리보기 → 공개·철회한다. 공개 필수값은 사용자 확인으로 브랜드명·소개 제목이며 미완성 초안 저장을 허용한다. 실제 홈과 실제 소식/팝업의 브랜드 표시에 공개본을 연결했다. [이번 검수·캡처·한계](backend/review/brand-home/README.md).
- **M2-2 지점·시설:** 관리자에서 지점과 시설 사진을 한 단위로 초안 저장·미리보기·공개/철회하고 실제 홈·[지점 안내](http://localhost:8768/branches/?branch=second)에 공개 리비전을 연결했다. 공개 본점 우선·동적 지점 선택·0곳 안내·선택 연락수단 숨김과 기존 미디어/저장 경계를 적용했다. [자체 검수·캡처·한계](backend/review/branches/README.md). 독립 검증과 사용자 시각 승인은 별도다.
- **M2-2 종료 상태:** [초기 독립 검증 FAIL](backend/review/branches-independent/README.md) → 공통 철회 잠금·테스트 fixture의 [R1 보완](backend/review/branches-repair/README.md) → [독립 재검증 PASS_WITH_WARNINGS](backend/review/branches-independent-recheck/README.md). F01·F02·W01 해결과 차단 결함 없음을 확인했으며 기존 `backend/review/workflow-01/verify.py`의 전역 포맷 경고는 남아 있다. 이전 FAIL·R1 보고·전환 중 모바일 캡처는 당시 기록으로 보존한다. 사용자 시각·관리자 사용성 승인이나 운영 배포 완료를 뜻하지 않는다.
- **M2-3 트레이너 관리:** 지점 편집에서 별도 저장 단위의 프로필·단일 약력을 등록·편집하고 초안 → 권한 미리보기 → 명시적 공개·철회한다. 이름·소속 지점만 공개 필수이며 선택 정보·사진은 없으면 숨긴다. 현재 공개 리비전의 소속·수동 순서·약력·사진과 공개 지점 조건으로 실제 지점 상세에 연결했다. 이동 초안은 현재 공개 소속을 바꾸지 않는다. [초기 자체 검사](backend/review/trainers/README.md) 후 [독립 검증 FAIL](backend/review/trainers-independent/README.md)의 최신 초안 검색 결함을 [M2-3-R1](backend/review/trainers-repair/README.md)에서 보완했다. 이후 [독립 재검증 PASS_WITH_WARNINGS](backend/review/trainers-independent-recheck/README.md)로 F01/P2·W02~W04 해결과 새 차단 결함 없음을 확인했다. 기존 전역 포맷 경고 W01은 유지하며 관리자 사용성 승인은 별개다. 2026-10-10 사용자가 검토한 PC/모바일 캡처의 직급·약력 배치는 “이 배치로 유지”로 승인했다.
- **다음 계획 M2-4 — 미착수:** 홈 최근 소식을 실제 공개 글 최대 5건과 연결한다. 홈·소식 목록은 최초 공개 최신순이며 수정·재공개로 순위를 올리지 않는다. 팝업의 최초 등록 빠른순은 유지한다. [첫 구현 단위·완료 기준](docs/IMPLEMENTATION-PLAN.md#다음-미완료-단위-m2-4-홈-최근-소식-실제-공개-글-연결)만 기록했으며 별도 구현 지시 전 시작하지 않는다.
- **미구현:** 홈 최근 소식 연결, 실제 지도·전화·카카오톡, 운영 자료·배포·운영 환경, 프로필 삭제/복원·운영 계정 확대. `prototype/` 원본은 계속 정적 참고 자료이며 보존한다.
- 기존 Chromium 프로토타입 검수 자료를 보존했다. 이번 소식 CMS의 실제 검증·새 캡처는 [별도 기록](backend/review/README.md)에 두며, 관리자 사용성의 사용자 승인·실제 기기 검증·출시 완료와 구분한다.

2026-10-10 사용자 지시부터 설계 → 개발 → 독립 검증 → 필요한 Git 반영을 역할별로 맡기고, 정상 보고와 진행 조건을 확인하면 승인된 계획 안에서 다음 작은 단위를 자동 진행한다. 담당 세션과 보고·승인 경계는 [실행 역할·작업 흐름](docs/WORKFLOW.md)을 따른다. M2-1 이후 확정한 지점 정책을 이번 M2-2의 [PRD](docs/PRD.md#fr-02-지점시설)와 [구현 계획](docs/IMPLEMENTATION-PLAN.md)에 반영했다.

본점은 1곳이며 공개 상태일 때 첫 순서·새 방문 기본값이다. 명시된 지점 선택을 유지하고 본점 비공개 시 첫 유효 공개 지점을 선택한다. 미완성 초안을 허용하며 공개 필수값은 지점명·주소·운영시간이다. 마지막 공개 지점도 철회 가능하고 0곳이면 준비 중 안내와 문의 버튼 숨김을 적용한다. 트레이너 CMS는 M2-3에서 연결했으며 실서비스 연결·사용자 사용성 확인은 후속 범위다. 전체 콘텐츠의 초안 → 미리보기 → 공개와 팝업의 별도 적용 정책은 유지한다.

첫 체크포인트 `46ef337423fb89c1eb7f9000762f32e67802bc57`은 깃노예가 로컬 커밋 후 기존 원격에 push했다. 최초 HTTPS 인증 실패 후 기존 인증을 명령 단위로 재사용해 성공한 Git 담당 결과다. 이번 M2-3·R1 및 종료 문서 변경은 아직 미커밋이며 이 체크포인트에 포함되지 않는다. 개발은 stage·commit·push·인증/전역 설정 변경을 수행하지 않았고 설계 검토 후 Git 담당이 별도 반영한다.

이번 M2-3 종료 작업은 [문서 정합성·보존 검사](backend/review/m2-3-closeout/README.md)만 수행했다. 위 독립 제품 검사 결과는 보고서 확인이며 이번에 제품 테스트나 캡처를 재실행한 것이 아니다.

## 제품 범위와 공개 화면

브랜드·다지점·시설·소속 트레이너·지점별 문의, 공통 공지·이벤트, 소식에 연결된 기간제 팝업, 운영자 콘텐츠 관리를 포함한다.

| 화면 | 현재 구성 |
| --- | --- |
| 홈 | 브랜드 소개 → 지점 탭과 시설 사진을 합친 미리보기 → 공통 최근 소식 → 푸터 |
| 별도 지점 안내 | 선택 지점 요약·시설·트레이너·위치·문의. 탭 수는 지점 데이터에 따라 증가 |
| 소식 목록·상세 | 전체·공지·이벤트, 촘촘한 목록과 본문 읽기 |
| 팝업 | 실제 공개 글·기간과 연결. PC 별도 창 요청, 모바일 순차 레이어. 자동 차단 시 수동 진입 |
| 콘텐츠 관리 | 소식·팝업 설정·브랜드/홈·지점/시설·소속 트레이너·이미지의 로컬 Wagtail 관리자 구현. M2-3 독립 재검증 PASS_WITH_WARNINGS. 사용자 사용성 승인은 별도 단계 |

헤더는 지점 안내·소식·문의하기, 푸터는 지점 안내·소식이다. 트레이너 독립 메뉴는 없으며 홈에는 트레이너·위치 상세를 표시하지 않는다. 문의 대상 지점을 명시한다. 고객 회원가입·결제·예약·PT 연계·자체 상담 폼·자유 페이지 빌더는 범위에 포함하지 않는다. 전체 요구와 미결정 사항은 [최신 PRD](docs/PRD.md)를 따른다.

## 주요 폴더

```text
.
├── README.md
├── AGENTS.md                       # 현재 프로젝트 작업 규칙
├── docs/
│   ├── PRD.md                      # 현재 제품 요구사항
│   ├── IMPLEMENTATION-PLAN.md      # 기술 방향·마일스톤·후속 설계
│   ├── WORKFLOW.md                 # 실행 역할·보고·단계 진행·Git 절차
│   └── legacy/                     # 이전 프로젝트 문서 세 개
├── backend/
│   ├── README.md                   # CMS 실행·계정·검증 안내
│   ├── pyproject.toml / uv.lock    # Python 의존성 고정
│   ├── compose.yaml               # 별도 로컬 PostgreSQL
│   ├── config/ / news/            # 앱 설정·콘텐츠 CMS·공개 경계·테스트
│   └── review/                    # 이번 CMS 검증·새 캡처
└── prototype/
    ├── README.md                   # 화면·검수 실행 상세
    ├── DESIGN.md                   # 현재 디자인 기준·승인 범위
    ├── index.html / branches.html  # 홈 / 별도 지점 안내
    ├── news*.html / news/          # 소식 목록·분류·상세·빈 상태
    ├── popup.html / preview-*.html # 팝업·상태별 화면
    ├── templates/                 # 공통 HTML 원본
    ├── scripts/                   # 정적 생성·브라우저 검수
    ├── assets/                    # 로컬 글꼴·임시 이미지
    └── review/                    # 캡처·영상·JSON 검수 기록
```

보존한 정적 지점 데이터는 [branch-data.js](prototype/branch-data.js), 정적 소식 데이터는 [news-data.js](prototype/news-data.js)에 있다. HTML 생성 관계와 수정 위치는 [프로토타입 README](prototype/README.md)를 따른다.

## 소식 CMS 실행과 확인

실제 수행한 설치·DB 준비·계정 생성·실행 순서는 [백엔드 README](backend/README.md)에 있다. 초기 준비 후 `backend/`에서 다음 명령으로 실행한다.

```bash
uv run python manage.py runserver 127.0.0.1:8768 --noreload --insecure
```

[실제 홈](http://localhost:8768/?branch=second), [CMS 로그인](http://localhost:8768/admin/), [실제 공개 소식](http://localhost:8768/news/?branch=second)을 연다. **관리자 → 소식 → 작성/편집 → 본문 아래 ‘팝업 설정’**에서 설정한다. 새 글은 먼저 초안 저장한다. 로컬 계정의 비밀번호는 `backend/.local-credentials`에만 저장하며 문서에 싣지 않는다. 실제 홈·지점·소식·팝업의 이동은 8768 안에서 끝난다. 기존 검수 자료에는 아래 보존 자료 서버가 필요하다. 기존 로컬 DB와 분리된 `127.0.0.1:55438`의 M1 전용 DB를 사용한다.

별도 터미널의 프로젝트 루트에서 실행한다. 기존 `8767` 정적 서버와 같은 포트를 쓰므로 동시에 실행하지 않는다.

```bash
python3 backend/scripts/serve-prototype.py
```

이 서버는 기존 [홈 주소](http://localhost:8767/?branch=second)만 `8768`의 실제 홈으로 연결하고 지점·캡처·검수 페이지는 보존한 파일로 제공한다. `backend/news/home.py`는 승인된 홈 HTML·CSS를 읽고 브랜드 소개·팝업과 소식 메뉴를 연결한다. 지점·시설은 실제 공개 리비전이고 홈 최근 소식은 정적 예시이므로 **홈 전체가 CMS화된 것은 아니다.** 브랜드 편집은 [관리자 → 브랜드·홈](http://localhost:8768/admin/snippets/news/brandcontent/)에서 확인한다.

## 프로토타입 실행

아래는 원본 정적 프로토타입만 검토하는 실행법이다. 위 서버 대신 사용하며 실제 DB 팝업 검증에는 `8768` 홈을 사용한다.

프로젝트 루트에서 실행한다. Python 3와 Node.js/npm을 사용한다. `npm start`는 Python 정적 서버를 호출하며, 화면 실행 자체에 npm 패키지 설치나 프런트엔드 빌드는 필요 없다.

```bash
cd prototype
npm start
```

[홈](http://localhost:8767/), [지점 안내](http://localhost:8767/branches.html?branch=second), [소식](http://localhost:8767/news.html)을 연다. 서버는 `127.0.0.1:8767`에 바인딩한다. 실제 문의나 지도 서비스로 연결하지 않는다.

기존 검수 자료는 서버 실행 후 [홈·지점 안내](http://localhost:8767/review/branch-slides/index.html), [공통 시설 슬라이드](http://localhost:8767/review/facility-motion/index.html), [정적 소식](http://localhost:8767/review/news/index.html), [상태 검수](http://localhost:8767/review/states/index.html)에서 확인한다. 캡처를 보는 데 Playwright 설치는 필요 없다.

## 검수 재현

기존 프로토타입 브라우저 검수를 재실행할 때만 별도 터미널의 `prototype/`에서 의존성과 Chromium을 준비한다. 아래 명령은 실제 [package.json](prototype/package.json)과 스크립트에 있다. 이번 CMS 작업에서는 이 생성·검수 명령을 재실행하지 않고 과거 자료를 보존했다. CMS 검증 명령·결과는 [별도 안내](backend/README.md#검증-재현)를 따른다.

```bash
npm ci
npx playwright install chromium
npm run review
npm run review:states
npm run review:news
npm run review:gallery
```

정적 서버가 실행 중이어야 한다. `review`는 홈·지점 안내, `review:states`는 팝업·다지점·빈 데이터·실패, `review:news`는 소식, `review:gallery`는 공통 자동 슬라이드를 확인한다. **검수 명령은 캡처·JSON을 덮어쓰며, `review:states/news/gallery`는 HTML도 재생성한다.** 생성만 필요하면 `npm run build:scenarios`를 사용한다. 세부 범위·제한은 [프로토타입 README](prototype/README.md)와 [디자인 검수 기록](prototype/DESIGN.md)을 확인한다.

자동 검수 통과와 사용자 시각 승인은 구분한다. 실제 기기·Chromium 이외 브라우저, 외부 서비스와 운영 환경은 미검증이다. **보존한 정적 원본의** 예시 팝업 기간은 한국 시간 **2026-10-01 00:00 이상 ~ 2026-11-01 00:00 미만**이다. 원본 미리보기는 브라우저 시각, 과거 상태 검수는 고정 시각을 쓴다. 실제 CMS 팝업은 DB 설정과 서버 시각을 사용하며 현재 검토용 기간은 [새 검수 기록](backend/review/popups/README.md#직접-확인)에 있다.

## 기준 문서와 이전 자료

- [작업 규칙](AGENTS.md)
- [실행 역할·작업 흐름](docs/WORKFLOW.md)
- [최신 제품 요구사항](docs/PRD.md)
- [최신 디자인·승인 범위](prototype/DESIGN.md) — 같은 역할의 `docs/DESIGN.md`는 만들지 않는다.
- [콘텐츠 관리·기술 설계](docs/IMPLEMENTATION-PLAN.md) — 확정 기술과 미검토 관리자 제안을 구분한다.

[docs/legacy/](docs/legacy/)의 README·AGENTS·PRD는 **이전 프로젝트의 참고 자료**다. 과거 디자인·지도 선택·실행 경로·승인·작업 중지·운영 규칙은 현재 지침으로 자동 승계하지 않는다. 현재 문서에 반영한 요구만 현재 기준으로 사용하며, 근거 없는 운영 정책은 PRD의 미결정 항목에 남긴다.
