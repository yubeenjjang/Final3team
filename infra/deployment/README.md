# 백엔드 Docker 부분 기동 (W64 초안)

- 작성: 한태경(R04, W64 주담당) · 2026-11-24 · 검토: 신유빈(R06)
- 상태: **초안.** 12/04 부분 기동본 준비용. 로컬 Docker에서만 확인했고 AWS(W65)는 아직이다.
- 기준: 백엔드 이미지 **Python 3.14**(11/24 팀장 결정), DB 이미지 `pgvector/pgvector:pg17`

## 파일
| 파일 | 역할 |
|---|---|
| `backend.Dockerfile` | 백엔드 이미지 하나로 API·마이그레이션·계정 비밀번호 설정을 모두 실행 |
| `backend.Dockerfile.dockerignore` | 이미지에 넣을 것만 허용(`backend/`, `Docs/Step 2/db/`, 비밀번호 설정 스크립트). `.env`·시험·문서 제외 |
| `compose.yaml` | `db` → `migrate` → `role-passwords` → `api` 순서로 기동 |
| `fill_env_secrets.py` | `.env`의 빈 비밀값만 무작위로 채움(값 출력 안 함, 권한 600) — 비밀번호 절차 v2의 3-1 |
| `set_role_passwords.py` | 앱·서비스 계정 비밀번호를 SCRAM 검증값으로 설정 — 비밀번호 절차 v2의 3-3 |

## 실행 (저장소 루트에서)
```bash
cp .env.example .env                       # 이름만 있는 예시를 복사 (POSTGRES_PASSWORD 줄이 없으면 추가)
python3 infra/deployment/fill_env_secrets.py   # 빈 비밀값만 채움. DB를 처음 띄우기 전에 실행
docker compose --env-file .env -f infra/deployment/compose.yaml up -d --build
curl http://127.0.0.1:8000/api/v1/health
```
- 축제 목록을 DB에서 읽으려면 `.env`에 `FESTIVAL_DATA=db`
- 정기 수집은 기본 기동에 포함하지 않는다. 공급원 키를 설정한 뒤 `docker compose --env-file .env -f infra/deployment/compose.yaml --profile scheduled up -d --build`로 `scheduler`를 켠다. 매시간 한국 시각 회차를 확인하고 축제 수집은 06:00 이후 하루 한 번 실행한다. 성공 회차는 DB에 기록되어 재시작해도 중복 실행하지 않으며, 실패 회차는 다음 실행 때 다시 시도한다. 서울시 2차 수집은 `SEOUL_CULTURE_ENABLED=true`와 `SEOUL_OPEN_API_KEY`를 설정한 경우에만 실행한다.
- 정기 실행 결과: `docker compose --env-file .env -f infra/deployment/compose.yaml logs scheduler`. `status=ok`는 실행, `status=already_done`은 같은 회차 건너뜀, `status=error`는 실패 후 재시도 대상이다. 공급원 목록에서 사라진 행은 취소로 단정하지 않고 공개 보류·관리자 검토로 보낸다.
- 끄기: `docker compose --env-file .env -f infra/deployment/compose.yaml down` (DB까지 지우려면 `down -v`)

## 지키는 원칙
- **비밀값은 이미지에 넣지 않는다.** Dockerfile에 `ENV`·`ARG`·비밀 파일 `COPY` 없음. 실행할 때 환경변수로만 받는다.
- **서비스마다 필요한 값만 준다.** `env_file`로 `.env`를 통째로 넘기지 않는다. `api`에는 관리자 비밀번호를 주지 않는다.
- **포트는 이 컴퓨터에만 연다**(`127.0.0.1`).
- **root가 아닌 계정**(`noldaga`, uid 10001)으로 실행한다.

## 확인 기록 (2026-11-24, 로컬 Docker)
- 코드: `yubeen 0af807e` + `tk`를 임시로 합친 사본, 마이그레이션 001~012
- 기동: `migrate`가 001~012 적용 후 종료 코드 0, `role-passwords` 0, `api` healthy
- `/api/v1/health` 200, `FESTIVAL_DATA=db`에서 `/api/v1/festivals` 200·`is_mock:false` (앱 계정 비밀번호로 실제 DB 조회)
- 다시 기동: `migrate`는 이미 적용된 파일을 "건너뜀"으로 끝내고 정상 기동
- **SEC-07:** `docker history`·이미지 설정에 비밀값 0건, 이미지 안 `.env` 0개·시험 폴더 없음, `api` 컨테이너에 관리자 비밀번호 없음, 전체 로그에 비밀값 0건
- 이미지 크기 약 306MB

## 아직 정하지 않은 것 (팀장 결정 대기)
1. **비밀번호 설정 스크립트의 저장소 위치**(절차 v2의 결정 E). 지금은 이 폴더에 둔 초안이다.
2. **`api`에 서비스 계정을 줄지**(A05 귀가 결과 조회). 귀가 DB 저장(`ROUTE_STORE=db`)에는 필요해서 지금은 넣어 두었다.
3. **프론트 Docker 포함 여부**: 실제 사용할 프론트 구현 기준으로 확정 예정.
4. **Redis·Celery 워커**: 코드가 아직 비어 있어 넣지 않았다. 코드가 생기면 서비스 추가.
5. **배포 비밀값 보관 방법**(서버 권한 제한 파일 vs AWS 보관 서비스): W65에서 결정.
6. **7일 백업**: `Docs/Step 2/db/backup_long_term.sh`(경로 본문 제외)를 언제·어디서 돌릴지 W65에서 결정.

## 참고
- `/api/v1/health`는 지금 DB·Redis 연결을 실제로 확인하지 않는다(응답의 `db`·`redis`가 `mock`). DB 상태 확인은 W12의 남은 일이다.
- `backend/api/requirements.txt`에 시험 도구(`pytest`)가 들어 있어 실행 이미지에도 설치된다. 실행용과 시험용 의존성을 나눌지 정하면 이미지가 더 작아진다.
- Python 3.14에서 `langsmith`가 "Python 3.16에서 없어질 함수" 경고를 낸다. 지금 동작에는 영향이 없다.
