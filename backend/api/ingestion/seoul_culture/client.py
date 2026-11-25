import os
from contextlib import nullcontext
from urllib.parse import quote

import httpx2

from api.providers.tourapi import _KeyRedactor

SERVICE = "culturalEventInfo"
BASE_URL = httpx2.URL(scheme="http", host="openapi.seoul.go.kr", port=8088)
PAGE_SIZE = 1000


class SeoulCultureError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _read_page(response: httpx2.Response) -> tuple[int, list[dict]]:
    if not response.is_success:
        raise SeoulCultureError("HTTP_ERROR")
    try:
        body = response.json()
    except ValueError:
        raise SeoulCultureError("INVALID_RESPONSE") from None
    if not isinstance(body, dict):
        raise SeoulCultureError("INVALID_RESPONSE")
    data = body.get(SERVICE, body)
    if not isinstance(data, dict) or not isinstance(data.get("RESULT"), dict):
        raise SeoulCultureError("INVALID_RESPONSE")
    code = data["RESULT"].get("CODE")
    if code == "INFO-200":
        return 0, []
    if code != "INFO-000":
        raise SeoulCultureError("RESULT_ERROR")

    total, rows = data.get("list_total_count"), data.get("row", [])
    if type(total) is not int or total < 0 or not isinstance(rows, list) or any(
        not isinstance(row, dict) for row in rows
    ):
        raise SeoulCultureError("INVALID_RESPONSE")
    return total, rows


def fetch_events(http_client: httpx2.Client | None = None) -> list[dict]:
    key = os.environ.get("SEOUL_OPEN_API_KEY", "").strip()
    if not key:
        raise SeoulCultureError("NO_KEY")
    encoded_key = quote(key, safe="")
    redactor = _KeyRedactor(key, encoded_key)
    rows: list[dict] = []
    total = None
    with nullcontext(http_client) if http_client is not None else httpx2.Client() as client:
        while total is None or len(rows) < total:
            start = len(rows) + 1
            end = min(start + PAGE_SIZE - 1, total) if total is not None else start + PAGE_SIZE - 1
            url = BASE_URL.copy_with(raw_path=f"/{encoded_key}/json/{SERVICE}/{start}/{end}".encode())
            with redactor.protect_logs():
                try:
                    response = client.get(url, timeout=5.0, follow_redirects=False)
                except (httpx2.RequestError, httpx2.InvalidURL):
                    raise SeoulCultureError("HTTP_ERROR") from None
            page_total, page = _read_page(response)
            if total is None:
                total = page_total
            if page_total != total or len(page) != min(PAGE_SIZE, total - len(rows)):
                raise SeoulCultureError("INCOMPLETE_LISTING")
            # 공급원이 설정값을 되돌려 보내더라도 DB에 키가 남지 않게 한다.
            rows.extend(
                {name: redactor.redact(value) if isinstance(value, str) else value for name, value in row.items()}
                for row in page
            )
    return rows
