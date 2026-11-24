import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from api.ingestion.db import create_ingestion_engine


@pytest.fixture(autouse=True)
def clear_geocoding_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)


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
                "festival_review_queue",
                "festival_change_history",
                "festival_sources",
                "festivals",
                "ingestion_jobs",
            ):
                connection.execute(text(f"DELETE FROM {table}"))
        yield engine
    finally:
        engine.dispose()
