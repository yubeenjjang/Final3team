"""Apply the chat body and notification retention rules using the service role."""

import sys

from sqlalchemy import text

from shared.db.session import service_db_session


def purge_expired() -> tuple[int, int]:
    with service_db_session() as db:
        messages = db.execute(text("""
            UPDATE public.chat_messages m
            SET body = NULL, deleted_at = COALESCE(m.deleted_at, statement_timestamp())
            FROM public.chat_rooms r WHERE r.room_id = m.room_id AND m.body IS NOT NULL AND (
                (r.room_type = 'companion' AND r.read_only_at <= statement_timestamp() - interval '72 hours')
                OR (r.room_type <> 'companion' AND m.created_at <= statement_timestamp() - interval '720 hours')
            )
        """)).rowcount
        notifications = db.execute(text("""
            DELETE FROM public.notifications WHERE created_at <= statement_timestamp() - interval '2160 hours'
        """)).rowcount
    return messages, notifications


def main() -> int:
    try:
        messages, notifications = purge_expired()
    except Exception:
        print("purge_chat status=error", file=sys.stderr)
        return 1
    print(f"purge_chat status=ok messages={messages} notifications={notifications}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
