import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session
from ulid import ULID

from api.schemas.admin_festivals import (
    FestivalRegistration, FestivalRegistrationResult, FestivalUpdate, FestivalUpdateResult,
)
from api.services.admin_festivals import (
    ADMIN_SOURCE_ID, IDENTITY_FIELDS, audit_value, duplicate_error, duplicate_proposal, missing_festival,
    registration_fields, update_fields, update_result,
)
from shared.db.session import service_db_session


def _write_history(
    db: Session, festival_id: str, before: Mapping[str, object], changes: Mapping[str, object],
    reason: str, actor: UUID, now: datetime,
) -> None:
    db.execute(text("""
        INSERT INTO public.festival_change_history
            (festival_id, field, before_value, after_value, source_id, actor, changed_at, reason, actor_user_id)
        VALUES (:festival_id, :field, CAST(:before AS jsonb), CAST(:after AS jsonb),
                :source, 'admin', :now, :reason, :actor)
    """), [
        {
            "festival_id": festival_id, "field": field, "before": json.dumps(audit_value(before.get(field))),
            "after": json.dumps(audit_value(value)), "source": ADMIN_SOURCE_ID,
            "reason": reason, "actor": actor, "now": now,
        }
        for field, value in changes.items()
    ])


def _queue_duplicate(db: Session, festival_id: str, proposal: str) -> int | None:
    # 호출자가 해당 축제 행을 잠근 상태에서 대기열을 추가한다.
    return db.scalar(text("""
        INSERT INTO public.festival_review_queue (festival_id, reason, proposed_value)
        SELECT :id, 'duplicate', CAST(:proposal AS jsonb)
        WHERE NOT EXISTS (
            SELECT 1 FROM public.festival_review_queue
            WHERE festival_id = :id AND reason = 'duplicate' AND approval_status = 'pending'
              AND proposed_value = CAST(:proposal AS jsonb)
        )
        RETURNING queue_id
    """), {"id": festival_id, "proposal": proposal})


class PostgresAdminFestivalStore:
    def register(self, request: FestivalRegistration, actor: UUID) -> FestivalRegistrationResult:
        fields = registration_fields(request)
        proposal = json.dumps(duplicate_proposal(fields), sort_keys=True)
        identity = {field: fields[field] for field in IDENTITY_FIELDS}
        lock_key = json.dumps([audit_value(value) for value in identity.values()])
        with service_db_session() as db:
            # 같은 이름·기간·장소의 동시 등록을 한 트랜잭션씩 처리한다.
            db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 55))"), {"key": lock_key})
            duplicate_id = db.scalar(text("""
                SELECT festival_id FROM public.festivals
                WHERE btrim(title) = :title AND start_date = :start_date AND end_date = :end_date
                  AND btrim(venue_name) = :venue_name AND category = 'festival'
                ORDER BY festival_id LIMIT 1 FOR NO KEY UPDATE
            """), identity)
            now = datetime.now(timezone.utc)
            if duplicate_id is not None:
                queue_id = _queue_duplicate(db, duplicate_id, proposal)
                if queue_id is not None:
                    _write_history(db, duplicate_id, {}, {"duplicate_submission": {"queue_id": queue_id}},
                                   request.reason, actor, now)
            else:
                festival_id = f"fst_{ULID()}"
                values = {
                    **fields, "review_status": "pending",
                    "festival_id": festival_id, "last_synced_at": now,
                }
                # 필드 이름은 요청 모델에서 정해진 DB 컬럼 이름만 들어옵니다.
                columns = ", ".join(values)
                params = ", ".join(f":{field}" for field in values)
                db.execute(text(f"INSERT INTO public.festivals ({columns}) VALUES ({params})"), values)
                db.execute(text("""
                    INSERT INTO public.festival_sources
                        (festival_id, source_id, source_item_id, source_url, raw_checksum, fetched_at)
                    VALUES (:id, :source, :id, :url, :checksum, :now)
                """), {
                    "id": festival_id, "source": ADMIN_SOURCE_ID, "url": fields.get("official_url"),
                    "checksum": hashlib.sha256(proposal.encode()).hexdigest(), "now": now,
                })
                _write_history(db, festival_id, {}, {**fields, "review_status": "pending"},
                               request.reason, actor, now)
        if duplicate_id is not None:
            # 정상 종료로 대기열과 이력을 커밋한 뒤 409를 반환합니다.
            raise duplicate_error()
        return FestivalRegistrationResult(festival_id=festival_id)

    def update(self, festival_id: str, request: FestivalUpdate, actor: UUID) -> FestivalUpdateResult:
        with service_db_session() as db:
            key = {"festival_id": festival_id}
            festival = db.execute(text("""
                SELECT * FROM public.festivals WHERE festival_id = :festival_id FOR NO KEY UPDATE
            """), key).mappings().one_or_none()
            if festival is None:
                raise missing_festival()
            now = datetime.now(timezone.utc)
            changes = update_fields(request, festival, now)
            if changes:
                assignments = ", ".join(f"{field} = :{field}" for field in changes)
                db.execute(text(f"""
                    UPDATE public.festivals SET {assignments} WHERE festival_id = :festival_id
                """), {**key, **changes})
                _write_history(db, festival_id, festival, changes, request.reason, actor, now)
            return update_result(festival_id, {**festival, **changes})
