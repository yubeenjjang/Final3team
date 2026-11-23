import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

import pytest

from api.providers.quota import QuotaGuard


@pytest.fixture(autouse=True)
def configure_quota(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTE_QUOTA_FILE", str(tmp_path / "quota.json"))
    for env in ("ROUTE_TMAP_DAILY_LIMIT", "ROUTE_KAKAO_DAILY_LIMIT", "ROUTE_KAKAO_LOCAL_DAILY_LIMIT"):
        monkeypatch.delenv(env, raising=False)


def test_P8_limit_persists_and_counters_are_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTE_TMAP_DAILY_LIMIT", "2")
    monkeypatch.setenv("ROUTE_KAKAO_LOCAL_DAILY_LIMIT", "1")
    guard = QuotaGuard()
    assert [guard.try_acquire("tmap") for _ in range(3)] == [True, True, False]
    another = QuotaGuard()
    assert another.try_acquire("tmap") is False
    assert another.try_acquire("kakao") is True
    assert another.try_acquire("kakao_local") is True
    assert another.try_acquire("kakao_local") is False
    assert guard.status() == {
        "tmap": {"used": 2, "limit": 2},
        "kakao": {"used": 1, "limit": 1000},
        "kakao_local": {"used": 1, "limit": 1},
    }


def test_P8_defaults() -> None:
    assert QuotaGuard().status() == {
        "tmap": {"used": 0, "limit": 10},
        "kakao": {"used": 0, "limit": 1000},
        "kakao_local": {"used": 0, "limit": 1000},
    }


def test_P8_resets_at_kst_midnight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTE_KAKAO_DAILY_LIMIT", "1")
    now = datetime(2026, 11, 22, 14, 59, 59, tzinfo=timezone.utc)
    guard = QuotaGuard(now=lambda: now)
    assert guard.try_acquire("kakao") is True
    assert guard.try_acquire("kakao") is False
    now += timedelta(seconds=1)
    assert guard.status()["kakao"] == {"used": 0, "limit": 1}
    assert guard.try_acquire("kakao") is True
    assert guard.status()["kakao"] == {"used": 1, "limit": 1}


def test_P8_twenty_concurrent_acquisitions_use_exact_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTE_TMAP_DAILY_LIMIT", "7")
    barrier = Barrier(20, timeout=10)

    def acquire() -> bool:
        guard = QuotaGuard()
        barrier.wait()
        return guard.try_acquire("tmap")

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(acquire) for _ in range(20)]
        results = [future.result() for future in futures]
    assert sum(results) == 7
    assert QuotaGuard().status()["tmap"] == {"used": 7, "limit": 7}


def test_P8_warns_once_when_usage_exceeds_eighty_percent(caplog: pytest.LogCaptureFixture) -> None:
    guard = QuotaGuard()
    with caplog.at_level(logging.WARNING, logger="api.providers.quota"):
        assert all(guard.try_acquire("tmap") for _ in range(8))
        assert not caplog.records
        assert guard.try_acquire("tmap") is True
        assert QuotaGuard().try_acquire("tmap") is True
        assert guard.try_acquire("tmap") is False
    assert len(caplog.records) == 1
    assert "tmap" in caplog.text
