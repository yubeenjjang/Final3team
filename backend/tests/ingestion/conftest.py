import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from api.ingestion.db import create_ingestion_engine


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "db: 일회용 PostgreSQL DB를 사용하는 시험")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if not os.environ.get("TEST_DB_URL"):
        skip = pytest.mark.skip(reason="일회용 DB의 TEST_DB_URL이 없습니다.")
        for item in items:
            if item.get_closest_marker("db"):
                item.add_marker(skip)


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DB_URL")
    if not url:
        pytest.skip("일회용 DB의 TEST_DB_URL이 없습니다.")
    engine = create_ingestion_engine(url)
    try:
        with engine.begin() as connection:
            # 수집 계정(noldaga_service)에는 TRUNCATE 권한이 없어서 DELETE로 비운다(외래 키 순서).
            for table in (
                "festival_change_history",
                "festival_sources",
                "festivals",
                "ingestion_jobs",
            ):
                connection.execute(text(f"DELETE FROM {table}"))
        yield engine
    finally:
        engine.dispose()
