# STEP5 — 공통 DB 연결과 시험 명령

1. `shared/db/session.py`, `shared/db/connection.py`, `shared/db/README.md`, `shared/db/migrate.py`를 읽고 SPEC P20·P21에 세션 계약과 확인 사항을 기록한다.
2. 귀가 저장소의 자체 엔진을 제거하고 공통 `service_db_session()`으로 요청·결과를 처리한다. A05는 결과보다 토큰 해시를 먼저 검증한다. `ROUTE_STORE` 기본값은 `memory`다.
3. `migration_files()`로 011·012의 적용 파일 선택을 점검한다. 발견한 실행기 문제와 서비스 계정 배포 설정은 유빈님 확인 사항으로 기록한다.
4. 저장소 루트에서 `uv run --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q`로 실행한다. `backend/`에서도 `uv run --with-requirements api/requirements.txt --with-requirements requirements-dev.txt python -m pytest tests -q`로 확인한다.
5. 경로 DB 통합 시험에 `db` 표시를 유지한다. `TEST_DB_URL`이 설정된 일회용 환경에서는 루트 공통 명령에 `-m db`를 추가한다. A02·A03 축제 조회에는 `TEST_DB_APP_URL`, 011 적용·되돌리기에는 소유자 권한 또는 `TEST_DB_MIGRATION_URL`이 필요하다.
