# 현재 검증 요약과 선별 보존 근거

**2026-10-15 현재 제품 개발 기준선 완료·커밋 준비 독립 조건부 통과:** 합의된 필수 제품 기능 중 확인된 미구현 C는 없다. 홈·지점/시설·트레이너·소식 CMS·팝업·지도/연락·사진 확대·공통 헤더는 기존 사용자 한정 승인(A)을 유지하고, 공개/초안·권한·충돌·QA 수명주기·dev/prod 설정은 로컬 구현·검증 완료와 잔여 한계(B)를 구분한다. 실제 자료·영업위치·운영권한·인프라·백업·배포는 후속 공개/운영 준비(D)다. 운영 비교·Docker·배포 준비는 사용자 우선순위로 잠시 중단했다. **운영 릴리스나 Git 커밋·푸시 완료를 뜻하지 않는다.** 이하 예전 날짜의 승인 대기·미구현 문구는 당시 단계 이력이며 현재 사용자 승인을 취소하거나 과거 판정을 변경하지 않는다.

[이번 독립 검증](qa-lifecycle-independent/commit-readiness-01.json)은 동일168파일 manifest·191소스 freeze 대조로 기존 전체164/164·4opt-in·skip0를 재사용했다. 전체 검사를 재실행하거나 새 검사와 합산하지 않았다. 새 locked 설치·기본 실행·정적 제공을 확인했으며, 실기기/Whale/OS IME·엄격 픽셀·OBS01·coldTimeout·W01·W004/W019와 실제 운영 한계는 남는다.

이번 독립 실행의 새 venv `uv sync --locked --no-python-downloads --link-mode copy`, 시스템 check·`makemigrations --check --dry-run`·migrate, Python81/JS49·제품55 lint/format은 통과했다. 현행 도구16의 기존 I0011건·format2건은 그대로다. collectstatic은 exit0·264파일(private/QA 제외·로그인 참조 자산18개)이며, 이전 복사본263개 고정 단언의 원 FAIL은 추가 `LICENSE.txt`1개 bytes 일치로 observer 원인을 확인했다. 같은 run의 별도 HTTP8 PASS와 원 FAIL·후속·기존164는 분리한다. 조율 중단 지시 혼선도 원 보고에 남겼다.

[own run 정리](qa-lifecycle/runs/qa-20261015T121720Z-a6d50c8fef95/cleanup-bf59dbd7.json)·[비밀값 제거 evidence](qa-lifecycle/runs/qa-20261015T121720Z-a6d50c8fef95/evidence-explicit-cleanup-7d22f008.json): 서버 stop/잔존process0·생성DB2개·새venv·run폴더 정리 완료, 중복 cleanup은 noop이다. 원본 서버3과 secret5 metadata 보존은 독립 결과이며 원본 DB 행 전수 대조를 뜻하지 않는다. 이번 문서 마감에서는 검사·QA·서버 작업을 재실행하지 않았다.

2026-10-14 KST. 완료·미사용 테스트 환경과 중복 결과물의 정리를 사용자 지시로 진행했다. 과거 bulk 캡처·로그·중간 보고서·일회성 코드는 선별 정리하며 원 FAIL을 성공으로 바꾸거나 서로 다른 실행을 합산하지 않는다. 이번 작업에서 제품 검사·전체 회귀는 재실행하지 않았다.

**2026-10-15 누적 기준선 커밋 준비(독립 검증 전 이력):** 로컬 개발 완료와 기존 사용자 한정 승인은 아래 근거대로 유지한다. 운영안 비교·Docker·실제 배포 준비는 사용자 우선순위로 잠시 중단했다. `docs/OPERATIONS.md`는 기존 미승인 제안으로 보존하며 확정안이 아니다. Git 반영은 아직 수행하지 않았다. 현재 소스168파일의 동일성이 확인됐으므로 같은164 전체 검사는 반복하지 않고, 테스트 담당의 독립 근거 대조·커밋 후보 새 설치/기본 실행과 필요한 관련 검사로 인계한다. OPS-01 전체164/164는 이번 재실행이 아닌 기존 결과이며 현재 CLI 복사 대상168파일의 재구성 manifest 해시가 당시 보존 해시와 일치한다. 제품 Python55 lint/format·Python81/JS49 구문 준비 검사는 통과했고, 현행 도구16의 기존 I0011건·format2건과 W01·OBS01·coldTimeout·픽셀/실기기·운영 한계는 유지한다. 후보는 수정32·신규107·승인된 추적 삭제1,946개이며 삭제 목록 SHA256은 `04ac3f1f56303ab85929c3c1f3cf23730bbe44a9f0ee1ffa5484f9cb20da1065`다. 파일별 SHA256·개별 용량·소스 freeze와 정확한 후보 목록은 로컬 비전송 준비파일 `.local/commit-readiness-01.json`에 두며 커밋 대상에서 제외한다.

## 현재 실행과 도구

현재 사용자8776, 원본성8769, canonical 프로토타입8767과 원본 DB·미디어·설정·키를 보호한다. 새 QA는 [백엔드 관리 CLI](../README.md#qa-환경-생성실행정리)를 따른다. [실제 정리·보류·한계](cleanup-residue-01/README.md), [현재 인벤토리·PID/OID·삭제 기록](cleanup-residue-01/inventory.json)이 이번 정리 근거다. 옛 포트·PID·private 경로는 당시 이력이며 현재 접속/제어 안내가 아니다.

제품·자동검사·backend/scripts·prototype/scripts·의존성을 유지한다. 실제 opt-in의 [popup-revisit](home-news/popup-revisit.mjs)·[popup-edges](home-news/popup-edges.mjs), 기존 통합 도구의 작은 코드 chain과 직접 입력도 유지한다. W01의 [verify.py](workflow-01/verify.py), [probe.py](image-chooser-focus-apply/probe.py), [inventory.py](contact-visibility-independent/inventory.py), [sandbox.py](image-chooser-focus-independent/sandbox.py)는 정적 재현/기존 도구 입력으로 보존한다. 소스 보존이 옛 tmp·DB·미디어 보존을 뜻하지 않는다. 정확한 목록은 정리 인벤토리에 있다.

## 정리 후 유지한 검증 요약

**OPS-01 개발·독립 결과:** [설정 경계·재현 설치·실행/정적 수집](ops-01/README.md), 최종 전체1회164/164 PASS·4opt-in·skip0. 이전148/148·142/142와 별도이며 생산 설정 검사와 development ownedDB를 구분한다. W004/W019·실제 운영 미검증을 유지하고 own4run/생성 DB6개를 정리했다. [독립 PASS_WITH_DEPLOYMENT_LIMITS](ops-01/independent-verification.json)·설계 검토 완료. 독립 선택16/16·후속 설정8/HTTP16·정적263/private·QA 제외 PASS, own2run/DB4개 DELETED다. 개발 전체/새 설치는 근거 읽기이며 재실행/합산하지 않았다. 독립 관찰 오류2건의 원기록·후속, W004/W019/W01·실제 운영 미검증은 유지한다.

| 단위 | 실제 실행·원실패와 후속 | 판정·근거 |
| --- | --- | --- |
| 통합 회귀 | 최초142건114 PASS/1 FAIL/27 ERROR → 보완 후141 PASS/1 FAIL/0 ERROR → 별도 지점1 PASS(내부11). 이후 새 최종 단일 실행142/142 PASS·4opt-in | [당시 최종142 결과](dev-integration-final-01/run-20261013-final-01/verification.json). 각 배치는 합산하지 않음 |
| 공개 사진·공통 확대 | 개발 최초146/148 → 한정 후속 → 최종 전체148/148 PASS·4opt-in. 독립 서버14/14·브라우저23·확대29사진, 별도 실제 비율23항목·일반/확대 각21사진 | 사용자가 직접 확인한 사진·라이트박스 범위 승인. 엄격 픽셀 원 FAIL은 아래 유지 |
| NAV01 헤더 공통 홈 | 개발16건15 PASS/1 FAIL·별도1 PASS, 텍스트40/로고40·standalone4. 독립 서버11/11·텍스트40/로고40. 텍스트 카운터3 PASS 후 도구FAIL → 별도 도구FAIL → 남은5 PASS; 로고8 PASS | [독립 기록](header-common-home-independent/verification.json). 직접 확인한 헤더 이동 범위 승인. 이후 전체152 실행 기록 없음 |
| QA 수명주기 | 독립12/12, 헤더4/4, 브라우저1/1(내부11), 수동9, Python4 Ruff lint/format·JS3 syntax | [독립 PASS_WITH_OBSERVATION_LIMIT](qa-lifecycle-independent/verification.json), [독립 요약](qa-lifecycle-independent/README.md). 각 실행 별도 집계 |

NAV01의 기존8776 반영은 guard stop/start 각1회와 PC1440/모바일375 각6경로의 한정 확인이었다. 당시 없는 로고·second 트레이너·카카오 URL은 사용자 확인 범위 밖이다. 독립 Broken pipe8 경고와 원 도구 실패도 지우지 않는다.

QA 개발 원실행은 자체12건9 PASS/3 ERROR, 후속11 PASS/1 오류 사례(기록2개), 별도 강제 중단1 PASS, 이후12건11 PASS/1 ERROR, 최종 두 배치 각각12/12였다. 초기 Django import 오류는 검사0개, 통합5개는 헤더4 PASS/브라우저1 FAIL, 별도 브라우저1 FAIL 뒤 다른 실행1 PASS(내부11)다. [원실패 분류](qa-lifecycle/failures.json)·[개발 이력](qa-lifecycle/verification.json)을 유지한다. 원 private 로그 bundle과 반복 archive의 과거 경로는 이번 정리 뒤 현재 파일 열람 위치가 아니다.

## 미해결 문제와 최소 근거

- **Ruff W01/B01/B02:** 최초 전역78 lint/40 format FAIL은 과거 관찰이며 전역 재실행·수정은 하지 않았다. 최종 a47 PASS와 b10 I0011건/format2개 FAIL을 구분한다. [b10 목록](dev-integration-final-01/ruff-b-python.txt), [lint 원 진단](dev-integration-final-01/run-20261013-final-01/ruff-b-lint.log), [format 원 진단](dev-integration-final-01/run-20261013-final-01/ruff-b-format.log)과 해당 소스를 유지한다. 경고를 없애려고 현재 도구를 삭제/수정하지 않았다.
- **OBS01:** 브라우저 export의 origin 정규식 결과0에 대한 후처리 AssertionError다. [원 오류·조건](qa-lifecycle-independent/failures.json), [당시 source](qa-lifecycle-independent/archive-summary-observer-initial.py), [정확한 기존 evidence](qa-lifecycle/runs/qa-20261013T151641Z-92518dfbfb6e/evidence-auto-result-b7565fd2.json), [관측 요약](qa-lifecycle-independent/auto-browser.json)을 유지한다. CLI1/내부11 PASS·실제 Chrome identity/종료·정리는 유효하다. 동적 HTTP origin export 부재를 transport 실패로 추정하지 않으며 새 negative origin·실제 중단 Chrome 조회 거절 강제 검사는 미실행이다. source의 이미 정리된 private CLI 로그 경로는 당시 기록이다.
- **cold 공개 GET Timeout:** 로그인HTTP200 후 첫 공개 GET 응답 헤더 대기에서10초 TimeoutError, stop/restart 이전 단계였다. [원 결과](qa-lifecycle/manual-restart-final.json), [같은 환경의 별도 후속 PASS](qa-lifecycle/manual-restart-followup.json), [8rendition 기록 간격17.16초 관찰](qa-lifecycle/cold-rendition-observation.json)을 유지한다. 정확한 원인은 미확정이며 제품 성능 수정이나 대기 확대로 성공 처리하지 않았다.
- **엄격 픽셀 관측:** [원76/77](content-image-lightbox-independent/pixel-proof-independent.json), [별도39/42](content-image-lightbox-independent/shape-pixels.json), [같은 CSS 크기 DPR2 원0/3](content-image-lightbox-independent/small-dpr2/pixels.json)을 유지한다. [실제 조건](content-image-lightbox-independent/small-dpr2/result.json)과 아래3캡처를 남겼다. 사용자 한정 승인과 detector/rasterization 경고를 구분하며 전체 픽셀 통과로 바꾸지 않는다.

## 대표 승인·실패 캡처

- A 홈·시설: [PC](../../prototype/review/facility-motion/home-desktop-full.png) · [모바일](../../prototype/review/facility-motion/home-mobile-full.png).
- 승인된 트레이너 직급·약력: [PC](trainers/regressions-final/combined/trainer/short-biography-desktop-section.png) · [모바일](trainers/regressions-final/combined/trainer/short-biography-mobile-section.png).
- 승인된 홈 소식5건: [PC](home-news/live-third/home/desktop-actual-news.png) · [모바일](home-news/live-third/home/mobile-actual-news-unobscured.png).
- 작은 popup DPR2 원 실패: [320×480](content-image-lightbox-independent/small-dpr2/long-normal-320x480-dpr2.png) · [320×224](content-image-lightbox-independent/small-dpr2/long-normal-320x224-dpr2.png) · [확대](content-image-lightbox-independent/small-dpr2/long-expanded-320x224-dpr2.png).

승인은 직접 확인한 범위에 한정한다. 실기기·Whale·OS 한국어 IME·W02 정확한 조기 재열기/Escape·전체 관리자 경계·운영/배포로 확대하지 않는다. W02 원 유효0/조건미충족1(ERROR)과 이후 사용자 한정 승인은 별개다. 원본 DB 행·미디어 bytes의 보존 대조는 ROOT가 자신의 메모리 기준과 비교하며, 과거 QA metadata-only 대조와 구분한다. raw DB·미디어·키·계정·코드 복제본의 새 archive는 만들지 않았다.
