# W64 백엔드 Docker 기동 절차 (12/04 부분 기동본)

- 작성: 한태경(R04, W64 주담당) · 2026-11-26 · 검토: 신유빈(R06)
- 기준: `yubeen` `34cab99`의 `infra/deployment/compose.yaml`(Redis·A06 워커 선택 프로필 포함)
- 상태: **로컬 Docker 절차.** 아래 확인값은 11/26 로컬에서 직접 실행한 결과다. AWS 적용은 [W65-AWS-PLAN.md](W65-AWS-PLAN.md)에서 따로 다룬다.
- 이 문서는 [README.md](README.md)를 보완한다. README에는 파일 구성과 원칙을 두고, 이 문서에는 **단계별 확인값·다시 기동·문제 해결·알려진 제한**을 둔다.

## 1. 준비
| 항목 | 확인 방법 |
|---|---|
| Docker와 Compose v2 | `docker compose version` |
| 저장소 루트에서 실행 | 모든 명령은 저장소 최상위 폴더 기준 |
| 포트 | 기본값은 DB `5432`, API `8000`. 이미 쓰는 포트면 `.env`에 `DB_PORT=`·`API_PORT=`로 바꾼다 |

## 2. 처음 기동

### 2-1. `.env` 만들기
```bash
cp .env.example .env
python3 infra/deployment/fill_env_secrets.py
```
- 기대 출력: `채운 항목: POSTGRES_PASSWORD, DB_USER_PASSWORD, DB_SERVICE_PASSWORD, DB_MIGRATION_DSN (값은 출력하지 않음)`
- `.env` 권한은 `-rw-------`(600)이고, Git 제외 대상이다.
- **DB를 처음 띄운 뒤에는 `POSTGRES_PASSWORD`를 바꾸지 않는다.** 바꾸면 5-2의 인증 실패가 난다. 스크립트는 이미 값이 있는 항목을 건드리지 않는다.

### 2-2. 모드 정하기
`.env`에 쓴 값 중 **compose가 넘기는 값만** 컨테이너에 들어간다(서비스마다 필요한 값만 넘기는 원칙). 지금 전달되는 주요 값은 다음과 같다.

| 서비스 | 전달되는 모드·키 |
|---|---|
| `api` | `FESTIVAL_DATA`, `ROUTE_PROVIDER`, `ROUTE_STORE`, `CROWD_PROVIDER`, `ASSISTANT_PROVIDER`, `ASSISTANT_TOKEN_SECRET`, `REDIS_URL`, `ROUTE_KEY_SECRET`, 공급원 키 4개(`TMAP_APP_KEY`, `KAKAO_REST_API_KEY`, `SEOUL_OPEN_API_KEY`, `DATA_GO_KR_SERVICE_KEY`) |
| `scheduler` | 서비스 계정, `DATA_GO_KR_SERVICE_KEY`, `SEOUL_CULTURE_ENABLED`, `SEOUL_OPEN_API_KEY`, `KAKAO_REST_API_KEY` |
| `assistant-worker` | 서비스 계정, `ASSISTANT_TOKEN_SECRET`, `FESTIVAL_DATA`, `ASSISTANT_FESTIVAL_RUNNER` |

- 축제 목록·상세를 DB에서 읽으려면 `FESTIVAL_DATA=db`
- 위 표에 없는 값(예: `AUTH_PROVIDER`)은 `.env`에 써도 컨테이너에 들어가지 않는다. 6-2 참고.

### 2-3. 기동
```bash
docker compose --env-file .env -f infra/deployment/compose.yaml up -d --build --wait
```
- `--wait`를 붙이면 `api`가 healthy가 되거나 앞 단계가 실패할 때까지 기다리고, 실패하면 종료 코드 1을 낸다.
- 11/26 확인: 처음 빌드 포함 약 36초, 종료 코드 0.

### 2-4. 확인
| 확인 | 명령 | 기대값 |
|---|---|---|
| 서비스 상태 | `docker compose --env-file .env -f infra/deployment/compose.yaml ps -a` | `db` healthy, `migrate` Exited (0), `role-passwords` Exited (0), `api` healthy |
| 마이그레이션 | `... logs --no-log-prefix migrate` | `적용: 001_…`부터 `적용: 028_review-fix.sql`까지 28줄 |
| 계정 비밀번호 | `... logs --no-log-prefix role-passwords` | `설정한 계정: noldaga_app, noldaga_service (값은 출력하지 않음)` |
| 헬스 | `curl http://127.0.0.1:8000/api/v1/health` | HTTP 200, `"status":"ok"`, `"db":"ok"`, `"redis":"not_configured"` |
| 축제 목록 | `curl http://127.0.0.1:8000/api/v1/festivals` | HTTP 200, `is_mock:false`, `total:0` |

- `total:0`은 빈 DB의 정상 결과다. 실제 축제를 보이려면 수집·적재가 따로 필요하다(W100).
- `...`은 `docker compose --env-file .env -f infra/deployment/compose.yaml`의 줄임이다.

## 3. 다시 기동·갱신
| 상황 | 명령 | 결과 |
|---|---|---|
| 끄기(데이터 유지) | `... down` | DB 볼륨 `noldaga-db`는 남는다 |
| 다시 켜기 | `... up -d --wait` | `migrate`가 28개 모두 `건너뜀`으로 끝나고 정상 기동(11/26 확인) |
| 코드 갱신 후 | `git pull` 다음 `... up -d --build --wait` | 새 마이그레이션 번호만 `적용`, 나머지는 `건너뜀` |
| 완전 초기화(로컬 시험 DB만) | `... down -v` | **DB 데이터가 모두 지워진다.** 운영 DB에서는 쓰지 않는다 |

## 4. 선택 기동(프로필)
| 프로필 | 켜는 방법 | 확인값 | 11/26 확인 |
|---|---|---|---|
| `redis` | `.env`에 `REDIS_URL=redis://redis:6379/0`, `--profile redis` | `/health`의 `"redis":"ok"`. Redis 포트는 호스트에 공개되지 않음 | 확인함 |
| `assistant` | `.env`에 `ASSISTANT_PROVIDER=db`, 32바이트 이상 `ASSISTANT_TOKEN_SECRET`, `--profile assistant` | A06 접수 202 → `queued` → 완료/실패 조회 | 실행하지 않음 |
| `scheduled` | 공급원 키 설정 후 `--profile scheduled` | `logs scheduler`의 `status=ok`·`already_done`·`error` | 실행하지 않음(실제 공급원 호출이 생김) |

여러 프로필은 `--profile redis --profile assistant`처럼 함께 쓴다. 자세한 설명은 README의 "Redis와 A06 워커 선택 기동"을 따른다.

## 5. 문제 해결
| 증상 | 원인 | 조치 |
|---|---|---|
| 5-1. 기동 전에 `.env에 POSTGRES_PASSWORD가 필요합니다` | `.env`에 비밀값이 비어 있음 | `fill_env_secrets.py` 실행 |
| 5-2. `up`이 종료 코드 1, `migrate` Exited (1), 로그에 `password authentication failed for user "postgres"`, `role-passwords`는 Created에서 멈춤 | DB를 만든 뒤 `.env`의 `POSTGRES_PASSWORD`가 바뀜(11/26 재현) | 원래 값으로 되돌린다. 로컬 시험 DB라면 `down -v` 후 다시 기동해도 된다 |
| 5-3. 5-2 상황인데 `/health`는 200 | 이전에 떠 있던 `api` 컨테이너가 그대로 남아 있음(11/26 관측) | `/health`만 보지 말고 `ps -a`에서 `migrate`·`role-passwords`가 Exited (0)인지 함께 본다 |
| 5-4. `migrate` 로그에 `적용 이력과 SQL 파일이 다릅니다: NNN` | 이미 적용한 SQL 파일 내용이 바뀜 | 적용한 파일은 고치지 않는다. 마이그레이션 담당에게 새 번호 파일로 요청 |
| 5-5. `port is already allocated` | 같은 포트를 다른 프로그램이 사용 중 | `.env`에 `DB_PORT`·`API_PORT`를 다른 값으로 지정 |

## 6. 알려진 제한 (팀 확인 필요)

### 6-1. 실제 모드에서 호출 한도 파일을 쓰지 못함
- 앱은 `noldaga` 계정으로 `/app/backend`에서 실행되는데, 이 폴더는 root 소유라 쓸 수 없다.
- 호출 한도 파일(`./.route_quota.json`, `./.crowd_quota.json`, `./.festival_info_quota.json`)과 잠금 파일을 이 폴더에 만들려다 `PermissionError`가 난다. 11/26 컨테이너 안에서 한도 확인 함수만 실행해 재현했고, 외부 API는 호출하지 않았다.
- 영향(코드 기준):
  - 혼잡·축제 부가 정보는 이 오류를 잡아서, 실제 모드를 켜도 항상 "조회 불가"로 응답한다.
  - 귀가 경로(`ROUTE_PROVIDER=real`)는 한도 확인 단계에서 실패한다.
- 기본 모의 모드에는 영향이 없다.
- `*_QUOTA_FILE` 환경변수도 compose가 넘기지 않아 `.env`로 피할 수 없다. `/tmp`로 지정하면 동작은 하지만, 컨테이너를 다시 만들 때마다 사용량이 초기화된다. TMAP 하루 10회 같은 한도 관리가 깨진다.
- 제안: 한도 파일 전용 명명 볼륨(예: `/app/state`, `noldaga` 소유)을 `api`에 붙이고 `ROUTE_QUOTA_FILE`·`CROWD_QUOTA_FILE`·`FESTIVAL_INFO_QUOTA_FILE`을 그 경로로 넘긴다. 단, `api`를 여러 개 띄우면 파일 잠금으로는 한도를 함께 셀 수 없다. W65에서 단일 호스트 기준으로 확인한다.

### 6-2. `.env.example`에 있지만 `api`에 전달되지 않는 실제 모드 값
- 로그인: `AUTH_PROVIDER`, `JWT_SECRET`, `JWT_ISSUER`
  - Docker에서는 로그인이 항상 모의 모드다. 11/26에 `.env`에 `AUTH_PROVIDER=db`를 넣고 컨테이너 환경을 확인해 보니 들어가지 않았다.
- 축제 부가 정보: `WEATHER_PROVIDER`, `TRANSIT_PROVIDER`, `TRAFFIC_INCIDENT_PROVIDER`, `VISIT_FORECAST_PROVIDER`(`VISIT_FORECAST_STORE`), `FACILITIES_PROVIDER`, `NOTICES_PROVIDER`
- 기타: `BUS_CROWD_PROVIDER`, `UTIC_ENABLED`, `ROUTE_PURGE_AFTER_HOURS`
- 12/04 부분 기동본에서 어떤 기능을 실제 모드로 보일지 정한 뒤, 그 값만 `api`의 `environment`에 추가한다. `JWT_SECRET` 같은 비밀값을 추가하면 SEC-07(이미지·히스토리·로그 비밀값 0건)을 다시 확인한다.

### 6-3. 그 밖의 결정 대기
README의 "아직 정하지 않은 것" 1~6을 따른다. 비밀값 보관과 7일 백업은 W65 구성안 2·3절에 기준안이 있다.

## 7. 12/04 부분 기동본 점검표
- [ ] 2-1~2-4를 새 폴더에서 그대로 따라 해 기대값이 나온다
- [ ] 3의 다시 켜기에서 28개 `건너뜀`
- [ ] SEC-07: 이미지 설정·빌드 히스토리·로그에 비밀값 0건, 이미지 안 `.env` 0개, `api`에 `POSTGRES_PASSWORD` 없음
- [ ] 6-1 처리 방향 결정(볼륨 추가 또는 부분 기동본은 모의 모드만)
- [ ] 6-2에서 부분 기동본에 넣을 실제 모드 결정
- [ ] 실제 축제 데이터를 넣은 DB에서 목록·상세 같은 ID 조회(W100 적재 후)
- [ ] 검증 기록을 남기고 W65로 인계(이미지 태그·커밋 기록)

## 8. 확인 기록 (2026-11-26, 로컬 Docker)
- 코드: `yubeen` `34cab99`, 시험용 Compose 프로젝트 이름과 시험용 포트 사용. 비밀값은 `fill_env_secrets.py`가 만든 무작위 값만 썼다.
- 2-1~2-4: 기대값과 같음(마이그레이션 28개 적용, `/health` 200 `db=ok`, 축제 목록 200 `is_mock:false` `total:0`)
- 3: `down` 후 다시 켜기에서 28개 `건너뜀`
- 4: `redis` 프로필에서 `/health`의 `redis=ok`, Redis 포트는 호스트에 공개되지 않음
- 5-2·5-3: 관리자 비밀번호를 바꿔 재현
- 6-1·6-2: 컨테이너 안에서 재현. 외부 API는 호출하지 않았다.
- 실행하지 않음: `assistant`·`scheduled` 프로필, 실제 공급원 호출, SEC-07 재검사(11/25 기록 참고), AWS
- 정리: 시험 컨테이너·네트워크·DB 볼륨·임시 `.env`·워크트리 삭제. 로컬 이미지 `noldaga-backend:local`은 남겨 두었다.
