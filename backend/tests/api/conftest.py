import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def pytest_configure() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(autouse=True)
def reset_mock_state() -> Iterator[None]:
    from api.mocks.store import reset_store

    reset_store()
    yield
    reset_store()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client
