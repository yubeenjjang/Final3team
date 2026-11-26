# W65 첫 AWS 배포 실행·검증 절차

이 문서는 [구성안](W65-AWS-PLAN.md)의 단일 EC2·Docker Compose 배포 절차다. **아직 AWS에서 실행하지 않았다.** 첫 배포는 도메인 없이 EC2 공개 IP의 **HTTP 시험 접속**으로 확인한다. TLS가 없으므로 개인정보·인증 토큰·API 키를 이 공개 경로로 보내지 않는다. 로컬 W64 검증과 AWS 결과를 섞지 않는다. 아래 명령은 서버 저장소 루트에서 실행한다.

## 1. 배포 전 입력값과 중단 조건

| 입력 | 확정할 값·근거 |
| --- | --- |
| AWS 계정·리전·서버 | 계정 ID, 리전, EC2 인스턴스 유형·AMI·고정 주소, 월 비용 상한과 과금 알림 |
| 공개 주소 | EC2의 현재 공개 IPv4 또는 Elastic IP. 재시작 후 주소가 바뀔 수 있으므로 외부 확인 전에 다시 조회. 도메인은 첫 배포에 필요 없음 |
| 접근 | 인스턴스 역할의 Session Manager·Secrets Manager 읽기·백업 S3 쓰기 권한. 운영자 접근 경로와 감사 로그 |
| 비밀값 | 관리자·앱·서비스 DB 비밀번호, `ASSISTANT_TOKEN_SECRET`(A06 사용 시), JWT/경로·공급원 키(해당 기능 사용 시). Secrets Manager 이름·권한·로테이션 담당 |
| 데이터 | 암호화된 EBS의 Docker 데이터 경로·용량, S3 백업 버킷·7일 만료 규칙·복원 시험 장소 |
| 정책 | RPO·RTO 목표, 백업 뒤 발생한 탈퇴·삭제의 재적용 방법, 서버 장애 시 운영자 연락 경로 |

필요한 값이 없으면 해당 기능을 켜지 않는다. 도메인 DNS가 없으면 `compose.aws.https.yaml`을 사용하지 않는다. 백업·삭제 재적용 절차가 없으면 운영 복원 완료로 판정하지 않는다. 비밀값을 저장소나 명령 인자·터미널 출력에 남기지 않는다.

## 2. AWS 자원·네트워크

1. 단일 EC2와 암호화된 EBS를 준비한다. Docker 데이터 경로가 해당 영속 볼륨에 있는지 기록한다. 단일 서버 장애 시 서비스가 중단되는 구성이다.
2. 첫 시험의 보안 그룹 인바운드는 TCP **80만 시험자 공인 IP/CIDR에서** 허용한다. 운영 접속은 Session Manager를 사용하며 22는 열지 않는다. 443은 아직 열지 않는다. DB 5432, Redis 6379, API 8000도 열지 않는다. 보안 그룹 아웃바운드는 이미지 다운로드·필요한 AWS 서비스 접근을 허용해야 한다.
3. 공개 IP를 기록한다. `http://<EC2_PUBLIC_IP>/api/v1/health`가 첫 시험 주소이며 포트는 80이다. 이것은 암호화되지 않은 HTTP다. 다른 경로의 외부 사용은 HTTPS 전환 뒤로 미룬다.
4. Secrets Manager와 비공개 S3 백업 버킷에 인스턴스 역할의 필요한 권한만 부여한다. S3 Block Public Access와 암호화를 확인하고, `backups/` 객체를 7일 후 만료시키는 수명주기 규칙을 둔다.
5. EC2·EBS·S3·비밀값·로그·데이터 전송의 예상 월 비용과 과금 알림을 실제 리전 기준으로 기록한다.

## 3. 설정·기동

1. 서버의 `yubeen` 브랜치를 `git pull --ff-only origin yubeen`으로 갱신하고 `git rev-parse HEAD`를 기록한다. 배포에 사용할 커밋을 고정한다. 빌드 후 백엔드·DB·Redis·Caddy 이미지 다이제스트를 기록한다. 외부 이미지 태그만을 재현 근거로 사용하지 않는다.
2. 인스턴스 역할로 Secrets Manager 값을 읽어 **호스트의 권한 제한 런타임 환경 파일**에 넣는다. 파일에는 `POSTGRES_PASSWORD`, `DB_USER_PASSWORD`, `DB_SERVICE_PASSWORD`를 포함한다. `FESTIVAL_DATA=db`는 승인 데이터가 준비됐을 때만 사용한다. A06을 켜면 `ASSISTANT_PROVIDER=db`, 공통 `ASSISTANT_TOKEN_SECRET`도 필요하다. Redis를 켜면 `REDIS_URL=redis://redis:6379/0`을 넣는다. 비밀값은 셸 인자·히스토리·Git에 쓰지 않는다. 환경 파일은 운영자만 읽도록 `umask 077`로 생성하고 `chmod 600`으로 제한한다. `docker compose config` 전체 출력과 `docker inspect`도 비밀값을 드러낼 수 있으므로 공유하지 않는다.

```sh
sudo install -d -m 700 /etc/noldaga
sudoedit /etc/noldaga/runtime.env  # 편집기에서 비밀값 입력; 명령 인자에는 쓰지 않음
sudo chmod 600 /etc/noldaga/runtime.env
```

이미 파일이 있으면 내용을 덮어쓰지 않고 필요한 항목만 편집한다. 파일을 출력하는 `cat`, `grep`, `env` 명령을 증빙에 사용하지 않는다.
3. Docker Compose 설정을 먼저 확인한다. 아래 명령의 `$RUNTIME_ENV`는 서버의 권한 제한 파일 **경로**이며, 파일 내용은 출력하지 않는다.

```sh
RUNTIME_ENV=/etc/noldaga/runtime.env
# 명령을 실행할 권한을 가진 운영자만 환경 파일을 읽을 수 있어야 한다.
sudo docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml config --quiet
```

4. `compose.aws.yaml`은 DB·API의 호스트 포트를 제거하고 Caddy HTTP만 80에 게시한다. Redis는 원래부터 호스트 포트가 없다. 기존 Compose 프로젝트에 오버레이를 처음 적용하기 전 `config --quiet`로 병합 구성을 확인한다. `down -v`를 운영 DB에서 실행하지 않는다.
5. 첫 기동은 DB→마이그레이션→역할 비밀번호 설정→API→Caddy 순서다. Redis와 A06 워커는 해당 기능을 사용하는 경우에만 함께 켠다.

```sh
sudo docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml up -d --build
sudo docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml ps
```

첫 기동 예시는 선택 프로필을 끈 최소 구성이다. Redis·A06 워커를 사용할 때만 `--profile redis`·`--profile assistant`를 해당 명령에 추가하고 API 설정도 맞춘다. `scheduler`는 실제 공급원 키와 수집 일정 검토 뒤 `--profile scheduled`로 별도 활성화한다. 서버의 `sudo docker ps`가 비어 있어도 Compose 기동 전 환경 파일·포트·영속 볼륨을 확인한다.

## 4. 배포 후 확인

| 확인 | 통과 조건·남길 기록 |
| --- | --- |
| 포트 | 호스트 게시 포트는 80만. 외부에서 5432·6379·8000·443 비공개 |
| HTTP 시험 | `http://<EC2_PUBLIC_IP>/api/v1/health` 200, 다른 경로 403. HTTPS·인증서 검증 완료로 표시하지 않음 |
| DB | `db` healthy, migrate 종료 0·001~최신 적용. 같은 설정 재실행에서 적용 이력 건너뛰기. API `/health db=ok` |
| Redis | 사용 시 `/health redis=ok`; 중단 시 503 `unavailable`, 재시작 후 `ok`. 미사용 시 `not_configured` |
| 축제 | **실제 승인된 데이터**가 적재된 뒤 A02 목록에서 `is_mock=false`·0건 초과, 동일 ID로 A03 상세 조회. 로컬 시험 행 결과로 대체하지 않음 |
| A06 | 사용 시 접수 202 `queued`→워커 완료/실패→A06-1 조회. 실제 Festival Agent 연결은 따로 구분 |
| 비밀값 | 이미지·히스토리·로그·외부 응답에 비밀값 원문 없음. API에 관리자 DB 비밀번호 없음 |
| 비용·로그 | 실제 자원·이미지 다이제스트·접속 시각·실패 항목·월 비용 추정 기록 |

서버 내부에서는 `curl --fail --silent --show-error http://127.0.0.1/api/v1/health`를 실행한다. 별도 시험자 PC에서는 `curl --fail --silent --show-error http://<EC2_PUBLIC_IP>/api/v1/health`를 실행한다. 두 명령에 비밀값을 넣지 않는다. `sudo docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml ps`로 컨테이너 상태를 확인하고, `sudo ss -ltn`으로 호스트 수신 포트를 확인한다. 외부에서 5432·6379·8000이 닫혔는지는 별도 네트워크의 시험자 PC와 보안 그룹 규칙으로 확인한다. HTTP 경로에는 실제 사용자 정보나 인증 요청을 보내지 않는다.

추가로 서버 내부와 외부에서 `curl --silent --output /dev/null --write-out '%{http_code}\n' http://<EC2_PUBLIC_IP>/api/v1/festivals`가 403인지 확인한다. 이 요청에는 인증 정보나 본문을 싣지 않는다.

## 4-1. 추후 도메인·HTTPS 전환

도메인을 확보하고 DNS A 레코드를 EC2 공개 IP에 연결한 뒤에만 `API_DOMAIN`을 권한 제한 런타임 파일에 추가한다. 보안 그룹에 TCP 443을 열고 80도 인증서 발급·리다이렉트용으로 유지한다. 그때 `compose.aws.https.yaml`을 마지막 오버레이로 추가해 `config --quiet` 확인 후 재기동한다. 예: `sudo docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml -f infra/deployment/compose.aws.https.yaml up -d`. 이후 `https://<API_DOMAIN>/api/v1/health` 200, 인증서 도메인·유효기간, HTTP→HTTPS 리다이렉트, Caddy 볼륨 재기동 후 인증서 유지를 실제로 검증한다. 이 검증 전까지 HTTPS 완료로 기록하지 않는다.

## 5. 백업·복원 시험

- 매일 **KST 06:30**에 `pg_dump --format=custom --exclude-table-data=public.route_results`로 논리 백업한다. 기존 [백업 실행기](../../Docs/Step%202/db/backup_long_term.sh)와 같은 제외 규칙이다. 06:00 스케줄러 작업과 겹치면 백업 시각을 조정한다.
- 서버에 AWS CLI와 쓰기 권한이 있는 백업 임시 디렉터리를 준비한 뒤, 아래처럼 파일을 생성·업로드한다. `BACKUP_BUCKET`은 사전에 정한 비공개 버킷 이름이다. 이 예시는 작업 등록 전 **수동 검증용**이며 비밀번호 값을 출력하지 않는다.

```sh
umask 077
RUNTIME_ENV=/etc/noldaga/runtime.env
BACKUP_BUCKET=replace-with-private-bucket
BACKUP_FILE="/var/lib/noldaga-backups/noldaga-$(date -u +%Y%m%dT%H%M%SZ).dump"
sudo docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml exec -T db sh -c 'exec pg_dump -U postgres -d "$POSTGRES_DB" --format=custom --exclude-table-data=public.route_results' > "$BACKUP_FILE"
test -s "$BACKUP_FILE"
aws s3 cp "$BACKUP_FILE" "s3://$BACKUP_BUCKET/backups/$(basename "$BACKUP_FILE")" --sse AES256
```

- 백업 파일은 비공개·암호화 S3 버킷에 올리고 7일 만료 규칙을 적용한다. S3 수명주기 삭제는 비동기이므로 7일 삭제가 엄격한 요구라면 별도 만료 확인·추가 삭제를 운영 작업으로 둔다. 업로드 성공·객체 크기·시각을 기록하고 실패 시 알린다. 경로 본문이 포함될 수 있는 DB 볼륨 스냅샷을 이 백업 대신 사용하지 않는다.
- 복원 시험은 **운영 DB가 아닌 별도 DB**에 `pg_restore --single-transaction`으로 수행한다. 복원 뒤 001~최신 스키마, A02·A03, 사용자별 DB 권한, 만료·삭제 정책을 확인한다. 백업 이후의 탈퇴·삭제를 재적용하는 근거가 없으면 운영 복구 완료로 표시하지 않는다.
- 실제 백업 작업 등록·복원 소요 시간·RPO/RTO는 W65/W67 실행 기록으로 남긴다. 이 문서 작성만으로 백업이 자동 실행되지는 않는다.

## 6. 공식 참고

- [Docker Compose `!reset` 오버레이](https://docs.docker.com/reference/compose-file/merge/)
- [Caddy 자동 HTTPS의 DNS·80·443 조건](https://caddyserver.com/docs/automatic-https)
- [AWS Session Manager의 인바운드 포트 없는 접속](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [AWS Secrets Manager와 Parameter Store의 용도](https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-a-parameter.html)
- [Amazon EBS 암호화](https://docs.aws.amazon.com/ebs/latest/userguide/how-ebs-encryption-works.html)
- [S3 퍼블릭 접근 차단](https://docs.aws.amazon.com/AmazonS3/latest/userguide/granting-public-access.html)
- [S3 수명주기 삭제의 비동기 처리](https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-to-set-lifecycle-configuration-intro.html)
