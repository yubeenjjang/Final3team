# review-fix 구현과 검증

1. 기존 인증 조회는 `get_current_user`와 `user_db_session`을 사용합니다. SSE는 WebSocket의 세션 검사 함수를 호출합니다. 모의 인증 경로도 같은 스트림 검사를 거칩니다.
2. A77은 대상 사용자 행을 잠근 뒤 프로필 역할을 확인합니다. A60·A62는 A49·A50과 같은 순서로 두 사용자 행을 잠그고 차단을 확인합니다. 모의 동행 쓰기는 친구·차단 상태와 같은 잠금을 사용합니다.
3. DB 001~028을 적용한 일회용 환경에서 서비스 역할로 보존 삭제와 재실행 집계를 검사합니다. SQL 실행기는 021 되돌리기 뒤 72시간 경계와 028 외래키의 적용·되돌리기·재적용을 검사합니다. 역할·RLS·동시성은 DB 표시 백엔드 시험에서 검사합니다.
4. 저장소 루트에서 백엔드 시험을 실행합니다. DB 시험은 일회용 DB의 `TEST_DB_URL`이 있을 때 함께 실행됩니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
bash 'Docs/Step 2/db/run_tests.sh'
```
