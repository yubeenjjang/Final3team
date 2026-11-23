import pytest

from api.ingestion.db import IngestionDBError, create_ingestion_engine

TEST_PASSWORD = "TEST_KEY_DO_NOT_USE"


@pytest.mark.parametrize(
    ("settings", "expected"),
    [({}, ("127.0.0.1", 5432, "noldaga")),
     ({"DB_HOST": "test.invalid", "DB_PORT": "55432", "DB_NAME": "test_db"},
      ("test.invalid", 55432, "test_db"))],
)
def test_I9_engine_reads_service_settings_and_hides_password(
    monkeypatch: pytest.MonkeyPatch,
    settings: dict[str, str],
    expected: tuple[str, int, str],
) -> None:
    for name in ("DB_HOST", "DB_PORT", "DB_NAME"):
        monkeypatch.delenv(name, raising=False)
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DB_SERVICE_PASSWORD", TEST_PASSWORD)
    engine = create_ingestion_engine()
    try:
        url = engine.url
        assert (url.host, url.port, url.database) == expected
        assert url.drivername == "postgresql+psycopg"
        assert url.username == "noldaga_service"
        assert url.password == TEST_PASSWORD
        assert TEST_PASSWORD not in repr(url)
        assert TEST_PASSWORD not in str(url)
        assert engine.hide_parameters
    finally:
        engine.dispose()


def test_I9_missing_password_has_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_SERVICE_PASSWORD", raising=False)
    with pytest.raises(IngestionDBError, match="DB_SERVICE_PASSWORD"):
        create_ingestion_engine()
