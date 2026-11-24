import os
import sys
from pathlib import Path

import pytest

# API는 api.*를, 공통 DB 시험은 backend.*를 사용한다.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
for path in (_BACKEND_DIR.parent, _BACKEND_DIR):
    sys.path.insert(0, str(path))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "db: 일회용 PostgreSQL DB를 사용하는 시험")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if not os.environ.get("TEST_DB_URL"):
        skip = pytest.mark.skip(reason="일회용 DB의 TEST_DB_URL이 없습니다.")
        for item in items:
            if item.get_closest_marker("db"):
                item.add_marker(skip)
