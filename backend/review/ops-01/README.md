# OPS-01 재현 실행·운영 설정 — 개발 자체 보고

2026-10-14 KST. **개발 자체 완료·독립 PASS_WITH_DEPLOYMENT_LIMITS·설계 검토 완료.** 제품 UI·게시 정책·의존성/lock·QA 도구·이전 보류 잔여물을 변경하지 않았다. 8776·8769·8767을 정지/재시작/변경하지 않았으며 Git·배포를 수행하지 않았다. [환경 계약·실제 사용 안내](../../README.md#개발과-운영-설정--ops-01), [명령·결과·정리 근거](verification.json).

## 변경

- `config/runtime.py`: development/production 선택, production no-dotenv, 필수 값·host/원점·경로 검증, 최소 HTTPS/cookie/proxy/HSTS/log 설정.
- `config/settings.py`: 기존 설정에 helper 연결. 개발 기본 host/원점·private 경로·cookie는 유지한다. 이미지 보호 view/storage/URL은 그대로 사용한다.
- `.env.example`: 비밀값 없는 참고 목록1개. 실제 운영 값은 비워 두었고 자동 로딩하지 않는다.
- `news/tests/test_runtime_settings.py`: 경계12개. 실제 Django RequestFactory로 proxy header의 기본 무시/명시 opt-in도 확인한다.
- 루트/backend README·IMPLEMENTATION-PLAN·현재 검수 요약의 관련 상태/명령만 갱신했다. PRD·디자인·W01은 변경하지 않았다.

설치된 Python3.13.15/Django5.2.18/Wagtail7.4.3와 PostgreSQL17.11을 확인했다. Django의 security check 등록/secret 기준, FileSystemFinder/get_files 및 Wagtail `wagtail_admin_base_url_check` 실제 API를 읽어 설정 경계를 확인했다.

## 실제 검사

| 실행 | 결과·범위 |
| --- | --- |
| 최초 경계 검사 | 12/12 PASS. 이후 추가한 QA-root 하위 경로/credential 공백/실제 proxy API 경계는 아래 최종 전체에서 확인 |
| 고유 runtime | CLI create→initialize fixtures/migrate→start/login200, actual current_database·migration 기록·권한10확인 PASS. 공개 rendition200, 익명 원본/미공개 원본/변환404, 자기 관리자 private 원본200 |
| production 설정 | deploy check exit0. W004(HSTS0 미정)·W019(기존 SAMEORIGIN) 유지. secret 누락·test DB·static/media 중첩은 실제 CLI 비정상 종료로 거절 |
| production collectstatic | 실제 ignore전체 인자로263파일/21,161,520bytes 수집. admin login 직접 assets18개 존재. private/QA 및 node_modules/review/templates/scripts sentinel 미포함 |
| 새 venv 재현 설치 | 기존 CLI auto --command 안에서 pyproject/uv.lock/.python-version만 자기 source에 복사. `uv sync --locked --no-python-downloads --link-mode copy` exit0, 새 prefix·고정 버전·Django check exit0, 원본/copy lock hash 동일 |
| 최종 전체 단일 실행 | **164 수집/실행·164 PASS/FAIL·ERROR·SKIP0**, 기존4opt-in 실행. 지점11·브랜드7·트레이너10·팝업재방문8·edges3·홈8 PASS. 별도 권한 output4는 전체 안의 서버 근거이며 브라우저 수에 더하지 않음 |
| 변경 범위 Ruff | settings/runtime/새 tests3파일 lint·format PASS. 전역 W01을 재실행/수정하지 않음 |

전체 실제 명령은 프로젝트 루트에서 다음1회였다. 과거148/148·142/142와 합산하지 않는다.

```bash
Y3GYM_ENV=development backend/.venv/bin/python -B backend/scripts/qa_lifecycle.py auto \
  --purpose 'OPS-01 final whole news.tests 4 opt-in once' --tests news.tests \
  --browser brand --browser branch --browser trainer --browser home_news
```

운영 모드는 test DB를 거절하므로 **production 로딩/deploy checks/collectstatic과 development ownedDB 연결/실행을 분리**했다. production에 준 비-test 이름은 DB를 생성하거나 접속하지 않았다. 실제 운영 DB 연결 성공으로 보고하지 않는다. 정적 수집에는 `--ignore node_modules --ignore review --ignore templates --ignore scripts --ignore '*.md' --ignore 'package*.json'`을 사용했다. runserver의 실제 정적 서버/TLS 제공이나 모든 정적 중첩 의존성의 운영 전달을 검증한 것은 아니다.

## 실패·정리·한계

제품 검사 실패는0이다. 결과 후처리에서 시스템 python3로 metadata helper를 부르며 `ModuleNotFoundError: No module named psycopg`가1회 발생했다. 보고서 쓰기 전 중단한 관찰 명령 오류였고 기존 venv로 같은 evidence를 읽어 정정했다. 전체 검사/설치를 재실행하거나 실패를 통과로 바꾸지 않았다. 예상한 누락/잘못된 운영 값의 CLI 거절은 별도 경계 검사다.

| owned run | 최종 상태 |
| --- | --- |
| `qa-20261014T034500Z-e46df7845f22` 경계 | DELETED, DB2 제거 |
| `qa-20261014T035316Z-350d53f5b24d` runtime | 소유 서버 stop→명시 complete→dry-run/exact plan→DELETED, DB2 제거 |
| `qa-20261014T035638Z-fa05f66d3da0` 전체 | 자동 evidence 보존→소유 자원 정리→DELETED, DB2 제거 |
| `qa-20261014T040204Z-f665e9b13983` 새 설치 | 새 venv/cache만 자기 경로·UID 확인 후 descriptor-safe rmtree로 제거→CLI DELETED. DB 미생성 |

패키지는 copy 모드로 설치했다. uv가 만든 venv/cache의 interpreter alias 등을 외부 target으로 따라가지 않고 새 fixture 하위 디렉터리만 정리했다. CLI의 symlink/hardlink 보호 정책을 완화하지 않았고 정리 거절도 없었다. 총 runtime4개·생성 DB6개 부재를 확인했다. 최소 단계별 evidence와 cleanup만 남기고 자기 중복 export3개는 정리했다. 원본 DB/media/credentials·코드 복제본·원 raw 로그/이미지를 review로 옮기지 않았다.

관리 CLI/브라우저 guard·protected_media/storage/URL·pyproject/lock7파일 hash와 원본/보호 env·credential/key metadata는 이번 자체 대조에서 동일했다. 원본 DB 행/미디어 bytes의 새 전수 대조나 원본 서버 HTTP는 실행하지 않았다.

실제 인프라·운영 WSGI/ASGI 서버·DNS/TLS·신뢰 프록시·정적 제공·운영 DB 권한/연결·실자료·secret/계정·백업/복구·배포는 미검증이며 사용자 선택은 운영 전 해당 설계를 확정할 때 필요하다. `/media`/private root/저장소/QA 디렉터리의 별도 공개 mount는 금지하고 기존 보호 view를 유지한다. 과거 coldTimeout/OBS01/엄격 픽셀/실기기 경계를 이번 작업으로 해결 처리하지 않는다.

## 독립 검증 마감

[독립 최종 PASS_WITH_DEPLOYMENT_LIMITS](independent-verification.json)를 설계가 직접 검토했다. 독립 선택 검사는1회16/16 PASS, runtime 후속은 설정8/HTTP16 PASS이며 정적263파일의 private·QA 제외를 확인했다. 독립 own2run/DB4개는 DELETED다. 새 제품/설정 결함은0이다. 위 개발 전체164/164·새 venv 설치는 독립에서 기존 근거를 읽은 것이며 재실행/합산하지 않았다. 이번 종료 문구 작업에서도 제품 검사를 재실행하지 않았다.

독립 observer 원오류2건은 JSON에 유지한다. 초기 metadata의 Boolean flag를 SHA 문자열과 비교한 가정 오류는 실행 전 근거 읽기에서 발생했고, RequestFactory의 Django 초기화 순서 오류는 초기 runtime 완료 설정/HTTP0건 상태로 기록됐다. 같은 초기화 DB/media/fixture에서 후속 설정8/HTTP16을 통과했으며 선택16/전체164/초기화를 반복하지 않았다. 개발의 시스템 Python psycopg 누락 관찰 오류와도 별개다.

보호3server·소스·lock·credential metadata 보존은 독립 범위로 확인했다. ROOT가 전달한 보호20항목·미디어204개의 bytes/metadata 변화0은 ROOT의 메모리 기준 직접 대조이며 독립의 원본 DB 행 전수 검사가 아니다. 실제 production DB 연결/권한·DNS/TLS·신뢰 프록시·static 제공·backup/restore·배포는 미검증이다. W004/W019/W01 및 과거 coldTimeout/OBS01/픽셀/실기기 한계를 유지하며 운영 승인으로 확대하지 않는다.
