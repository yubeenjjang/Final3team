# D1. DB 접근 방식 — 권오현 의견 (2026-11-22, 유빈님과 결정용)

> 결정 주체: 신유빈(`backend/shared/db/` 담당) · 의견: 권오현(스키마·SQL 작성). 근거: DB 스키마 설계서 v0.3.3 **3절(접속 역할·RLS·사용자 정보 설정 규칙)**, 시험 T21~T23.
> 정해야 할 것 4가지: ① 라이브러리 ② 요청마다 사용자 설정 위치 ③ 마이그레이션 적용 방식 ④ 워커(Celery) 쪽 연결

## 0. 스키마가 이미 정해 둔 조건 (바꾸기 어려운 것)
| 조건 | 내용 | 근거 |
|---|---|---|
| 접속 역할 2개 | 사용자 요청 = `noldaga_app`(RLS 적용), 수집·감지·정책·워커 = `noldaga_service`(RLS 우회) | 3절 표 |
| **요청마다 트랜잭션 + 사용자 설정** | `BEGIN` 직후 `SELECT set_config('app.user_id', :sub, true)`(= `SET LOCAL`), 끝나면 `COMMIT`/`ROLLBACK` | 3절 ①②④ |
| **금지** | `SET app.user_id`(LOCAL 없이)·`set_config(…, false)` — 연결에 남아 다음 사용자에게 새어 나감 | 3절 ③, **T22에서 실제로 샘** |
| 자동 커밋 금지 | `noldaga_app`으로 트랜잭션 밖 쿼리 안 함 | 3절 ④ |
| 연결 반납 때 초기화 | `RESET ALL`(또는 풀의 reset) | 3절 ⑤ |
| 한 요청에 역할 섞지 않음 | 사용자 요청 안에서 `noldaga_service`를 섞어 쓰지 않음(필요하면 서비스 함수로 분리) | 3절 ⑥ |
| 확장 | `pgvector`(RAG), `pg_trgm` | 2절 |
| 마이그레이션 | **순수 SQL 001~009 + 되돌리기 SQL**, 시험 149개가 이 파일로 돌아감 | `Docs/Step 2/db/` |

## 1. 라이브러리 — 제안: **SQLAlchemy 2.x (Core 위주) + psycopg 3**
| 후보 | 장점 | 단점 | 의견 |
|---|---|---|---|
| **A. SQLAlchemy 2.x + psycopg 3** | 비동기(API)·동기(Celery 워커) **둘 다 같은 라이브러리**, 연결 풀·트랜잭션 관리 내장, `pgvector` 파이썬 패키지가 지원, 팀원이 자료 찾기 쉬움 | ORM까지 쓰면 배울 게 많음 | ✅ **추천.** ORM 모델은 최소로, 조회는 Core(`select`)·`text()` 위주 |
| B. asyncpg 직접 | 가장 빠름, 단순 | 동기 워커(Celery)용 연결을 따로 만들어야 함, 트랜잭션·풀 규칙을 우리가 직접 지켜야 함 | 워커가 동기라 이중 관리 부담 |
| C. ORM 중심(SQLAlchemy ORM 모델 전부) | 코드 자동 완성 | 48개 테이블 모델을 다 만들어야 함, RLS·CHECK는 어차피 SQL | 지금 일정엔 과함 |

## 2. 요청마다 사용자 설정 — 제안: **공통 의존성 하나에서만**
- `backend/shared/db/session.py`(유빈님)에 FastAPI 의존성 `get_db(current_user)` 하나를 둔다:
  1. 연결 풀(`noldaga_app` 계정)에서 연결 → `BEGIN`
  2. 로그인 사용자면 첫 문장 `SELECT set_config('app.user_id', :sub, true)`, 비로그인은 **안 함**
  3. 라우터·repository는 이 세션만 받아 씀 → 끝나면 `COMMIT`, 예외면 `ROLLBACK`
- 서버 내부 작업(수집·감지·정책·관리자 기록)은 **별도 의존성 `get_service_db()`**(`noldaga_service` 계정, 별도 풀).
- **규칙을 코드로 막기:** 저장소에서 `SET app.user_id`·`set_config(…, false)` 문자열을 찾는 시험 1개(CI/pytest), 풀 reset 켜기(`pool_reset_on_return`).
- **시험:** 설계서 T21~T23을 파이썬 쪽에서도 1번 — 같은 연결로 A 요청 → B 요청 때 A 정보가 안 남는지.

## 3. 마이그레이션 적용 — 제안: **지금 SQL 파일 그대로 + 작은 적용기**
- `backend/shared/db/migrations/`에 `001_…sql`~`009_…sql`(+`_down`)을 그대로 옮기고, `schema_migrations` 표에 적용 기록을 남기는 짧은 적용 스크립트(또는 Alembic을 쓰되 각 단계가 SQL 파일을 실행만).
- 이유: RLS·CHECK·트리거·`SECURITY DEFINER`가 SQL 그 자체이고, 시험 149개가 이 파일로 검증됨. 자동 생성 도구(Alembic autogenerate)는 RLS·정책을 못 만듦.
- 로컬·AWS 모두 같은 이미지 `pgvector/pgvector:pg17`, 같은 순서(`Docs/Step 2/db/run_tests.sh`가 기준).

## 4. 워커(Celery) 쪽 — 제안
- 워커는 사용자 요청이 아니므로 **`noldaga_service` 동기 연결**(같은 SQLAlchemy, psycopg 동기 드라이버).
- 사용자 대신 쓰는 작업(예: 챗봇 작업 결과 저장)은 작업에 `user_id`를 실어 보내고, **서비스 함수가 그 행만** 갱신(RLS 우회 계정이라 WHERE를 반드시 붙이는 규칙 + 시험).

## 5. 유빈님께 확인 부탁 (월요일)
1. 라이브러리 A(SQLAlchemy 2 + psycopg 3, Core 위주)로 가도 될까요?
2. `get_db`/`get_service_db` 두 의존성을 `shared/db/session.py`에 두는 구조, 괜찮을까요? 언제쯤 쓸 수 있을까요? (제가 인증 W18을 11/23~26에 해야 해서, 늦어지면 제가 초안을 PR로 드려도 될까요?)
3. 마이그레이션은 SQL 파일 그대로 + 적용 기록 표로 할까요, Alembic으로 감쌀까요?
4. DB 접속 계정 2개(`noldaga_app`·`noldaga_service`) 비밀번호는 환경변수 이름을 무엇으로 할까요? (`infra/`·W64 시크릿 규칙과 맞추기)
