import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "db: 일회용 PostgreSQL DB를 사용하는 시험")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if not os.environ.get("TEST_DB_URL"):
        skip = pytest.mark.skip(reason="일회용 DB의 TEST_DB_URL이 없습니다.")
        for item in items:
            if item.get_closest_marker("db"):
                item.add_marker(skip)
