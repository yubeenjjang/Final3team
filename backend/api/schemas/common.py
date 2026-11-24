from typing import Literal

from pydantic import BaseModel


class MockResponse(BaseModel):
    is_mock: Literal[True] = True


class HealthResponse(BaseModel):
    is_mock: bool = True
    status: Literal["ok", "degraded"] = "ok"
    db: Literal["mock", "ok", "unavailable"] = "mock"
    redis: Literal["mock", "not_configured"] = "mock"
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail
