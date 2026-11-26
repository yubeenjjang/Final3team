"""DB 없이도 사용자 문맥의 설정 범위를 확인하는 세션 시험."""

import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from backend.shared.config import load_db_settings
from backend.shared.db.connection import create_user_engine
from backend.shared.db import session as db_sessions
from backend.shared.db.session import service_db_session, user_db_session


class _Transaction:
    def __init__(self) -> None:
        self.error = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        self.error = error_type


class _Session:
    def __init__(self) -> None:
        self.statements = []
        self.transactions = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        return None

    def begin(self):
        transaction = _Transaction()
        self.transactions.append(transaction)
        return transaction

    async def execute(self, statement, parameters):
        self.statements.append((str(statement), parameters))


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_context_is_only_set_for_authenticated_request(self):
        # 같은 세션을 재사용해 A 뒤의 비회원·B 요청을 흉내 냅니다.
        session = _Session()
        first_user, second_user = uuid4(), uuid4()
        with patch("backend.shared.db.session._user_engine"), patch(
            "backend.shared.db.session.async_sessionmaker",
            return_value=lambda: session,
        ):
            async with user_db_session(first_user):
                pass
            async with user_db_session():
                pass
            async with user_db_session(second_user):
                pass

        self.assertEqual(len(session.transactions), 3)
        self.assertEqual(len(session.statements), 2)
        self.assertTrue(all("set_config('app.user_id', :user_id, true)" in sql for sql, _ in session.statements))
        self.assertEqual(
            [params["user_id"] for _, params in session.statements],
            [str(first_user), str(second_user)],
        )

    async def test_exception_reaches_transaction_for_rollback(self):
        session = _Session()
        with patch("backend.shared.db.session._user_engine"), patch(
            "backend.shared.db.session.async_sessionmaker",
            return_value=lambda: session,
        ):
            with self.assertRaises(RuntimeError):
                async with user_db_session():
                    raise RuntimeError("query failed")

        self.assertIs(session.transactions[0].error, RuntimeError)


@unittest.skipUnless(os.environ.get("DB_LIVE_TEST") == "1", "실제 테스트 DB가 필요합니다")
class LiveSessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        # 공용 풀의 열린 연결은 뒤의 통합 시험이 원본 DB를 복제하지 못하게 한다.
        if db_sessions._user_engine.cache_info().currsize:
            await db_sessions._user_engine().dispose()
            db_sessions._user_engine.cache_clear()
        if db_sessions._service_engine.cache_info().currsize:
            db_sessions._service_engine().dispose()
            db_sessions._service_engine.cache_clear()

    async def test_committed_session_setting_is_reset_on_pool_return(self):
        """DB-09: 커밋된 일반 세션 설정도 다음 요청에 남지 않아야 합니다."""
        engine = create_user_engine(load_db_settings())
        user_id = str(uuid4())
        try:
            async with engine.connect() as connection:
                first_pid = (await connection.execute(text("SELECT pg_backend_pid()"))).scalar_one()
                await connection.execute(
                    text("SELECT set_config('app.user_id', :user_id, :local)"),
                    {"user_id": user_id, "local": False},
                )
                await connection.commit()
            async with engine.connect() as connection:
                second_pid, remaining = (await connection.execute(text(
                    "SELECT pg_backend_pid(), current_setting('app.user_id', true)"
                ))).one()
        finally:
            await engine.dispose()
        self.assertEqual(first_pid, second_pid)
        self.assertIn(remaining, (None, ""))

    async def test_user_and_service_use_separate_roles(self):
        async with user_db_session() as session:
            user_role = (await session.execute(text("SELECT current_user"))).scalar_one()
        with service_db_session() as session:
            service_role = session.execute(text("SELECT current_user")).scalar_one()
        self.assertEqual(user_role, "noldaga_app")
        self.assertEqual(service_role, "noldaga_service")

    async def test_same_connection_does_not_keep_previous_user(self):
        """실제 PostgreSQL 풀에서 A → 비회원 → B의 문맥 누출을 확인합니다."""
        first_user, second_user = uuid4(), uuid4()
        observed = []
        for user_id in (first_user, None, second_user):
            async with user_db_session(user_id) as session:
                observed.append(
                    (await session.execute(
                        text("SELECT pg_backend_pid(), current_setting('app.user_id', true)")
                    )).one()
                )

        self.assertEqual(observed[0][0], observed[1][0])
        self.assertEqual(observed[1][0], observed[2][0])
        self.assertEqual(observed[0][1], str(first_user))
        self.assertIn(observed[1][1], (None, ""))
        self.assertEqual(observed[2][1], str(second_user))

    async def test_failed_request_rolls_back_user_context(self):
        user_id = uuid4()
        with self.assertRaises(RuntimeError):
            async with user_db_session(user_id) as session:
                await session.execute(text("SELECT current_setting('app.user_id', true)"))
                raise RuntimeError("request failed")
        async with user_db_session() as session:
            remaining = (await session.execute(text("SELECT current_setting('app.user_id', true)"))).scalar_one()
        self.assertIn(remaining, (None, ""))
