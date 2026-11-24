import json
import re
import sqlite3
from contextlib import closing, nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.jobs import purge_route_results
from api.repositories.route_store import RouteStore
from tests.routes.test_p9_real_routes import Clock


@pytest.mark.parametrize("dry_run", [False, True])
def test_purge_counts_or_updates_with_same_cutoff(dry_run):
    now = Clock().now
    session = Mock()
    session.execute.side_effect = [
        SimpleNamespace(scalar_one=lambda: True),
        SimpleNamespace(scalar_one=lambda: 5, rowcount=5),
    ]

    assert RouteStore(lambda: nullcontext(session)).purge_expired(now, dry_run=dry_run) == 5

    lock, sweep = session.execute.call_args_list
    assert "pg_try_advisory_xact_lock" in str(lock.args[0])
    sql, params = sweep.args
    assert "provider = 'tmap'" in str(sql)
    assert "purged_at IS NULL AND queried_at <= :cutoff" in str(sql)
    assert params["cutoff"] == now - timedelta(hours=23)
    if dry_run:
        assert str(sql).startswith("SELECT count(*)")
        assert "now" not in params
    else:
        assert str(sql).lstrip().startswith("UPDATE")
        assert params["now"] == now


@pytest.mark.parametrize(("age", "expected"), [
    (timedelta(hours=23, microseconds=-1), 0),
    (timedelta(hours=23), 1),
    (timedelta(hours=23, microseconds=1), 1),
])
def test_purge_dry_run_selects_results_at_23h_boundary(age, expected):
    now = Clock().now
    with closing(sqlite3.connect(":memory:")) as db:
        store = _sqlite_store(db)
        db.execute("INSERT INTO public.route_results (provider, queried_at) VALUES ('tmap', ?)",
                   ((now - age).isoformat(timespec="microseconds"),))
        assert store.purge_expired(now, dry_run=True) == expected


def _sqlite_store(db):
    db.executescript("""
        ATTACH DATABASE ':memory:' AS public;
        CREATE TABLE public.route_results (
            id TEXT, provider TEXT, queried_at TEXT, purged_at TEXT,
            candidates TEXT, evidence TEXT DEFAULT '{}', provider_ref TEXT,
            route_hash TEXT DEFAULT '', score_version TEXT, cache_key TEXT,
            source_type TEXT, validity_check TEXT
        );
    """)

    def execute(statement, params=None):
        if params is None:  # PostgreSQL advisory lock
            return SimpleNamespace(scalar_one=lambda: True)
        values = {name: value.isoformat(timespec="microseconds") for name, value in params.items()}
        sql = str(statement).replace("CAST('{}' AS jsonb)", "CAST('{}' AS text)")
        cursor = db.execute(sql, values)
        return SimpleNamespace(scalar_one=lambda: cursor.fetchone()[0], rowcount=cursor.rowcount)

    return RouteStore(lambda: nullcontext(SimpleNamespace(execute=execute)))


def test_P25_purge_clears_tmap_derived_fields_and_keeps_original_deletion_time():
    now = Clock().now
    cutoff = (now - timedelta(hours=23)).isoformat(timespec="microseconds")
    recent = (now - timedelta(hours=22)).isoformat(timespec="microseconds")
    previous_purge = (now - timedelta(hours=1)).isoformat(timespec="microseconds")
    candidates = json.dumps([{"duration_min": 16, "fare_krw": 1550, "transfers": 1, "summary": "합성 경로"}])
    with closing(sqlite3.connect(":memory:")) as db:
        store = _sqlite_store(db)
        db.executemany("""
            INSERT INTO public.route_results VALUES
                (?, ?, ?, ?, ?, '{"source":true}', 'ref', 'derived-hash', 'score-v1', 'key', 'cache', '{"ok":true}')
        """, [
            ("expired", "tmap", cutoff, None, candidates),
            ("legacy", "tmap", cutoff, previous_purge, None),
            ("recent", "tmap", recent, None, candidates),
            ("kakao", "kakao", cutoff, None, None),
        ])
        db.execute("""
            UPDATE public.route_results
            SET evidence = '{}', provider_ref = NULL, validity_check = '{}'
            WHERE id = 'legacy'
        """)
        assert store.purge_expired(now, dry_run=True) == 2
        assert store.purge_expired(now) == 2
        assert store.purge_expired(now) == 0
        rows = {row[0]: row[1:] for row in db.execute("SELECT * FROM public.route_results")}
        cleared = (None, "{}", None, "", None, None, "cache", "{}")
        assert rows["expired"] == ("tmap", cutoff, now.isoformat(timespec="microseconds"), *cleared)
        assert rows["legacy"] == ("tmap", cutoff, previous_purge, *cleared)
        assert rows["recent"][3] == candidates
        assert rows["kakao"][6] == "derived-hash"


def test_purge_does_not_run_while_lock_is_held():
    session = Mock()
    session.execute.return_value.scalar_one.return_value = False

    assert RouteStore(lambda: nullcontext(session)).purge_expired(Clock().now) is None
    assert session.execute.call_count == 1


@pytest.mark.parametrize(("args", "result", "code", "stdout", "stderr"), [
    ([], 5, 0, r"purge_route_results status=ok mode=purge processed=5 duration_ms=\d+\n", ""),
    (["--dry-run"], 5, 0, "5\n", ""),
    ([], None, 3, "", r"purge_route_results status=locked mode=purge processed=0 duration_ms=\d+\n"),
    (["--dry-run"], RuntimeError("synthetic sensitive value"), 1, "",
     r"purge_route_results status=error mode=dry-run processed=unknown duration_ms=\d+\n"),
])
def test_purge_command_output_and_exit_code(monkeypatch, capsys, args, result, code, stdout, stderr):
    monkeypatch.delenv("ROUTE_PURGE_AFTER_HOURS", raising=False)
    store = Mock()
    if isinstance(result, Exception):
        store.purge_expired.side_effect = result
    else:
        store.purge_expired.return_value = result
    monkeypatch.setattr(purge_route_results, "RouteStore", lambda: store)

    assert purge_route_results.main(args) == code
    assert store.purge_expired.call_args.kwargs == {"after_hours": 23, "dry_run": bool(args)}
    output = capsys.readouterr()
    assert re.fullmatch(stdout, output.out)
    assert re.fullmatch(stderr, output.err)


@pytest.mark.parametrize("hours", [1, 12, 23])
def test_purge_command_passes_configured_hours(monkeypatch, hours):
    monkeypatch.setenv("ROUTE_PURGE_AFTER_HOURS", str(hours))
    store = Mock()
    monkeypatch.setattr(purge_route_results, "RouteStore", lambda: store)

    assert purge_route_results.main(["--dry-run"]) == 0
    assert store.purge_expired.call_args.kwargs == {"after_hours": hours, "dry_run": True}


@pytest.mark.parametrize("value", ["-1", "0", "24", "1.5", "", "synthetic-invalid"])
def test_purge_command_rejects_invalid_hours_before_opening_db(monkeypatch, capsys, value):
    monkeypatch.setenv("ROUTE_PURGE_AFTER_HOURS", value)
    store_factory = Mock()
    monkeypatch.setattr(purge_route_results, "RouteStore", store_factory)

    with pytest.raises(SystemExit) as error:
        purge_route_results.main([])

    assert error.value.code == 2
    store_factory.assert_not_called()
    assert "ROUTE_PURGE_AFTER_HOURS는 1~23 사이의 정수여야 합니다." in capsys.readouterr().err
