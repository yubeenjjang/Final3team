"""Small, bounded Redis connectivity probe shared by API health checks."""

import os

from redis.asyncio import Redis


def configured_url() -> str | None:
    return os.environ.get("REDIS_URL") or None


async def ping() -> bool:
    url = configured_url()
    if url is None:
        raise ValueError("REDIS_URL is not configured")
    client = Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    try:
        return bool(await client.ping())
    finally:
        await client.aclose()
