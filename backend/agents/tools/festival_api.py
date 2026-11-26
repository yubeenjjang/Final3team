"""Minimal HTTP wrappers for the single Festival Agent tools."""

from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


class FestivalApiTools:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1", timeout_s: float = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def __call__(self, name: str, args: Mapping[str, Any]) -> dict[str, Any]:
        if name == "search_festivals":
            allowed = {"region", "date_from", "date_to", "q", "status", "page_size"}
            if set(args) - allowed:
                return self._invalid()
            # The agent tool defaults to 10, while the public API defaults to 20.
            query = urlencode({"page_size": 10, **args})
            url = f"{self.base_url}/festivals" + (f"?{query}" if query else "")
        elif name == "get_official_notices":
            if (set(args) - {"festival_id", "type"} or "festival_id" not in args
                    or not isinstance(args["festival_id"], str)
                    or ("type" in args and args["type"] not in {"operation", "traffic_control", "no_stop", "bus_detour", "road_closure"})):
                return self._invalid()
            festival_id = quote(args["festival_id"], safe="")
            url = f"{self.base_url}/festivals/{festival_id}/notices"
            if "type" in args:
                url += "?" + urlencode({"type": args["type"]})
        elif name in {"get_festival", "get_crowd"}:
            if set(args) != {"festival_id"} or not isinstance(args["festival_id"], str):
                return self._invalid()
            festival_id = quote(args["festival_id"], safe="")
            url = f"{self.base_url}/festivals/{festival_id}"
            if name == "get_crowd":
                url += "/crowd"
        else:
            return self._invalid()

        try:
            with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=self.timeout_s) as response:
                body = json.load(response)
                return self._wrap(body, response.headers.get("X-Request-ID"), response.headers.get("X-Mock") == "true")
        except HTTPError as exc:
            try:
                body = json.load(exc)
            except (ValueError, OSError):
                body = {}
            error = body.get("error") or {}
            return {"ok": False, "error": {
                "code": error.get("code", "TOOL_HTTP_ERROR"),
                "message": error.get("message", "도구 요청에 실패했습니다."),
                "retryable": bool(error.get("retryable", exc.code >= 500)),
            }, "request_id": error.get("request_id")}
        except (URLError, TimeoutError, OSError):
            return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "message": "도구에 연결할 수 없습니다.", "retryable": True}}

    @staticmethod
    def _wrap(body: Any, request_id: str | None, mock_header: bool) -> dict[str, Any]:
        if not isinstance(body, dict):
            return {"ok": False, "error": {"code": "TOOL_INVALID_RESPONSE", "retryable": False}}
        return {"ok": True, "data": body, "request_id": request_id, "is_mock": mock_header or body.get("is_mock") is True}

    @staticmethod
    def _invalid() -> dict[str, Any]:
        return {"ok": False, "error": {"code": "VALIDATION_ERROR", "message": "허용되지 않은 도구 인자입니다.", "retryable": False}}
