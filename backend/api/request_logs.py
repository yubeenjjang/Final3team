import logging
import re

_ROUTE_PATH = re.compile(r"(/api/v1/routes/(?:return|visit))(?:/([^/]+))?/?")
_AUTH_PATH = re.compile(r"(/api/v1/auth/(?:signup|login|refresh|logout))/?")
_ME_PATH = re.compile(r"(/api/v1/me(?:/profile|/festival-preferences|/companion-activity|/favorites)?)/?")
_CHAT_PATH = re.compile(
    r"/api/v1/(?:ws/chat|chat-rooms(?:/[^/]+(?:/(?:invitations|accept|decline|leave|read|messages))?)?"
    r"|me/(?:chat-rooms|notifications(?:/read)?)|ws-tickets)/?"
)
_CHAT_ROOM_PATH = re.compile(r"/api/v1/chat-rooms/[^/]+(?:/([^/]+))?/?")
_CHAT_SOCKET_PATH = "/api/v1/ws/chat"
_FAVORITE_ITEM_PATH = re.compile(r"/api/v1/me/favorites/[^/]+/?")
_FESTIVAL_INFO_PATH = re.compile(r"/api/v1/festivals/[^/]+/(crowd|notices|weather|transit|visit-forecast)/?")

request_logger = logging.getLogger("uvicorn.error.api_requests")


def auth_endpoint(path: str) -> str | None:
    match = _AUTH_PATH.fullmatch(path)
    return match[1] if match else None


def me_endpoint(path: str) -> str | None:
    match = _ME_PATH.fullmatch(path)
    if match:
        return match[1]
    if _FAVORITE_ITEM_PATH.fullmatch(path):
        return "/api/v1/me/favorites/{festival_id}"
    return None


def chat_endpoint(path: str) -> str | None:
    if not _CHAT_PATH.fullmatch(path):
        return None
    if room := _CHAT_ROOM_PATH.fullmatch(path):
        return "/api/v1/chat-rooms/{room_id}" + ("/" + room[1] if room[1] else "")
    return path.rstrip("/")


def private_endpoint(path: str) -> str | None:
    route = _ROUTE_PATH.fullmatch(path)
    if route:
        return route[1] + ("/{route_request_id}" if route[2] else "")
    info = _FESTIVAL_INFO_PATH.fullmatch(path)
    if info:
        return "/api/v1/festivals/{festival_id}/" + info[1]
    return auth_endpoint(path) or me_endpoint(path) or chat_endpoint(path)


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
        if record.name == "uvicorn.error":
            record.args = tuple(
                value.partition("?")[0]
                if isinstance(value, str) and value.partition("?")[0].rstrip("/") == _CHAT_SOCKET_PATH else value
                for value in args
            )
        if record.name == "uvicorn.asgi" and len(args) == 3 and isinstance(args[2], dict):
            scope = args[2]
            path = scope.get("path")
            if scope.get("type") in ("http", "websocket") and isinstance(path, str):
                if endpoint := private_endpoint(path):
                    record.args = args[:2] + ({"type": scope["type"], "path": endpoint},)
        return True


_private_requests = _PrivateRequestFilter()
for logger_name in ("uvicorn.access", "uvicorn.asgi", "uvicorn.error"):
    logging.getLogger(logger_name).addFilter(_private_requests)
