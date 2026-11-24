"""동행 자동 종료와 보존 기간이 지난 내용 정리. 팀 보존 워커에서 시간마다 호출합니다."""

import logging

from sqlalchemy import text

from api.repositories.companions import maintain_companions
from api.services.companion_rules import now_utc
from shared.db.session import service_db_session

logger = logging.getLogger(__name__)


def main() -> int:
    try:
        with service_db_session() as db:
            if not db.scalar(text("SELECT pg_try_advisory_xact_lock(190072)")):
                return 3
            counts = maintain_companions(db, now_utc())
    except Exception:
        logger.error("동행 자동 종료·정리에 실패했습니다.")
        return 1
    print(" ".join(f"{name}={count}" for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
