# M2-1 브랜드·홈 소개 관리 검수

검수일: 2026-10-10. 사용자 ‘ok 다음으로 넘어가자’로 M2의 첫 편집 단위만 진행했다. 공개 필수값은 이번 사용자 응답으로 **브랜드명·소개 제목**, 설명·로고·대표 사진은 선택으로 확정했다. 관리자 전체 사용성이나 실제 브랜드 자료 교체의 사용자 승인과는 구분한다.

**최종 결과:** 변경 전 서버 33개 통과. 변경 후 서버 50개 통과(발견 51개 중 별도 브라우저 1개 제외), 별도 브랜드 쓰기 브라우저 7개 흐름·실행 중 사이트 읽기/미리보기 4개 흐름·팝업 재노출 회귀 8개 흐름 통과. 최종 브라우저 JSON의 수집 오류는 0개다. Django 시스템 검사·미생성 마이그레이션 검사·Ruff 문법/서식 검사도 통과했다. 링크·캡처 경로 확인은 [document-checks.json](document-checks.json)에 기록한다.

## 실제 구현·직접 확인

- [관리자 로그인](http://localhost:8768/admin/) → [브랜드·홈](http://localhost:8768/admin/snippets/news/brandcontent/) → Y3GYM 선택. 브랜드명·로고, 소개 제목/설명, 대표 사진·대체 설명·가로/세로 중심을 편집한다.
- 초안 저장 → 우측 미리보기 → 하단 저장 버튼 옆 메뉴의 공개. 공개 철회는 동일 메뉴에서 제공한다. 공개 필수값 오류는 입력을 유지하고 안내한다. 수정 초안은 일반 홈에서 노출하지 않는다.
- [실제 홈](http://localhost:8768/?branch=second)과 [공개 소식](http://localhost:8768/news/?branch=second)의 브랜드 표시는 공개 리비전만 사용한다. 실제 게시글 팝업도 동일하다. 공개본이 없으면 준비 중 안내와 기본 지점·소식 탐색을 제공한다.
- 로컬 DB에 `0003_brandcontent`를 적용하고 승인된 임시 소개 문구·합성 대표 사진으로 사이트 공통 1행을 생성했다. 실제 로고는 없으며 텍스트 로고를 유지한다. 기존 계정·소식·팝업 설정과 원본 프로토타입은 보존했다.

## 검사와 캡처의 구분

| 기록 | 범위 |
| --- | --- |
| [baseline-tests.txt](baseline-tests.txt) | 변경 전 실행한 기존 서버 33개 검사 |
| [server-tests.txt](server-tests.txt) | 브랜드 및 기존 CMS/팝업의 서버·실제 DB 회귀 검사. 브라우저 검사는 별도 실행 |
| [result.json](result.json) · [browser-tests.txt](browser-tests.txt) | 별도 테스트 DB·임시 계정·임시 미디어에서 실제 관리자 브라우저 쓰기 흐름. 종료 후 테스트 DB/파일 제거 |
| [live/result.json](live/result.json) · [live-browser.txt](live-browser.txt) | 실행 중 `8768`의 관리자·홈·저장 전 미리보기. 콘텐츠 초안 저장/공개/철회는 실행하지 않음 |
| [popups/checks.json](popups/checks.json) · [popup-regression.txt](popup-regression.txt) | 현재 공개 팝업의 읽기 전용 재노출 회귀. 8개 흐름 |

서버 검사는 신규/수정 초안 보호, 실제 미리보기 권한, 공개/철회, 공유 이미지 사용처·접근 통제, 필수값과 과거 빈 리비전 공개 거부, 사진 중심 범위, CSRF/모델 권한/잠금, 오래된 폼 및 실제 동시 저장, 단일 브랜드·초기화 재실행 보존을 포함한다. 기존 소식·팝업 검사도 함께 실행한다.

쓰기 브라우저 검수는 운영자 메뉴 → 편집 → 초안 저장/재진입 → 미리보기 → 공개 → 사진 제거 → 공개 철회를 확인한다. 실행 중 사이트의 기존 콘텐츠를 검수용으로 덮어쓰지 않는다. `live/` 검수는 팝업을 독립적인 브라우저 문맥에서만 숨겨 홈 소개를 캡처하며 사용자 브라우저의 숨김 기록과 DB 노출 기간은 바꾸지 않는다. 팝업 동작은 별도 회귀로 확인한다.

| 실제 실행 중 화면 | PC | 모바일 |
| --- | --- | --- |
| 홈 첫 화면 | [1440×900](live/home-pc-first.png) | [375×812](live/home-mobile-first.png) |
| 홈 전체 | [1440px 폭](live/home-pc-full.png) | [375px 폭](live/home-mobile-full.png) |
| 관리자 | [입력 상단](live/brand-editor.png) · [사진·중심](live/brand-editor-photo.png) | [입력 화면](live/brand-editor-mobile.png) |
| 저장 전 미리보기 | [운영자 화면](live/brand-draft-preview.png) | 동일한 반응형 홈 템플릿 |

PC 40px/모바일 30px 소개 제목, 배경 `#F8FAFC`, 대표 사진 PC 4:3/모바일 16:10, 가로 넘침·하단 문의 바와 이미지/글꼴 로딩을 확인한다. 첫 화면/전체 캡처를 직접 열어 사진·글자·배치도 확인했다. 긴 모바일 전체 캡처에는 촬영 시점의 고정 문의 바가 처음 viewport 위치에 함께 찍힌다. 사용자 디자인 승인을 자동 검사로 대신하지 않는다.

별도 테스트 DB의 상태 예시는 [사진 없음](home-mobile-no-photo.png), [공개 철회](home-mobile-withdrawn.png), [수정 초안 미리보기](brand-draft-preview.png)에 있다. 이 DB는 검사 후 제거하므로 임시 서버 주소는 현재 접속 경로가 아니다.

## 재현

`backend/`에서 실행한다. Python·Django·Wagtail·PostgreSQL 버전과 준비 절차는 [백엔드 README](../../README.md)를 따른다. 브라우저는 기존 `prototype/node_modules`의 Playwright/Chromium을 재사용한다.

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
uv run python manage.py test news.tests --noinput --verbosity 1
Y3GYM_RUN_BRAND_BROWSER=1 uv run python manage.py test news.tests.test_brand_browser --noinput --verbosity 1
node scripts/review-brand-home.mjs --live-read-only
Y3GYM_POPUP_REVIEW_DIR=review/brand-home/popups node scripts/review-popup-revisit.mjs
```

쓰기 브라우저 명령은 Django가 만든 별도 테스트 서버에서만 동작한다. 단독 Node 쓰기 실행은 거부한다. 기본 서버 검사에서는 브라우저 1개를 건너뛰고 두 번째 검사 명령으로 별도 실행한다. 캡처 재현은 이 폴더의 같은 이름 결과를 갱신한다. 기존 M1·프로토타입 검수 파일은 재생성하지 않는다.

초기 검수 스크립트에서 지연 로딩 이미지의 `decode()` 대기와 빈 문서의 저장소 접근 오류가 발생했다. 검수 스크립트만 수정해 재실행했으며 최종 결과 JSON과 서비스 오류를 구분한다.

## 남은 범위·한계

- 다음 단위는 M2-2 지점·시설 관리다. 본점·표시 순서·마지막 공개 지점·지점 공개 필수값은 아직 미결정이며 이번에 확정하지 않았다.
- 지점/시설·트레이너 CMS, 홈 최근 소식 연결, 실제 지도·전화·카카오톡과 운영 배포는 미구현이다. 정적 지점 페이지는 공통 브랜드 변경에도 아직 연결되지 않는다.
- 로고 입력·공개본 및 이미지 보호는 서버에서 확인했지만 공식 로고와 실제 사진·긴 운영 문구의 최종 시각 검토는 하지 않았다. 새 로고 표시값은 최대 180×32px의 비율 유지 시작값이다.
- 관리자 사용성의 사용자 확인, 실제 기기·Whale/Chromium 이외 브라우저·한국어 IME·운영 미디어/캐시·백업/복구는 미검증이다. 이번 팝업 회귀는 Chromium의 재노출 흐름이며 과거의 native 창 크기/좌표 검사를 다시 실행했다고 보고하지 않는다.
- 기존 M1 검수의 중복 이미지 업로드 탭 오류는 이번에 재현/수정하지 않았다. 운영 권한·브랜드 삭제/복원 정책도 미결정이며 브랜드 삭제 조작은 제공하지 않는다.

이번 단위를 마친 뒤 다른 기능을 자동으로 시작하지 않는다.

## 변경 파일

- 모델/공개 경계: [models.py](../../news/models.py), [0003_brandcontent.py](../../news/migrations/0003_brandcontent.py), [publication.py](../../news/publication.py), [context.py](../../news/context.py).
- 관리자/초기 자료: [wagtail_hooks.py](../../news/wagtail_hooks.py), [bootstrap_brand_review.py](../../news/management/commands/bootstrap_brand_review.py).
- 공개 홈/브랜드 표시: [home.py](../../news/home.py), [brand_wordmark.html](../../news/templates/news/brand_wordmark.html), [base.html](../../news/templates/news/base.html), [popup.html](../../news/templates/news/popup.html), [brand.css](../../news/static/news/brand.css).
- 검증: [test_brand.py](../../news/tests/test_brand.py), [test_concurrency.py](../../news/tests/test_concurrency.py), [test_brand_browser.py](../../news/tests/test_brand_browser.py), [review-brand-home.mjs](../../scripts/review-brand-home.mjs), 이 폴더의 결과·캡처.
- 현재 문서: [루트 README](../../../README.md), [백엔드 README](../../README.md), [PRD](../../../docs/PRD.md), [구현 계획](../../../docs/IMPLEMENTATION-PLAN.md), [디자인 문서](../../../prototype/DESIGN.md). UI 원본·기존 검수·잠금 파일·환경 설정·AGENTS는 변경하지 않았다.
