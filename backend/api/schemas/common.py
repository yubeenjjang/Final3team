from typing import Literal

from pydantic import BaseModel


class MockResponse(BaseModel):
    is_mock: Literal[True] = True


class HealthResponse(MockResponse):
    status: Literal["ok"] = "ok"
    db: Literal["mock"] = "mock"
    redis: Literal["mock"] = "mock"
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail
