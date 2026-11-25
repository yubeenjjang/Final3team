import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from api.ingestion.db import create_ingestion_engine
from shared.db import session as sessions


@pytest.fixture(autouse=True)
def clear_geocoding_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)


@pytest.fixture
def db_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    url = os.environ.get("TEST_DB_URL")
    if not url:
        pytest.skip("일회용 DB의 TEST_DB_URL이 없습니다.")
    engine = create_ingestion_engine(url)
    try:
        owner_url = os.environ.get("TEST_DB_MIGRATION_URL")
        if owner_url:
            # 다른 시험(공지·동행·경로 등)이 축제를 참조한 행을 남길 수 있어 소유자 계정으로 함께 비운다.
            owner = create_ingestion_engine(owner_url)
            try:
                with owner.begin() as connection:
                    connection.execute(text("TRUNCATE festivals, ingestion_jobs CASCADE"))
            finally:
                owner.dispose()
        else:
            with engine.begin() as connection:
                # 수집 계정(noldaga_service)에는 TRUNCATE 권한이 없어서 DELETE로 비운다(외래 키 순서).
                for table in (
                    "festival_review_queue",
                    "festival_change_history",
                    "festival_sources",
                    "festivals",
                    "ingestion_jobs",
                ):
                    connection.execute(text(f"DELETE FROM {table}"))
        monkeypatch.setattr(sessions, "_service_engine", lambda: engine)
        yield engine
    finally:
        engine.dispose()
