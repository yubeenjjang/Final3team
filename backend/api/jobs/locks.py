"""정기 실행과 수동 명령이 함께 사용하는 PostgreSQL 트랜잭션 잠금."""

from sqlalchemy import text

ROUTE_RESULTS = text("SELECT pg_try_advisory_xact_lock(hashtext('noldaga.purge_route_results'))")
COMPANIONS = text("SELECT pg_try_advisory_xact_lock(190072)")
RETENTION = text("SELECT pg_try_advisory_xact_lock(hashtext('noldaga.retention'))")
FESTIVALS = text("SELECT pg_try_advisory_xact_lock(hashtext('noldaga.collect_festivals'))")
WITHDRAWAL_LOG = text("SELECT pg_try_advisory_xact_lock(hashtext('noldaga.withdrawal_log'))")
