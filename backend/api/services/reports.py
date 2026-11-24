import re
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from api.errors import ApiError
from api.schemas import reports as schema
from api.schemas.chat import MAX_BIGINT, ROOM_ID_PATTERN
from api.schemas.companions import POST_ID_PATTERN

KST = ZoneInfo("Asia/Seoul")
PAGE_SIZE = 20
ACTION_TARGET = {
    "hide_message": "chat_message",
    "hide_post": "companion_post",
    "close_room": "chat_room",
    "block_user": "user",
}


def target_not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "신고할 수 있는 대상을 찾을 수 없습니다.")


def report_not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "신고 내역을 찾을 수 없습니다.")


def duplicate_report() -> ApiError:
    return ApiError(409, "REPORT_ALREADY_SUBMITTED", "오늘 이미 이 대상을 신고했습니다.")


def target_id(request: schema.ReportCreate) -> str:
    value = request.target_id
    if request.target_type == "user":
        try:
            return str(UUID(value))
        except ValueError:
            raise target_not_found() from None
    if request.target_type == "chat_message":
        if re.fullmatch(r"[0-9]{1,19}", value) and 0 < int(value) <= MAX_BIGINT:
            return str(int(value))
    else:
        pattern = ROOM_ID_PATTERN if request.target_type == "chat_room" else POST_ID_PATTERN
        if re.fullmatch(pattern, value):
            return value
    raise target_not_found()


def check_decision(status: schema.ReportStatus, target_type: schema.TargetType, action: schema.ReportAction) -> None:
    if status in ("actioned", "dismissed"):
        raise ApiError(403, "FORBIDDEN", "이미 처리된 신고입니다.")
    if action != "dismiss" and ACTION_TARGET[action] != target_type:
        raise ApiError(403, "FORBIDDEN", "이 신고 대상에는 선택한 조치를 적용할 수 없습니다.")


class ReportReviewStore(Protocol):
    def list(self, status: schema.ReportStatus | None, page: int) -> schema.ReportPage: ...
    def detail(self, admin_id: UUID, report_id: str) -> schema.ReportDetail: ...
    def decide(self, admin_id: UUID, decision: schema.ReportDecision) -> schema.ReportResult: ...
