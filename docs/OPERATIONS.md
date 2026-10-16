# Y3GYM AWS Ubuntu·Docker 운영 안내

현재 상태: **2026-10-16, 공개 화면의 검토용 문구 제거와 후속 푸터 소개·브랜드명·13px 수정 운영 반영 및 관련 확인 완료.** 적용 범위와 미확인 항목은 아래 ‘공개 운영 문구·문의 안내·푸터’ 절을 따른다. 카카오맵은 별도 한정 사용자 확인을 유지하며, 이번 결과를 전체 운영 준비 완료로 확대하지 않는다.

이전 WWW 작업 종료 기록: **2026-10-16 19:47 KST, 실제 www HTTPS·URI308 적용/개발 자체 확인 완료, 자체 근거로 작업 종료·추가 독립 검증 중단**. [WWW 최소 근거](../backend/review/docker-01/README.md)는 proxy만1회 교체·신뢰 TLS2호스트·HTTP/HTTPS10체인·익명 브라우저3흐름과 원 로컬/DNS FAIL→별도 후속 PASS를 구분한다. app/DB ID·시작/PID·env bytes·named volume5의 소유/권한을 보존했다. 기존 PC 백업은18:47 초기 스냅샷으로 이후 업로드를 포함하지 않으며 [독립 백업 복구 한정 PASS](../backend/review/docker-01/server-backup-restore-independent.json)와 함께 보존한다. Git/DNS/SG/새 AWS자원 쓰기0, 자동백업·retention·RPO/RTO·실사진 ACL·재부팅/완전 복구는 미완료다. 아래 설치/TLS/관리자/백업 수치는 각 당시 이력이며 source191은 현재 Caddy 수정 전 freeze다.

2026-10-14의 OCI 단일 VM 비교안은 선택하지 않았고 이번 AWS 확정으로 대체했다. 이전 무료 한도나 Nginx/native venv 제안을 AWS 운영 조건으로 승계하지 않는다. Supabase/Vercel 이전과 다른 플랫폼 추가는 이번 범위가 아니다. 제품 디자인·CMS 공개/초안·이미지 접근 정책은 유지한다.

## 단계와 승인 경계

| 단계 | 범위·현재 경계 |
| --- | --- |
| A Docker 구성·로컬 검증 | **로컬 완료.** 개발23/23·CLI15/15·전체167/167(4 opt-in·skip0), 독립 Docker23/23(실 TLS 브라우저6 포함)·최소 native JPEG/WebP probe 확인. 독립의 전체167/CLI15는 동일189소스 인계 근거 재사용이다. 소유 자원 정리·한계 유지. |
| B AWS 사전 배포·실배포 | **루트·www HTTPS/URI308 및 후속 카카오맵·공개 문구 운영 반영을 한정 확인했다.** 초기 관리자 접근 관측/전체 browser FAIL과 TLS 독립 한정 PASS는 유지한다. PC 초기 스냅샷1회·격리 복구/독립 한정 PASS는 이전 단위 근거이며 이후 업로드를 포함하지 않는다. 이번 공개 문구 반영에서는 app만 교체했고 DB·proxy·데이터 연결은 유지했다. |
| C 공개 운영 준비 | **미완료·정기 보관 운영 미정.** PC private 사본1회와 격리 복구만 확인했다. 실제 콘텐츠 최종 확정/사진 ACL·콘텐츠 운영 권한·재부팅·완전 서버 복원은 남았고 HSTS0/W004·SAMEORIGIN/W019 한계를 유지한다. 자동주기·retention·RPO/RTO와 PC 외 정기 보관 운영은 미정이다. |

이 단계 A/B/C는 배포 진행 단계이며 제품 필수 기능 미구현 분류와 다르다. 기존 제품 한정 사용자 승인은 유지하고, 실제 운영 릴리스는 별도로 판정한다.

## 현재 배포 테스트 대상과 확인 범위

다음은 **2026-10-16 19:47 KST WWW 적용 후 마지막 읽기 근거**다. 이후 지속 상태나 용량을 보장하지 않는다. 기존 strict known_hosts SSH·명령 단위 sudo를 사용했고 실제 AWS 계정/서버 IP/resource ID/인증값은 저장하지 않는다. 아래 별도 TLS·관리자·백업·pre-DNS 절의 수치는 각각 당시 이력이다.

| 항목 | 확인된 상태 |
| --- | --- |
| 대상·접속 | 서울 배포 테스트 서버. 설계측 AWS CLI2.38.1의 임시 로그인·EC2 read-only 조회 PASS, `ubuntu` SSH 접속 PASS. |
| OS·사양 | Ubuntu26.04LTS / x86_64 / t3.micro(2vCPU·1GiB RAM) / gp3 8GiB. |
| 조회 시 여유 자원 | 마지막 free1162641408bytes·MemAvailable411865088bytes·inode684257. 실제 swap268439552·DB70651904·media2469888·static/Caddy21970944bytes를 원예산+swap metadata4096에서 각1회 차감한 잔여 예약선1140129792bytes·차이22511616bytes(21.47MiB)다. 원 free512MiB/FS128MiB reserve 유지, 미래 성장/최대용량 보장은 아니다. |
| 설치·서비스 관측 | 기존 Docker/containerd/Compose·불변 image3 유지. app/database/proxy3 healthy·OOMKilled false·restart0. WWW에서 proxy만1회 force-recreate, app/DB ID·시작/PID는 적용 직전 기준과 같다. named volume5의 inode/dev/UID/GID/mode·env bytes 동일, 공개 host port는 proxy80/443뿐이다. daemon/SSH/기존 타 서비스 재시작·재부팅0이다. |
| 네트워크·CPU 모드 | 사용자 적용/설계 확인 TCP80/443 IPv4인터넷·SSH22 기존 제한을 유지했다. IPv6/group sources·8000/5432는 없다. DEV SG API write0·CPU Unlimited 유지, 실제 루트/www 공개 TLS 확인과 비용 영향 미검증을 구분한다. |
| DNS·현재 WWW | 사용자 CNAME www→y3gym.co.kr TTL600·루트 A 유지. 이번 기본 resolver/공개 DNS에서 승인 대상 해석을 확인했고 generic WWW Caddy site를 적용했다. HTTPSwww→HTTPSroot308 한 단계, HTTPwww→HTTPSwww→HTTPSroot308 두 단계, 경로/query 보존. DEV DNS/SG 쓰기0, WWW 서버 적용1회다. |

사용자는 현재 전용 t3.micro/8GiB를 약 한 달 사용한 뒤 다른 AWS로 이전하며 t3.small·20GiB 확장·스냅샷 추가 지출을 명시적으로 거절했다. 새 유료 자원/plan·EIP/S3/RDS를 추가하지 않는다. Free plan 남은31일·표시 credit$29.76·expiry2027-05-01은 사용자 콘솔 확인값이다. Billing API로 검증하지 않았고 비용0을 보장하지 않는다. t3 Unlimited의 추가 CPU credit 과금 가능성은 유지하며 모드는 변경하지 않는다.

빈 DB·앱 준비 완료를 공개 배포나 서버 수용량 승인으로 확대하지 않는다. **2026-10-16 Docker A 로컬 검증·앞선 문서 마감 당시의 AWS 접속0/Git 쓰기0와 대상 미확정 기록은 과거 근거로 보존**하며 이후 단계와 구분한다.

## 카카오맵 운영 설정

공개 지도는 기존 `Y3GYM_KAKAO_MAP_JS_KEY`를 운영 비공개 환경 파일 → Compose의 app environment → Django `KAKAO_MAP_JS_KEY` → 지점 페이지의 `branch-map-config` JSON으로 전달한다. JavaScript 키만 사용하고 REST/Admin 키·서버 비밀값을 넣지 않는다. 키가 비어 있으면 SDK를 요청하지 않고 기존 외부 지도 링크·안내를 유지한다. 키 값은 저장소나 검사 출력에 기록하지 않는다.

2026-10-16 운영 확인에서 JSON 요소와 위 전달 경로는 정상이었으나 운영 환경 파일의 해당 값이 비어 있었다. 사용자가 비공개 파일로 제공한 기존 JavaScript 키를 이 항목에만 반영했고 app만 같은 이미지로 재생성했다(Compose 명령 경과 약9.2초이며 실제 중단 시간을 측정한 값은 아니다). 다른 앱 환경변수·DB/proxy 컨테이너 ID와 시작 시각·Compose/Caddy/routes 파일·미디어/정적 볼륨 연결은 유지했다. 이전 항목만 담은 root0600 롤백 자료는 기존 release의 `private/kakao-map-setting.before-20261016T114523Z.json`에 보관한다. 실제 키는 Git이나 검사 출력에 포함하지 않았다.

같은 날 운영 origin `https://y3gym.co.kr`의 지점 페이지를 새 Chromium headless·1440×1000에서 읽기 전용으로 확인했다. 페이지 `keyConfigured=true`, `sdkLoaded=true`, `mapState=ready`, 실제 지도 타일12개·영역 안 마커1개 로딩, 페이지 오류0·요청 차단0을 확인했다. 선택 지점은 와이쓰리짐 동백점이며 공개 도로명주소 `경기도 용인시 기흥구 동백중앙로 269`를 사용한다. 기존 외부 좌표 지도 링크·새 창 속성도 유지했다. SDK HTTP200만으로 완료 판정한 것이 아니며 카카오 콘솔 설정을 직접 조회한 것은 아니다. 현재 공개 지점1곳이므로 두 지점 전환·실기기 검증은 미실행이고 SDK 실패 주입 검사를 추가로 수행하지 않았다.

사용자는 이후 운영 페이지에서 지도 정상 표시를 직접 확인했다. 이 확인 범위의 승인을 기록하며 다지점·실기기·다른 브라우저 전체 검증으로 확대하지 않는다.

최소 실행 근거는 로컬 `backend/review/qa-lifecycle/runs/qa-20261016T114821Z-d47921370f1b/evidence-auto-result-58f53a45.json`의 비밀값 제거 `command.log`에 남겼으며 run별 원자료는 Git 반영 대상에서 제외한다. 저장소의 검증 요약은 위 확인 결과와 한계다. 이 실행의 브라우저·프로필·run 폴더는 기존 CLI로 정리해 DELETED이며 새 DB·Docker 자원 생성은0이다. 전체 회귀·별도 독립 검증·DB/사진 백업·복구는 수행하지 않았다.

운영자는 기존 비공개 환경 파일의 이 항목만 수정하고 이전 값·존재 여부를 비공개 위치에 보관한다. 기존 Compose의 같은 release·project·env 경로로 `up -d --no-deps --no-build --pull never --force-recreate --wait --wait-timeout 90 app`을 실행해야 컨테이너 환경에 반영된다. 짧은 앱 중단 영향을 적용 전에 알리며 DB·미디어·proxy·TLS·www는 변경하지 않는다. 롤백도 해당 항목만 이전 값으로 되돌린 뒤 app만 재생성한다. DB·사진 백업이나 복구 연습은 이 설정 변경의 선행 조건이 아니다.

확인은 페이지 JSON의 키 설정 여부, 보이는 선택 지점의 공개 도로명주소, 실제 SDK·지도 타일·마커 및 외부 지도 링크를 구분한다. 키 존재나 HTTP 200만으로 지도 표시 완료로 처리하지 않는다.

## 공개 운영 문구·문의 안내·푸터

**후속 푸터 수정(2026-10-16):** 소개를 ‘1:1 프리피엄 프라이빗 PT센터’로 바꾼 뒤 사용자 정정에 따라 ‘1:1 프리미엄 프라이빗 PT센터’로 바로잡았다. 주소 위 이름은 헤더와 동일한 공개 브랜드명/fallback을 사용한다. `news/footer.html`·`news/brand.css` 두 런타임 파일만 수정했으며 소개·이름·주소의 `.footer-description`을 13px로 지정했다. 주소·문의 목적지·메뉴·Copyright는 유지했다. 새 이미지 `y3gym-footer:61245d975183`/`sha256:da572e15c54f6a67110ec42a36bda484f454787462ce5a51de1e718007c30e94`는 아래 이전 문구 정리 이미지 위에 해당 두 파일만 추가한 배포물이다. 소스 fingerprint는 `61245d975183a5c0afac515a9a7fb3b9c6257da58157ffe6b0dfd7851ce9b1e6`이며 Git 쓰기는 하지 않았다. 앱만 재생성(명령 경과9.934초)하고 static의 `news/brand.css`만 갱신했다. 다른 앱 환경값·데이터 연결·DB/proxy의 ID/시작/restart·Compose/Caddy/routes 해시는 이전과 같고 DB·미디어·지도·TLS/www는 변경하지 않았다. 이전 앱 참조와 CSS 경로만 담은 롤백 자료는 기존 release의 root0600 `private/footer-image.before-20261016T124445Z.json`이다.

**철자 정정 반영:** 같은 날 `news/footer.html`의 ‘프리피엄’을 ‘프리미엄’으로 정정해 `y3gym-footer:07fe5c80a9fa`/`sha256:21127351f0b537936bfffd0d833644389f9d7f9bb1383c5087e72d3c4b106603`을 app만 교체했다. fingerprint는 `07fe5c80a9fa3ffb82024eb64aaa1a8acf6261afcf895c4e95ba7011aca1c4dc`다. 후보 이미지 안 문구와 운영 홈·지점·소식 목록의 푸터 HTML을 확인했다. 주소·CSS(13px)·앱 환경값·DB/proxy/미디어·TLS/www는 유지했으며 정적 파일 갱신·DB 검사·전체 회귀는 반복하지 않았다. 이전 앱 참조만 담은 롤백 파일은 기존 release의 root0600 `private/footer-spelling-image.before-20261016T124852Z.json`이다. 임시 이미지 확인 컨테이너는 종료·제거됐고 새 QA 환경·Git 쓰기는 없다.

기존 관련 검사1건은 격리 PostgreSQL 준비 실패로 **미실행**했으며 제품 테스트 통과로 기록하지 않는다(`qa-20261016T124129Z-7a6643eaac93`). 별도 후보 이미지의 실제 Django 템플릿을 DB 쿼리 금지 상태에서 홈/지점/소식·공개 브랜드/fallback·주소/선택 지점·13px CSS 기준으로 확인했다(`qa-20261016T124345Z-7e8491731a0a`, PASS). 운영 Chromium PC1440×1000/모바일375×1000의 홈·지점·소식 목록6화면에서 서버 HTML/실제 문구·헤더와 이름 일치·주소 내용 불변·computed 13px·기존 Copyright14px·가로 넘침 없음·페이지 오류0을 확인했다(`qa-20261016T124524Z-ccc2992d5a59`, PASS). PC/모바일 캡처는 로컬 검수 자료로만 보존하며 Git에 포함하지 않는다. 세 실행 폴더·자기 브라우저를 정리했고 첫 실행의 전용 DB 컨테이너/볼륨2개도 정리했다. 전체 회귀·실기기 검증·사용자 화면 승인을 뜻하지 않는다. 아래 내용은 직전 문구 정리 단계의 이력이다.

2026-10-16 공개 렌더링 원본에서 ‘시각 검토용/임시 자료’, ‘로컬 CMS 검토 자료’, 사진별 가상·테스트 안내와 문의의 ‘실제 서비스는 연결하지 않습니다’를 제거했다. 홈 안내는 현재 선택한 공개 지점의 위치·문의 안내로 연결된다는 문장으로 바꿨다. 정적 프로토타입과 개발 전용 샘플은 그대로 두고, 실제 공개 HTML을 만드는 `news/home.py`·공개 템플릿·모바일 팝업 JS를 수정했다. 실제 문의 링크에는 모의 처리용 `data-preview-contact`가 없었으며 승인된 문의 방식은 바꾸지 않았다. 비공개 미리보기 안내와 필요한 빈 상태·실패 안내는 유지한다.

공통 `news/footer.html`은 [참고 사이트](https://www.seungjong.co.kr/)의 푸터 정보 구성을 참고해 기존 색상·글꼴·클래스 안에 현재 공개 브랜드, 지점 안내·소식, 선택 지점명·주소·위치와 문의 링크, 연도·브랜드명 기반 Copyright를 표시한다. 다른 회사의 상호·대표자·연락처를 복사하지 않았다. 지점이 없으면 지점 정보/문의 링크를 만들지 않으며 탭 전환 시 공개 지점과 푸터를 함께 갱신한다.

- **관련 검사:** 최종 격리 실행 `qa-20261016T121625Z-af88d67bcb35`에서 신규 `news.tests.test_public_presentation` 4건과 기존 헤더 이동·보호 미리보기 검사 각1건, **6/6·skip0**을 확인했다. PC1440/모바일375의 두 지점 전환·빈 연락처·실제 문의 영역 이동·소식 상세·PC 별도 창/모바일 레이어 팝업을 포함한다. 이전 전체 회귀와 합산하지 않았고 전체 회귀·별도 독립 검증을 반복하지 않았다.
- **원 실패/후속:** 최초 로컬 DB 연결 실패는 검사 미실행이다. 별도 Docker 격리 첫 실행의 홈 푸터 중복 쿼리1 FAIL·새 테스트의 Wagtail 기본 collection 복구3 ERROR는 각각 링크 조합 수정·`serialized_rollback=True`로 보완한 뒤 위 최종6건을 실행했다. 운영 브라우저 첫 실행은 점검이 실제 지점 ID를 `main`으로 가정한 도구 오류로 실패했고, 공개 데이터의 ID를 읽도록 바로잡은 후 별도 실행에서 확인했다. 원 실패 기록은 성공으로 바꾸지 않았다.
- **운영 반영:** 사용자 승인 후 `Y3GYM_APP_IMAGE`만 `y3gym-public-copy:b246855e29d9`로 바꾸고 static의 `news/context.js`·`news/mobile-popup.js` 두 파일만 갱신했다. 새 앱 이미지 ID는 `sha256:2f3c5e323a2d6c88b43d6efcd21b6ec0c2e42b75541d19242721a532f5ddd2bc`, 소스 fingerprint는 `b246855e29d9fc0ccfb7ddae93509315f4cd025f56a687d0e1c808c28dd62171`이다. 코드 기준은 HEAD `628aa66`에 누적 미커밋 변경을 포함하며 원격 문서 커밋만으로 만든 배포물로 표기하지 않는다. 앱만 재생성했고 명령 경과9.29초는 실제 중단 시간 측정이 아니다.
- **보존/롤백:** 실행 앱의 환경변수 전체와 미디어·정적 볼륨 연결은 이전과 같고 DB/proxy ID·시작 시각·restart 횟수 및 Compose/Caddy/routes 해시는 불변이다. 운영 DB·미디어·카카오 키·TLS·www를 변경하지 않았고 마이그레이션·백업·복구·Git 쓰기0이다. 기존 release의 root0600 `private/public-copy-image.before-20261016T122434Z.json`에는 이전 이미지 참조와 정적 파일 두 경로만 보관한다. 필요하면 이전 이미지에서 이 두 정적 파일과 앱 참조만 복원하고 app만 재생성한다.
- **실제 운영 확인:** 서버 HTML의 홈·지점·소식 목록과 변경 정적 파일 해시를 확인했다. 새 Chromium에서 PC1440×1000/모바일375×1000의 문구·metadata/alt/title/aria·푸터·가로 넘침·모바일 메뉴·문의 영역 이동·지점 탭·전화/채팅 href·브랜드 홈 이동을 확인했다. alert0·페이지 오류0·변경 요청0이며 실제 발신/메시지 전송은 하지 않았다. 현재 공개 지점1곳·공개 글/트레이너/노출 팝업0이므로 실제 운영 상세/팝업과 다지점 동작을 확인한 것으로 확대하지 않는다. 해당 흐름은 위 격리 자료로 확인했고 실기기·Whale은 미검증이다. PC/모바일 푸터 캡처 두 개는 로컬 검수 자료로만 보존하며 Git에 포함하지 않는다.
- **CMS 별도 수정:** 공개 브랜드 소개 제목 **‘와이쓰리 테스트’**는 저장된 콘텐츠이므로 자동 치환하지 않았다. 운영자가 Wagtail 브랜드·홈 소개에서 실제 제목을 입력하고 게시해야 한다. 2026-10-16 사용자가 공개 문구 정리와 푸터 수정 결과를 직접 확인한 범위에서 승인했다.
- **QA 정리:** Docker 격리 검사 두 실행은 각각 소유 컨테이너·볼륨2개와 실행 폴더를 정리했고 운영 브라우저 두 실행도 종료·폴더 정리했다. 최초 로컬 DB 연결 실패 run `qa-20261016T121204Z-90adb65d4f53`만 DB 소유 관찰 연결 불가로 RETAINED이며, 기존 연결 복구 후 관리 CLI로 미사용·소유를 확인할 때 정리한다. 삭제 가드를 우회하거나 기존 DB를 재시작하지 않았다. 기존 사용 환경과 배포/롤백 이미지는 유지한다.

## 실제 www HTTPS·리다이렉트 적용

2026-10-16 19:36 KST 기존 release의 `deploy/Caddyfile`에 환경 변수 기반 `www.{$Y3GYM_DOMAIN}` site와 `redir https://{$Y3GYM_DOMAIN}{uri} 308`만4줄 추가했다. 기존 root/import/routes·strict_sni_host·헤더 보호·127.0.0.1 health는 유지한다. [Caddy redir](https://caddyserver.com/docs/caddyfile/directives/redir)·[automatic HTTPS](https://caddyserver.com/docs/automatic-https)의 동작과 아래 실제 관측을 구분한다. Django ALLOWED_HOSTS/CSRF/admin origin·env/secret·앱 이미지·DB·UI는 바꾸지 않았다.

[개발 자체 WWW 근거](../backend/review/docker-01/README.md)의 최종 상태는 `PASS_WWW_PROXY_ONLY_TLS_REDIRECT_ANONYMOUS_WITH_LIMITS`이며 **자체 검증 근거로 작업 종료·추가 독립 검증 중단**다. 새 Caddy SHA256은 `8a07e50458dd9c8bbbea1c319e6087e6f41c18bf46a76aa750321643137be728`, 이전 값은 `12b89e8c366c0941c2b7c73f76ac983bcae8d32c0b8a99d07942440cc0416381`이다. Compose/routes/deploy.py SHA는 그대로이며 앱 ID `sha256:478d6a9fb51e94498427e06893c9915e7c83e182d80418d9b31082f60025c39e`와 build98 fingerprint를 재사용했다(Caddy는 앱 build 대상 밖). 이전 source191 freeze는 현재 Caddy와 다르다. 전체170/170·4opt-in·skip0는 이전 근거 재사용이고 이번 재실행이 아니다.

로컬 및 서버 staged `caddy validate`는 고정 이미지·64MiB·read-only·network none에서 PASS다. 서버 root0600 후보를 검증한 뒤 기존 파일 mode0644를 보존해 원자 교체하고 아래 **proxy만1회** 실행했다. app/DB ID·시작/PID, env bytes·named volume5의 inode/dev/소유/권한은 같고 서비스3 healthy·OOM/restart0이다. production proxy 기본 capability와 media 미마운트도 유지했다. rollback은 실행하지 않았다.

```bash
Y3GYM_RELEASE=/opt/y3gym/releases/base628aa66-dirtyb59117b373c1-logo-f1321a7-daa77580cd1b
Y3GYM_ENV_FILE="$Y3GYM_RELEASE/private/production.env"
Y3GYM_PROJECT=y3gym-test-daa77580cd1b
# 승인된 staged validate·원자 교체 후 실제 사용한 proxy 단독 재적용 명령.
sudo docker --host unix:///run/docker.sock compose --env-file "$Y3GYM_ENV_FILE" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" up -d --no-deps --no-build --pull never --force-recreate --wait --wait-timeout 90 proxy
```

| 실제 외부 확인 | 결과 |
| --- | --- |
| 신뢰 TLS | 기본 trust/hostname 검증으로 root·www TLS1.3 PASS. www SAN `www.y3gym.co.kr`, Let’s Encrypt YE2, 만료2027-01-14 09:38:21 UTC(18:38:21 KST). root YE1 인증서 fingerprint/만료는 적용 전과 같다. 검증 우회0. |
| URI308 | `/`, `/branches/?branch=main`, `/news/?category=event`, `/admin/login/?next=%2Fadmin%2F`, 복수 query/encoded return·space를 HTTP/HTTPS에서 확인한10체인. HTTPSwww→HTTPSroot 한 단계, HTTPwww→HTTPSwww→HTTPSroot 두 단계, 모든 Location 경로/query 정확·최종200·loop0. |
| 루트 회귀·보안 | 홈/health/익명 admin200·필수 CSS/JS/font/LICENSE8개200·헤더 브랜드href `/`. Host/SNI 불일치421·외부 Origin/valid CSRF403·위조 forwarded 헤더 경계·없는 media404 PASS. HSTS0·SAMEORIGIN·W004/W019 정책 유지. |
| 새 익명 브라우저 | HTTPSwww 홈·HTTPwww 지점·HTTPSwww 익명 로그인3흐름 최종 HTTPSroot200, 페이지 오류0·외부 차단0·폰트/기본 화면 확인. 지점 query는 Caddy에서 보존된 뒤 기존 client가 정규화했다. 인증 로그인/관리자 쓰기·캡처/HAR/영상/trace·본문/사진 저장0. |

원 로컬 runtime FAIL3건과 foreground 진단 exit1은 보존한다. config validate는 PASS였고 원 startup은 bootstrap 로그2줄만 남아 정확한 exit 원인은 미확정이다. 별도 same-UID/cap `cat`에서 own JSON0600 읽기 `Permission denied`를 재현했으며 비밀값 없는 동일 파일만0444로 바꾼 단일 후속에서 runtime308 세 URI를 통과했다. 이를 원 startup의 누락 로그로 대신하지 않는다. production cap/private env 권한을 넓히지 않았다. 최초 외부 검사는 `gaierror(-2)`로 중단했고 실패 host/당시 DNS 응답을 보존하지 못해 정확한 원인은 미확정이다. 기본/공개 resolver 재관측 후 **DNS/주소override·재적용 없이 별도 후속**에서 TLS/URI/루트/브라우저 PASS를 확인했다. 원 FAIL을 성공으로 바꾸지 않았다.

0.5초 자원 감시에서 적용 중 최소 MemAvailable317542400bytes·free1163030528bytes, 외부 후속 최소 margin22654976bytes였고 guard 위반/OOM 증가0이다. 원 image/FS128·DB256·media128·static/Caddy64·logs90·free512·swap256MiB와 swap metadata4096bytes를 유지했다. 위 현재 여유는 시점 관측이며 장기/WAL/최대 업로드 수용량을 뜻하지 않는다. 공개 GET은 자연스럽게 rendition/cache를 만들 수 있어 현재 DB 전체 불변·미디어0를 주장하지 않는다. 계정/fixture/콘텐츠 명시 쓰기는0이다.

own QA9run 모두 DELETED·Docker5개 제거·자기 run env PID0이며 서버 validator/후보 stage는 없다. 운영 rollback만 `$Y3GYM_RELEASE/private/Caddyfile.before-www-qa-20261016T103634Z-3d4ea1a23a9e`에 root0600/부모0700·이전SHA로 보존한다. 독립 승인과 명시적 미사용/퇴역 확인 뒤 정리한다. 실패 시 운영자는 이 사본의 SHA·권한과 현재 구성 SHA를 확인하고 **같은 디렉터리의 고유 임시 파일로 복사→기존0644로 원자 교체→위 proxy 단독 명령**으로 되돌린다. 앱/DB/env/volume을 reset하지 않는다. 다음은 **미실행 rollback 절차 예시**이며 위 변수와 사전 확인을 전제로 한다.

```bash
Y3GYM_ROLLBACK="$Y3GYM_RELEASE/private/Caddyfile.before-www-qa-20261016T103634Z-3d4ea1a23a9e"
# 사본 old SHA·현재 new SHA·소유/권한 확인 후, 고유 임시 파일을 같은 cfg 디렉터리에 생성.
Y3GYM_ROLLBACK_STAGE=$(sudo mktemp "$Y3GYM_RELEASE/deploy/.Caddyfile.rollback.XXXXXXXX")
sudo install -o root -g root -m 0644 -- "$Y3GYM_ROLLBACK" "$Y3GYM_ROLLBACK_STAGE"
sudo mv -T -- "$Y3GYM_ROLLBACK_STAGE" "$Y3GYM_RELEASE/deploy/Caddyfile"
sudo docker --host unix:///run/docker.sock compose --env-file "$Y3GYM_ENV_FILE" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" up -d --no-deps --no-build --pull never --force-recreate --wait --wait-timeout 90 proxy
```

이번 WWW에서는 Git·DNS·SG·새 AWS자원·새 백업·인증 로그인·전체 제품 회귀0이다. 실사진 ACL·CMS 편집·인증서 미래 갱신·재부팅/완전 장애 복구·정기 백업은 미검증이다. 아래 PC 사본은18:47 초기 스냅샷으로 이후 사용자 업로드를 포함하지 않는다. [독립 백업 복구 한정 PASS](../backend/review/docker-01/server-backup-restore-independent.json)는 이전58테이블/536행·미디어0 복구를 확인했고 기본 렌더는 DEV 후속 재사용이다. 기존 백업/관리자/TLS 원 판정과 한계는 유지한다.

## 실제 AWS에서 PC 비공개 백업·격리 복구

다음은 **2026-10-16 18:47 KST 초기 스냅샷 이력**이며 이후 사용자 업로드를 포함하지 않는다. [독립 백업 복구 한정 PASS](../backend/review/docker-01/server-backup-restore-independent.json)는 이 사본의58테이블/536행·미디어0 복구를 확인했으며 기본 렌더는 DEV 후속 재사용이다. 사용자 승인 목적지에 **당시 실제 서버 DB·media 백업1회**를 보관했다. [최소 sanitized 근거](../backend/review/docker-01/README.md)는 현재 자료의 비공개 비교·파일 크기/SHA·원 FAIL과 별도 후속·정리를 구분한다. 기존 관리자 전달 파일을 읽거나 로그인하지 않았고 계정/비밀번호를 reset하지 않았다. DB dump에는 현재 계정의 인증 hash·세션 등 민감한 DB 자료가 들어가므로 private 파일로만 보관한다. 본문·사진·개별 DB값/인증 hash·세션·production.env·TLS private key를 공유 근거나 QA 원로그로 복사하지 않았다.

| 항목 | 이번 실제 결과 |
| --- | --- |
| PC 보관 위치 | `/home/shlee/.local/share/y3gym/backups/backup-20261016T094735Z-193f8e0ab1cb`. 부모/고유 폴더0700·파일0600·비symlink·저장소/Docker build context/QA 밖, 기존 파일 덮어쓰기0. 전송 파일을 fsync하고 원격 size/SHA와 대조했다. 이 PC 사본은 보존한다. |
| 파일 종류·크기 | `database.dump` PostgreSQL custom-format259964bytes, `media.tar`10240bytes(스냅샷 당시 media파일0), `manifest.json`457bytes(불변 image/release·dump/media SHA), `verification.json`7345bytes(비공개 대조 보조자료). 총278006bytes·4파일 모두 source/PC SHA와 모드 일치다. manifest의 표준 복구 해시 계약은 dump/media2개 그대로다. |
| 일관성·서비스 | 기존 `deploy.py backup`으로 app/proxy writer를 중단한 사이 dump/media를 export했다. KST18:47:39.680~18:48:37.968, 중단·재개 구간58.2877초다. 정지 구간 전후의 비공개 DB/media 대조가 일치했고 재개 후 현재 자료도 일치했다. app/proxy는 같은 container ID/image로 다시 기동, database의 ID/시작 시각과 SSH/daemon은 유지했다. 서비스3 healthy·OOM/restart0·신뢰 루트 HTTPS200을 확인했다. |
| 용량·중단선 | 사전 DB 물리12531379bytes·media0. 이번 export 프로세스에만 단일 파일12MiB OS 상한을 적용하고 최종 staging 합계≤12MiB를 검사했다.0.5초 감시의 free 잔여 예약선+16MiB·RAM256MiB·inode100000을 유지했으며 export 최소 MemAvailable364007424bytes·최소 margin30932992bytes·OOM 증가0이다. 단일 파일 상한/최종 합계 검사와 지속 free 감시를 구분하며 12MiB를 다음 백업의 고정 정책/업로드 한도로 삼지 않는다. |
| 마지막 예산 | 원 image/FS128·DB256·media128·static/Caddy64·logs90·free512·swap256MiB를 낮추지 않고 swap extent metadata4096bytes를 추가 계상했다. 마지막 실제 DB할당69955584bytes로 증가한 사용분을 DB 예산에서 각1회 차감해 잔여 예약선1143312384bytes·free1174454272bytes·차이31141888bytes(29.70MiB)다. 원 free512MiB·FS128MiB reserve는 유지한다. DB 디렉터리 할당 증가를 새 이미지 점유나 예산 축소로 해석하지 않으며 월간/WAL/최대 업로드 수용량은 미검증이다. |
| 실제 격리 복구 | 같은 앱 ID `sha256:478d6a9fb51e94498427e06893c9915e7c83e182d80418d9b31082f60025c39e`·고정 PG17.11을 재사용했다. 새 QA/Compose project/DB/volume·fresh secret/PG 역할로 `restore --confirm-empty-restore`를 실행했다. dump의 owner 이름 호환성만 유지했으며 그 역할은 새 로컬 클러스터의 별도 객체/새 비밀번호다. 기존 운영/개발 DB로 복원하지 않았다. |
| 복구 비교·렌더 | private 기준의58테이블 행 집계/해시·현재 계정값·public/draft/revision 관계·media 파일 개수/크기/SHA가 일치했다. 해당 스냅샷은 User1·브랜드/지점/소식/트레이너/이미지/rendition/revision0이다. 별도 후속에서 localhost51025의 health/홈/익명 로그인/지점/소식200·없는 media404, Django `protected_media` routing을 확인했다. 해당 포트는 QA 종료와 함께 제거됐다. 실제 사진이 없어 사진 내용/공개·비공개 ACL 복구나 실제 CMS 편집을 확인한 것으로 확대하지 않는다. 원 계정으로 인증 로그인0·fixture/공개/외부 서비스 요청0이다. |

첫 사전 읽기는 관측기 TypeError로 실패했다. 원 type-only 실패와 UUID 직렬화 지원 보완 후 별도 사전 PASS를 보존했고 제품/배포/QA 도구 소스는 바꾸지 않았다. 최초 로컬 복구 `qa-20261016T095254Z-d58dfc4a61ab`는 **DB58테이블·리비전·미디어 비교 PASS / localhost 기본 렌더 URLError FAIL**이다. 이를 전체 성공으로 바꾸지 않았다. 자기 진단 run `qa-20261016T095826Z-23fbe41c6c36`의 동일 container/image/HTTP process에서 임시 application internal-only 설정은 effective binding 없음·ConnectionRefused111, 자기 일반 bridge 추가 후 실제127.0.0.1 binding·HTTP200을 관측했다. [Docker 포트 게시 기준](https://docs.docker.com/engine/network/port-publishing/)과 실제 재현 근거를 구분한다.

설계가 이 재현을 검토한 뒤 승인한 후속 `qa-20261016T095958Z-efd64e847436`에서는 **임시 QA application 설정만 기존 Compose의 일반 bridge 방식**으로 맞췄다. DB network internal·고유127.0.0.1 app 포트·같은 image·새 빈 복구 guard와200/404/데이터 일치 기대값은 유지했다. 새 고유 환경에 같은 PC 백업을 복구해 비교·렌더 PASS를 확인했고 서버 export/중단을 반복하지 않았다. 생산 네트워크/방화벽/DB 권한/앱 코드/원본 private 백업 변경·timeout 증가·검사 삭제는 없다.

export run `qa-20261016T094732Z-193f8e0ab1cb`와 위 로컬3run은 sanitized 근거 저장 후 모두 DELETED다. 로컬 소유 자원17개(최초 복구7·진단3·후속7)를 기존 관리 CLI로 정리하며 original/shared 이미지·기존 서버/DB/media/worktree/credentials는 유지했다. PC 사본의 size/SHA/0600 확인 후 자신의 원격 private staging4파일만 개별 unlink·빈 디렉터리 rmdir로 제거했다. 원본 DB/media·다른 backup·PC 사본은 삭제하지 않았다.

반복 백업은 **현재 PC가 켜지고 SSH 가능한 상태에서 수동으로 시작**한다. 매번 현재 자료와 DB/media 크기·동일 이미지·서비스 healthy, 실제 사용분을 반영한 잔여 예약선+16MiB를 먼저 재확인하고 새 고유 server staging/PC 폴더를 사용한다. 원 reserve 축소·기존 사본 덮어쓰기/삭제로 공간을 마련하지 않는다. 아래는 기존 서버 SSH 안에서 실행하는 core 명령 예시이며 이번에는 이 경로에 private 비교 관측과 명시 no-build/pull-never 재개를 함께 사용했다. 기존 도구의 기본 export는 dump/media/manifest3파일이고 이번 `verification.json`은 별도 private 검수 보조자료다. 실제 현재 크기가 이번 한시12MiB 상한에 맞지 않으면 먼저 계획을 다시 확인하며 실패를 숨기고 반복하지 않는다.

```bash
Y3GYM_RELEASE=/opt/y3gym/releases/base628aa66-dirtyb59117b373c1-logo-f1321a7-daa77580cd1b
Y3GYM_ENV_FILE="$Y3GYM_RELEASE/private/production.env"
Y3GYM_PROJECT=y3gym-test-daa77580cd1b
Y3GYM_BACKUP_ID="backup-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
Y3GYM_STAGE="$Y3GYM_RELEASE/private/export-$Y3GYM_BACKUP_ID"
# 실행 전 현재 크기/예약선 확인. 기존 stage가 있으면 backup 자체가 거절한다.
sudo python3 -B "$Y3GYM_RELEASE/backend/scripts/deploy.py" --env "$Y3GYM_ENV_FILE" --project "$Y3GYM_PROJECT" backup --directory "$Y3GYM_STAGE"
```

PC에서는 `umask 077`과 부모0700을 확인하고 `/home/shlee/.local/share/y3gym/backups/<새-고유-ID>`를0700으로 만든다. 기존 strict known_hosts SSH의 `sudo tar -C <자기-stage> -cf - -- database.dump media.tar manifest.json` stdout을 PC private 파일로만 받아 각0600으로 저장한다. raw dump/tar를 터미널·QA로그에 출력하거나 source/QA에 복사하지 않는다. 이번에는 기존 SSH와 Python streaming tarfile로 이름/regular/중복을 확인하고 파일을 O_EXCL로 생성했으며 4파일을 fsync·size/SHA 검사했다. 전달 후 manifest와 dump/media SHA·개수/권한·물리 off-server 위치를 확인한 다음 자기 staging만 정리한다. 별도 복구는 관리 CLI `auto --resource-backend docker --command`의 새 run·동일 image·새 빈 target에서 아래 명령 경로를 사용하며 기존 target/volume 거절 guard를 유지한다.

```bash
# 다음 값은 새 고유 관리 QA가 만든 fresh env·project와 보존 PC 사본 경로다.
python3 backend/scripts/deploy.py --env "$Y3GYM_RESTORE_ENV" --project "$Y3GYM_RESTORE_PROJECT" restore --directory "$Y3GYM_PC_BACKUP" --confirm-empty-restore
```

backup/전송이 실패하면 새 partial 사본을 private로 유지해 원 실패/중단·재개 여부를 확인한다. 기존 성공 사본을 삭제하거나 계정/원본 DB/media를 reset하지 않는다. 표준 backup의 finally 재개가 실패했을 때만 같은 release/env의 app/proxy 상태를 확인하고 기존 no-deps/no-build/pull-never/no-recreate 기동으로 복구하며 database/SSH/daemon을 중단하지 않는다. PC 전송이 끝나지 않았다면 server staging을 삭제하지 않는다. 실패한 local restore는 기존 DB로 다시 시도하지 않고 자기 자원 정리/새 빈 격리 환경의 원인 한정 후속으로 구분한다.

**범위·미결정:** 이 사본은 DB·media 데이터 백업이며 환경/인증 파일·TLS private key·전체 OS/이미지 저장소 백업이 아니다. 완전 서버 재구성에는 동일 앱/PG 호환성, 운영 설정·새/별도 보관 secret과 인증서 재구성이 필요하다. 현재 계정값은 private DB에 보존했지만 비밀번호 로그인·기존 세션 재사용·실사진 ACL·실제 콘텐츠 공개/편집·최대용량·재부팅·전체 장애 복구를 검증하지 않았다. 자동작업/주기·retention·RPO/RTO는 미정이며 **PC가 오프라인이면 이 수동 백업은 실행되지 않는다.** 승인된 PC 사본은 보존하고 자동 삭제/새 AWS 유료 자원은 만들지 않는다. 당시 www CNAME/서버 적용 대기는 이력이며 현재 상태는 위 WWW 적용 절을 따른다.

## 최초 테스트 관리자 생성·접근 확인

이 절은 **초기 관리자 생성/독립 관측 당시 이력**이다. 사용자가 이후 계정/비밀번호/자료를 바꿀 수 있으므로 이번 백업은 당시 users/content 값을 가정하지 않고 현재 private 자료를 새로 읽어 보존했으며 기존 전달 파일로 로그인하지 않았다.

사용자가 지정한 `y3-test`·메일로 이 테스트 서버 전용 최초 관리자1개를 생성했다. [최소 근거](../backend/review/docker-01/README.md)는 **계정 생성 완료 / 개발·독립 인증/화면 접근 관측 성공 / 전체 브라우저 FAIL 유지**를 구분한다. 사전 신뢰 HTTPS 로그인200·users0/동일 계정명 없음·서비스3 healthy·자원 중단선 통과 후, 기존 app에서 표준 `createsuperuser`를 한 번 실행했다. 새 랜덤 초기 비밀번호는 stdin으로 전달해 Django 표준 validator를 먼저 통과했고 argv/출력/로그/환경 dump에 기록하지 않았다. 표준 비대화식 명령용 변수는 해당 관리 프로세스 안에서만 설정하고 즉시 제거했으며 Docker 서비스 env는 변경하지 않았다.

- **생성·보존:** users0→1, active/staff/superuser true·비밀번호 검증 성공이다. 기존 계정/비밀번호 복사·덮어쓰기·reset은 없다. BrandContent/Branch/Post/Trainer/ContentImage/Rendition은 모두0이다.
- **개인 전달:** [관리자 로그인](https://y3gym.co.kr/admin/login/), 아이디 `y3-test`. 실제 초기 비밀번호는 `/home/shlee/.config/y3gym/aws-test-admin.credentials`에만 있으며 소유 UID1000·파일0600·부모0700·regular/비symlink다. 저장소·Docker build context·QA 밖이며 기존 파일을 덮어쓰지 않았다. 이 파일과 계정은 사용자 접속용으로 유지한다.
- **실제 접근:** 새 고유 QA의 격리 브라우저에서 HTTPS 로그인·대시보드와 소식/브랜드/지점/트레이너 목록4·새작성4 GET을 확인했다. 목록/새작성8개200·새작성 필드 접근과 대시보드 도착URL을 관측했고 page error0이다. 대시보드 emit200을 실제 응답 코드 보존으로 확대하지 않는다. 기존 콘텐츠가 없으므로 기존 자료 편집·저장·공개·사진·실제 운영 권한 분리를 검증한 것으로 확대하지 않는다. 로그인 값 외 콘텐츠 입력·fixture·저장/삭제/공개0, trace/video/HAR/스크린샷·쿠키/토큰/본문/제출 payload 기록0이다.
- **원 브라우저 FAIL:** 마지막 `assert.equal(result.blocked_requests, 0)`이10건 때문에 실패했다. `trainer_add`는 마지막 완료 단계 라벨이며 트레이너 제품 오류 근거가 아니다. 원 수집은 횟수만 기록해 요청별 method/path/차단 이유를 알 수 없다. guard는 루트 HTTPS의 GET/HEAD 및 로그인/로그아웃 POST만 허용했다. 어느 조건에서 막혔는지 미확인이며 성공을 위해 허용 범위/기대값을 바꾸거나 재실행하지 않았다. 원 DEV FAIL·요청별 내역 미수집을 유지하며 아래 별도 독립 관측을 그 원인으로 소급하지 않는다.
- **로그아웃·마지막 읽기:** 표준 logout302, own session cookie 부재·보호 dashboard302를 관측했다. 이후 DB에서 해당 계정의 인증 세션 행0, last_login 설정·계정1·콘텐츠/이미지0을 확인했으며 추가 세션 삭제0이다. 서비스3 healthy·ID/시작 시각/재시작0·OOM0을 유지했다. 마지막 free1192738816bytes·잔여 예약선1160187904bytes·차이32550912bytes(31.04MiB), RAM437641216bytes이며 원 reserve와 swap metadata4096 추가 회계는 유지했다.

생성 run `qa-20261016T091134Z-fa68381d507b`는 PASS, 브라우저 run `qa-20261016T091340Z-0fb9a7c27113`는 원 FAIL이다. 브라우저 자동 정리는 임시 결과의 숫자 `errors:0`에 기존 exporter가 `len()`을 호출해 TypeError로 막혔다. 원 결과·SHA를 보존한 뒤 own 임시 요약만 `errors:[]`/page_error_count0으로 맞췄으며 FAIL·blocked10은 그대로다. 기존 CLI complete→dry-run→정확 plan으로 sanitized 근거를 먼저 저장하고 두 run 모두 DELETED·폴더 부재·소유 프로세스0을 확인했다. QA/인증/제품 코드나 차단 정책은 변경하지 않았고 브라우저 재실행·서비스 재시작0이다. 서버·관리자·개인 전달 파일을 유지한다. 이후 독립 관측은 별도로 완료했으며 전체 FAIL·정책·관측 한계를 유지한다.

[후속 관리자 독립 확인](../backend/review/docker-01/server-admin-independent.json)은 **FAIL_GUARD_ZERO_ACCESS_AND_LOGOUT_OBSERVED**다. 정상신뢰 새 브라우저 로그인302·대시보드 실제 표시·목록/add8실제200·작성 form4, 표준logout302·cookie부재·보호dashboard302·최종 계정 인증세션0을 확인했다. 독립 차단10건은 모두 `GET https://www.gravatar.com/avatar/<masked>`의 `off_origin`이며 콘텐츠쓰기0·미분류0이다. 예상한 외부 차단과 blocked0 가정이 충돌했으므로 원 assertion/guard/외부 아바타 정책과 전체 FAIL을 그대로 둔다. DEV 원10건은 metadata가 없어 같은 원인으로 단정하지 않는다. 독립 dashboard HTTP200은 원 관측 상수였으므로 실측null/미확인이고 실제 화면 표시만 확인했다. console10 개별 원문/원인도 미확인이다. 새 제품 로그인 결함 확인·관리자 사용성 승인은 아니다. 독립 보고서 기준 users1/권한/email·콘텐츠/이미지0·기존 서비스3 healthy/ID/start/OOM/restart0·개인 파일 권한을 유지했고 TEST own `qa-20261016T092541Z-24b0f64e5f86`은 DELETED·Chrome PID부재다. 이번 문서 마감은 해당 근거를 읽었으며 로그인/SSH/서버·개인 파일 재조회·검사를 실행하지 않았다.

## 실제 루트 HTTPS 시작·검증

이 절은 **실제 TLS 시작·익명 스모크 당시 개발 근거**다. 당시 관리자 미준비·users0와 독립 대기 기록은 보존하며 이후 TLS 독립 한정 PASS와 현재 관리자 상태는 위 현재 문단/관리자 절을 따른다.

개발 자체 [실행·계측·실패/후속·정리 근거](../backend/review/docker-01/README.md)를 보존한다. 이전 pre-DNS JSON과 원 FAIL3건, 독립 swap observer false의 정확한 원인 미확정은 변경하지 않았다. 이번 단위에서는 원래 SSH/DMI 대상·서버 DNS·이미지3/파일4 해시·app/DB healthy·빈 데이터/권한/대기 migration0을 읽은 뒤, 기존 Compose로 **proxy만1회** `--no-deps --no-build --pull never` 시작했다. 영속 volume은 전용 Caddy data/config2개만 추가했으며 기존 app/DB의 ID·시작 시각·restart0, 원래 running service26개, env bytes·설정4파일·swap을 보존했다.

| 실제 확인 | 결과·범위 |
| --- | --- |
| URL·신뢰 TLS | [루트 홈](https://y3gym.co.kr/)·[익명 로그인](https://y3gym.co.kr/admin/login/)을 시스템 CA 신뢰·호스트명 검증을 켜고 확인했다. TLS1.3, SAN y3gym.co.kr만, issuer Let’s Encrypt YE1, 만료2027-01-14 07:44:31 UTC다. verify off·ignoreHTTPSErrors를 사용하지 않았다. 자동 갱신은 아직 관찰하지 않았다. |
| HTTP·정적·브랜드 | HTTP→HTTPS308·정확한 루트 Location, HTTPS 홈/health/익명 로그인200, 필수 CSS/JS·branch-data·Pretendard font/LICENSE8경로200·hash를 확인했다. 브랜드 홈 href는 `/`다. 홈 첫0.0781초, 반복3회0.0770/0.0881/0.0767초는 **기존 warm app·빈 DB·각각 새 외부 HTTPS 연결**이며 cold 시작·용량 성능이 아니다. |
| Host·프록시·CSRF | HTTPS에서 위조 Forwarded/X-Forwarded-Proto/Host/Port/For/Real-IP를 보내도 홈200·잘못된 redirect 없음, HTTP에서 https 전달헤더 위조에도308이다. 실제 TLS SNI 루트/잘못된 Host421, 유효 CSRF+외부 Origin403, 같은 토큰+정상 Origin의 빈 로그인 form200, 토큰 누락403이다. 실제 사용자명/비밀번호·로그인 시도는 없었다. 원 전달헤더 값의 upstream echo는 추가/관찰하지 않았으며 frozen proxy 설정과 실제 HTTP 경계 결과를 구분한다. |
| media routing | 실행 중 Django resolver가 `news.views.protected_media`이고 proxy에는 media mount가 없다. 없는 `/media/…` 요청404·Django 보안 헤더를 확인했다. 빈 DB이므로 실제 공개/비공개 사진·업로드·변환·초안/공개·라이트박스 흐름 확인으로 확대하지 않는다. |
| 실제 익명 브라우저 | 새 관리 run의 격리 Chromium profile/context에서 홈·로그인2화면200, 브랜드 href `/`, font ready·로그인 입력 표시를 확인했다. TLS 검증 활성, 기존 프로필/쿠키 재사용0, page error0·외부 transport0이며 검사 후 종료했다. 화면 디자인·모바일·CMS 사용성 승인이나 전체 제품 회귀가 아니다. |
| 정책·로그 | 실제 CSRF Secure/SameSite=Lax·SAMEORIGIN·nosniff, HSTS header 없음/설정0을 확인했다. 기존 W004(HSTS0)·W019(SAMEORIGIN 미리보기 정책)를 유지하며 이번에 check --deploy를 재실행하지 않았다. Caddy의 불필요 header_up2·admin endpoint disabled·TLS 요구로 HTTP/2·HTTP/3 skipped 경고도 실행 JSON에 남겼다. 세 서비스 stdout/stderr에서 서버 비밀값3개 검출0이다. |

0.5초 감시에서 proxy 시작117샘플·최대 간격0.55339초·최소 MemAvailable374095872bytes(356.77MiB), 보정 후 외부 확인24샘플·최대0.51688초·최소398340096bytes를 기록했다. OOM kill 증가0·reserve 초과0·proxy restart0이며 proxy 한도는64MiB 그대로다. 마지막 stats는 proxy16.7MiB/64MiB·app109.2MiB/512MiB·DB28.41MiB/192MiB다. 최소 free margin은 시작33,845,248bytes, 보정 후 외부 확인33,746,944bytes이며 마지막 읽기33,669,120bytes다. 모두 잔여 예약선+16MiB·RAM256MiB·inode100000 중단선 위였지만 표본 사이 순간 피크·지속 부하·월간 성장·최대 사진 수를 보장하지 않는다.

원예산 image/FS128·DB256·media128·static/Caddy state64·logs90·free512·swap256MiB는 낮추지 않았다. 기존 합계1503657984+swap extent metadata4096=1503662080bytes에서 실제 물리 swap268439552·DB53014528·media4096·static21860352·Caddy data77824/config12288bytes를 **각 한 번** 차감해 잔여 예약선1160253440bytes다. 마지막 free1193922560bytes와 차이는33669120bytes(32.11MiB)이며 공용 free512MiB·FS128MiB reserve를 유지한다. Caddy 쓰기 upperdir은 별도 물리24576bytes다. 시작 직전→마지막 df 감소532480bytes에는 새 volume/쓰기 레이어 외 daemon·로그·동시 파일시스템 변화가 포함된다. `/var/lib/docker` 전체 순회의 큰 증가에는 이미 존재한 readonly overlay lower layer가 다시 보이는 효과가 있으므로 새 물리 레이어 점유로 계산하지 않았다. 같은 파일시스템만 센 마지막 `du -sx`는 Docker75448320/containerd1191182336bytes이며 volume 합계와 다시 중복 차감하지 않는다.

외부 첫 수집 run `qa-20261016T084434Z-ac9d4bd8117d`는 static loop의 `path`가 보고서 Path 변수를 덮어써 저장에서 FAIL했다. 원 traceback·CLI exit1을 보존하며 보존되지 않은 외부 결과를 PASS로 주장하지 않는다. 저장 변수만 `report_path`로 바꾼 별도 run `qa-20261016T084544Z-292f481b39e6`에서 외부 TLS/HTTP·브라우저 PASS를 기록했다. Caddy start run `qa-20261016T084240Z-759e14c83dea`는 exit0이다. 세 run 모두 기존 CLI가 sanitized 근거를 먼저 저장한 뒤 DELETED·폴더 부재로 정리했다. 이 후속에서 서버 재시작·재배포·새 영구 QA 도구를 추가하지 않았다.

현재 release는 `/opt/y3gym/releases/base628aa66-dirtyb59117b373c1-logo-f1321a7-daa77580cd1b`, env는 그 안 `private/production.env` root0600·부모root0700, project는 `y3gym-test-daa77580cd1b`다. 이미지3·서비스3·전용 network·volume5·release/env·swap/fstab과 별도 private TLS 실행 JSON을 의도적으로 보존한다. Caddy data에는 인증서 private key가 있으므로 공유 근거로 복사하지 않는다. 아래는 **기록용 명령**이며 이번 검사에서 stop/restart를 실행하지 않았다. 일반 중단은 volume/인증서를 삭제하지 않으며 `down -v`·global prune을 쓰지 않는다.

```bash
Y3GYM_RELEASE=/opt/y3gym/releases/base628aa66-dirtyb59117b373c1-logo-f1321a7-daa77580cd1b
Y3GYM_PRIVATE_ENV="$Y3GYM_RELEASE/private/production.env"
Y3GYM_PROJECT=y3gym-test-daa77580cd1b
# 서비스3개 전체 중단: DB/media/static/인증서 유지
sudo python3 -B "$Y3GYM_RELEASE/backend/scripts/deploy.py" --env "$Y3GYM_PRIVATE_ENV" --project "$Y3GYM_PROJECT" stop
# 중단된 기존 구성 재시작: 새 build/pull/recreate 없이 기존 volume 재사용
sudo docker compose --env-file "$Y3GYM_PRIVATE_ENV" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" up -d --no-build --pull never --no-recreate --wait --wait-timeout 90 database app proxy
# 공개 proxy만 중단 / 시작: app·DB 보존
sudo docker compose --env-file "$Y3GYM_PRIVATE_ENV" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" stop proxy
sudo docker compose --env-file "$Y3GYM_PRIVATE_ENV" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" up -d --no-deps --no-build --pull never --wait --wait-timeout 90 proxy
# 운영 private 화면에서 확인하고 공유 전 비밀값 제거
sudo docker compose --env-file "$Y3GYM_PRIVATE_ENV" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" logs --tail 100 proxy app database
```

이번 개발 자체 스모크를 공개 운영 완료·독립 TLS 검증 완료로 바꾸지 않는다. 운영 관리자/권한·실제 콘텐츠/사진·지도키·최대 업로드/동시성·재부팅/자동 복구·자동 인증서 갱신·서버 backup/외부 전송/복원은 미검증이다. Git·DNS/SG/AWS 추가 변경이나 다음 기능을 시작하지 않고 설계 검토를 기다린다.

## DNS 변경 전 빈 DB·앱 준비 마감

이 절은 **16:58 KST pre-DNS 준비와 이후 독립 기본·스왑 후속 확인의 이력**이다. 당시 DNS 미변경·proxy/ACME0·app/database2·volume3과 명령 범위는 보존하며 최신 상태와 현재 명령은 위 HTTPS 절을 따른다.

[마감 최소 요약](../backend/review/docker-01/README.md)은 [기존 실행 최소 요약](../backend/review/docker-01/README.md)의 `server_preparation`과 CLI sanitized archive를 읽어 요약했다. 기존 JSON·원 FAIL·원로그를 수정하지 않았다. 이번 마감에서 pull/provision/migrate/collectstatic/up/validator·전체 제품 검사를 실행하지 않았다. 이전 결합191소스 SHA `8bdc75ca1c44d88c920d02952e5b45e3041160b7c2b34cfdf84ed40a22ff69fc`, 빌드98입력 fingerprint `b59117b373c1fe90fdef8433ef7c5e40eebd214617097024734cf1039039660d`와 전체170/170·4opt-in·skip0·1회 근거를 보존했다.

| 준비 항목 | 실제 결과·보존 상태 |
| --- | --- |
| release·project | `/opt/y3gym/releases/base628aa66-dirtyb59117b373c1-logo-f1321a7-daa77580cd1b`, Compose project `y3gym-test-daa77580cd1b`. Compose·Caddyfile·routes.caddy·deploy.py 4개만 전송했고 frozen source의 각 SHA가 일치한다. 전체 소스/venv/QA·원본 DB/media를 복제하지 않았다. |
| private env | 위 release의 `private/production.env`, root 소유0600·부모 root0700. SECRET_KEY와 분리된 bootstrap/app DB 비밀번호3개를 서버에서 한 번 생성했으며 후속에서 env bytes를 그대로 재사용했다. 값은 출력·로컬 복사·Git 기록하지 않았고 app/database의 stdout/stderr에서 실제 비밀값 검출0이다. Kakao key는 빈 값이다. |
| 실행 횟수 | 기존 app stream/load1, PG pull1(10.5207초), Caddy pull1(4.8949초), swap 생성/활성화·fstab 추가1, env/secret 생성1, deploy validate/provision/prepare 각1, app/database up1. 실패 Caddy exec1과 별도 보정 validator1을 구분한다. 공개 proxy·ACME·운영 관리자·fixture 생성0이다. |
| DB·권한 | DB `y3gym_test_daa77580cd1b`, app role `y3gym_app_daa77580cd1b`, bootstrap role `y3gym_boot_daa77580cd1b`. app의 superuser/createdb/createrole/replication 모두false, pending migration0, users/BrandContent/Branch/Post/Trainer 모두0이다. max_connections20·shared_buffers32MB를 실제 조회했다. |
| app·volume | worker1/thread2, app512MiB·DB192MiB 한도. app rootfs readonly, app media UID/GID10001:10001·0700, static10001:10001·0755, PG data999:999·0700이다. 전용 `_database`, `_media`, `_static` volume3을 보존하며 Caddy data/config volume은 없다. 마지막 stats는 app100.8MiB/DB43.64MiB다. |
| 내부 읽기 전용 확인 | SSH/Docker loopback HTTP에서 Host `y3gym.co.kr`·`X-Forwarded-Proto: https`를 명시해 health(DB)/홈/익명 관리자 로그인200, SAMEORIGIN·nosniff·CSRF Secure/SameSite=Lax를 확인했다. 홈 첫0.1551초, 반복3회0.0604/0.0586/0.0579초다. 공통 CSS/JS·branch-data·Pretendard/라이선스 등 필수8경로 존재·static251파일/논리21050741bytes를 확인했다. 실제 TLS나 인증 관리자 사용 검증이 아니다. |
| 격리 Caddy 확인 | network none·readonly/config RO·no-new-privileges·host port0을 유지하고 일회성 validator에 NET_BIND_SERVICE만 추가해 PASS했다. production Compose의 capability 정책은 변경하지 않았고 proxy 서비스·외부 인증서 발급을 시작하지 않았다. X-Forwarded-Proto/For 설정이 불필요하다는 validator 경고2개는 남긴다. |

원예산은 image/FS128·DB256·media128·static/Caddy state64·logs90·free512·swap256MiB로 합계1503657984bytes였다. swap 논리268435456bytes에 ext4 extent metadata4096bytes가 더해져 물리268439552bytes다. 원예산을 낮추지 않고 실제4KiB를 **추가**해1503662080bytes로 계상했다. 물리 swap268439552·DB53014528·media4096·static21860352bytes를 각 한 번만 차감하면 잔여 예약선1160343552bytes이고, 마지막 free1196077056bytes와의 차이는35733504bytes(34.08MiB)다. free512MiB와 FS128MiB reserve를 유지한다. swap은 `/var/lib/y3gym/y3gym-test-0729a88ca540.swap` root0600·nlink1·비symlink, fstab 전용 항목1개·기존 prefix 보존이며 후속에서 재생성/증설/편집하지 않았다. kernel SwapTotal은 header page를 제외한268431360bytes다.

감시는0.5초 설정, 마지막 후속36샘플·최대 관측간격0.52794초였다. 최소 MemAvailable356868096bytes(340.34MiB), 최소 inode684358, OOM kill 증가0·budget 초과0이다. free 잔여 예약선+16MiB·RAM256MiB·inode100000 중단선을 유지했다. 이는 해당 작업의 표본 관측이며 순간 피크 상한·월간 WAL/media 성장·동시 관리자/사진 변환·최대 업로드 수용량을 입증하지 않는다.

| 보존한 원 FAIL | 별도 후속 확인 |
| --- | --- |
| PG observer: tag@digest 요청 문자열을 tag 없는 RepoDigests와 직접 비교 | pull exit0·정확 ID/amd64는 유지하고 repository와 digest를 엄격 정규화해 읽기 전용 PASS. PG 재pull0, tag 존재 강제나 느슨한 substring 비교 없음. |
| swap observer: 논리256MiB를 물리 할당의 상한으로 가정 | stat/du/filefrag/ext4/header/소유·fstab로 non-data metadata4KiB 확인. 원예산 유지+4096bytes 추가 계상 PASS, swap 재생성/resize0. |
| Caddy exec255 EPERM: validator의 `--cap-drop ALL`이 binary의 유효 file capability를 제거 | 불변 image의 `/usr/bin/caddy` xattr에서 NET_BIND_SERVICE만 확인. 별도 validator에서 그 capability만 복원해 PASS. 원 FAIL을 config parse 실패나 성공으로 바꾸지 않았다. |

다음은 **기록용 운영 명령**이며 이번 마감에서 실행하지 않았다. 현재 범위의 시작은 app/database만 명시한다. deploy.py의 일반 `up`은 proxy까지 포함하므로 DNS 전 시작 명령으로 사용하지 않는다.

```bash
Y3GYM_RELEASE=/opt/y3gym/releases/base628aa66-dirtyb59117b373c1-logo-f1321a7-daa77580cd1b
Y3GYM_PRIVATE_ENV="$Y3GYM_RELEASE/private/production.env"
Y3GYM_PROJECT=y3gym-test-daa77580cd1b
# 중단: 데이터/volume 유지
sudo python3 -B "$Y3GYM_RELEASE/backend/scripts/deploy.py" --env "$Y3GYM_PRIVATE_ENV" --project "$Y3GYM_PROJECT" stop
# 재시작: 공개 proxy 제외, 이미 준비한 app/database만
sudo docker compose --env-file "$Y3GYM_PRIVATE_ENV" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" up -d --wait --wait-timeout 90 app database
# 최근 로그: private 운영 화면에서만 확인하고 공유 전 비밀값 제거
sudo docker compose --env-file "$Y3GYM_PRIVATE_ENV" -p "$Y3GYM_PROJECT" -f "$Y3GYM_RELEASE/compose.production.yaml" logs --tail 100 app database
```

own QA5run(`071900Z`, `072353Z`, `073702Z`, `074448Z`, `075754Z`)은 기존 관리 CLI가 sanitized 근거를 먼저 저장한 뒤 모두 DELETED로 정리했고 local run 폴더/소유 client는 남지 않았다. CLI의 local Docker 제거 수0은 원격 준비 자원을 삭제했다는 뜻이 아니다. 서버 이미지3·app/database·전용 network·volume3개·release/private env·swap/fstab은 후속 DNS/TLS 준비용으로 의도적으로 보존한다. 원격 private의 원 실패 로그와 성공 후속 로그/JSON도 별도로 유지한다. 폐기 시에는 명시적인 완료·미사용 확인과 실제 소유 경계 확인 후 별도 지시를 받아 정리하며 `down -v`·global prune을 일반 중단에 사용하지 않는다.

외부 HTTPS/DNS 전환·공개 Caddy/ACME·실제 인증 관리자/이미지 업로드·공개/초안 흐름·최대용량/동시성·EC2 재부팅·실제 백업/외부 전송·복구·실자료/계정 인계는 미실행이다. 별도 로컬 테스트의 TLS·복원 결과를 이번 서버 검증으로 바꾸지 않는다. 독립 기본 확인과 별도 스왑 후속 확인은 완료했다. 스왑 원 observer false의 정확한 원인은 미확정이며, 후속 실제 fstab 옵션도 sw이므로 옵션 차이를 원인으로 확정하지 않는다. 설계의 DNS 반영 확인과 별도 원격 지시 전 다음 배포 단계는 시작하지 않는다.

## 준비 앱 이미지1 cold stream/load 실측

이 절은 **15:55 KST 앱1 적재 단계 이력**이며 이후 PG/Caddy·swap·DB/app의 현재 결과는 위 마감 절을 따른다.

고유 관리 run `qa-20261016T065445Z-5545eb1f349f`에서 **앱1개만** 실제 적재했다. [실제 stream 해시·소유 client/monitor identity·41회 샘플·전후 계측·정리](../backend/review/docker-01/README.md)를 보존한다. 방식은 `docker image save y3gym-prepared:b59117b373c1-logo-f1321a7`의 stdout을 strict SSH의 소유 wrapper가 실행한 `sudo docker --host unix:///run/docker.sock image load` stdin으로 연결한 것이다. 로컬/원격 tar/gzip 파일을 따로 저장하지 않았다. 로컬/원격 ID는 `sha256:478d6a9fb51e94498427e06893c9915e7c83e182d80418d9b31082f60025c39e`, amd64·전체 labels가 일치한다. 기존 TEST의94파일 직접 검증은 같은 불변 image ID로 인계받았고 이번에 컨테이너로 재검사하지 않았다.

실제 전송은110139392bytes(105.04MiB), SHA256 `52c1dc91353577e781a7e35d8c363eb3f673ba7adbb21d2ec5fa0948aee23426`, 경과17.5369초, load exit0이다. client3개(local save/SSH load/SSH monitor)와 remote wrapper/load PID·start ticks·argv hash·run ID를 기록했다. 감시는0.5초 설정/최대 관측간격0.505초·41샘플이다.

| 측정 | 시작 전 | 작업·후속 샘플 최저 | 적재 후 |
| --- | --- | --- | --- |
| 가용 disk bytes | 2741612544 | 2282106880 | 2282106880(2.13GiB) |
| MemAvailable bytes | 502300672 | 455069696(434.0MiB) | 499249152(476.1MiB) |
| 가용 inode | 721149 | 698821 | 698821 |

free floor1503657984bytes와 RAM256MiB·inode100000 중단선을 유지했다. free가 floor+16MiB에 접근하면 자기 client만 중단하도록 했으며 이번 중단/재시도0·OOM kill 증가0·ENOSPC0이다. 최저 free는 floor보다778448896bytes(742.4MiB), 최저 RAM은 중단선보다약178MiB 높았다. Docker/containerd의 샘플별 RSS 최대는63.0/44.6MiB, 후속 inspect 계측은64.4/28.5MiB로 구분한다. 이는 해당 샘플에서 관측한 값이며 sub-0.5초 transient나 PG/Caddy 피크의 상한 보장이 아니다.

원격 inspect Size459035877bytes와 실제 파일시스템 변화를 구분했다. 로컬 inspect459039973bytes와4096bytes 표기 차이가 있으나 ID/labels는 정확히 같다. 실제 df 감소459505664bytes(438.22MiB), containerd allocated459591680bytes·Docker allocated217088bytes다.0.5초 샘플에서 최저 free는 최종 free와 같아 최종 점유를 넘는 별도 transient 피크는 관측되지 않았다. df delta에는 SSH/daemon/파일시스템 metadata의 동시 변화도 포함하므로 이미지 논리 Size와 동일한 값으로 취급하지 않는다.

원격 image1·container/volume0·swap0이며 SSH PID/시작 시각·기존 TCP listen이 유지됐다. daemon/기존 서비스 중지·전역prune·PG/Caddy pull·DB/media/secret/admin·DNS/TLS·DEV SG/IAM/AWS자원·Git 변경은0이다. 사용자 콘솔의80/443 적용과 설계의 실제 SG 읽기 확인은 DEV 작업과 구분한다. 앱8000/PG5432는 비공개이고 실제 앱 프로세스/HTTPS 인증서는 없다.

미생성 DB256/media128/staticstate64/log90/swap256/free512/imageFS128MiB 합계1503657984bytes를 그대로 보존했다. 현재 floor 위742.4MiB와 기존3이미지 unique-layer estimate를 기록했지만 **PG/Caddy의 실제 추가 점유·cold peak와 swap/DB/app 안전성은 아직 미검증**이다. 예산을 낮추지 않고 다음 이미지별 gate를 설계가 별도 지시한다.

CLI가 비밀값 제거 근거를 저장한 뒤 run/own local process를 정리해 DELETED·폴더 부재·local owned Docker 자원0이다. 원격 load client exit0, monitor는 자기 stdin stop/SSH wait로 종료했으며 daemon은 유지했다. 원격 준비 app image는 후속 배포용으로 보존하고 임의 삭제하지 않는다. 로컬 원본 image/source191·DB/media/worktree·로고 main 머지·local170 근거·old JSON은 보존했고 제품 검사를 재실행하지 않았다.

## 최소 Docker4 실제 설치·빈 daemon 실측

이 절의 수치는 **15:29 KST 최소 설치·빈 daemon 단계 이력**이다. 최신 빈 DB·앱 준비 결과는 위 마감 절을 따른다.

사용자 보류 후 동일 대상 재개 승인을 받아 PLAN-01/02의 이번 gate만 완료했다. [실제 simulate/install argv·패키지 metadata·계측·정확 캐시 정리](../backend/review/docker-01/README.md)를 보존한다. 공식 Docker key/repo는 기존 파일이 없음을 확인한 뒤 새 root 소유0644로 추가하고 signed APT update를 수행했다. 기존 daemon override도 없었다.

simulate와 실제 설치의 core argv는 `apt-get -o DPkg::Lock::Timeout=0 -o Dpkg::Options::=--force-confold --no-install-recommends --no-upgrade --no-remove -y install`에 아래 정확한 버전4개를 전달한 것이며 simulate만 `--simulate`를 추가했다. `LC_ALL=C DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l`로 기존 서비스 재시작을 억제했다.

| 패키지 | 실제 설치된 APT 버전 |
| --- | --- |
| docker-ce / docker-ce-cli | `5:29.9.1-1~ubuntu.26.04~resolute` 각각 |
| containerd.io | `2.4.2-2~ubuntu.26.04~resolute` |
| docker-compose-plugin | `5.6.0-1~ubuntu.26.04~resolute` |

신규4·upgrade0·remove0이며 Buildx/rootless Extras·Suggested/Recommends는 설치하지 않았다. 다운로드73524880bytes·Installed-Size285807616bytes를 확인했다. APT update 후 가용량3029508096bytes에서 다운로드/설치와 unpack128MiB·daemon초기화128MiB·APT/trigger64MiB 여유를 차감해도 예상최소2334631280bytes(2.17GiB)로 이번 패키지 단계의2GiB gate를 통과했다. 실제 설치 직후2669072384bytes, 이번에 새로 받은 정확한4 deb만 버전/아키텍처/SHA256·일반 파일·소유 확인 후 제거한 최종 가용량은2742505472bytes(2.55GiB)다. 기존 SSL deb3개의 inode/size/mtime는 보존했고 전역 apt clean/purge는 하지 않았다.

| 빈 daemon 실제 측정 | 결과 |
| --- | --- |
| Docker/containerd | active·enabled, Docker socket도 active·enabled. 실제 reboot는 미실행. |
| image store | overlayfs + `io.containerd.snapshotter.v1`, cgroupv2/systemd. 실제 새 image store도 압축 content+해제 snapshot 방식임을 확인했다. |
| daemon RSS / MemAvailable | dockerd55717888bytes(53.1MiB), containerd30777344bytes(29.4MiB), MemAvailable472801280bytes(450.9MiB), swap0. |
| inode / 빈 data dir | root 가용 inode721149. `/var/lib/docker`217088bytes·`/var/lib/containerd`98304bytes allocated. 앱/DB/media volume은 생성하지 않았다. |
| network·권한 | Docker 기본 bridge/host/none와 docker0 생성, ip_forward0→1은 승인된 daemon 초기화 효과다. API는 root:docker Unix socket0660·fd://이며 TCP API 신규 listen 없음. ubuntu는 docker 그룹에 추가하지 않았다. |
| 원본 서비스·SSH | 기존 모든 running service PID/시작 monotonic 시각 동일, SSH PID526723 유지·새 strict SSH 접속 성공·ssh.socket active/enabled. 기존 TCP listen 그대로이며80/443 실행0. needrestart의 기존 세션 outdated/재시작 대기 안내를 기록했고 실제 재시작/재부팅은0이다. |
| 비어 있는 실행 상태 | 서버 image/container/named volume0, hello-world·앱 load·PG/Caddy pull0. |

현재2.55GiB와 기존 이미지/자료/log/512MiB reserve 예산을 그대로 대조하면 swap256MiB 가정의 산술 여유는 약113.3MiB이며, 여기에 **cold import 추가 피크가 아직 반영되지 않았다**. 설치 성공을 이미지 import·swap·DB/app 안전성 승인으로 확대하지 않는다. 다음은 설계 검토 후 이미지별 stream/pull과 단계별 df/피크 계측 범위를 별도 지시받아 진행한다. 이 gate에서 업로드/pull/load·swap·DB/admin·실secret·ACME·DNS/SG·AWS자원/IAM·Git 추가 쓰기는0이다. 인증서 연락메일 sang4196@naver.com은 확정된 후속 준비값이며 아직 사용하지 않았다.

기존 준비 앱 image sha478d…·191 소스/로고9·old JSON·로컬170 PASS와 원 FAIL/한계를 보존했고 제품 소스·기존 도구·앱 lock 의존성은 수정하지 않았고 제품 검사는 재실행하지 않았다. 이 서버의 운영용 패키지와 daemon은 QA 정리 대상이 아니다. 로컬 QA 환경도 새로 만들지 않았다. 설계 인계의14:55 KST/24h288점 CPUCreditBalance288·SurplusBalance/Charged최대0은 개발 재조회가 아니며 전체 비용0/미래 보장으로 해석하지 않고 Unlimited는 유지한다.

## 현재 결합 배포물·1GiB/8GiB 용량 검토

이 절은 **원격 이미지 적재 전 배포물·용량 계획 이력**이다. 당시 원격 실행0·피크 미측정과 설치 지시 대기를 이후 실행 상태로 읽지 않는다. 원예산을 보존한 현재 실측은 위 마감 절을 따른다.

아래의2.82GiB·패키지 미설치 예산과 원격변경0은 **14:51 KST 배포물 준비 단계의 이력**이다. 최신 최소 설치 실측은 위 절을 따른다.

2026-10-16 현재 Docker+로고 결합 소스191파일(`8bdc75ca1c44d88c920d02952e5b45e3041160b7c2b34cfdf84ed40a22ff69fc`)로 로컬 linux/amd64 빌드를 실제 수행했다. 이미지 label은 base HEAD628aa66·dirty input fingerprint·로고 merge f1321a7을 따로 기록한다. Git main의 깨끗한 Docker 배포물이라는 뜻이 아니다. [실측·전체 소스/입력 hash·명령·정리 근거](../backend/review/docker-01/README.md)를 따른다.

| 이번 실제 확인 | 결과 |
| --- | --- |
| 준비 앱 이미지 | `y3gym-prepared:b59117b373c1-logo-f1321a7`, ID `sha256:478d6a9fb51e94498427e06893c9915e7c83e182d80418d9b31082f60025c39e`; inspect Size459039973bytes(약438MiB). 설치 지시 대기용으로 이 이미지1개만 별도 보존한다. |
| 고정 의존 이미지 | PostgreSQL inspect631474556bytes(약602MiB), Caddy92804911bytes(약89MiB). Size 합계를 실제 새 호스트 디스크 점유로 쓰지 않는다. |
| 전송·레이어 측정 | 3이미지 save tar299870720bytes·gzip292010334bytes(약278MiB). OCI tar 안의 파일시스템32레이어 압축293447120bytes·해제 tar820275200bytes와 metadata6319254bytes를 구분한 image-store 기본 추정1120041574bytes(약1.04GiB). 파일시스템 할당/컨테이너/임시 import 추가 점유는 별도다. 측정 archive는 QA와 함께 정리했다. |
| 필수 파일·실행 | runtime 입력92개 hash·prototype/CSS/JS/폰트/라이선스 존재와 QA/비밀/원본 media 제외 PASS. 실제 production WSGI·health·홈·브랜드 CSS·헤더 로고 HTTP200. owned 내부 CA TLS이며 실 도메인 인증서 검증은 아니다. |
| 결합 전체 검사 | 새 관리 환경에서 `backend/.venv/bin/python -B manage.py test news.tests --noinput --verbosity 2`, 기존4opt-in·170/170 PASS·skip0·실행1회·489.579초. 호스트 Python/Node 검사와 앱 컨테이너 최소 스모크를 구분한다. 과거 Docker23/CLI15를 이번 소스로 재실행한 것이 아니다. |
| 새 첫 홈/반복 측정 | 새 process/DB/media에서 첫 HTTPS 홈0.281초, 반복3회0.077/0.081/0.080초. 로컬 Docker 레이어 캐시는 warm이고 합성240×60 PNG를 사용했다. EC2 cold 성능이나 옛20.162초 원인 확인으로 확대하지 않는다. |
| 최소 시작 자료 | 실측 empty-start 합성 DB 디렉터리53239542bytes·static21050741bytes·media541bytes. 실제 자료·한 달 WAL/업로드 성장 예측이나 총량 제한을 뜻하지 않는다. |

검토한 env는 workers1/threads2, PG max_connections20/shared_buffers32MB, 앱512MiB/DB192MiB/Caddy64MiB 상한이다. 두 새 컨테이너 스모크 모두 healthy였으며 작은 합성 홈 이후 앱 약101MiB/DB46~78MiB/Caddy15~40MiB를 관측했다. 이것은1GiB EC2의 daemon/OS 포함 수용량·동시 접속·최대 허용 이미지 검증이 아니다. 기존 파일당10MiB/128Mp·proxy12MiB와 timeout30초는 유지했고 제품/이미지 정책·Compose 기본값을 변경하지 않았다.

[Docker 공식 Ubuntu 지원](https://docs.docker.com/engine/install/ubuntu/)에26.04/amd64가 포함되고 resolute 공식 Packages.gz에서 Docker29.9.1·containerd2.4.2·Compose5.6.0 패키지를 확인했다. 핵심5패키지 설치 합계361692160bytes/다운로드91308904bytes다. 서버에서 빌드하지 않는 최소4패키지(Engine/CLI/containerd/Compose)는285807616bytes/73524880bytes이며 buildx를 뺀 계획이다. 실제 의존성 설치 closure/설치는 미실행이다. 읽기 전용 dpkg 조회에서 필요한 libc6/libseccomp2/iptables/nftables/libsystemd0와 curl/CA는 설치돼 있고 충돌 후보 Docker·containerd·runc8종은 미설치였다. 다른 패키지를 purge하지 않았다.

[Docker29의 새 설치 기본 containerd image store](https://docs.docker.com/engine/storage/containerd/)는 압축 blob과 해제 snapshot을 함께 저장한다. 아래는 **추천 가정**이며 실측 quota나 비용/운영 보장이 아니다.

| 공간 예산 항목 | 가정 |
| --- | --- |
| 이미지 기본 점유·파일시스템/metadata 여유 | 실측 레이어 기준1120041574bytes +128MiB |
| 최소4패키지·다운로드·APT/의존성 여유 | 285807616 +73524880bytes +64MiB |
| DB·media·static/Caddy state·순환 로그 | 256MiB·128MiB·64MiB·90MiB. 기존 정책을 줄이거나 총량을 제한한 값이 아니다. |
| 남겨 둘 가용 공간 | 512MiB |
| swap256MiB 추가 시 | 합계3050140918bytes, 현재 가용3030962176bytes보다19178742bytes(약18.3MiB) 부족. |
| swap512MiB 추가 시 | 합계3318576374bytes, 약274.3MiB 부족. |

**임시 load 피크는 미확인**이다. 원격 통합 gzip을 따로 저장하면 위 계산에292010334bytes가 더 필요하다. 제한된 합성 시작 데이터 실측만 대입하면 swap256/512MiB 계획은 산술상 각각 약359/103MiB가 추가로 남지만, import 추가 피크·daemon RAM·실자료 성장 전이다. 따라서 **현재8GiB에서 제한된 빈DB 사전검수가 안전하다는 판정도 아직 불가**하다. 불가능하다고 단정하거나 예산을 낮춰 가능으로 바꾸지 않는다.

설계가 서버 변경을 별도로 지시하면 최소 패키지 설치 후 df/MemAvailable 실측 → 앱만 stream/load → 고정 PostgreSQL·Caddy 이미지 순차 pull과 매 단계 공간 확인 → 실제 남은 공간으로 swap 크기 재검토 → 승인된 빈DB 사전검수 순서를 검토한다. 먼저 swap을 만들거나3이미지 archive를 원격에 쌓지 않는다. 실제 cold import 피크·Docker 설치 후 overhead/여유와 실자료 예산을 확인하기 전 전체 설치 가능을 확정하지 않는다. 원격 실행은 아직0이다.

최상위 디렉터리 allocated 사용량만 읽기 전용으로 집계했다: `/usr`2853208064bytes, `/var`1089269760bytes, `/home`60563456bytes, `/opt`4096bytes, `/root`73728bytes. `/boot`는 별도 filesystem이며 root 용량에 합산하지 않는다. 파일 내용·전체 파일명은 읽거나 나열하지 않았고 삭제/확보 가능 공간을 가정하지 않았다.

빌드/전체 run `qa-20261016T053335Z-c7ec80bce2bd`와 시간 측정 run `qa-20261016T054819Z-7fc55e0f8c49`는 비밀값 제거 근거 저장 후 DELETED·소유 process/container/network/volume0이다. 로고 Git 반영으로 미사용이 확인된040418 후보와 미초기화035910 AWS 준비 run도 승인된 관리 CLI complete→dry-run→정확 plan으로 정리했다. 원 FAIL→후속·과거20.162초/Trainer 원인 미확정·기존 경고는 보존한다. 준비 앱 이미지는 승인된 서버 import/ID 확인 또는 대체/취소 후 미사용 확인 시 정확한 tag만 해제하며 공유 base/build cache는 유지한다. 실제 admin account·운영 DB/media 복사·업로드·설치/스왑/보안그룹/DNS 변경·개발 Git 쓰기는0이다.

## 이미지와 실행 경계

| 구성 | 고정값·확인 범위 |
| --- | --- |
| Python 앱 기반 | `python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26` |
| PostgreSQL | `postgres:17.11-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826` |
| Caddy | `caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f` |
| 앱 의존성 | 기존 Django5.2.18/Wagtail7.4.3와 모든 기존 lock 버전 유지, Gunicorn26.2.0만 추가. 빌더 uv0.12.16, `uv sync --locked --no-dev --no-install-project --no-editable --no-python-downloads`. 원본 개발 venv는 sync하지 않는다. |

공식 registry에서 세 기반 이미지의 linux/amd64·arm64 manifest를 확인했다. **실제 로컬 실행은 linux/amd64**이며 ARM 실행 검증을 대신하지 않는다. 앱 컨테이너의 Debian bookworm과 EC2 호스트의 Ubuntu는 서로 다른 OS 층이다. [공식 Python 이미지](https://hub.docker.com/_/python), [공식 PostgreSQL 이미지](https://hub.docker.com/_/postgres), [공식 Caddy 이미지](https://hub.docker.com/_/caddy), [Gunicorn26.2.0/Python3.13 지원](https://pypi.org/project/gunicorn/26.2.0/).

[Dockerfile](../Dockerfile)·[allowlist build context](../.dockerignore)·[운영 Compose](../compose.production.yaml)는 개발 DB용 `backend/compose.yaml`과 분리한다. 앱은 UID/GID10001·읽기 전용 root filesystem, 제한된 `/tmp`, private media 및 별도 static named volume을 사용한다. Caddy에는 static만 읽기 전용으로 공유하며 **media를 mount/파일 제공하지 않는다**. DB·media·Caddy 인증서/data/config는 각각 영속 volume이다. 앱·DB는 host port를 공개하지 않고 프록시80/443만 공개한다. Caddy 관리자 API는 비활성이다.

`source_fingerprint`는 앱 이미지 입력만 식별한다. Compose·Caddy 설정·배포/QA 도구는 이 값에 포함하지 않으며 최종 검증 근거의 별도 파일 hash/source manifest로 식별한다. 앱 image ID와 이 설정 manifest를 함께 보관한다.

기존 prototype의 필수 index HTML·CSS·JS·사진 자산·폰트/LICENSE를 함께 포함한다. 원본 env/인증·DB/media·QA·review·venv/node_modules·cache·테스트 코드는 이미지에 넣지 않는다. 운영 전체 소스 bind mount는 없다.

## 운영 환경과 최초 명시 단계

대상 접속 확인은 완료했지만 현재 서버에는 Docker/Compose가 없고 설치·배포는 미진행이므로 아래 배포 명령은 아직 실제 서버에서 실행하지 않았다. 설치·배포 단계의 별도 지시에 따라 Docker Engine/Compose가 준비된 **확인된 Ubuntu 호스트**의 Git checkout 프로젝트 루트에서 실행한다. 호스트 배포 도구에는 Python3.11 이상과 Git 명령이 필요하며 로컬 검증 Python은3.13.15다. Docker/Compose·호스트 Python 버전·architecture·디스크 여유·시간 동기화를 먼저 확인한다. [환경 예시](../backend/.env.example)를 승인된 비공개 절대 경로의 **0700 디렉터리/0600 파일**로 복사하고 실제 값을 현지에서 채운다. 예시는 자동 로딩하지 않는다. 배포 도구는 invoking operator의 소유·mode·필수값을 확인하고 literal `KEY=VALUE`를 사용한다. 실제 비밀값을 저장소·대화·로그에 붙이지 않는다.

- 새 production `DJANGO_SECRET_KEY`와 별도의 bootstrap DB/앱 DB 비밀번호를 사용한다. 초기 데이터는 미확정이며 개발 DB·QA 자료·계정과 개발 env를 자동 복사하지 않는다.
- `Y3GYM_DOMAIN`은 실 도메인 하나, `Y3GYM_ADMIN_ORIGIN=https://실도메인`, 명시적인 `Y3GYM_ALLOWED_HOSTS`·CSRF 원점을 설정한다. `Y3GYM_TLS_EMAIL`은 인증서 연락처다.
- `Y3GYM_APP_IMAGE`는 매 릴리스의 고유 tag/digest다. `latest`를 사용하지 않는다. Git SHA만 같아도 누적 변경이 다르면 다른 배포물이다. build 결과의 dirty/source fingerprint·image ID를 함께 보관한다.
- Docker 앱의 DB host/port는 내부 `database:5432`, media/static은 `/var/lib/y3gym/media`, `/var/lib/y3gym/static`이다. production은 개발 `.env.local`을 읽지 않는다.

아래 `ENV_FILE`은 실제 승인된 private 파일 절대 경로로 바꾼다. shell 변수는 이 문서 예시이며 파일이 이미 존재한다고 가정하지 않는다.

```bash
ENV_FILE=/approved/private/path/production.env
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym validate
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym build
# 최초 새 DB에서 한 번만: 기존 역할/DB가 있으면 거절하고 reset하지 않는다.
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym provision
# 운영자가 migration 계획·호환성/백업을 확인한 후 명시 실행.
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym prepare
# 새 관리자는 별도 명시 작업. 운영자가 직접 새 사용자/비밀번호를 입력한다.
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym admin
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym up
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym status
```

로그는 위 status의 서비스별 실제 NAME을 확인하고 해당 컨테이너 ID로 조회한다. 아래 두 변수는 실제 출력으로 교체하며 비밀 환경을 출력하지 않는다.

```bash
Y3GYM_CONTAINER_NAME=replace-with-status-NAME
docker inspect --format '{{.Id}}' "$Y3GYM_CONTAINER_NAME"
Y3GYM_CONTAINER_ID=replace-with-inspect-ID
docker logs --since 10m --tail 100 "$Y3GYM_CONTAINER_ID"
```

승인된 Ubuntu 호스트에서는 `systemctl is-enabled docker`·`systemctl is-active docker`로 daemon의 부팅 활성화와 현재 상태를 확인한다. Compose의 `unless-stopped`는 Docker daemon 기동을 전제로 하며 명시적으로 stop한 서비스를 자동 복구시키는 설정이 아니다. 이번 로컬 검사는 컨테이너 교체·stop/start 범위이며 **실제 EC2/Ubuntu 재부팅 후 자동 기동은 미검증**이다. 부팅 활성화 변경과 재부팅 검사는 B 단계의 확인된 서버에서 진행한다. [Docker 부팅 설정](https://docs.docker.com/engine/install/linux-postinstall/#configure-docker-to-start-on-boot-with-systemd), [restart 정책](https://docs.docker.com/engine/containers/start-containers-automatically/).

DB bootstrap `Y3GYM_DB_ADMIN_USER/PASSWORD`는 초기 관리·provision·backup/restore에만 사용한다. 앱의 `Y3GYM_DB_USER`는 자기 DB owner로 migration이 가능하지만 **NOSUPERUSER/NOCREATEROLE/NOCREATEDB/NOREPLICATION**이다. 사용자·DB 생성은 `provision` 명시 단계이며 secret 없는 기존 role/DB 확인 후 중복을 거절한다. 비밀 SQL 세션에 한해서 statement/error-statement 로깅을 억제하고 실제 오류 로그의 비밀값 부재를 검사한다. 이 동작은  앱 startup·기존 volume 재시작에서 반복하지 않는다. 앱 startup에 migrate/collectstatic/seed/관리자 자동 생성은 없다. 관리 작업이 필요할 때만 `prepare`·`admin`을 별도로 호출한다.

초기 기본값은 workers1·threads2·PG max_connections50/shared_buffers128MB, 앱512m/DB512m/프록시128m 메모리 상한이다. **선택 EC2에서 성능/수용량을 승인한 값이 아니다.** `Y3GYM_WORKERS/THREADS`, `Y3GYM_PG_MAX_CONNECTIONS/PG_SHARED_BUFFERS`, `Y3GYM_APP_MEMORY/DB_MEMORY/PROXY_MEMORY`로 조정한다. worker×thread와 유지보수 여유를 DB 접속 수 안에 두고 OS·Docker·WAL·백업 공간을 별도 확보한다. 기본 Django CONN_MAX_AGE0·psycopg prepare_threshold None과 요청 단위 트랜잭션·행 잠금은 유지한다.

Gunicorn timeout/graceful_timeout은30초이며 cold 문제를 감추는 timeout 증가를 하지 않는다. 사용하지 않는 제어 소켓은 비활성화해 읽기 전용 root filesystem의 홈 경로에 쓰지 않는다. [Gunicorn 제어 소켓 설정](https://gunicorn.org/reference/settings/#control_socket_disable). 앱 readiness는 DB SELECT1을 포함하고 Caddy health는 컨테이너 loopback8081의 실제 HTTP 응답을 확인한다. 이 health 포트는 host에 publish하지 않는다. restart는 unless-stopped, 정상 SIGTERM 종료, 서비스별 json-file10m×3 로그 순환을 사용한다. 외부 TLS 성공·실제 페이지 응답은 health와 별도로 확인한다.

## HTTPS·헤더·미디어

실 도메인 DNS와80/443 접근 조건을 확인해야 Caddy 자동 HTTPS/갱신이 동작한다. 대상·DNS·방화벽 승인 전 인터넷 관리자 평문 접근을 만들지 않는다. [Caddy 자동 HTTPS](https://caddyserver.com/docs/automatic-https).

Caddy는 외부 `Forwarded`, `X-Forwarded-Host/Port`, `X-Real-IP`를 제거하고 `X-Forwarded-Proto`를 실제 scheme, `X-Forwarded-For`를 직접 peer로 덮어쓴다. 현재 구조는 외부 CDN/LB를 신뢰 프록시로 가정하지 않는다. 앱 직접 host port는 없으며 이 경계에서만 Django proxy HTTPS 신뢰를 활성화한다. `strict_sni_host on`으로 TLS SNI와 Host가 다른 요청도 거절한다. Host/CSRF·secure cookie·위조 헤더를 실제 TLS 경로로 검증한다. [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [strict_sni_host](https://caddyserver.com/docs/caddyfile/options#strict-sni-host).

이미지 파일당10MiB·128Mp와 형식 검증은 유지한다. 프록시 body 상한12MiB(12,582,912바이트)는 multipart 여유를 포함한다. body/write timeout30초와 Gunicorn30초를 함께 검토하며 느린 업로드/실서버 성능은 별도 확인한다. [request_body](https://caddyserver.com/docs/caddyfile/directives/request_body).

기존 `protected_media → FileResponse`, live_revision 공개 참조·익명 원본 차단·권한 미리보기·마지막 공개 사용 철회를 유지한다. static 우회나 public bucket·signed download redirect로 보호 정책을 바꾸지 않는다. lightbox는 기존 같은 원점의 max-2560x2560 파생본을 사용한다.

W004 HSTS는 기본0을 유지하고 실제 도메인 TLS·갱신·redirect·cookie 확인 후 사용자 정책으로 확정한다. W019 SAMEORIGIN은 Wagtail iframe 미리보기에 필요하므로 유지하고 실제 같은 원점 preview/외부 frame 차단을 확인한다. 경고 제거용 DENY·검사 숨김은 하지 않는다.

로컬 TLS는 [명시 QA override](../deploy/compose.qa.yaml)·[소유 CA용 Caddyfile](../deploy/Caddyfile.qa)만 사용한다. 고유 합성 `.test` 도메인과 loopback 임시 port, disposable browser 컨테이너 안의 소유 CA 신뢰 저장소를 사용하며 SSL 검증을 생략하지 않는다. **운영 Compose/Caddyfile에 내부 CA·localhost fallback·임시 포트를 넣지 않는다.**

## 업데이트·중단·롤백

```bash
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym stop
# 새 고유 이미지 tag로 환경 파일을 갱신한 후 build → 계획/백업 검토 → prepare → up.
```

기본 start/stop/update는 volume을 삭제하지 않는다. 일반 운영에 `down -v`·global prune을 사용하지 않는다. 코드 rollback은 DB schema와 호환될 때 이전 고정 image로 전환하는 작업이다. 비호환 migration은 전진 수정 또는 같은 시점의 DB+media 복구와 데이터 손실 승인이 필요하다. 코드 교체를 DB 복구로 취급하지 않는다.

## 일관된 로컬 export와 격리 복원

```bash
python3 backend/scripts/deploy.py --env "$ENV_FILE" --project y3gym backup --directory /approved/private/path/backup-new
# 별도 새 프로젝트·새 빈 volume/DB·일치하는 원 image·별도 승인 환경에서만 실행.
python3 backend/scripts/deploy.py --env /approved/private/path/restore.env --project y3gym-restore restore --directory /approved/private/path/backup-new --confirm-empty-restore
```

backup은 실행 중인 앱과 환경의 image ID가 같은지 먼저 확인하고 proxy/app을 멈춰 관리자 쓰기와 lazy rendition 생성을 함께 정지한다. 논리 DB dump·원본/파생 media를 메모리에 일괄 적재하지 않고 파일로 스트리밍하며, 실제 이미지의 릴리스/source fingerprint·image ID·파일 해시 manifest를 보관한다. 종료 후 기존 서비스를 다시 기동한다. env/암호화 키는 저장소에 복제하지 않고 운영자가 별도 암호화 보관해야 한다. restore는 기존 container뿐 아니라 실제 예정 이름의 volume도 조사해 Compose 라벨이 없거나 foreign인 volume까지 거절하며 새 DB를 provision하고 일치하는 image와 dump/media 해시를 확인한다. 자동 공개 전환은 하지 않는다.

**현재 목적지는 사용자 승인 PC private 폴더이며 실제 서버→PC 전송1회와 격리 복구를 확인했다.** 자동주기·보존기간·RPO/RTO·정기 외부보관/암호화 운영은 미정이다. S3·EBS snapshot 등 새 서비스를 임의 생성하지 않는다. 단일 EC2의 DB/디스크 장애는 앱·media에도 영향을 주며 사용자에게 패치·장애 대응·복구 책임이 있다.

약 한 달 뒤 다른 AWS 서버로 옮길 때에는 **향후 배포된 승인 DB·media를 기존 `deploy.py backup/restore`로 일관되게 내보내고 별도 빈 대상에 복원하는 방향**으로 재사용한다. 이번에는 승인된 PC 위치로 백업·격리 검수만 수행했다. 실제 다른 AWS 이전 대상·일정·운영 복원은 별도 결정 사항이며 미래 이전 기능을 새로 구현하거나 운영 이전하지 않았다.

## 비용·관측과 AWS 배포 전 확인

서울 테스트 대상의 사양과 설계측 AWS CLI 임시 로그인·읽기 전용 접속은 확인했다. 실제 비용·예산, CPU Unlimited 모드의 비용 조건, 무료 적용 자격·공인IPv4·송신·백업·도메인 비용은 별도 확인 대상이다. 새 서버나 사양/디스크 증설은 승인 전이며 AWS를 무료라고 가정하거나 OCI 무료 조건을 대입하지 않는다.

**사용자 콘솔 보고(2026-10-16): Free plan·예상 잔여 `$29.76`·표시 만료 `2027-05-01`.** 이는 API로 검증한 값이 아니다. Free plan 종료일과 크레딧 만료일을 동일시하지 않으며 각각의 날짜·잔여/적용 조건은 별도 미확인으로 남긴다. 표시 만료일의 정확한 대상도 확인 전이고 예상 잔여액을 확정 예산·서비스 비용이나 한 달 사용 보장으로 해석하지 않는다.

EC2 기본 CloudWatch의 CPU/net 등은 기본5분, 상세 모니터링은 별도 옵션이다. 상태 검사와 EBS/volume 지표는 각 지표의 제공 주기를 구분한다. **guest 메모리·파일시스템 여유는 기본 EC2 지표에 없으며 별도 수집이 필요하다.** 이번에 agent/추가 유료 수집을 설치하지 않는다. [EC2 모니터링](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html), [CloudWatch agent 수집 지표](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/metrics-collected-by-CloudWatch-agent.html).

운영자가 최소한으로 확인·내보낼 자료는 다음과 같다. 각 기록에 대상 별칭·기간/확인 시각·단위·필터를 붙인다. **월 AWS 실측 비용·서비스별 사용량·무료 적용과 Credit 잔여/만료의 검증은 미완료**이며 위 사용자 콘솔 보고와 구분해 확인 대상으로 남긴다. 자동 비용 API나 유료 세부 수집·새 agent/모니터링 시스템은 추가하지 않는다.

| 자료 | 확인·내보내기 방법과 해석 범위 |
| --- | --- |
| 월별 서비스 비용 | Cost Explorer에서 같은 청구월·비용 지표·통화를 정하고 Service별로 묶는다. Charge type의 Credit/Refund를 포함한 CSV와 두 유형을 제외한 CSV를 각각 Download CSV로 저장하고 필터를 기록한다. 같은 월 Bills의 서비스 내역·청구조정·세금/지원 항목과 대조해 차이 원인을 남긴다. 그래프만 보고 환급을 누락하지 않으며 무료 자격·Credit 잔여/만료·최종 청구금액은 해당 Billing 콘솔에서 따로 확인한다. |
| CPU·네트워크 / guest 메모리·디스크 | 기본 EC2 CPU/net의 선택 기간·집계 방식·값을 공유용 표로 옮긴다. guest RAM·파일시스템 여유는 호스트의 `free -m`·`df -h`, 컨테이너별 현황은 실제 ID의 `docker stats --no-stream`으로 별도 확인한다. 단일 시점 snapshot을 과거 시계열이나 용량 승인으로 해석하지 않는다. |
| DB·사진 용량 | status에서 실제 DB/app 컨테이너를 확인한 뒤 대상 DB에 연결해 `SELECT pg_database_size(current_database());`로 바이트 크기를 확인한다. 앱의 `/var/lib/y3gym/media` 원본·파생 파일 크기 합계는 별도로 기록한다. 공유 자료에는 총량·증감·단위만 넣고 host 디스크 여유와 구분한다. |
| Gunicorn 오류·처리시간 | 앞의 실제 ID `docker logs` 절차로 app의 error/access 로그를 확인한다. 현행 access 형식의 상태코드와 처리초수(`%(L)s`)에서 기간·표본 수·5xx/오류 건수·처리시간을 기록한다. 이 값은 브라우저부터의 전체 지연이나 서비스 SLO를 검증한 값이 아니다. |
| 백업 생성 / 외부 전송 / 복구 | 로컬 생성은 dump/media·manifest 존재와 해시, 외부 전송은 승인 목적지 도착·해시, 복구는 별도 빈 환경의 DB·사진·권한 확인 결과를 각각 기록한다. 로컬 생성 성공을 외부 전송/복구 성공으로 바꾸지 않는다. 현재 로컬 생성·격리 복원 검증은 완료했고 외부 전송은 미설정이다. |

[Cost Explorer CSV 내보내기](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-download-csv.html), [Service·Charge type/Credit/Refund 필터](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-filtering.html), [PostgreSQL17 DB 크기 함수](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)를 확인한 안내다. 위 `free`·`df`·`docker stats`는 앞선 Docker A 후속 문서 마감에서 로컬 실행명·도움말의 옵션 정의만 확인했다. 예시는 승인된 호스트에서 앞 절의 실제 컨테이너 ID를 채운 뒤 쓰는 읽기 전용 방법이며, **그 당시 자료 값 조회와 AWS 실행은 하지 않았다.** 현재 서버 여유 자원은 별도 설계 사전 조회에서 전달된 snapshot이다. 이번 후속 개발 문서 작업에서는 이 예시나 DB/사진 용량 조회를 다시 실행하지 않았다.

```bash
free -m
df -h
docker stats --no-stream "$Y3GYM_CONTAINER_ID"
```

원본 CSV/Bills·raw 로그는 비공개로 보관한다. 공유 복사본은 필요한 월·서비스·통화·금액/필터·지표 열만 선택하고 인증값·계정 식별자·불필요 resource ID·IP/개인정보를 제거하거나 마스킹한 뒤 확인한다. DB dump/행 데이터·사진 원본/파생 파일·env/계정 파일·브라우저 프로필은 첨부에서 제외한다. 공유에는 용량/건수와 백업 단계별 결과만 남긴다.

## 검증 결과와 한계

[개발 자체 검증·동결 근거](../backend/review/docker-01/README.md)는 로컬 Docker23/23·CLI15/15·전체 `news.tests`167/167(4 opt-in·skip0)의 실제 실행 기록이다. 세 실행의189파일 소스 manifest와 앱 입력98파일 fingerprint, 별도 Compose/Caddy·배포/QA 도구 hash를 보관했다. 앞선 전체167 결과·`GENERATED.md`가 빠진 중간 Docker PASS·원 FAIL10개는 별도 이력으로 유지한다.

[독립 최종 판정](../backend/review/docker-01/independent-verification.json)은 **PASS_WITH_OBSERVER_HISTORY_AND_DEPLOYMENT_LIMITS**이며 설계가 검토했다. 실제 Docker23/23(소유 CA의 실 TLS 브라우저6 포함)과 작은 합성 JPEG/WebP의 메모리 encode/decode·resize native probe를 확인했고 새 제품 결함은0이다. JPEG/WebP HTTP 업로드·대용량 처리·픽셀 충실도까지 확인한 결과는 아니다. 독립의 전체167/CLI15는 동일189소스 인계 근거 재사용이며 독립 재실행이나23건과의 합산이 아니다.

독립 OBS1은 Django 설정 모듈이 없는 관측 진입점의 원 FAIL이며 정상 엔트리와 같은 설정을 보정한 후 PASS했다. OBS2는 JavaScript 숫자 직렬화의 정밀도 손실로 추가6파일의 교차 관측에서 정확한 나노초 전후 비교가 미검증인 상태를 유지한다. 이와 별개로 유효한 보호 근거는 서버3 full identity, 파일6개의 내용 SHA/inode/size/mode, Docker 내부 private2의 정밀 나노초 전후 대조 PASS다. 원 DB 행·원 미디어 전체 감사나 운영 검증으로 확대하지 않는다.

개발 소유 run72개와 독립 소유 run1개는 각각 DELETED다. 독립 소유 Docker 자원16개를 정리했고 container/network/volume/image 잔여0이며 공유 pinned 이미지/build cache와 기존 QA·원본 자원은 보존했다. 백업/복원은 관리자·lazy rendition 쓰기를 멈춘 local export, 새 빈 DB/media의 실제 restore·앱 역할 조회·파일12개 해시 일치 범위다. 복원 proxy의 공개 기동·VM 밖 재해 복구·외부 백업 전송을 확인한 결과는 아니다.

**이번 마감은 테스트된189소스 밖의 README·backend README·이 운영 안내·구현 계획 네 문서만 수정한 후속 docs-only 작업이다.** 개발/독립 JSON의 당시 판정·194파일 freeze·원 FAIL은 재작성하지 않았다. 따라서 현재 네 문서 hash는 당시 freeze와 다르며 테스트된189소스는 그대로다. 이번에는 문서 링크·명령 정의·소스 해시 불변만 확인하고 제품 회귀를 재실행하지 않았다.

A 로컬 검증은 한계를 유지한 완료, B는 접속·읽기 전용 사전 확인 완료/배포 미진행, C 공개 운영은 미완료·외부 백업 미설정이다. 실제 설치/배포·실도메인 인증서/갱신·EC2 성능/재부팅·ARM 실행·실자료 인계와 외부 백업 목적지/주기/보존/암호화/RPO/RTO는 확인 전이다. W004/W019·과거 coldTimeout/OBS01·W01·실기기/Whale/OS IME·엄격 픽셀 한계와 당시 AWS0/Git0 기록을 유지한다. 이번 후속 문서 작업에서 개발 담당의 AWS/SSH 접속과 Git 쓰기는0이다.
