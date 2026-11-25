from datetime import datetime, timedelta, timezone
from uuid import uuid4

from api.jobs import scheduler
from api.services import withdrawal_log


def test_append_entries_and_prune_keep_only_ids_and_times(monkeypatch, tmp_path):
    path = tmp_path / "nested" / "withdrawals.jsonl"
    monkeypatch.setenv("WITHDRAWAL_LOG_PATH", str(path))
    monkeypatch.setenv("WITHDRAWAL_LOG_KEEP_DAYS", "8")
    now = datetime(2026, 11, 25, 6, tzinfo=timezone.utc)
    old, recent = uuid4(), uuid4()
    assert withdrawal_log.append(old, now - timedelta(days=9))
    assert withdrawal_log.append(recent, now - timedelta(days=1))
    with path.open("a") as handle:
        handle.write("not json\n")
    assert [user for user, _ in withdrawal_log.entries()] == [old, recent]
    assert "@" not in path.read_text()  # 이메일 등 개인정보 없음
    assert withdrawal_log.prune(now) == 1
    assert [user for user, _ in withdrawal_log.entries()] == [recent]
    assert "not json" in path.read_text()  # 읽을 수 없는 줄은 사람이 확인하도록 남김


def test_missing_file_and_write_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("WITHDRAWAL_LOG_PATH", str(tmp_path / "none.jsonl"))
    assert withdrawal_log.entries() == [] and withdrawal_log.prune(datetime.now(timezone.utc)) == 0
    blocker = tmp_path / "file"
    blocker.write_text("")
    monkeypatch.setenv("WITHDRAWAL_LOG_PATH", str(blocker / "child.jsonl"))
    assert withdrawal_log.append(uuid4(), datetime.now(timezone.utc)) is False


def test_prune_job_is_daily():
    job = next(job for job in scheduler.JOBS if job.name == "prune_withdrawal_log")
    assert job.daily
