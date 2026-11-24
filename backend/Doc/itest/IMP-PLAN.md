# 화면 흐름 통합 시험 실행 방법

## 전체 백엔드 시험

저장소 루트에서 실행한다. 두 시험 DSN 중 하나라도 비어 있으면 통합 시험 일곱 건을 건너뛴다. 기존 DB 시험의 실행 조건은 각 시험에 따른다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

## PostgreSQL 통합 시험 실행

1. 로컬 PostgreSQL 17과 pgvector에 시험 전용 빈 DB를 준비한다. [DDL 실행기](../../../Docs/Step%202/db/run_tests.sh) 순서를 따라 적용 SQL 001~026을 한 번 적용한다. 010은 자체 트랜잭션이 있다. 사전 검사·down·시험 SQL은 적용 SQL 목록에서 제외한다.
2. 보호된 환경 파일이나 현재 셸에서 아래 두 URL을 환경변수로 설정한다. 두 URL은 같은 클러스터의 같은 시험 전용 DB를 가리킨다. 원본 시험 DB의 다른 연결을 닫고 실행한다. PostgreSQL은 연결 중인 DB를 템플릿으로 복제할 수 없다.
   - `TEST_DB_URL`은 `noldaga_service`로 접속하거나 해당 역할로 전환할 수 있는 PostgreSQL URL이다.
   - `TEST_DB_MIGRATION_URL`은 원본 DB 소유자이면서 `CREATEDB`, `postgres` 유지관리 DB 접속과 `SET ROLE noldaga_app`이 가능한 PostgreSQL URL이다. 원본 DB 이름은 `postgres`, `template0`, `template1`과 다른 이름으로 지정한다.
3. 저장소 루트에서 통합 시험만 실행한다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests/integration -m db -q -rs
```

시험 세션은 원본에 적용된 구조를 임시 DB로 복제한 뒤 그 복제본에서 API, 워커, 정기 작업을 실행한다. 세션이 끝나면 생성한 복제본을 정리한다. HTTP·WebSocket 요청은 FastAPI의 ASGI 앱을 직접 호출한다. 축제 조회와 요청별 사용자 세션은 `noldaga_app`, 내부 쓰기와 워커·정기 작업은 `noldaga_service`로 실행한다. TourAPI와 챗봇 답변은 합성 데이터로 대체한다.
