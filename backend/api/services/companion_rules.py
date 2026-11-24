from datetime import date, datetime, timedelta, timezone
from os import environ
from zoneinfo import ZoneInfo

from api.errors import ApiError
from api.schemas.companions import PostAction, PostStatus

KST = ZoneInfo("Asia/Seoul")
PAGE_SIZE = 20
RETENTION = timedelta(hours=72)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def auto_end_after() -> timedelta:
    hours = int(environ.get("COMPANION_AUTO_END_H", "12"))
    if hours <= 0:
        raise ValueError("COMPANION_AUTO_END_H는 양의 정수여야 합니다.")
    return timedelta(hours=hours)


def validate_meeting(meet_at: datetime, start: date | None, end: date | None, now: datetime) -> None:
    day = meet_at.astimezone(KST).date()
    if start is None or end is None or not start <= day <= end or meet_at <= now:
        raise ApiError(400, "MEET_AT_INVALID", "만남 시각은 축제 기간 안의 미래 시각이어야 합니다.")


def festival_not_found() -> ApiError:
    return ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")


def not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "동행 글 또는 신청을 찾을 수 없습니다.")


def forbidden() -> ApiError:
    return ApiError(403, "FORBIDDEN", "동행 글 또는 신청을 처리할 권한이 없습니다.")


def post_closed() -> ApiError:
    return ApiError(409, "POST_CLOSED", "모집이 마감됐거나 동행이 끝났습니다.")


def require_active(status: PostStatus, meet_at: datetime, now: datetime) -> None:
    if status in {"ended", "cancelled"} or meet_at + auto_end_after() <= now:
        raise post_closed()


def require_approval_slot(status: PostStatus, approved_count: int, capacity: int) -> None:
    if approved_count >= capacity:
        raise ApiError(409, "CAPACITY_FULL", "남은 모집 인원이 없습니다.")
    if status != "open":
        raise post_closed()


def require_pending(status: str) -> None:
    if status != "pending":
        raise ApiError(409, "APPLICATION_NOT_PENDING", "대기 중인 신청만 처리할 수 있습니다.")


def check_application(author_id: object, actor_id: object, status: PostStatus) -> None:
    if author_id == actor_id:
        raise ApiError(403, "OWN_POST", "본인이 작성한 글에는 신청할 수 없습니다.")
    if status != "open":
        raise post_closed()


def application_exists() -> ApiError:
    return ApiError(409, "APPLICATION_EXISTS", "이미 신청한 동행입니다.")


def post_action_status(
    action: PostAction, status: PostStatus, meet_at: datetime, now: datetime,
) -> PostStatus:
    require_active(status, meet_at, now)
    if action == "cancel" and meet_at <= now:
        raise ApiError(409, "POST_CLOSED", "만남 시각 이후에는 동행을 종료해 주세요.")
    return {"close": "full", "end": "ended", "cancel": "cancelled"}[action]


def edited_status(capacity: int, approved_count: int, manually_closed: bool) -> PostStatus:
    if capacity < approved_count:
        raise ApiError(409, "CAPACITY_FULL", "정원은 승인된 인원보다 작을 수 없습니다.")
    return "full" if manually_closed or capacity == approved_count else "open"
