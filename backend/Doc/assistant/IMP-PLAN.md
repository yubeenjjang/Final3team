# A06 실행 및 검증

1. 일회용 PostgreSQL에 기존 001~021과 `Docs/Step 2/db/022_assistant.sql`을 적용합니다. API와 워커에 동일한 DB 설정 및 `ASSISTANT_PROVIDER=db`를 지정합니다. API에 `ASSISTANT_TOKEN_SECRET`을 32바이트 이상으로 설정하고, JWT를 사용할 때는 기존 DB 인증 설정을 지정합니다.
2. `backend/`에서 API와 별도로 `python -m api.jobs.assistant_worker`를 실행합니다. 워커 프로세스를 여러 개 실행할 수 있습니다. 30초 시도 제한은 별도 자식 프로세스에서 시행하고, 5초 뒤의 재시도 가능 시각은 DB에 기록합니다. 워커의 정리 스레드가 70초 이상 멈춘 작업과 보존 만료 작업을 처리합니다.
3. Festival Agent 연결 시 `agents.festival_agent:run`을 제공하거나 `ASSISTANT_FESTIVAL_RUNNER`에 `agents` 패키지 아래의 실행 함수를 지정합니다. 실행 함수는 `(RunInput, step)`을 받고 `AgentResult` 또는 같은 필드의 매핑을 반환합니다. LLM HTTP 429·5xx는 `status_code`가 있는 예외로, 시간 초과는 `TimeoutError`로 전달합니다.
4. 큐 공급원을 교체할 때 `AssistantQueue`의 접수·선점·상태 기록 계약과 중복 실행 방지를 유지합니다. 별도 큐에 발행하려면 DB 작업 커밋과 발행의 일관성이 필요합니다. Redis 연결 전에는 요청 제한을 API 프로세스 단위 메모리로 관리하고 SSE 구독마다 PostgreSQL 연결을 사용합니다.
5. 루트에서 아래 오프라인 전체 시험을 실행합니다. 실DB 시험에는 022까지 적용된 일회용 DB의 `TEST_DB_URL`을 사용합니다. 필요하면 RLS 계정의 `TEST_DB_APP_URL`을 따로 지정합니다. 로컬 pgvector 이미지가 있는 환경에서 `Docs/Step 2/db/run_tests.sh`로 SQL 적용·되돌리기·재적용을 확인합니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```
