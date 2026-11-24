from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def add(db: Session, recipients: Sequence[UUID], event: str, ref_type: str, ref_id: str) -> None:
    if recipients:
        db.execute(text("""
            INSERT INTO public.notifications (user_id, type, ref_type, ref_id)
            SELECT uid, :event, :ref_type, :ref_id FROM unnest(CAST(:recipients AS uuid[])) AS uid
        """), {"recipients": list(recipients), "event": event, "ref_type": ref_type, "ref_id": ref_id})
