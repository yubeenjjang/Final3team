# db2b 실행 및 확인

저장소 루트에서 오프라인 시험을 실행합니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

단위 시험은 상태 확인의 모의 모드·DB 오류·시간 초과, 수집 잠금 충돌, 목록과 상세의 공개 조건, 경로·찜·챗봇에서 같은 축제 조회를 쓰는지 확인합니다.

DB 시험에는 001~028을 적용한 일회용 PostgreSQL의 서비스 계정 `TEST_DB_URL`, 앱 계정 `TEST_DB_APP_URL`, 마이그레이션 계정 `TEST_DB_MIGRATION_URL`을 사용합니다. 다음 시험은 공개·비공개 축제의 조회 권한과 목록의 동시성, 풀에 연결이 돌아간 뒤 원래 격리 수준으로 복구되는지 확인합니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests/ingestion/test_i12_catalog_db.py backend/tests/api/test_notice_db.py -m db -q -rs
```
