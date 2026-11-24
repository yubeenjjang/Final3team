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


@pytest.fixture(autouse=True)
def approve_crowd_area_for_log_test(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if (
        request.node.originalname != "test_a3_requests_keep_ids_and_status_without_raw_inputs"
        or request.node.callspec.params.get("mode") != "real"
    ):
        return
    from api.services import seoul_crowd

    # A3의 가짜 서울시 응답에 대응하는 시험용 승인입니다.
    monkeypatch.setattr(
        seoul_crowd, "approved_area_codes",
        lambda festival: {"POI009"} if festival.festival_id == "fst_000001" else set(),
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client
