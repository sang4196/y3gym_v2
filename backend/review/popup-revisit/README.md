# 팝업 새로고침·홈 재방문 재노출

2026-10-10. 사용자가 **일반 닫기 후 새로고침·홈 재방문 때 다시 표시하고, 오늘 하루 보지 않기를 선택했을 때만 숨기는 방식**을 확인했다. 이전 ‘탭당 자동 시도 한 번’ 정책을 대체한다. 디자인·노출 순서·공개/기간·관리자·데이터 구조는 변경하지 않았다.

## 변경 내용

- [home-popups.js](../../news/static/news/home-popups.js)의 `cms-auto-batch` 세션 제한을 제거했다. 이전 탭의 플래그·표시 기록이 남아 있어도 자동 노출을 막지 않는다. 일반 닫기는 숨김 기록을 저장하지 않으며 매 홈 로드에서 등록 순서로 자동 열기를 시도한다.
- ‘오늘 하루 보지 않기’ 선택 후 닫은 글만 한국 시간 다음 날 00시까지 제외한다. 새로고침·홈 재방문·새 탭에서 유지하고 만료 후 다시 표시한다. 기존 한국 시간 계산·저장 실패 안내를 재사용했다.
- PC는 글별 창 이름을 재사용해 이미 열린 창을 중복 생성하지 않는다. 모바일은 같은 페이지에서 한 개씩 표시한다. 같은 화면의 크기·지점 선택 변경만으로 다시 자동 열지 않는다.
- 뒤로가기 캐시 복원은 서버의 최신 공개/기간 조건을 받도록 홈을 갱신한다. 일반 `pageshow`는 추가 열기를 하지 않는다. 이벤트 동작은 [MDN pageshow](https://developer.mozilla.org/en-US/docs/Web/API/Window/pageshow_event)를 확인했다.
- 자동 차단·로딩 실패는 수동 복구 링크를 제공한다. 새로고침에서는 자동 열기를 다시 시도한다. 세션 저장소 사용 불가는 자동 노출 제한으로 사용하지 않는다.
- [새 재노출 검사](../../scripts/review-popup-revisit.mjs)를 추가하고 기존 [크기 검사](../../scripts/review-popup-sizing.mjs)·[경계 검사](../../scripts/review-popup-edges.mjs)·[CMS 통합 검사](../../scripts/review-popups.mjs)의 이전 정책 가정을 갱신했다. PRD·구현 계획·디자인·실행 문서도 최신 정책으로 맞췄다.

기존 [연결 검수](../popups/README.md)·[크기 수정 검수](../popup-sizing/README.md)는 당시 결과로 보존했다. 그 폴더의 JSON·캡처를 덮어쓰지 않았고 README에는 이후 정책 변경 안내만 추가했다. 정적 프로토타입의 UI 소스와 검수 자료는 재생성하지 않았다.

## 이번 실행 결과

앱 DB의 공개 예시 글 17·18·21·22를 읽었다. 테스트 글을 추가하거나 DB의 설정/기간을 수정하지 않았다. 숨김 기록은 격리한 브라우저 컨텍스트에만 저장했다.

| 검증 | 결과·근거 |
| --- | --- |
| 재노출·오늘 숨김 | **8개 흐름 PASS**, 오류 0. [checks.json](checks.json) · [실행 출력](browser-tests.txt) |
| 모바일·크기 전환·세션 저장소 제한 | **3개 흐름 PASS**, 오류 0. [edge-checks.json](edges/edge-checks.json) · [실행 출력](edge-tests.txt) |
| 실제 PC 창 크기·사진·긴 글·모바일 회귀 | **10개 흐름 PASS**, 오류 0. 실제 창 경계 25회 측정. [checks.json](sizing/checks.json) · [실행 출력](sizing-tests.txt) |
| 서버 팝업 회귀 | **16개 테스트 통과**. 공개본/초안·기간·권한·동시 적용. [실행 출력](server-tests.txt) |
| 기본 점검 | `manage.py check`, `ruff check .`, `ruff format --check .`, 변경 JS 5개 `node --check` 통과 |

재노출 검사에서 확인한 동작:

| 상황 | 결과 |
| --- | --- |
| PC 일반 닫기 → 같은 탭 새로고침 | 4개 다시 열림. 숨김 기록 없음 |
| PC 팝업을 열어 둔 채 새로고침 | 기존 4개 창 재사용, 중복 창 없음 |
| 소식 → 홈 재방문 / 뒤로가기 | 4개 다시 열림 |
| 이전 탭 자동 시도 플래그가 1 | 재노출을 막지 않음 |
| 첫 글 오늘 숨김 → 새로고침·재방문·새 탭 | 나머지 3개만 표시. 저장 시각은 한국 시간 다음 날 00시 |
| 숨김 기록 만료 | 4개 다시 표시 |
| 모바일 일반 닫기 → 새로고침·재방문 | 전체 순차 재노출, 별도 창 없음. 오늘 숨김은 선택 글만 제외 |
| 자동 차단 후 새로고침 | 자동 시도와 수동 복구 링크 유지 |

대표 캡처는 [모바일 새로고침 후](mobile-reloaded.png), [PC](sizing/popup-1.png)다. 크기 회귀는 화면이 표시되는 Chromium(`headless:false`, `viewport:null`)에서 검사했다. 재노출/모바일 동작은 별도의 headless Chromium 검사이며 창 크기 검증으로 확대하지 않는다.

## 재현 명령

서버 8768·보존 자료 서버 8767, 기간 내 공개 팝업 예시 두 개 이상과 그래픽 세션이 필요하다. 아래 명령은 이 폴더의 최신 결과·캡처를 갱신한다.

```bash
cd backend
node scripts/review-popup-revisit.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-revisit/edges node scripts/review-popup-edges.mjs
Y3GYM_POPUP_REVIEW_DIR=review/popup-revisit/sizing node scripts/review-popup-sizing.mjs
uv run python manage.py test news.tests.test_popups --noinput --verbosity 2
uv run python manage.py check
uv run ruff check .
uv run ruff format --check .
```

브라우저 검수의 초기 실패 기록은 `attempt-1`·`attempt-2`에 보존했다. 팝업 `window.close()`가 클릭 확인보다 먼저 완료되거나 초기 opaque `about:blank`에서 검수용 UUID/세션 플래그 초기화가 실패한 검사 코드 문제였다. 실제 창 닫힘 확인과 초기 문서의 검수 플래그 예외 처리를 보완했으며 최종 근거는 위 PASS JSON이다. 애플리케이션 오류를 무시하도록 바꾼 것은 아니다.

## 직접 확인과 미검증

[실제 홈](http://localhost:8768/?branch=second)에서 일반 닫기를 누르고 **같은 탭을 새로고침**한다. 소식으로 이동했다가 홈에 돌아와도 다시 표시한다. 오늘 숨김을 선택했다면 해당 글은 한국 시간 자정까지 제외한다. 기존 자동 시도 기록을 수동으로 삭제할 필요가 없다. 예시의 서버 기간이 끝나면 팝업이 나오지 않는 것은 정상이며 검수 스크립트가 임의로 연장하지 않는다.

- 캐시 복원 핸들러는 `persisted:true` 이벤트를 주입해 서버 재조회 분기를 확인했다. 실제 뒤로가기 재방문도 검사했지만 모든 OS/브라우저의 BFCache 복원을 검증한 것은 아니다.
- 자동 차단·세션 저장소 제한·숨김 만료는 격리된 브라우저 환경 대체다. 실제 브라우저 설정 변경·하룻밤 대기 검증은 하지 않았다.
- Whale·실제 모바일 기기에서 이번 재노출 검사는 미실행이다. 이전 Windows 직접 제어 도구 연결 오류가 해결됐다고 보고하지 않는다.
- 관리자에서 테스트 글을 추가하는 `review-popups.mjs`는 정책 관련 단언·레이아웃 격리만 수정하고 문법 검사했다. 이번에는 사용자 DB를 보존하기 위해 전체 관리자 브라우저 검수를 재실행하지 않았다. 기존 소식 CMS 서버 33개 전체도 이번에 다시 실행한 것으로 보고하지 않는다.
- UI 색상·레이아웃·폰트·창 크기 계산·관리자·DB·다른 기능은 변경하지 않았다.
