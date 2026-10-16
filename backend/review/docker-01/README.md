# Docker·AWS·www 설정의 최소 유지 근거

2026-10-16 Git 반영용 요약이다. 아래 결과는 기존 실행 근거를 읽어 보존한 것이며 이번 Git 작업에서 제품·서버 검사를 재실행하지 않았다. 상세 개발 JSON·계측·run별 자료는 원 루트의 로컬 미추적 자료로 보존하고 Git에서 제외했다. 독립 요약 8개는 원문 그대로 포함했다. 원 FAIL과 별도 후속은 합산하거나 성공으로 바꾸지 않는다.

## 현재 www 설정

- 기존 자체 검증의 `current_status`: `PASS_WWW_PROXY_ONLY_TLS_REDIRECT_ANONYMOUS_WITH_LIMITS`.
- 실제 Caddy SHA-256: `8a07e50458dd9c8bbbea1c319e6087e6f41c18bf46a76aa750321643137be728`.
- proxy만 1회 교체, www→루트 경로/query 보존 308. HTTP www는 HTTPS www를 거치는 두 단계다. 신뢰 TLS 2호스트, URI 5개×HTTP/HTTPS의 10체인, 루트·정적8개·익명 로그인/보안 경계, 새 익명 브라우저3흐름은 기존 자체 PASS다.
- 로컬 runtime 원 FAIL3건과 로그 한계, 최초 DNS gaierror의 정확한 원인 미확정은 유지한다. 별도 권한 재현·후속 runtime·외부 DNS 후속 PASS와 구분한다.
- 사용자 최신 지시로 자체 근거에 따라 이번 WWW 작업은 종료했고 추가 독립 검증은 중단했다. 독립 완료로 표기하지 않는다.
- app/DB identity·env bytes·volume5 소유/권한 보존은 당시 관찰이며 이번 Git 작업에서 서버/DB에 접근하지 않았다.
- PC 백업은 18:47 KST 초기 스냅샷(사용자1·콘텐츠/리비전/미디어0), 사본4개278006bytes다. 이후 업로드는 포함하지 않는다. 복구의58테이블/536행·미디어0 한정 PASS와 전체 운영 복구·정기 외부 보관 미완료를 구분한다.

## 로컬 검증과 남은 관찰

- 기존 Docker189 소스: 개발 Docker23/23·CLI15/15·전체167/167·4opt-in·skip0. 독립은 Docker23/23와 작은 JPEG/WebP native probe를 직접 확인했고 전체167·CLI15는 동일 소스 인계 재사용이다.
- 이후 결합191 소스: 전체170/170·4opt-in·skip0·실행1회. 이전169/170, 별도 Trainer1 PASS·로고167 PASS와 합산하지 않는다. 초기 cold-home20.162s의 정확한 원인은 미확정이다.
- 결합191 SHA: `8bdc75ca1c44d88c920d02952e5b45e3041160b7c2b34cfdf84ed40a22ff69fc`; 앱98입력 fingerprint: `b59117b373c1fe90fdef8433ef7c5e40eebd214617097024734cf1039039660d`. 이는 www Caddy 후속 수정 전 이력이다.
- 독립 관리자 전체 판정은 `FAIL_GUARD_ZERO_ACCESS_AND_LOGOUT_OBSERVED` 그대로다. Gravatar 외부 GET10건을 guard가 차단해 blocked0 가정은 FAIL이고, 9화면·로그아웃 관측 성공은 별개다. guard를 완화하지 않았다.
- OBS2의 cross-controller 나노초 정밀도, HSTS0/W004·SAMEORIGIN/W019·실사진 ACL·지도 키·실기기/Whale/OS IME·재부팅/완전 복구·정기 외부 보관은 기존 한계다.

## 개발 원실패와 후속

아래는 기존 개발 원실패의 단계·후속 설명을 최소 보존한 것이다. 원 run 자료와 상세 계측은 Git에 넣지 않는다.

- **FAIL · image_probe**: Empty tests directory remained after context exclusion; exact directory exclusion added.
- **FAIL · image_probe**: Non-root reader could not read mode0600/0700 copied QA source; root-owned runtime code made readable.
- **FAIL · provision**: Temporary PostgreSQL init server passed readiness before final server; final PID1 postgres readiness required.
- **FAIL · upload_observer**: QA expected edit redirect; actual upload returns image list. Persisted bytes and DB record assertion retained.
- **FAIL · host_negative**: Invalid Host response failed expectation; original status was not captured. Added strict_sni_host; later verified421.
- **FAIL · csrf_observer**: Hardcoded csrftoken name disagreed with production y3gym_csrf. Fresh form token and exact secure-cookie checks used.
- **FAIL · browser_CA_setup**: certutil SEC_ERROR_BAD_DATABASE before browser launch: pinned pwuser UID/GID1001, NSS directory owned1000. Dedicated container HOME/NSS directories with managed run UID/GID; later browser TLS login/upload/preview executed with normal verification.
- **FAIL · static_hash_observer**: Wagtail cache query was included in filesystem filename. URL path parsed; actual HTTP byte hash comparison retained.
- **FAIL · unit_harness**: 15 lifecycle unit cases:14 passed,1 missing owned redaction-fixture setup. Setup corrected; new run15/15 passed.
- **FAIL · browser_save_draft_observer**: Browser login/upload/same-origin preview completed, then nonexistent action-save-draft selector timed out30sec. Existing exact-role Korean save-draft button used; timeout and persisted-title assertion unchanged.

- 서버 준비의 tag@digest/RepoDigest 비교, swap4096-byte metadata 가정, Caddy validator EPERM 원실패는 유지한다. 각각 별도 읽기 후속·validator 한정 NET_BIND_SERVICE 보완과 구분하며 재pull·swap 재생성·운영 권한 확대를 뜻하지 않는다.
- Git 담당이 새 QA 자원을 만들거나 기존 자원을 정리하지 않았다. 앞선 자체/독립 단계의 정리와 운영 rollback 보존은 각 원본의 범위다.

## 원본 식별과 포함 여부

SHA-256은 로컬 원본 파일의 값이다. 원문 포함이라고 표시한 독립 요약 외에는 이 유지 요약만 Git에 포함하며 아래 원본 파일 링크를 제공하지 않는다.

| 원본 이름 | 당시/현재 기록된 상태 | 원본 SHA-256 | Git 보존 |
| --- | --- | --- | --- |
| app-image-import-independent.json | `PASS_APP_IMAGE_IDENTITY_READ_ONLY_NEXT_GATE_UNVERIFIED` | `bf964ef5d9241f1620bb8feb614a8a938e0625b53d355af64861d907a30005f8` | 원문 독립 요약 |
| app-image-import.json | `PASS_APP_IMAGE_ONLY_COLD_IMPORT` | `9af93105644e3b4ac3ead8421c08732b774e5950f53a9c38a68613ad86e283e1` | 이 문서의 최소 요약; 원문은 로컬 |
| deployment-preparation-independent.json | `PASS_WITH_INSTALLATION_GATES` | `cf257f7381f97e212e7d2119e107f54244fbeb73ea9d1b634e5fef5abb62d082` | 원문 독립 요약 |
| deployment-preparation.json | `LOCAL_ARTIFACT_AND_WHOLE_PASS_INSTALL_CAPACITY_REVIEW_REQUIRED` | `81e3ed2bc71d178d348d4ee3919597c394371514a40815dffa333c2910d48f17` | 이 문서의 최소 요약; 원문은 로컬 |
| independent-verification.json | `PASS_WITH_OBSERVER_HISTORY_AND_DEPLOYMENT_LIMITS` | `434dc0c8d5ff2f024e279bf2e37efe42105b0881c7bcd44bfaea1b9659087a83` | 원문 독립 요약 |
| minimum-installation-independent.json | `PASS_MINIMUM_INSTALLATION_READ_ONLY_NEXT_IMAGE_UNVERIFIED` | `a624bc967731f7d1733d1680959442b44e069e8fa3a0c4ade4f5be37f73058a6` | 원문 독립 요약 |
| minimum-installation.json | `PASS_MINIMUM4_INSTALLED_EMPTY_DAEMON_MEASURED_AWAITING_IMAGE_GATE` | `762a07e2dceb67e7c6767883d878b7ecf8c73b85f964cb2098b3929a0c957bc5` | 이 문서의 최소 요약; 원문은 로컬 |
| server-admin-independent.json | `FAIL_GUARD_ZERO_ACCESS_AND_LOGOUT_OBSERVED` | `75f934ad19ffe39563bbce0327c004381f48e8f0efb3472512b7c96703f1965f` | 원문 독립 요약 |
| server-admin.json | `INITIAL_ADMIN_CREATED_ACCESS_OBSERVED_BROWSER_ASSERTION_FAIL_PENDING_INDEPENDENT` | `f8ef27922a76a4df0921e49110fdd676d961289278aa8910c1d801136903062d` | 이 문서의 최소 요약; 원문은 로컬 |
| server-backup-restore-independent.json | `PASS_ONE_PRIVATE_DB_MEDIA_RESTORE_WITH_LIMITS` | `2bc46287ad05ca6a04f85ef348b086ed65b398db2c1948ccc33b492bebd646c2` | 원문 독립 요약 |
| server-backup-restore.json | `PASS_SINGLE_AWS_TO_PC_PRIVATE_BACKUP_AND_ISOLATED_RESTORE_WITH_PRESERVED_FAILURES` | `d4d0af39294b6eb3e5305ed6e0293d0592a70f48df22eb8c6e97131ef2bcf392` | 이 문서의 최소 요약; 원문은 로컬 |
| server-https-independent.json | `PASS_ROOT_HTTPS_ANONYMOUS_WITH_EVIDENCE_REDACTION_WARNING` | `78fe2c1c057c193641ac189625fcd4b1e0fe09b64b31a78ae3469adc6a32f157` | 원문 독립 요약 |
| server-https.json | `PASS_TRUSTED_ROOT_HTTPS_ANONYMOUS_HTTP_BROWSER_WITH_LIMITS` | `911fbf998043bde269622e437082a094f959116af5cc6ca6dd5c90595a519c54` | 이 문서의 최소 요약; 원문은 로컬 |
| server-preparation-closeout.json | `PASS_EMPTY_DB_APP_PRE_DNS_READY_WITH_PRESERVED_FAILURE_HISTORY` | `a03ce279e27c0a7c4d53e2bcb886d6498362557307c648d6b36473512316ffda` | 이 문서의 최소 요약; 원문은 로컬 |
| server-preparation-independent.json | `PASS_OBSERVED_SCOPE_WITH_SWAP_FSTAB_METADATA_UNVERIFIED` | `c864ede5e863df8c1fa78cdbf29e8757ac6bfd882f4bd27c4d2f3346bb297a07` | 원문 독립 요약 |
| server-www.json | `PASS_WWW_PROXY_ONLY_TLS_REDIRECT_ANONYMOUS_WITH_LIMITS` | `fc0bba35df638f2131e13a83a8d061beeded9c93c756d9e6e92c6c9f22f39fde` | 이 문서의 최소 요약; 원문은 로컬 |
| verification.json | `PASS_WITH_OPERATION_LIMITS` | `0c3830f642db1ff3eec04b5e098d46976e0c831bca99e042565e2b6e7dff954b` | 이 문서의 최소 요약; 원문은 로컬 |
