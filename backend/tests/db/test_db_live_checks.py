"""실제 PostgreSQL에서 확인하는 DB 연결·권한 시험 (R04 한태경).

검증 항목 문서의 DB-01~07(비회원·사용자 연결 재사용), DB-10~14(실패 시 롤백·연결 정리),
DB-15~17(계정 분리)을 시험으로 고정한다. DB-08·18은 `test_no_db_checks.py`, DB-09는 유빈님
`test_session.py`와 태경 독립 재검증으로 확인했다.

실행 조건 (하나라도 없으면 건너뜀)
- `DB_LIVE_TEST=1`
- `DB_HOST`·`DB_PORT`·`DB_NAME`·`DB_USER_*`·`DB_SERVICE_*`: 앱·서비스 계정 접속값
- `DB_MIGRATION_DSN`: 시험 데이터를 넣고 지우는 관리자 접속값
- 001 이후 마이그레이션이 적용된 **일회용** DB (운영 DB에 돌리지 않는다)
- `backend/shared/db/session.py`(yubeen)가 있어야 함 — main 병합 전이면 건너뜀
- DB-13은 `DB_TEST_CONTAINER`(재시작할 Docker 컨테이너 이름)가 있을 때만 실행.
  컨테이너는 **고정 포트**(`-p 127.0.0.1:포트:5432`)로 띄워야 한다. 임의 포트(`-p 127.0.0.1::5432`)는
  재시작하면 포트가 바뀌어 이후 시험이 모두 접속 실패한다(11/24 확인).

시험 데이터는 모두 가상 값이며 끝나면 지운다. 비밀번호는 출력하지 않는다.
"""

import asyncio
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

REQUIRED_ENV = ("DB_HOST", "DB_NAME", "DB_USER_USERNAME", "DB_USER_PASSWORD",
                "DB_SERVICE_USERNAME", "DB_SERVICE_PASSWORD", "DB_MIGRATION_DSN")
missing = [name for name in REQUIRED_ENV if not os.environ.get(name, "").strip()]
pytestmark = pytest.mark.skipif(
    os.environ.get("DB_LIVE_TEST") != "1" or bool(missing),
    reason="DB_LIVE_TEST=1과 DB 접속 환경변수가 필요함 (일회용 DB 전용)",
)

PUB_A, PUB_B = "fst_LIVEPUB001", "fst_LIVEPUB002"
UNPUBLISHED, HIDDEN = "fst_LIVEUNPUB1", "fst_LIVEHIDE01"
USER_A, USER_B = uuid.uuid4(), uuid.uuid4()
PERMISSION_DENIED = "42501"   # 권한 없음·RLS 위반 모두 이 SQLSTATE


# ---------------------------------------------------------------- 공통 도구

def _session_module():
    try:
        from backend.shared.db import session
    except ImportError as exc:
        pytest.skip(f"DB 세션 코드를 불러올 수 없음: {exc}")
    if not hasattr(session, "user_db_session") or not hasattr(session, "service_db_session"):
        pytest.skip("user_db_session이 아직 main에 없음 (yubeen 병합 전)")
    return session


def _admin():
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(os.environ["DB_MIGRATION_DSN"], autocommit=True)


def run_user(fn):
    """사용자 연결 풀을 새로 만들어 비동기 시험 하나를 실행하고 풀을 닫는다(이벤트 루프마다 풀 분리)."""
    s = _session_module()
    s._user_engine.cache_clear()

    async def main():
        try:
            return await fn(s)
        finally:
            await s._user_engine().dispose()
            s._user_engine.cache_clear()

    return asyncio.run(main())


def sqlstate(exc: BaseException) -> str | None:
    orig = getattr(exc, "orig", exc)
    return getattr(orig, "sqlstate", None)


async def fetch(session, sql: str, **params):
    from sqlalchemy import text
    return (await session.execute(text(sql), params)).all()


async def state(session):
    """현재 연결 번호, 세션 설정값, app_current_user()."""
    row = (await fetch(session, "SELECT pg_backend_pid(), current_setting('app.user_id', true), app_current_user()"))[0]
    return row[0], row[1] or "", row[2]


async def my_favorites(session) -> list[str]:
    return [r[0] for r in await fetch(session, "SELECT festival_id FROM favorites ORDER BY 1")]


@pytest.fixture(scope="module", autouse=True)
def seed():
    """가상 축제 4건(공개 2, 비공개 1, 숨김 1)과 사용자 A·B, 각자 관심 축제 1건."""
    _session_module()
    with _admin() as db:
        # 018 공개 조건은 EV01 축제 분류까지 필요하다.
        db.execute("""INSERT INTO festivals (festival_id, title, region_code, category, source_class_level2, review_status, published_at) VALUES
            (%s,'시험 공개 축제 1','SEOUL','festival','EV01','approved',now()), (%s,'시험 공개 축제 2','BUSAN','festival','EV01','approved',now()),
            (%s,'시험 비공개 축제','SEOUL','festival','EV01','pending',NULL), (%s,'시험 숨김 축제','SEOUL','festival','EV01','hidden',now())""",
                   (PUB_A, PUB_B, UNPUBLISHED, HIDDEN))
        for uid, name in ((USER_A, "live-a"), (USER_B, "live-b")):
            db.execute("INSERT INTO users (user_id, email, password_hash) VALUES (%s, %s, '!')", (uid, f"{name}@example.invalid"))
            db.execute("INSERT INTO profiles (user_id, display_name) VALUES (%s, %s)", (uid, name))
        db.execute("INSERT INTO favorites (user_id, festival_id) VALUES (%s,%s), (%s,%s)", (USER_A, PUB_A, USER_B, PUB_B))
    yield
    with _admin() as db:
        db.execute("DELETE FROM favorites WHERE user_id IN (%s,%s)", (USER_A, USER_B))
        db.execute("DELETE FROM profiles WHERE user_id IN (%s,%s)", (USER_A, USER_B))
        db.execute("DELETE FROM users WHERE user_id IN (%s,%s)", (USER_A, USER_B))
        db.execute("DELETE FROM festivals WHERE festival_id IN (%s,%s,%s,%s)", (PUB_A, PUB_B, UNPUBLISHED, HIDDEN))


def admin_favorites(uid) -> list[str]:
    with _admin() as db:
        return [r[0] for r in db.execute("SELECT festival_id FROM favorites WHERE user_id=%s ORDER BY 1", (uid,))]


# ---------------------------------------------------------------- 2-1. 비회원 요청

def test_db01_guest_has_no_user_context():
    async def go(s):
        async with s.user_db_session() as session:
            return await state(session)
    _, setting, current = run_user(go)
    assert setting == "" and current is None


def test_db02_guest_sees_no_private_rows_and_cannot_save():
    async def go(s):
        async with s.user_db_session() as session:
            favs = await my_favorites(session)
            profiles = await fetch(session, "SELECT user_id FROM profiles")
        with pytest.raises(Exception) as caught:
            async with s.user_db_session() as session:
                await fetch(session, "INSERT INTO favorites (user_id, festival_id) VALUES (:u, :f) RETURNING 1", u=str(USER_A), f=PUB_B)
        return favs, profiles, caught.value
    favs, profiles, error = run_user(go)
    assert favs == [] and profiles == []          # 실제로는 A·B 관심 축제가 있음
    assert sqlstate(error) == PERMISSION_DENIED    # RLS가 저장을 막음
    assert admin_favorites(USER_A) == [PUB_A]


def test_db03_guest_sees_only_published_festivals():
    async def go(s):
        async with s.user_db_session() as session:
            return {r[0] for r in await fetch(session, "SELECT festival_id FROM festivals WHERE festival_id LIKE 'fst_LIVE%'")}
    assert run_user(go) == {PUB_A, PUB_B}         # 비공개·숨김 축제는 안 보임


@pytest.mark.parametrize("table", ["users", "refresh_tokens"])
def test_db04_app_role_cannot_read_account_tables(table):
    async def go(s):
        with pytest.raises(Exception) as caught:
            async with s.user_db_session() as session:
                await fetch(session, f"SELECT 1 FROM {table} LIMIT 1")
        return caught.value
    assert sqlstate(run_user(go)) == PERMISSION_DENIED


# ---------------------------------------------------------------- 2-2. 사용자 A → B 연결 재사용

def test_db05_same_connection_a_guest_b_each_sees_own():
    async def go(s):
        out = []
        for uid in (USER_A, None, USER_B, None):
            async with s.user_db_session(uid) as session:
                pid, setting, current = await state(session)
                out.append((pid, setting, current, await my_favorites(session)))
        return out
    out = run_user(go)
    assert len({row[0] for row in out}) == 1, "같은 연결을 재사용하지 않아 검증 무효"
    (_, sa, ca, fa), (_, sg, cg, fg), (_, sb, cb, fb), (_, sg2, cg2, fg2) = out
    assert (sa, ca, fa) == (str(USER_A), USER_A, [PUB_A])
    assert (sg, cg, fg) == ("", None, [])
    assert (sb, cb, fb) == (str(USER_B), USER_B, [PUB_B])
    assert (sg2, cg2, fg2) == ("", None, [])


def test_db06_user_b_cannot_read_change_or_delete_a_data():
    async def go(s):
        async with s.user_db_session(USER_B) as session:
            seen = await fetch(session, "SELECT festival_id FROM favorites WHERE user_id = :a", a=str(USER_A))
            deleted = await fetch(session, "DELETE FROM favorites WHERE user_id = :a RETURNING 1", a=str(USER_A))
            updated = await fetch(session, "UPDATE profiles SET display_name = '바꾼이름' WHERE user_id = :a RETURNING 1", a=str(USER_A))
        with pytest.raises(Exception) as caught:
            async with s.user_db_session(USER_B) as session:
                await fetch(session, "INSERT INTO favorites (user_id, festival_id) VALUES (:a, :f) RETURNING 1", a=str(USER_A), f=PUB_B)
        return seen, deleted, updated, caught.value
    seen, deleted, updated, error = run_user(go)
    assert seen == [] and deleted == [] and updated == []
    assert sqlstate(error) == PERMISSION_DENIED
    assert admin_favorites(USER_A) == [PUB_A]
    with _admin() as db:
        assert db.execute("SELECT display_name FROM profiles WHERE user_id=%s", (USER_A,)).fetchone()[0] == "live-a"


def test_db07_concurrent_a_and_b_requests_do_not_mix():
    async def one(s, uid):
        async with s.user_db_session(uid) as session:
            await fetch(session, "SELECT pg_sleep(0.02)")
            _, setting, current = await state(session)
            return uid, setting, current, await my_favorites(session)

    async def go(s):
        return await asyncio.gather(*(one(s, USER_A if i % 2 else USER_B) for i in range(20)))

    for uid, setting, current, favs in run_user(go):
        assert setting == str(uid) and current == uid
        assert favs == ([PUB_A] if uid == USER_A else [PUB_B])


# ---------------------------------------------------------------- 2-3. 실패 시 롤백·연결 정리

def test_db10_exception_after_save_rolls_back():
    async def go(s):
        with pytest.raises(RuntimeError):
            async with s.user_db_session(USER_A) as session:
                await fetch(session, "INSERT INTO favorites (user_id, festival_id) VALUES (:u, :f) RETURNING 1", u=str(USER_A), f=PUB_B)
                raise RuntimeError("저장 직후 요청 실패")
    run_user(go)
    assert admin_favorites(USER_A) == [PUB_A]


def test_db11_after_constraint_error_same_connection_is_clean():
    async def go(s):
        async with s.user_db_session() as session:
            pid_before = (await state(session))[0]
        with pytest.raises(Exception) as caught:
            async with s.user_db_session(USER_A) as session:   # 이미 있는 관심 축제 → 기본키 위반
                await fetch(session, "INSERT INTO favorites (user_id, festival_id) VALUES (:u, :f) RETURNING 1", u=str(USER_A), f=PUB_A)
        async with s.user_db_session() as session:
            after = await state(session)
            festivals = await fetch(session, "SELECT count(*) FROM festivals WHERE festival_id LIKE 'fst_LIVE%'")
        return pid_before, caught.value, after, festivals[0][0]
    pid_before, error, (pid_after, setting, current), count = run_user(go)
    assert sqlstate(error) == "23505"               # 제약 위반
    assert pid_after == pid_before, "같은 연결 재사용이 아니어서 검증 무효"
    assert setting == "" and current is None and count == 2


def test_db12_cancelled_request_returns_connection_without_open_transaction():
    async def go(s):
        async def slow():
            async with s.user_db_session(USER_A) as session:
                await fetch(session, "SELECT pg_sleep(5)")
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await asyncio.wait_for(slow(), timeout=0.5)
        await asyncio.sleep(0.5)
        async with s.user_db_session() as session:
            return await state(session)
    _, setting, current = run_user(go)
    assert setting == "" and current is None
    with _admin() as db:
        stuck = db.execute("SELECT count(*) FROM pg_stat_activity WHERE usename = %s AND state LIKE 'idle in transaction%%'",
                           (os.environ["DB_USER_USERNAME"],)).fetchone()[0]
    assert stuck == 0


@pytest.mark.skipif(not os.environ.get("DB_TEST_CONTAINER") or not shutil.which("docker"),
                    reason="DB_TEST_CONTAINER(일회용 Docker 컨테이너)가 있어야 재시작 시험 가능")
def test_db13_first_request_after_db_restart_succeeds():
    container = os.environ["DB_TEST_CONTAINER"]

    async def go(s):
        async with s.user_db_session() as session:
            await state(session)                       # 풀에 연결을 하나 만들어 둠
        subprocess.run(["docker", "restart", container], check=True, capture_output=True)
        for _ in range(60):
            ready = subprocess.run(["docker", "exec", container, "pg_isready", "-U", "postgres"], capture_output=True)
            if ready.returncode == 0:
                break
            await asyncio.sleep(1)
        await asyncio.sleep(1)
        async with s.user_db_session(USER_A) as session:   # 끊긴 연결을 버리고 새로 연결해야 함
            return await my_favorites(session)
    assert run_user(go) == [PUB_A]


def test_db14_pool_limits_and_exhaustion_error_are_recorded():
    """풀이 가득 찼을 때의 API 응답 모양은 미정이라, 현재 설정과 오류 종류만 기록한다."""
    from sqlalchemy import exc, text
    from sqlalchemy.ext.asyncio import create_async_engine
    from backend.shared.config import load_db_settings
    from backend.shared.db.connection import _connection_url, create_user_engine

    async def go():
        engine = create_user_engine(load_db_settings())
        pool = engine.sync_engine.pool
        limits = (pool.size(), pool._max_overflow, pool._timeout)
        await engine.dispose()
        small = create_async_engine(_connection_url(load_db_settings(), "user"), pool_size=1, max_overflow=0, pool_timeout=1)
        try:
            async with small.connect() as first:
                await first.execute(text("SELECT 1"))
                started = time.monotonic()
                with pytest.raises(exc.TimeoutError):
                    async with small.connect():
                        pass
                waited = time.monotonic() - started
        finally:
            await small.dispose()
        return limits, waited
    (size, overflow, timeout), waited = asyncio.run(go())
    print(f"\n[DB-14 기록] 사용자 풀 기본값: pool_size={size}, max_overflow={overflow}, pool_timeout={timeout}s "
          f"→ 동시 {size + overflow}개 초과 시 {timeout}초 대기 후 sqlalchemy.exc.TimeoutError")
    assert (size, overflow, timeout) == (5, 10, 30.0)  # 바뀌면 기록을 갱신해야 함
    assert 0.9 <= waited < 3


# ---------------------------------------------------------------- 2-4. 계정 분리

def test_db15_request_and_internal_sessions_use_separate_roles():
    async def go(s):
        async with s.user_db_session() as session:
            return (await fetch(session, "SELECT current_user"))[0][0]
    user_role = run_user(go)
    s = _session_module()
    s._service_engine.cache_clear()
    try:
        from sqlalchemy import text
        with s.service_db_session() as session:
            service_role = session.execute(text("SELECT current_user")).scalar_one()
    finally:
        s._service_engine().dispose()
        s._service_engine.cache_clear()
    assert user_role == os.environ["DB_USER_USERNAME"] == "noldaga_app"
    assert service_role == os.environ["DB_SERVICE_USERNAME"] == "noldaga_service"


def test_db16_only_service_role_bypasses_rls():
    with _admin() as db:
        rows = dict(db.execute("SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname IN ('noldaga_app','noldaga_service')").fetchall())
    assert rows == {"noldaga_app": False, "noldaga_service": True}


@pytest.mark.parametrize(("table", "sql"), [
    ("route_requests", "INSERT INTO route_requests (route_request_id) VALUES ('rr_LIVETEST01')"),
    ("incident_logs", "INSERT INTO incident_logs (incident_id) VALUES ('inc_LIVETEST01')"),
])
def test_db17_app_role_cannot_write_route_or_incident_tables(table, sql):
    async def go(s):
        with pytest.raises(Exception) as caught:
            async with s.user_db_session() as session:
                await fetch(session, sql + " RETURNING 1")
        return caught.value
    assert sqlstate(run_user(go)) == PERMISSION_DENIED
    # 실제 쓰기는 테이블 권한과 RLS 둘 중 하나만 있어도 막힌다. 권한이 실수로 생기면 바로 알 수 있게 권한 자체도 확인한다.
    with _admin() as db:
        granted = db.execute(
            "SELECT has_table_privilege(%s, %s, 'INSERT'), has_table_privilege(%s, %s, 'UPDATE'), "
            "has_table_privilege(%s, %s, 'DELETE')",
            (os.environ["DB_USER_USERNAME"], f"public.{table}") * 3,
        ).fetchone()
    assert granted == (False, False, False), f"앱 계정에 {table} 쓰기 권한이 있음: {granted}"
