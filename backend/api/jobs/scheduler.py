"""한국 시간 기준으로 실행할 시각이 지난 운영 작업을 한 번 실행한다."""

import argparse
import sys
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import date, datetime, timezone
from time import monotonic

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

from api.ingestion.festivals import collect
from api.ingestion.festivals.normalize import KST
from api.ingestion.seoul_culture import collect as seoul_culture
from api.jobs import locks, retention
from api.jobs.maintain_companions import maintain_companions
from api.jobs.purge_route_results import DEFAULT_PURGE_AFTER_HOURS, RouteStore
from shared.db.session import service_db_session


class JobLocked(Exception):
    pass


@dataclass(frozen=True)
class Job:
    name: str
    lock: TextClause
    run: Callable[[Session, datetime], dict[str, int]]
    daily: bool = False
    enabled: Callable[[], bool] | None = None


def _purge_routes(db: Session, now: datetime) -> dict[str, int]:
    count = RouteStore(lambda: nullcontext(db)).purge_expired(now, after_hours=DEFAULT_PURGE_AFTER_HOURS)
    if count is None:
        raise JobLocked
    return {"processed": count}


def _sweep(db: Session, now: datetime) -> dict[str, int]:
    # 경로 결과의 UPDATE(013 트리거)와 요청의 DELETE(022 CASCADE)가 경합하지 않게 한다.
    if not db.scalar(locks.ROUTE_RESULTS) or not db.scalar(locks.COMPANIONS):
        raise JobLocked
    return retention.sweep(db, now)


def _collect_festivals(db: Session, now: datetime) -> dict[str, int]:
    job = collect.collect_to_db(date(now.year, 1, 1), locked_engine=db.get_bind())
    return {"scanned": job.scanned, "inserted": job.inserted, "updated": job.updated, "rejected": job.rejected}


def _collect_seoul_culture(db: Session, now: datetime) -> dict[str, int]:
    job = seoul_culture.collect_to_db(now, locked_engine=db.get_bind())
    return {"scanned": job.scanned, "inserted": job.inserted, "updated": job.updated, "rejected": job.rejected}


JOBS = (
    Job("purge_route_results", locks.ROUTE_RESULTS, _purge_routes),
    Job("maintain_companions", locks.COMPANIONS, maintain_companions),
    Job("retention", locks.RETENTION, _sweep, daily=True),
    Job("collect_festivals", locks.FESTIVALS, _collect_festivals, daily=True),
    Job("collect_seoul_culture", locks.FESTIVALS, _collect_seoul_culture, daily=True, enabled=seoul_culture.enabled),
)


def _run_once(job: Job, slot: datetime, now: datetime) -> dict[str, int] | None:
    with service_db_session() as db:
        if not db.scalar(job.lock):
            raise JobLocked
        previous = db.scalar(text("""
            SELECT last_success_slot FROM public.scheduled_job_runs WHERE job_name = :name
        """), {"name": job.name})
        if previous is not None and previous >= slot:
            return None

        counts = job.run(db, now)
        db.execute(text("""
            INSERT INTO public.scheduled_job_runs (job_name, last_success_slot) VALUES (:name, :slot)
            ON CONFLICT (job_name) DO UPDATE SET last_success_slot = EXCLUDED.last_success_slot
        """), {"name": job.name, "slot": slot})
    return counts


def run_due(now: datetime | None = None) -> int:
    now = (now or datetime.now(timezone.utc)).astimezone(KST)
    hourly_slot = now.replace(minute=0, second=0, microsecond=0)
    daily_slot = hourly_slot.replace(hour=6)
    failed = locked = False

    for job in JOBS:
        slot = daily_slot if job.daily else hourly_slot
        if slot > now or (job.enabled is not None and not job.enabled()):
            continue

        started = monotonic()
        counts = None
        try:
            counts = _run_once(job, slot, now)
            status = "ok" if counts is not None else "already_done"
        except JobLocked:
            locked = True
            status = "locked"
        except Exception:
            failed = True
            status = "error"

        # 예외·본문·공급원 데이터 대신 고정된 상태와 집계만 출력한다.
        fields = "".join(f" {name}={count}" for name, count in (counts or {}).items())
        elapsed = round((monotonic() - started) * 1000)
        print(f"{job.name} status={status} slot={slot.isoformat()} duration_ms={elapsed}{fields}",
              file=sys.stderr if status in {"error", "locked"} else sys.stdout, flush=True)

    if failed:
        return 1
    return 3 if locked else 0


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    return run_due()


if __name__ == "__main__":
    raise SystemExit(main())
