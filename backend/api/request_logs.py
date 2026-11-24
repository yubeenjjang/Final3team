import logging
import re

_ROUTE_PATH = re.compile(r"(/api/v1/routes/(?:return|visit))(?:/([^/]+))?/?")
_CROWD_PATH = re.compile(r"/api/v1/festivals/[^/]+/crowd/?")
_AUTH_PATH = re.compile(r"(/api/v1/auth/(?:signup|login|refresh|logout))/?")

request_logger = logging.getLogger("uvicorn.error.api_requests")


def auth_endpoint(path: str) -> str | None:
    match = _AUTH_PATH.fullmatch(path)
    return match[1] if match else None


def private_endpoint(path: str) -> str | None:
    route = _ROUTE_PATH.fullmatch(path)
    if route:
        return route[1] + ("/{route_request_id}" if route[2] else "")
    if _CROWD_PATH.fullmatch(path):
        return "/api/v1/festivals/{festival_id}/crowd"
    return auth_endpoint(path)


class _PrivateRequestFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple):
            return True
        # Keep Uvicorn's access formatter arguments and replace its raw target.
        if record.name == "uvicorn.access" and len(args) == 5:
            client, method, target, version, status = args
            if isinstance(target, str) and (endpoint := private_endpoint(target.partition("?")[0])):
                record.args = client, method, endpoint, version, status
        if record.name == "uvicorn.asgi" and len(args) == 3 and isinstance(args[2], dict):
            scope = args[2]
            path = scope.get("path")
            if scope.get("type") == "http" and isinstance(path, str) and (endpoint := private_endpoint(path)):
                record.args = args[:2] + ({"type": "http", "path": endpoint},)
        return True


_private_requests = _PrivateRequestFilter()
for logger_name in ("uvicorn.access", "uvicorn.asgi"):
    logging.getLogger(logger_name).addFilter(_private_requests)
