from backend.tests.w96_internal_probe import run_probe


def test_w96_internal_probe_reports_cache_and_valid_completion():
    result = run_probe(count=2, concurrency=2, delay_s=0.01)
    scenarios = result["scenarios"]
    assert len(scenarios) == 8
    assert all(row["valid_completed"] == 2 and row["errors"] == 0
               and row["rejected"] == 0 and row["unfinished"] == 0 for row in scenarios)
    assert [row["provider_executions"] for row in scenarios] == [1, 0, 1, 0, 2, 0, 2, 0]
