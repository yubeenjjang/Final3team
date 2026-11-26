from typing import Annotated, Literal
from unicodedata import category

from pydantic import BaseModel, BeforeValidator, Field


def normalize_display_name(value: object) -> object:
    if not isinstance(value, str):
        return value
    if any(category(char) == "Cc" for char in value):
        raise ValueError("닉네임에는 제어문자를 넣을 수 없습니다.")
    return value.strip()


DisplayName = Annotated[str, Field(min_length=2, max_length=12), BeforeValidator(normalize_display_name)]


class MockResponse(BaseModel):
    is_mock: Literal[True] = True


class HealthResponse(BaseModel):
    is_mock: bool = True
    status: Literal["ok", "degraded"] = "ok"
    db: Literal["mock", "ok", "unavailable"] = "mock"
    redis: Literal["mock", "not_configured", "ok", "unavailable"] = "mock"
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail
