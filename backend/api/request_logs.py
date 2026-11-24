import logging
import re

_ROUTE_PATH = re.compile(r"(/api/v1/routes/(?:return|visit))(?:/([^/]+))?/?")
_AUTH_PATH = re.compile(r"(/api/v1/auth/(?:signup|login|refresh|logout))/?")
_ME_PATH = re.compile(r"(/api/v1/me(?:/profile|/festival-preferences|/companion-activity|/favorites)?)/?")
_FAVORITE_ITEM_PATH = re.compile(r"/api/v1/me/favorites/[^/]+/?")
_FRIENDS_PATH = re.compile(r"(/api/v1/(?:users/search|friend-requests|me/friend-requests|me/friends))/?")
_FRIEND_ACTION_PATH = re.compile(r"/api/v1/friend-requests/[^/]+/[^/]+/?")
_FRIEND_ITEM_PATH = re.compile(r"(/api/v1/me/(?:friends|blocks))/[^/]+/?")
_FESTIVAL_INFO_PATH = re.compile(r"/api/v1/festivals/[^/]+/(crowd|notices|weather|transit|visit-forecast)/?")
_COMPANION_PATH = re.compile(
    r"/api/v1/(?:festivals/[^/]+/companion-posts|companion-posts(?:/[^/]+(?:/[^/]+)?)?"
    r"|companion-applications/[^/]+/[^/]+)/?"
)

ADMIN_REVIEW_PATH = "/api/v1/admin/festivals/review-queue"

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


def friends_endpoint(path: str) -> str | None:
    match = _FRIENDS_PATH.fullmatch(path)
    if match:
        return match[1]
    if _FRIEND_ACTION_PATH.fullmatch(path):
        return "/api/v1/friend-requests/{request_id}/{action}"
    match = _FRIEND_ITEM_PATH.fullmatch(path)
    return match[1] + "/{user_id}" if match else None


def companion_endpoint(path: str) -> str | None:
    if not _COMPANION_PATH.fullmatch(path):
        return None
    if path.startswith("/api/v1/festivals/"):
        return "/api/v1/festivals/{festival_id}/companion-posts"
    parts = path.rstrip("/").split("/")
    if parts[3] == "companion-applications":
        return "/api/v1/companion-applications/{application_id}/{action}"
    if len(parts) == 4:
        return "/api/v1/companion-posts"
    detail = "/api/v1/companion-posts/{post_id}"
    if len(parts) == 5:
        return detail
    return detail + ("/" + parts[5] if parts[5] in {"applications", "meeting-place"} else "/{action}")


def private_endpoint(path: str) -> str | None:
    route = _ROUTE_PATH.fullmatch(path)
    if route:
        return route[1] + ("/{route_request_id}" if route[2] else "")
    info = _FESTIVAL_INFO_PATH.fullmatch(path)
    if info:
        return "/api/v1/festivals/{festival_id}/" + info[1]
    if path.rstrip("/") == ADMIN_REVIEW_PATH:
        return ADMIN_REVIEW_PATH
    return auth_endpoint(path) or me_endpoint(path) or friends_endpoint(path) or companion_endpoint(path)


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
