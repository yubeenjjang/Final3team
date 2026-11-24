"""서비스 계정으로 보관 기준(기본 23시간)에 도달한 TMAP 결과 본문을 정리한다."""

import argparse
import os
import sys
from datetime import datetime, timezone
from time import monotonic

from api.repositories.route_store import DEFAULT_PURGE_AFTER_HOURS, RouteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="DB를 변경하지 않고 정리 대상 건수만 출력")
    args = parser.parse_args(argv)
    try:
        after_hours = int(os.environ.get("ROUTE_PURGE_AFTER_HOURS", str(DEFAULT_PURGE_AFTER_HOURS)))
    except ValueError:
        parser.error("ROUTE_PURGE_AFTER_HOURS는 1~23 사이의 정수여야 합니다.")
    if not 1 <= after_hours <= 23:
        parser.error("ROUTE_PURGE_AFTER_HOURS는 1~23 사이의 정수여야 합니다.")

    started = monotonic()
    mode = "dry-run" if args.dry_run else "purge"
    try:
        count = RouteStore().purge_expired(
            datetime.now(timezone.utc), after_hours=after_hours, dry_run=args.dry_run,
        )
    except Exception:
        # DB 예외에 연결 정보나 값이 포함될 수 있어 예외 메시지를 기록하지 않는다.
        elapsed_ms = round((monotonic() - started) * 1000)
        print(f"purge_route_results status=error mode={mode} processed=unknown duration_ms={elapsed_ms}",
              file=sys.stderr)
        return 1

    elapsed_ms = round((monotonic() - started) * 1000)
    if count is None:
        print(f"purge_route_results status=locked mode={mode} processed=0 duration_ms={elapsed_ms}",
              file=sys.stderr)
        return 3
    if args.dry_run:
        print(count)
    else:
        print(f"purge_route_results status=ok mode={mode} processed={count} duration_ms={elapsed_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
