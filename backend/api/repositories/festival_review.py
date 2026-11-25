import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from api.errors import ApiError
from api.schemas.festival_review import (
    ApprovalStatus, ReviewItem, ReviewPage, ReviewReason, ReviewRequest, ReviewResult,
)
from api.services.festival_review import check_pending, review_changes
from shared.db.session import service_db_session

_LIST = text("""
    WITH filtered AS NOT MATERIALIZED (
        SELECT q.queue_id, q.festival_id, f.title AS festival_name, q.reason,
               CASE WHEN jsonb_typeof(q.proposed_value) = 'object' THEN q.proposed_value END AS proposed_value,
               q.approval_status, q.created_at
        FROM public.festival_review_queue q
        JOIN public.festivals f USING (festival_id)
        WHERE q.approval_status = :status AND (CAST(:reason AS text) IS NULL OR q.reason = :reason)
    )
    SELECT totals.total, page.*
    FROM (SELECT count(*) AS total FROM filtered) totals
    LEFT JOIN (
        SELECT * FROM filtered ORDER BY created_at DESC, queue_id DESC
        LIMIT :limit OFFSET :offset
    ) page ON true
    ORDER BY page.created_at DESC, page.queue_id DESC
""")


class PostgresReviewStore:
    def list_items(
        self, status: ApprovalStatus, reason: ReviewReason | None, page: int, page_size: int,
    ) -> ReviewPage:
        with service_db_session() as db:
            rows = db.execute(_LIST, {
                "status": status, "reason": reason, "limit": page_size, "offset": (page - 1) * page_size,
            }).mappings().all()
        return ReviewPage(
            items=[ReviewItem.model_validate(row) for row in rows if row["queue_id"] is not None],
            total=rows[0]["total"], page=page, page_size=page_size,
        )

    def decide(self, request: ReviewRequest, reviewer: UUID) -> ReviewResult:
        with service_db_session() as db:
            key = {"queue_id": request.queue_id}
            # 수집과 같은 축제 행 잠금을 먼저 잡아 같은 축제의 결정을 직렬화합니다.
            festival = db.execute(text("""
                SELECT f.* FROM public.festivals f
                WHERE f.festival_id = (
                    SELECT festival_id FROM public.festival_review_queue WHERE queue_id = :queue_id
                )
                FOR NO KEY UPDATE
            """), key).mappings().one_or_none()
            if festival is None:
                check_pending(None)
            queue = db.execute(text("""
                SELECT approval_status, proposed_value, reason
                FROM public.festival_review_queue WHERE queue_id = :queue_id FOR UPDATE
            """), key).mappings().one_or_none()
            check_pending(queue["approval_status"] if queue else None)

            now = datetime.now(timezone.utc)
            updates = review_changes(request, festival, queue["proposed_value"], now)
            changes = {field: value for field, value in updates.items() if festival[field] != value}
            if changes:
                # 필드 이름은 FestivalPatch의 허용 목록과 서버 지정 상태 칸으로 제한됩니다.
                assignments = ", ".join(f"{field} = :{field}" for field in changes)
                try:
                    db.execute(text(f"""
                        UPDATE public.festivals SET {assignments} WHERE festival_id = :festival_id
                    """), {**changes, "festival_id": festival["festival_id"]})
                except (DataError, IntegrityError):
                    raise ApiError(422, "VALIDATION_ERROR", "적용할 축제 필드와 값을 확인해 주세요.") from None

            approval_status = "approved" if request.decision == "approve" else "rejected"
            db.execute(text("""
                UPDATE public.festival_review_queue
                SET approval_status = :status, reviewer = :reviewer, reviewed_at = :now
                WHERE queue_id = :queue_id
            """), {**key, "status": approval_status, "reviewer": reviewer, "now": now})
            db.execute(text("""
                INSERT INTO public.festival_change_history
                    (festival_id, field, before_value, after_value, actor, changed_at)
                VALUES (:festival_id, 'review_decision', CAST(:before AS jsonb),
                        CAST(:after AS jsonb), 'admin', :now)
            """), {
                "festival_id": festival["festival_id"], "now": now,
                "before": json.dumps({
                    "approval_status": queue["approval_status"],
                    "values": {field: festival[field] for field in changes},
                }, default=str),
                "after": json.dumps({
                    "queue_id": request.queue_id, "decision": request.decision,
                    "reason": request.note, "queue_reason": queue["reason"], "reviewer": str(reviewer),
                    "approval_status": approval_status, "values": changes,
                }, default=str),
            })
        return ReviewResult(queue_id=request.queue_id, approval_status=approval_status, applied=bool(changes))
