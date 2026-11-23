"""DB 없이도 사용자 문맥의 설정 범위를 확인하는 세션 시험."""

import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from backend.shared.db.session import user_db_session


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
