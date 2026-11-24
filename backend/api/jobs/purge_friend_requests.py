"""거절·취소 응답 후 30일이 지난 친구 신청을 서비스 계정으로 삭제한다."""

import sys

from api.jobs.locks import RETENTION
from api.repositories.friends import delete_expired_requests
from shared.db.session import service_db_session


def main() -> int:
    try:
        with service_db_session() as db:
            if not db.scalar(RETENTION):
                print("purge_friend_requests status=locked", file=sys.stderr)
                return 3
            count = delete_expired_requests(db)
    except Exception:
        print("purge_friend_requests status=error", file=sys.stderr)
        return 1
    print(f"purge_friend_requests status=ok deleted={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
