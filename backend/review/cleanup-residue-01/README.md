# 기존 테스트 잔여물 정리 결과 — 좁은 독립 확인 완료

2026-10-14 KST. 사용자 승인과 ROOT의 구체 실행 지시에 따른 개발 정리를 마쳤다. **좁은 독립 확인 완료(기존 경고·관측 한계 유지)**다. 새 도구·새 환경·backup/압축을 만들지 않았고 Git 쓰기·제품/현행 도구 수정·기능/전체 회귀를 하지 않았다. [현재75경로 분류·정확한 PID/OID·실제 기록](inventory.json), [유지 검증·원실패·한계 요약](../README.md).

인벤토리의 `role`·`exists`는 실행 전 관찰이며 최종 상태는 `current_result`·`execution`·`current_summary`를 따른다.

| 실제 처리 | 수량·관찰 크기 |
| --- | --- |
| 완료 서버 종료 | 7개:8772/8773/8774/8775/8780/8781/34471 |
| legacy 논리 DB drop | 31개·약361.9MiB(물리 파일/OS free space와 구분) |
| 임시 폴더 삭제 | 63개·약650.5MiB allocated snapshot |
| 단독 /tmp 파일 삭제 | 조사68개 중58개·672KiB allocated |
| backend/review 파일 unlink | 3,742개·약296.0MiB, 역사 one-off 코드226개 포함 |
| prototype/review 파일 unlink | 131개·약41.8MiB |

현재8776·원본성8769·canonical 프로토타입8767과 canonical DB·원본 미디어·설정/계정/키·제품172파일·자동검사·backend/scripts·prototype/scripts·의존성을 보호했다. 기존 관리 CLI status124 DELETED·active/unknown0을 확인했고 제어 registry는 유지했다. legacy를 관리 도구에 채택하지 않았다.

종료 전 PID/starttime/exe/cwd/argv hash/UID/boot ID·선택 환경·소유 loopback socket을 확인하고 pidfd SIGTERM만 사용해7개 모두 kernel 종료를 확인했다. DB는 실제 instance/settings 대응·exact name/OID/comment hash·접속0·다른 환경 공유 없음·보호 original 제외를 재확인하고 Identifier DROP 뒤 부재를 확인했다. 강제 접속 종료나 broad kill은 없었다.

폴더는 exact realpath/inode/UID·regular ownership/nlink·현재 process 의존을 확인했다. 알려진 symlink12개는 config/prototype target을 따라가지 않고 링크 자체만unlink한 뒤 descriptor 기반 rmtree로 처리했다. 예기치 않은 guard 실패/공유 경로 삭제는0이다.

8772·34471은 서로 다른 revision/ID라는 이유로 보류하지 않았다. 완료 수동 fixture의 실제 ContentImage 원본20개는 보호 원본/자산 동일10개·자체 fixture 입력 동일9개·TEST 합성1개였고, 고유 비표식 업로드/비어 있지 않은 지도키는 관찰되지 않았다. 완료·미사용 조건으로 이 두 환경도 정리했다. 원본8769·현재8776은 별도 보호했다.

현재 남은 /tmp 디렉터리는 보호2개와 귀속 미확정3개다. 보류3개는 checkpoint-push-a1rh9bgw, content-image-lightbox-closeout-n9i845fs, kakao-map-docs-jlxzm4bs이며 이름만으로 삭제하지 않았다. 단독 파일은 활성8767의stdout/stderr 로그와 보호8769 환경 포인터2개를 유지했다. 귀속 증거가 부족한8개의 작은 generic migration/test/HTML/JS 파일도 보류했다. exact 경로·inode·이유는 inventory에 있으며 다음 조사를 자동 시작하지 않는다.

실제 opt-in의 popup mjs2개, 작은 기존 도구 chain/W01·OBS01 source20개와 필요한 직접 입력, 최신 판정 JSON, 대표 승인/실패 캡처9개를 유지했다. W01 static source 보존을 옛 환경 보존 이유로 삼지 않았다. 원 FAIL→별도 후속·실행 counts와 사용자 한정 승인은 유지 요약에 남겼다. 반복 raw archive/bulk JSON/과거 보고서·캡처는 영구 보존하지 않았다.

AGENTS 선별 보존 정책, 루트/backend README·PRD·구현 계획·WORKFLOW·DESIGN·프로토타입 안내의 현재 상태와 삭제 자료 링크를 정정했다. 현재 수동표는 완료8772의옛 접속/ID 표를 정리하고 승인 범위와 신규 CLI를 안내하는 작은 진입점으로 갱신했다. 제품 정책/디자인 수치와 실제 결과를 바꾸지 않았다.

ROOT는 legacy 정리 뒤 자신의 메모리 기준과 소스172/미디어204의내용·metadata/원본3DB174table rowhash+OID/보호process3/인증·키metadata/HEAD·index를 READ ONLY로 대조해 변경0을 전달했다. 이는 설계 직접 근거이며 개발의 검사로 표기하지 않는다. 개발은 소유권·부재·정지·keep source20 hash와 현재 문서 링크/비밀값 검사만 수행했다. 실제 기본 GET·최종 독립 판정은 독립 담당의 후속 범위이며 이번 개발에서 실행하지 않았다.

cold 공개 GET Timeout의 정확한 원인, OBS01 실제 동적 origin export·새 negative origin·실제 중단 Chrome 읽기 거절, 실기기/Whale/OS IME·운영/배포·전체 회귀는 이번 작업으로 해결/검증 처리하지 않는다. 실제 문서 검사 결과는 inventory의 document_validation을 따른다.

## 독립 확인

2026-10-14 KST. **PASS_WITH_RETAINED_LIMITS.** 독립 담당이 읽기 전용으로 확인하고 이 절과 inventory의 `independent_verification`만 마감했다.

- 직접 대조: 삭제63경로·31DB exact 이름/OID·종료7PID와 포트는 없었다. 보호process3·tmp5·원본DB3·미디어204파일의 존재, private 파일5의0600, registry124 DELETED를 확인했다. 소스20 hash·입력14·opt-in4의실행파일6/상대import6도 정적으로 확인했다. 기존 확인을 최종 마감에서 반복하지 않았다.
- 최종 standalone: 삭제58경로는 없고 남긴2파일(활성8767 로그FD·현재8769 포인터 포함)과 보류8파일은 같은inode다. 보류dir3 및 선별캡처9도 유지한다. 새 정리/환경/코드/검사·lint/캡처·백업을 만들지 않았다.
- 실제 비인증GET은8776 루트/로그인·8769 로그인200,8767 루트302였다. 원래8768 redirect는 따라가지 않았으며 HTTP 응답을 UI 승인으로 확대하지 않는다. 로그인POST·원본쓰기·재시작은 없었다.
- ROOT의메모리172소스/204미디어내용·원본3DB174table/identity·HEAD/index 대조와 개발의3873파일unlink·문서653링크/비밀검사 결과는 전달받은 근거다. 독립이 사전 내용 비교나 개발 검사를 재실행한 것으로 표기하지 않는다.
- [유지 요약](../README.md#미해결-문제와-최소-근거)의142/148·NAV/QA 한정 실행·원FAIL/후속은 별개이며 W01·OBS01·coldTimeout·픽셀 경고와 미확인 기기/운영 범위는 그대로다. 커밋·푸시·배포·다음 작업은 하지 않았다.
