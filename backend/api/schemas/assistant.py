from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.schemas.routes import ROUTE_REQUEST_ID_PATTERN

CONVERSATION_ID_PATTERN = r"^cv_[0-9A-Za-z]{6,26}$"
RUN_ID_PATTERN = r"^run_[0-9A-Za-z]{6,26}$"


class AssistantContext(BaseModel):
    festival_id: str | None = Field(default=None, pattern=FESTIVAL_ID_PATTERN)
    route_request_id: str | None = Field(default=None, pattern=ROUTE_REQUEST_ID_PATTERN)


class AssistantRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(default=None, pattern=CONVERSATION_ID_PATTERN)
    context: AssistantContext = Field(default_factory=AssistantContext)
    reference_date: Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")] | None = None

    @field_validator("request_id", "message")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("사용할 수 없는 문자가 포함되어 있습니다.")
        return value

    @field_validator("reference_date")
    @classmethod
    def validate_reference_date(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValueError("기준 날짜를 확인해 주세요.") from None
        return value
