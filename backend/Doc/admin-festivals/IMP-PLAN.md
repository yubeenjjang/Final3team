# admin-festivals 구현·검증

1. `api/routers/admin/festivals.py`에서 공통 `require_role("admin")`을 사용한다. 요청 스키마가 API 필드와 값 형식을 검증한다. 저장소는 등록·수정에 동일한 계약을 사용하며, `AUTH_PROVIDER=db`에서 PostgreSQL 저장소에 연결한다.
2. 021 다음에 `Docs/Step 2/db/022_admin-festivals.sql`을 파일 단위 트랜잭션으로 적용한다. A55는 같은 이름·기간·장소를 트랜잭션 advisory lock으로 직렬화한다. A56·A24·수집은 동일 축제 행 잠금을 사용한다. 코드와 기록이 분리되지 않도록 변경·검토와 이력을 한 트랜잭션에서 저장한다.
3. 모의 HTTP 시험에서 두 관리자 경로의 역할, 검증 및 게시 수명주기, A24 연동을 확인한다. PostgreSQL 표시는 022까지 적용한 일회용 DB의 `TEST_DB_URL`과 선택 `TEST_DB_APP_URL`을 사용하며 RLS, 동시 등록·게시, 두 수집 경로를 확인한다. `Docs/Step 2/db/run_tests.sh`는 022 적용·되돌리기·재적용과 감사 이력이 있는 경우의 되돌리기 중단을 확인한다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

검증 결과는 538개 통과, 36개 DB 시험 건너뜀, 하위 시험 2개 통과다. 샌드박스에서는 쓰기 가능한 uv 캐시와 asyncio 파이프를 사용했다. `TEST_DB_URL` 미설정과 Docker 소켓 권한 제한으로 PostgreSQL 및 SQL 실행기의 실제 적용은 확인하지 못했다. SQL 실행기 셸 구문은 `bash -n`으로 확인했다.
