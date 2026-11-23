import logging
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any
from urllib.parse import quote, unquote, urlencode

import httpx2

BASE_URL = httpx2.URL(scheme="https", host="apis.data.go.kr", path="/B551011/KorService2/")
COMMON_PARAMS = {"MobileOS": "ETC", "MobileApp": "noldaga", "_type": "json"}
ERROR_MESSAGES = {
    "NO_KEY": "TourAPI 서비스 키를 설정해 주세요.",
    "KEY_ERROR": "TourAPI 서비스 키를 확인해 주세요.",
    "HTTP_ERROR": "TourAPI 요청에 실패했습니다.",
    "RESULT_ERROR": "TourAPI 응답을 처리할 수 없습니다.",
}
HTTP_LOGGERS = (
    "httpx2",
    "httpcore2.connection",
    "httpcore2.http11",
    "httpcore2.http2",
    "httpcore2.proxy",
    "httpcore2.socks",
)


class TourApiError(Exception):
    def __init__(self, code: str, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail
        message = ERROR_MESSAGES[code]
        super().__init__(f"{message} ({detail})" if detail else message)


class _KeyRedactor(logging.Filter):
    def __init__(self, key: str, encoded_key: str) -> None:
        super().__init__()
        variants = {key, encoded_key, unquote(encoded_key)}
        self._keys = re.compile("|".join(map(re.escape, sorted(variants, key=len, reverse=True))))

    def redact(self, message: str) -> str:
        return self._keys.sub("***", message)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        safe_message = self.redact(message)
        if safe_message != message:
            record.msg = safe_message
            record.args = ()
        return True

    @contextmanager
    def protect_logs(self) -> Iterator[None]:
        loggers = [logging.getLogger(name) for name in HTTP_LOGGERS]
        for logger in loggers:
            logger.addFilter(self)
        try:
            yield
        finally:
            for logger in loggers:
                logger.removeFilter(self)


class TourApiClient:
    def __init__(self, client: httpx2.Client | None = None) -> None:
        key = os.environ.get("DATA_GO_KR_SERVICE_KEY")
        if not key:
            raise TourApiError("NO_KEY")
        self._encoded_key = key if "%" in key else quote(key, safe="")
        self._redactor = _KeyRedactor(key, self._encoded_key)
        self._client = client if client is not None else httpx2.Client()
        self._owns_client = client is None
        self.calls: dict[str, int] = {}

    def __enter__(self) -> "TourApiClient":
        return self

    def __exit__(self, *exc: object) -> None:
        if self._owns_client:
            self._client.close()

    def redact(self, text: str) -> str:
        return self._redactor.redact(text)

    def search_festivals(
        self, start: date, end: date | None = None, page_size: int = 100
    ) -> list[dict[str, Any]]:
        params = {
            "eventStartDate": start.isoformat().replace("-", ""),
            "arrange": "A",
            "numOfRows": str(page_size),
        }
        if end is not None:
            params["eventEndDate"] = end.isoformat().replace("-", "")

        festivals: list[dict[str, Any]] = []
        page = 1
        while True:
            params["pageNo"] = str(page)
            body = self._get_body("searchFestival2", params)
            items = self._items(body)
            festivals.extend(items)
            if len(festivals) >= self._total_count(body):
                return festivals
            if not items:
                raise TourApiError("RESULT_ERROR", "목록 페이지에 항목이 없습니다.")
            page += 1

    def get_common(
        self, content_id: str, *, call_limit: int | None = None
    ) -> dict[str, Any]:
        return self._get_detail("detailCommon2", {"contentId": content_id}, call_limit)

    def get_intro(
        self, content_id: str, *, call_limit: int | None = None
    ) -> dict[str, Any]:
        return self._get_detail(
            "detailIntro2", {"contentId": content_id, "contentTypeId": "15"}, call_limit
        )

    def _get_detail(
        self, endpoint: str, params: dict[str, str], call_limit: int | None
    ) -> dict[str, Any]:
        items = self._items(self._get_body(endpoint, params, call_limit))
        return items[0] if items else {}

    def _request(
        self, endpoint: str, params: dict[str, str], call_limit: int | None
    ) -> httpx2.Response:
        query = urlencode(COMMON_PARAMS | params) + f"&serviceKey={self._encoded_key}"
        try:
            url = BASE_URL.copy_with(path=BASE_URL.path + endpoint, query=query.encode())
        except httpx2.InvalidURL:
            url = None
        if url is None:
            raise TourApiError("HTTP_ERROR")

        for _ in range(2):
            calls = self.calls.get(endpoint, 0)
            if call_limit is not None and calls >= call_limit:
                break
            self.calls[endpoint] = calls + 1
            with self._redactor.protect_logs():
                try:
                    response = self._client.get(url, timeout=10.0, follow_redirects=False)
                except (httpx2.ConnectError, httpx2.TimeoutException):
                    continue
                except (httpx2.RequestError, httpx2.InvalidURL):
                    break
            if response.status_code < 500:
                return response
        raise TourApiError("HTTP_ERROR")

    def _result_error(self, text: str) -> TourApiError:
        return TourApiError("RESULT_ERROR", self.redact(text)[:200])

    def _get_body(
        self, endpoint: str, params: dict[str, str], call_limit: int | None = None
    ) -> dict[str, Any]:
        response = self._request(endpoint, params, call_limit)
        if 400 <= response.status_code < 500:
            code = "KEY_ERROR" if "SERVICE_KEY" in response.text else "HTTP_ERROR"
            raise TourApiError(code)
        if not response.is_success:
            raise TourApiError("HTTP_ERROR")

        try:
            payload = response.json()
        except ValueError:
            payload = None
        envelope = payload.get("response") if isinstance(payload, dict) else None
        header = envelope.get("header") if isinstance(envelope, dict) else None
        if not isinstance(header, dict):
            raise self._result_error(response.text)
        if header.get("resultCode") != "0000":
            raise self._result_error(str(header.get("resultMsg") or response.text))
        body = envelope.get("body")
        if not isinstance(body, dict):
            raise self._result_error(response.text)
        return body

    @staticmethod
    def _items(body: dict[str, Any]) -> list[dict[str, Any]]:
        items = body.get("items")
        if items == "":
            return []
        if isinstance(items, dict):
            item = items.get("item")
            if isinstance(item, dict):
                return [item]
            if isinstance(item, list) and all(isinstance(entry, dict) for entry in item):
                return item
        raise TourApiError("RESULT_ERROR", "응답 항목의 형식이 올바르지 않습니다.")

    @staticmethod
    def _total_count(body: dict[str, Any]) -> int:
        try:
            return int(body["totalCount"])
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
        raise TourApiError("RESULT_ERROR", "목록 전체 건수가 올바르지 않습니다.")
