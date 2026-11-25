"""DB를 백업에서 복원한 직후 실행: 탈퇴 기록에 있는 계정을 다시 정리한다 (DB 설계서 7-0 ⑥).

실행: PYTHONPATH=backend python -m api.jobs.reapply_withdrawals [--dry-run]
복원 → 이 명령 → 서비스 재개 순서를 지킨다. 이미 정리된 계정(status='deleted')과 없는 계정은 건너뛴다.
"""
import argparse
import sys

from sqlalchemy import text

from api.services import withdrawal_log
from api.services.account_deletion import purge_account
from shared.db.session import service_db_session


def reapply(dry_run: bool = False) -> dict[str, int]:
    counts = {"entries": 0, "reapplied": 0, "already_deleted": 0, "missing": 0}
    seen = set()
    for user_id, _ in withdrawal_log.entries():
        if user_id in seen:
            continue
        seen.add(user_id)
        counts["entries"] += 1
        with service_db_session() as db:
            status = db.scalar(text("SELECT status FROM public.users WHERE user_id = :uid FOR UPDATE"),
                               {"uid": user_id})
            if status is None:
                counts["missing"] += 1
            elif status == "deleted":
                counts["already_deleted"] += 1
            else:
                counts["reapplied"] += 1
                if not dry_run:
                    purge_account(db, user_id)
                else:
                    db.rollback()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="정리할 계정 수만 센다")
    args = parser.parse_args(argv)
    counts = reapply(dry_run=args.dry_run)
    print(" ".join(f"{key}={value}" for key, value in counts.items()) + (" dry_run=true" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
