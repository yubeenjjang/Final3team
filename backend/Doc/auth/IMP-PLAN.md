# 자체 인증 구현·검증

1. `api/auth/tokens.py`에서 Argon2id 비밀번호와 JWT, Refresh 해시를 처리합니다.
2. `api/auth/state.py`에서 TTL 기반 폐기·로그인 카운터·갱신 잠금 인터페이스를 구현합니다.
3. `api/auth/service.py`에서 서비스 계정의 가입·로그인·갱신·폐기 트랜잭션을 처리합니다. `api/deps.py`에 JWT 검증과 요청 단위 RLS를 연결합니다.
4. `api/routers/accounts/auth.py`가 모드를 선택하고 `api/request_logs.py`가 인증 요청 로그를 정리합니다.

저장소 루트에서 실행합니다.

```bash
uv run --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

`test_auth_db_mode.py`에서 해시·JWT·입력 검증·중복·잘못된 자격 증명·갱신·폐기·한도·인증 상태 장애를 확인합니다. `test_a3_log_redaction.py`의 인증 시험은 Uvicorn의 HTTP 파서와 액세스·ASGI 로그를 거쳐 원문 노출을 검사합니다.

`test_auth_postgres.py`는 001~009를 적용한 일회용 PostgreSQL에서 실행합니다. `TEST_DB_URL`에는 `SET LOCAL ROLE noldaga_service`가 가능한 접속 정보를 넣습니다. `TEST_DB_APP_URL`을 설정하면 `noldaga_app` 계정으로 직접 연결합니다. 생략 시 `TEST_DB_URL`에 `SET LOCAL ROLE noldaga_app` 권한도 필요합니다. 시험은 실제 저장 행·롤백·폐기·RLS를 확인한 뒤 생성한 계정만 정리합니다.
