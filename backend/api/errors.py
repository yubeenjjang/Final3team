from collections.abc import Mapping

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as DBPoolTimeout
from starlette.exceptions import HTTPException

from api.schemas.common import ErrorDetail, ErrorResponse

SERVICE_BUSY_CODE = "DB_POOL_TIMEOUT"
SERVICE_BUSY_MESSAGE = "요청이 많아 잠시 후 다시 시도해 주세요."
_DB_POOL_RETRY_AFTER_S = 1


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable


def error_response(
    request: Request, error: ApiError, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    request_id = request.state.request_id
    body = ErrorResponse(
        error=ErrorDetail(
            code=error.code,
            message=error.message,
            request_id=request_id,
            retryable=error.retryable,
        )
    )
    response = JSONResponse(
        content=body.model_dump(), status_code=error.status, headers=headers
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Mock"] = "true"
    return response


async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
    headers = {"Retry-After": str(_DB_POOL_RETRY_AFTER_S)} if error.code == SERVICE_BUSY_CODE else None
    return error_response(request, error, headers)


async def handle_db_pool_timeout(request: Request, _error: DBPoolTimeout) -> JSONResponse:
    return await handle_api_error(request, ApiError(503, SERVICE_BUSY_CODE, SERVICE_BUSY_MESSAGE, True))


async def handle_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    fields = (
        ".".join(str(part) for part in issue["loc"][1:])
        or str(issue["loc"][0])
        for issue in error.errors()
    )
    message = f"입력값을 확인해 주세요 ({', '.join(dict.fromkeys(fields))})."
    return error_response(request, ApiError(422, "VALIDATION_ERROR", message))


async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
    codes = {
        404: ("NOT_FOUND", "요청한 주소를 찾을 수 없습니다."),
        405: ("METHOD_NOT_ALLOWED", "이 주소에서 지원하지 않는 요청 방식입니다."),
    }
    code, message = codes.get(
        error.status_code, ("HTTP_ERROR", "요청을 처리할 수 없습니다.")
    )
    return error_response(request, ApiError(error.status_code, code, message), error.headers)


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return error_response(
        request, ApiError(500, "INTERNAL_SERVER_ERROR", "서버에서 오류가 발생했습니다.")
    )
