# W65 첫 AWS 배포 실행·검증 절차

이 문서는 [구성안](W65-AWS-PLAN.md)의 단일 EC2·Docker Compose 배포 절차다. **아직 AWS에서 실행하지 않았다.** 로컬 W64 검증과 AWS 결과를 섞지 않는다. 아래 명령은 서버의 저장소 루트에서 실행하는 예시이며, 실제 계정·도메인·비용 승인을 받은 뒤 사용한다.

## 1. 배포 전 입력값과 중단 조건

| 입력 | 확정할 값·근거 |
| --- | --- |
| AWS 계정·리전·서버 | 계정 ID, 리전, EC2 인스턴스 유형·AMI·고정 주소, 월 비용 상한과 과금 알림 |
| 도메인 | API용 `API_DOMAIN`, DNS A/AAAA가 서버 공인 주소를 가리키는지 확인. 프론트 주소·CORS는 담당 화면 배포 방식에 맞춰 별도 확정 |
| 접근 | 인스턴스 역할의 Session Manager·Secrets Manager 읽기·백업 S3 쓰기 권한. 운영자 접근 경로와 감사 로그 |
| 비밀값 | 관리자·앱·서비스 DB 비밀번호, `ASSISTANT_TOKEN_SECRET`(A06 사용 시), JWT/경로·공급원 키(해당 기능 사용 시). Secrets Manager 이름·권한·로테이션 담당 |
| 데이터 | 암호화된 EBS의 Docker 데이터 경로·용량, S3 백업 버킷·7일 만료 규칙·복원 시험 장소 |
| 정책 | RPO·RTO 목표, 백업 뒤 발생한 탈퇴·삭제의 재적용 방법, 서버 장애 시 운영자 연락 경로 |

이 값 중 하나라도 없으면 해당 기능을 켜지 않는다. 특히 **도메인 DNS가 준비되지 않았으면 HTTPS 프록시를 올리지 않고**, 백업·삭제 재적용 절차가 없으면 운영 복원 완료로 판정하지 않는다. 비밀값을 저장소나 명령 인자·터미널 출력에 남기지 않는다.

## 2. AWS 자원·네트워크

1. 단일 EC2와 암호화된 EBS를 준비한다. Docker 데이터 경로가 해당 영속 볼륨에 있는지 기록한다. 단일 서버 장애 시 서비스가 중단되는 구성이다.
2. 보안 그룹 인바운드는 사용자용 TCP **80·443**만 연다. 운영 접속은 Session Manager를 사용하며 22는 열지 않는다. DB 5432, Redis 6379, API 8000은 외부 공개하지 않는다.
3. API 도메인의 DNS를 EC2 공인 주소에 연결한다. Caddy가 인증서를 발급·갱신할 수 있도록 80·443과 Caddy 데이터 볼륨을 유지한다.
4. Secrets Manager와 비공개 S3 백업 버킷에 인스턴스 역할의 필요한 권한만 부여한다. S3 Block Public Access와 암호화를 확인하고, `backups/` 객체를 7일 후 만료시키는 수명주기 규칙을 둔다.
5. EC2·EBS·S3·도메인·비밀값·로그·데이터 전송의 예상 월 비용과 과금 알림을 실제 리전 기준으로 기록한다.

## 3. 설정·기동

1. 서버에 고정 Git 커밋을 체크아웃하고 `git rev-parse HEAD`를 기록한다. 빌드 후 백엔드·DB·Redis·Caddy 이미지 다이제스트를 기록한다. 외부 이미지 태그만을 재현 근거로 사용하지 않는다.
2. 인스턴스 역할로 Secrets Manager 값을 읽어 **호스트의 권한 제한 런타임 환경 파일**에 넣는다. 파일에는 `API_DOMAIN`, `POSTGRES_PASSWORD`, `DB_USER_PASSWORD`, `DB_SERVICE_PASSWORD`, `FESTIVAL_DATA=db`를 포함한다. A06을 켜면 `ASSISTANT_PROVIDER=db`, 공통 `ASSISTANT_TOKEN_SECRET`도 필요하다. Redis를 켜면 `REDIS_URL=redis://redis:6379/0`을 넣는다. 서비스별 비밀값 전달은 Compose 설정에서 다시 점검한다.
3. Docker Compose 설정을 먼저 확인한다. 아래 명령의 `$RUNTIME_ENV`는 서버의 권한 제한 파일 **경로**이며, 파일 내용은 출력하지 않는다.

```sh
RUNTIME_ENV=/etc/noldaga/runtime.env
# 명령을 실행할 권한을 가진 운영자만 환경 파일을 읽을 수 있어야 한다.
docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml config --quiet
```

4. `compose.aws.yaml`은 DB·API의 호스트 포트를 제거하고 Caddy만 80·443에 게시한다. **기존 운영 Compose 프로젝트에 오버레이를 처음 적용하기 전** `docker compose ... config`로 최종 포트와 볼륨을 확인한다. `down -v`를 운영 DB에서 실행하지 않는다.
5. 첫 기동은 DB→마이그레이션→역할 비밀번호 설정→API→Caddy 순서다. Redis와 A06 워커는 해당 기능을 사용하는 경우에만 함께 켠다.

```sh
docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml --profile redis --profile assistant up -d --build
docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml --profile redis --profile assistant ps
```

위 예시는 두 선택 기능을 **모두 켜는 경우**다. 실제 선택에 맞게 `--profile redis`와 `--profile assistant`를 빼거나 넣고, API 설정도 같은 선택과 일치시킨다. `scheduler`는 실제 공급원 키와 수집 일정 검토 뒤 `--profile scheduled`로 별도 활성화한다.

## 4. 배포 후 확인

| 확인 | 통과 조건·남길 기록 |
| --- | --- |
| 포트 | 호스트와 외부에서 5432·6379·8000 비공개. 80은 HTTPS로 리다이렉트, 443만 API 요청 처리 |
| HTTPS | `https://<API_DOMAIN>/api/v1/health` 200, 인증서 도메인·유효기간 확인. Caddy 데이터 볼륨 재기동 뒤 유지 |
| DB | `db` healthy, migrate 종료 0·001~최신 적용. 같은 설정 재실행에서 적용 이력 건너뛰기. API `/health db=ok` |
| Redis | 사용 시 `/health redis=ok`; 중단 시 503 `unavailable`, 재시작 후 `ok`. 미사용 시 `not_configured` |
| 축제 | **실제 승인된 데이터**가 적재된 뒤 A02 목록에서 `is_mock=false`·0건 초과, 동일 ID로 A03 상세 조회. 로컬 시험 행 결과로 대체하지 않음 |
| A06 | 사용 시 접수 202 `queued`→워커 완료/실패→A06-1 조회. 실제 Festival Agent 연결은 따로 구분 |
| 비밀값 | 이미지·히스토리·로그·외부 응답에 비밀값 원문 없음. API에 관리자 DB 비밀번호 없음 |
| 비용·로그 | 실제 자원·이미지 다이제스트·접속 시각·실패 항목·월 비용 추정 기록 |

## 5. 백업·복원 시험

- 매일 **KST 06:30**에 `pg_dump --format=custom --exclude-table-data=public.route_results`로 논리 백업한다. 기존 [백업 실행기](../../Docs/Step%202/db/backup_long_term.sh)와 같은 제외 규칙이다. 06:00 스케줄러 작업과 겹치면 백업 시각을 조정한다.
- 서버에 AWS CLI와 쓰기 권한이 있는 백업 임시 디렉터리를 준비한 뒤, 아래처럼 파일을 생성·업로드한다. `BACKUP_BUCKET`은 사전에 정한 비공개 버킷 이름이다. 이 예시는 작업 등록 전 **수동 검증용**이며 비밀번호 값을 출력하지 않는다.

```sh
umask 077
RUNTIME_ENV=/etc/noldaga/runtime.env
BACKUP_BUCKET=replace-with-private-bucket
BACKUP_FILE="/var/lib/noldaga-backups/noldaga-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose --env-file "$RUNTIME_ENV" -f infra/deployment/compose.yaml -f infra/deployment/compose.aws.yaml exec -T db sh -c 'exec pg_dump -U postgres -d "$POSTGRES_DB" --format=custom --exclude-table-data=public.route_results' > "$BACKUP_FILE"
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
