# 게시글 연동 팝업 · 실제 DB/홈 검수

**이력 안내:** 이 기록·캡처는 게시글 연결 당시의 탭당 자동 시도 한 번 정책을 검증한 자료다. 이후 사용자 확인으로 일반 닫기 후 새로고침·홈 재방문 때 재노출하도록 변경했다. 아래 과거 결과를 덮어쓰지 않으며 [최신 재노출 검증](../popup-revisit/README.md)을 현재 정책의 근거로 삼는다.

2026-10-10 로컬 검수. 이번 작업은 게시글의 팝업 설정과 실제 홈 연결까지다. 브랜드·지점/시설 관리, 홈 전체 CMS화와 운영 배포에는 착수하지 않았다. 자동 검사와 아래 캡처는 관리자 사용성의 사용자 승인을 대신하지 않는다.

## 변경 전 확인과 이번 구현

변경 전 실행 중인 CMS와 정적 서버를 확인하고 기존 서버 17개 검사를 재실행해 통과했다. 당시 팝업은 프로토타입의 가상 데이터뿐이었으며 관리자·모델·서버 연결은 없었다. M1 구현 계획에서 후속으로 분리한 기능이었다. 별도 팝업 관리자 메뉴는 미검토 제안이었고, 최신 사용자 지시대로 소식 편집 화면에 설정을 포함했다.

- **관리자:** 소식 작성/편집 → 본문 아래 **팝업 설정**. 새 글은 먼저 초안 저장한다. 팝업 사용·시작/종료(한국 시간)·현재 상태/이유와 **팝업 설정 적용**을 제공한다. 글 URL을 직접 입력하지 않는다.
- **저장:** `news.PopupSetting` / `0002_popupsetting`에 실제 저장한다. 본문 리비전과 별도이며 설정 적용이 본문을 저장·게시하지 않는다. 나중의 본문 저장·게시도 설정을 되돌리지 않는다. 게시 권한·편집 잠금·Post 행 잠금과 설정 버전 충돌 검사를 유지한다.
- **공개:** 홈·팝업 문서·모바일 데이터는 공통 서버 판정 `사용 && 글 공개 && 시작<=현재<종료`를 사용한다. 제목·짧은 설명·선택 대표 사진·연결 글은 현재 공개 리비전만 사용한다. 종료·팝업 해제는 글 공개를 철회하지 않는다.
- **사용자 확정 정책:** 기간 중첩 전체 허용, 개수 제한 없는 전체 자동 노출, 처음 글을 등록한 순서, 전체 지점 공통. 최초 초안 리비전 시각으로 정렬하며 같은 시각은 ID 순이다. PC 글별 별도 창, 모바일 한 개씩 순차 레이어, 탭당 자동 묶음 한 번이다.
- **복구:** 평소 ‘알림 보기’는 제거했다. 자동 차단·실패·저장소 제한 시에만 텍스트형 직접 열기 링크를 제공한다. 한국 시간 다음 날 0시까지 글별 오늘 숨김, 기존 닫기 ×·반응형·키보드 동작을 재사용한다.

## 직접 확인

두 서버 실행법은 [백엔드 README](../../README.md)를 따른다.

- [실제 홈 — 새 탭에서 열기](http://localhost:8768/?branch=second)
- [기존 홈 주소](http://localhost:8767/?branch=second) — `serve-prototype.py` 실행 시 실제 홈으로 연결
- [소식 관리자 목록](http://localhost:8768/admin/snippets/news/post/)
- [최종 검토 글 21 편집](http://localhost:8768/admin/snippets/news/post/edit/21/) · [글 22 편집](http://localhost:8768/admin/snippets/news/post/edit/22/)
- [실제 팝업 21](http://localhost:8768/popups/21/?branch=second) · [연결 게시글 21](http://localhost:8768/news/21/?branch=second)

최종 브라우저 실행에서 새로 만든 TEST 글은 **21·22**다. 기간은 **2026-10-10 10:54 이상 ~ 2026-10-11 11:54 미만(한국 시간)**이다. 앞선 성공 검수의 **17·18**도 보존해 현재 자동 대상은 **17 → 18 → 21 → 22**다. 17·18은 2026-10-11 11:48에 먼저 종료된다. 종료 후 글은 계속 공개되며 팝업만 제외된다. 실제 DB 확인 시점과 기간은 [local-state.json](local-state.json), 최종 실행의 테스트 글·설정은 [checks.json](checks.json)에 있다.

재실행은 새 TEST 글 두 개를 추가하고 기존 글을 보존한다. 자기 테스트 글만 수정·게시·철회하며 성공하면 검토용으로 다시 공개한다. 실패한 시도의 글은 삭제하지 않고 비공개로 남겼다. 중단된 초기 시도의 자기 초안 13·14는 팝업 사용을 해제했다. 기존 사용자 글·이미지·원본 프로토타입은 초기화하지 않았다.

자동 묶음은 탭당 한 번이므로 재검토에는 새 탭을 사용한다. 오늘 숨김을 선택했다면 다음 한국 시간 0시까지 해당 브라우저에서 자동으로 표시되지 않는다. 직접 URL은 공개·기간 조건에 따라 확인할 수 있다.

## 실제 실행한 검사

`backend/`에서 실행했다.

| 명령 / 방법 | 결과 |
| --- | --- |
| 변경 전 `uv run python manage.py test news.tests --noinput --verbosity 1` | 기존 17개 통과. [로그](baseline-server-tests.txt) |
| 변경 후 같은 서버 검사 명령 | **33개 통과** = 기존 17 + 팝업 16. [로그](server-tests.txt) |
| `uv run python manage.py check` | 문제 없음 |
| `uv run python manage.py makemigrations --check --dry-run` | 모델 변경 미반영 없음 |
| `uv run python manage.py migrate` / `showmigrations news` | `0002_popupsetting` 실제 로컬 DB 적용 확인 |
| `uv run ruff check .` / `uv run ruff format --check .` | 통과, 26개 Python 파일 포맷 확인 |
| 새 JS 4개와 검수 `.mjs` 2개의 `node --check` | 구문 검사 통과 |
| `node scripts/review-popups.mjs` | **9개 흐름 PASS**, 페이지 오류/경고 0. [JSON](checks.json) · [로그](browser-tests.txt) |
| `node scripts/review-popup-edges.mjs` | **3개 흐름 PASS**, 오류 0. [JSON](edge-checks.json) · [로그](edge-browser-tests.txt) |
| 작업 전 파일 SHA-256 대조 | 기존 204개 중 DESIGN/README 문서 두 개만 변경. 기존 UI 소스·캡처·legacy·M1 검수 원본 보존. [결과](preservation.json) |

서버 검사는 별도 테스트 DB에서 시작 직전·시작 정각·기간 중·종료 정각·종료 후를 각각 판정했다. 사용 해제·공개 철회·종료 뒤 글 조회, 공개 수정 초안의 제목/설명/이미지 보호, 본문 저장·게시 뒤 설정 유지, 권한·CSRF·편집 잠금·오래된 설정/동시 최초 적용 충돌을 포함한다. 테스트 DB만 생성·제거하고 로컬 앱 DB는 초기화하지 않았다.

브라우저는 실제 관리자 입력·DB 재진입·작성 중 제목/본문 유지·실제 홈/글 이동·복수 전체 순서·탭당 한 번·한국 시간 오늘 숨김을 확인했다. 홈은 320/375/768/1024/1440px, 모바일은 375×812와 375×568을 확인했다. 짧은 화면의 닫기 가시성·Tab 포커스·Escape·크기 전환 후 잠금 해제·저장소 제한 복구와 JavaScript 비활성 탐색을 포함한다.

중간 검사에서 발견한 서버 조회명·권한 응답 검사·프런트 응답 상태 처리와 검수의 지연 이미지 대기를 수정한 뒤 위 최종 결과를 얻었다. 변경 후 테스트를 `--keepdb`로 반복하면 Wagtail TransactionTestCase의 초기 데이터가 제거된 테스트 DB가 남을 수 있어 최종 서버 검사는 위의 **`--keepdb` 없는 명령**으로 새 테스트 DB에서 실행했다.

## 변경 파일

| 위치 | 내용 |
| --- | --- |
| [models.py](../../news/models.py), [0002_popupsetting.py](../../news/migrations/0002_popupsetting.py) | 글당 별도 팝업 설정·기간 검증·상태/이유, 실제 DB 테이블 |
| [panels.py](../../news/panels.py), [popup_admin.py](../../news/popup_admin.py), [wagtail_hooks.py](../../news/wagtail_hooks.py) | 글 편집 패널·별도 저장·권한/잠금/충돌 검사·관리자 URL |
| [관리자 패널](../../news/templates/news/admin/popup_panel.html), [새 탭 대체 form](../../news/templates/news/admin/popup_settings.html) | 새 글 안내·한국 시간·본문 입력 유지·설정 적용 |
| [home.py](../../news/home.py), [popups.py](../../news/popups.py), [views.py](../../news/views.py), [URL](../../config/urls.py), [middleware.py](../../news/middleware.py) | 보존한 홈 연결·공통 서버 판정·공개 리비전 조회·기간/공개 404·no-store |
| [홈 팝업 진입](../../news/templates/news/popup_entry.html), [팝업 문서](../../news/templates/news/popup.html) | 실제 데이터·기본 HTML 탐색·기존 표시 형식 |
| [home-popups.js](../../news/static/news/home-popups.js), [mobile-popup.js](../../news/static/news/mobile-popup.js), [popup-window.js](../../news/static/news/popup-window.js), [popup-settings.js](../../news/static/news/popup-settings.js) | 전체/순차 노출·조건부 복구·오늘 숨김·편집 비동기 적용 |
| [test_popups.py](../../news/tests/test_popups.py) | 서버 경계·초안 보호·설정/본문 분리·실제 DB 동시 적용 검사 16개 |
| [review-popups.mjs](../../scripts/review-popups.mjs), [review-popup-edges.mjs](../../scripts/review-popup-edges.mjs), [serve-prototype.py](../../scripts/serve-prototype.py) | 새 브라우저 검증·기존 홈 URL 연결. 원본 생성 스크립트는 실행하지 않음 |
| [루트 README](../../../README.md), [백엔드 README](../../README.md), [PRD](../../../docs/PRD.md), [구현 계획](../../../docs/IMPLEMENTATION-PLAN.md), [디자인](../../../prototype/DESIGN.md), [프로토타입 README](../../../prototype/README.md) | 이번 실제 완료 범위·최신 정책·실행·미구현/미검증 상태 갱신 |

이 폴더의 JSON·로그·캡처는 이번 작업의 새 검수 자료다. 기존 M1 `backend/review/` 파일은 덮어쓰지 않았다.

## 캡처

| 화면 | 파일 |
| --- | --- |
| 본문 아래 관리자 팝업 설정 | [설정](admin-popup-settings.png) · [초안 상태](admin-draft-settings.png) · [작성 중 입력 유지](admin-unsaved-body-preserved.png) |
| PC 홈 1440×900 / 전체 | [첫 화면](home-1440-first.png) · [전체](home-1440-full.png) |
| 모바일 홈 375×812 / 전체 | [첫 화면](home-375-first.png) · [전체](home-375-full.png) |
| 실제 CMS 팝업 | [PC](popup-desktop.png) · [모바일 첫 알림](popup-mobile-first.png) · [다음 알림](popup-mobile-second.png) · [짧은 화면](popup-mobile-short.png) |
| 복구 링크 | [자동 차단](home-blocked-manual-links.png) · [저장소 제한](home-storage-fallback.png) |

공개 화면의 글꼴·사진·잘림·가로 넘침과 위 관리자/팝업 캡처를 실제로 열어 확인했다. 전체 캡처를 위한 사진 eager 로딩은 검수 브라우저 안에서만 적용했다. 원본 UI·색상·글꼴·시설 슬라이드 코드는 변경하지 않았다.

## 미검증·남은 범위

- 자동 차단은 `window.open`이 `null`을 반환하도록 재현하고 **수동 클릭의 실제 새 창과 서버 글 이동**을 검증했다. Headless Chromium은 차단 기본 인자를 제거한 별도 확인에서도 자동 창을 허용했다. 실제 사용자 브라우저의 차단 설정·새 탭 처리·창 위치/크기 제한과 실제 기기는 별도 확인 대상이다. 헤드리스에서는 `resizeTo`가 반영되지 않아 PC 캡처의 창 높이가 700px이며 승인된 CSS의 하단 배치를 유지한다.
- 서버 단위 검사에는 공개/초안 대표 이미지 접근 회귀가 포함된다. 새 브라우저 검수의 글은 대표 이미지가 없는 선택 상태다. **기존 M1 중복 이미지 업로드 브라우저 검사는 재실행하지 않았고**, 당시 Wagtail 탭 오류를 해결했다고 보고하지 않는다.
- 팝업 제목·짧은 설명·대표 사진은 연결 글 공개본을 사용한다. 별도 팝업용 문구/사진 입력은 이번 범위 밖이며 구체화 전이다.
- 홈 최근 소식·브랜드·지점/시설·트레이너는 정적 자료다. 실제 로고·운영 정보·지도·문의·배포·운영 저장소/캐시, 다른 브라우저·한국어 IME와 관리자 사용성 사용자 검토는 남아 있다.
- 이번 요청을 마친 뒤 브랜드·지점 관리 구현을 자동으로 시작하지 않는다.
