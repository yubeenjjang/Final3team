"""Festival Agent boundary. A runner receives only an authorized, redacted query."""

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module
from inspect import iscoroutine
from typing import Annotated, Literal, Protocol

from httpx2 import TimeoutException
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator

from api.schemas.assistant import AssistantRequest
from api.schemas.routes import ROUTE_REQUEST_ID_PATTERN
from api.services import assistant, mock_assistant

Code = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")]
Ref = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_.:-]{1,150}$")]
Name = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{1,63}$")]


class UsedTool(BaseModel):
    tool: Literal["search_festivals", "get_festival", "get_crowd", "get_facilities",
                  "get_official_notices", "request_return_route", "get_route_request_status"]
    ok: bool
    error_code: Code | None = None


class Evidence(BaseModel):
    type: Name
    ref: Ref
    provider: Name
    queried_at: AwareDatetime


class AgentResult(BaseModel):
    answer: str | None = Field(default=None, repr=False, max_length=12_000)
    used_tools: list[UsedTool] = Field(default_factory=list, max_length=50)
    evidence: list[Evidence] = Field(default_factory=list, max_length=50)
    route_request_id: str | None = Field(default=None, pattern=ROUTE_REQUEST_ID_PATTERN)
    error_code: Code | None = None
    retryable: bool = False
    is_mock: bool = False

    @field_validator("answer")
    @classmethod
    def clean_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = "".join(char for char in value if char != "\x00" and not 0xD800 <= ord(char) <= 0xDFFF)
        return cleaned.strip() or None


@dataclass(frozen=True)
class RunInput:
    run_id: str
    query: AssistantRequest = field(repr=False)


class AgentRunner(Protocol):
    def run(self, job: RunInput, step: Callable[[str], None]) -> AgentResult: ...


def is_transient(error: Exception) -> bool:
    if isinstance(error, (TimeoutError, TimeoutException)):
        return True
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    return isinstance(status, int) and (status == 429 or 500 <= status <= 599)


class MockFestivalRunner:
    def run(self, job: RunInput, step: Callable[[str], None]) -> AgentResult:
        step("supervisor")
        payload = mock_assistant.complete_run(job.query, in_process_routes=False)
        step("festival")
        error = payload.get("error") or {}
        return AgentResult.model_validate({
            **payload, "error_code": error.get("code"), "retryable": error.get("retryable", False), "is_mock": True,
        })


class FestivalAgentRunner:
    def __init__(self, entrypoint: Callable) -> None:
        self._entrypoint = entrypoint

    def run(self, job: RunInput, step: Callable[[str], None]) -> AgentResult:
        # No actor credentials or privileged tool executors are passed into the agent.
        value = self._entrypoint(job, step)
        if iscoroutine(value):
            value = asyncio.run(value)
        if isinstance(value, AgentResult):
            return value
        return AgentResult.model_validate(value)


def get_runner() -> AgentRunner:
    configured = os.environ.get("ASSISTANT_FESTIVAL_RUNNER")
    module_name, _, function = (configured or "agents.festival_agent:run").partition(":")
    if not module_name.startswith("agents.") or not function.isidentifier():
        raise ValueError("Festival Agent 실행 경로를 확인해 주세요.")
    try:
        module = import_module(module_name)
    except ImportError:
        if not configured:
            return MockFestivalRunner()
        raise
    entrypoint = getattr(module, function, None)
    if callable(entrypoint):
        return FestivalAgentRunner(entrypoint)
    if configured:
        raise ValueError("Festival Agent 실행 경로를 확인해 주세요.")
    return MockFestivalRunner()
