import json
from contextlib import contextmanager, nullcontext
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from api.ingestion.festivals import collect
from api.ingestion.festivals.store import JobResult
from api.jobs import locks, retention, scheduler


@pytest.mark.parametrize(("utc", "jobs"), [
    ("2026-12-31T20:59:59+00:00", ["purge_route_results", "maintain_companions"]),
    ("2026-12-31T21:00:00+00:00", ["purge_route_results", "maintain_companions", "retention", "prune_withdrawal_log", "collect_festivals"]),
    ("2026-12-31T21:17:00+00:00", ["purge_route_results", "maintain_companions", "retention", "prune_withdrawal_log", "collect_festivals"]),
])
def test_due_slots_in_korea(monkeypatch, capsys, utc, jobs):
    run = Mock(return_value={"processed": 0})
    monkeypatch.setattr(scheduler, "_run_once", run)
    assert scheduler.run_due(datetime.fromisoformat(utc)) == 0
    calls = [call.args for call in run.call_args_list]
    assert [job.name for job, _, _ in calls] == jobs
    for job, slot, now in calls:
        assert slot.date() == date(2027, 1, 1)
        assert slot.utcoffset() == timedelta(hours=9)
        assert slot.minute == slot.second == 0
        assert slot.hour == (6 if job.daily else now.hour)
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.splitlines()) == len(jobs)


@pytest.mark.parametrize(("exception", "code", "status"), [
    (RuntimeError("synthetic sensitive text"), 1, "error"),
    (scheduler.JobLocked(), 3, "locked"),
])
def test_failure_is_summarized_and_other_jobs_continue(monkeypatch, capsys, exception, code, status):
    run = Mock(side_effect=[exception, {}, None, {"deleted": 0}, {"scanned": 5}])
    monkeypatch.setattr(scheduler, "_run_once", run)
    assert scheduler.run_due(datetime(2027, 1, 1, 0, tzinfo=timezone.utc)) == code
    assert run.call_count == 5
    output = capsys.readouterr()
    assert len(output.err.splitlines()) == 1
    assert f"purge_route_results status={status}" in output.err
    assert "synthetic sensitive text" not in output.err
    assert "retention status=already_done" in output.out
    assert "scanned=5" in output.out


def test_job_records_only_a_completed_slot_and_can_retry(monkeypatch):
    db = Mock()
    run = Mock(side_effect=[ValueError, {"processed": 3}])
    db.scalar.side_effect = [True, None, True, None, True, datetime(2027, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(scheduler, "service_db_session", lambda: nullcontext(db))
    job = scheduler.Job("test_job", locks.RETENTION, run)
    slot = now = datetime(2027, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        scheduler._run_once(job, slot, now)
    db.execute.assert_not_called()
    assert scheduler._run_once(job, slot, now) == {"processed": 3}
    assert scheduler._run_once(job, slot, now) is None
    assert run.call_count == 2
    assert db.execute.call_args.args[1] == {"name": "test_job", "slot": slot}


def test_commit_failure_does_not_emit_success(monkeypatch, capsys):
    @contextmanager
    def broken_commit():
        db = Mock()
        db.scalar.side_effect = [True, None]
        yield db
        raise RuntimeError("synthetic sensitive text")

    monkeypatch.setattr(scheduler, "JOBS", (scheduler.Job("test_job", locks.RETENTION, Mock(return_value={})),))
    monkeypatch.setattr(scheduler, "service_db_session", broken_commit)
    assert scheduler.run_due(datetime(2027, 1, 1, tzinfo=timezone.utc)) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.startswith("test_job status=error ")
    assert "synthetic sensitive text" not in output.err


def test_collect_uses_current_korea_year_and_service_engine(monkeypatch):
    db = Mock()
    collect_db = Mock(return_value=JobResult("internal-id", "success", 4, 1, 2, 0))
    monkeypatch.setattr(collect, "collect_to_db", collect_db)
    now = datetime.fromisoformat("2027-01-01T06:00:00+09:00")
    assert scheduler._collect_festivals(db, now) == {"scanned": 4, "inserted": 1, "updated": 2, "rejected": 0}
    collect_db.assert_called_once_with(date(2027, 1, 1), locked_engine=db.get_bind.return_value)


def test_scheduled_festival_collection_uses_normal_db_path_without_artifacts_or_raw_log(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    store = Mock()
    store.finish_job.return_value = JobResult("internal-id", "failed", 0, 0, 0, 0)
    factory = Mock(return_value=store)
    monkeypatch.setattr(collect, "FestivalStore", factory)
    engine = Mock()

    with pytest.raises(RuntimeError):
        collect.collect_to_db(date(2027, 1, 1), locked_engine=engine)

    factory.assert_called_once_with(engine)
    assert store.finish_job.call_args.kwargs["failed"] is True
    assert store.finish_job.call_args.args[2] == [{"content_id": None, "stage": "searchFestival2", "code": "NO_KEY"}]
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr() == ("", "")


def test_festival_cli_uses_same_advisory_lock_before_opening_output(monkeypatch, tmp_path, capsys):
    engine = Mock()
    lock = Mock()
    lock.scalar.return_value = False
    lock.get_bind.return_value = engine
    monkeypatch.setattr(collect, "service_db_session", lambda: nullcontext(lock))
    client = Mock()
    monkeypatch.setattr(collect, "TourApiClient", client)
    out = tmp_path / "collect"
    assert collect.main(["--since", "2027-01-01", "--out", str(out), "--db"]) == 3
    lock.scalar.assert_called_once_with(locks.FESTIVALS)
    engine.dispose.assert_not_called()
    client.assert_not_called()
    assert not out.exists()
    assert len(capsys.readouterr().err.splitlines()) == 1


def test_festival_cli_reports_shared_configuration_failure(monkeypatch, tmp_path, capsys):
    session = Mock(side_effect=ValueError("fixture DB configuration"))
    monkeypatch.setattr(collect, "service_db_session", session)
    out = tmp_path / "collect"
    assert collect.main(["--since", "2027-01-01", "--out", str(out), "--db"]) == 1
    report = json.loads((out / "report.json").read_text())
    assert report["db"] is None
    assert report["errors"] == [{"content_id": None, "stage": "db_start", "code": "DB_ERROR"}]
    assert "fixture DB configuration" not in capsys.readouterr().err


def test_festival_partial_status_fails_scheduled_slot(monkeypatch):
    monkeypatch.setattr(collect, "_collect", Mock(return_value=(0, JobResult("internal-id", "partial", 4, 1, 1, 1))))
    with pytest.raises(RuntimeError):
        collect.collect_to_db(date(2027, 1, 1), locked_engine=Mock())


@pytest.mark.parametrize("installed", [0, 1, 2])
def test_checkpoint_tables_must_be_fully_installed_or_absent(installed):
    db = Mock()
    db.execute.return_value.scalar_one.return_value = installed
    if installed == 0:
        assert retention._delete_expired_checkpoints(db, datetime.now(timezone.utc)) == 0
    else:
        with pytest.raises(RuntimeError):
            retention._delete_expired_checkpoints(db, datetime.now(timezone.utc))
    db.execute.assert_called_once()
