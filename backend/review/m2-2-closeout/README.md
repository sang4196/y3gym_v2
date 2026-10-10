# M2-2 종료 문서 정리

작업일: 2026-10-10 한국 시간. **문서 검사 PASS. 제품 구현·테스트 재실행은 수행하지 않았다.** M2-2의 현재 종료 상태는 [초기 독립 FAIL](../branches-independent/README.md) → [R1 보완](../branches-repair/README.md) → [독립 재검증 PASS_WITH_WARNINGS](../branches-independent-recheck/README.md)다. 초기 보고·R1 보고·기존 캡처의 촬영 당시 상태를 재작성하지 않았다.

## 변경 파일과 내용

| 파일 | 이번 변경 |
| --- | --- |
| [루트 README](../../../README.md) | M2-2 종료 이력·경고·승인 한계와 M2-3 미착수/착수 조건 |
| [백엔드 README](../../README.md) | 독립 재검증 근거·실제 실행 수치 참조, 기존 경고·미검증과 이번 문서 검사의 구분 |
| [PRD](../../../docs/PRD.md#fr-03-트레이너) | 트레이너 공개 필수 이름·소속 지점, 나머지 선택·미완성 초안 허용·빈 영역 숨김, 단일 약력 목록·지점 내 수동 순서. FR-06의 M2-2 종료 상태와 후속 미결정 구분 |
| [구현 계획](../../../docs/IMPLEMENTATION-PLAN.md#다음-단위-m2-3-트레이너-관리) | M2-2 최종 상태, M2-3의 편집/공개 단위·지점별 이중 공개 조건·소속 이동 초안 분리·4:5 승인 카드·미디어/잠금 회귀·임시 자료·제외 범위와 미착수 조건 |
| [WORKFLOW](../../../docs/WORKFLOW.md) | 종료 문서 보고 → 설계 검토 → 깃노예의 별도 체크포인트 지시. M2-3은 체크포인트와 설계의 별도 구현 지시 이후 착수 |

새 검증 도구·결과·이 보고는 이 폴더에만 추가했다. 제품 소스·모델·마이그레이션·프로토타입은 수정하지 않았다.

## 이번에 수행한 문서 검사

프로젝트 루트에서 다음 명령을 실제 실행했다. 종료 코드 0, **로컬 링크 179개·Markdown 앵커 22개·검사항목 18개 PASS**다.

```bash
python3 backend/review/m2-2-closeout/verify_documents.py --output backend/review/m2-2-closeout/document-checks.json
```

[검사 결과](document-checks.json)와 [검사 도구](verify_documents.py)를 남겼다. 최신 문서 5개와 수정하지 않은 DESIGN의 로컬 경로·앵커, 공백/충돌 표시, 종료 이력·근거의 일치, 트레이너 확정 정책·M2-3 범위/제외/미착수, 독립 보고의 수치, 기존 실행 명령/테스트 소스 경로 존재를 검사한다. `git diff --check`도 읽기 전용으로 실행해 통과했다. 추적되지 않은 문서의 공백/충돌은 별도로 직접 검사하며 Git 검사만으로 전체 변경을 판정하지 않는다. 외부 링크 접속·HTTP·DB·서버·제품 테스트·제품 전체 포맷/lint는 실행하지 않았다. 새 문서 검사 도구 한 파일에만 `backend/.venv/bin/ruff format backend/review/m2-2-closeout/verify_documents.py`를 적용했다. 재실행하려면 `--output`에 새 파일명을 지정한다. 기존 결과는 덮어쓰지 않는다.

추가로 [작업 전후 보존 대조](preservation.json)를 수행했다. 기존 1,194파일 중 허용한 문서 5개만 변경됐고 나머지 1,189파일은 동일하다. 이전 백엔드 검수 780파일·프로토타입 186파일·제품 코드/설정/기존 스크립트·미디어 141파일·비밀 2파일·의존성 정의 5파일과 Git index가 동일하다. 기존 Bash 실행 예시도 보존했다. 새 종료 보고의 링크/앵커는 별도로 검사한다. `.git` 내부 파일 전체·`.venv`·node_modules·컴파일 캐시 등은 파일 보존 비교에서 제외한다. 이번에는 DB 행 해시를 새로 취득하지 않았으며 DB·서버·계정·미디어 조작 명령도 실행하지 않았다.

## 읽은 독립 재검증과 남은 한계

[독립 실행 요약](../branches-independent-recheck/verification.json)·[문제/경고 목록](../branches-independent-recheck/findings.json)·[독립 검증 당시 보존](../branches-independent-recheck/preservation-result.json)을 대조했다. F01·F02·W01 해결, 차단 결함 없음, 서버 79 PASS·옵트인 2 skip, 추가 독립 13 PASS·원래 재현 1 PASS, 브랜드 7/지점 11흐름 단독·합동·역순 PASS, 실제 앱 읽기 전용 5·팝업 재노출 8흐름 PASS는 **앞선 독립 실행 결과**다. 이번 문서 검사의 재실행 수로 합산하지 않는다.

기존 `backend/review/workflow-01/verify.py`의 전역 포맷 경고는 유지한다. 실제 기기·Whale/Chromium 이외 브라우저·한국어 IME·운영 배포/캐시/저장소/백업·사용자 시각/관리자 사용성은 미검증이다. 기존 native 팝업 좌표/크기·태블릿 포함 전체 조합·중복 이미지 업로드 오류도 이번 문서 작업에서 재검사하지 않았다.

프로필 삭제/복원·운영 계정 확대, 홈 최근 소식 CMS화, 실제 지도/전화/카카오톡·배포 등 후속 범위는 미구현이다. 삭제/복원·운영 권한·지도 제공자·호스팅/백업 세부 정책은 미결정으로 남는다. **M2-3 구현은 시작하지 않았고 commit·push·배포도 수행하지 않았다.** 설계가 이 종료 보고를 검토한 후 별도로 Git 체크포인트를 지시한다.
