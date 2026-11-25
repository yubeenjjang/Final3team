import asyncio
import json
from datetime import datetime, timedelta

import httpx2
import pytest

from api.providers.kakao import KakaoClient
from api.providers.tmap import TmapClient
from api.schemas.routes import PlaceEndpoint, ReturnRouteRequest
from api.services.festival_lookup import find_festival
from api.services.mock_routes import _candidate
from . import FIXTURES, QUERY, TEST_KEY


@pytest.mark.parametrize(
    ("client_type", "key_env", "fixture", "provider", "tier"),
    [
        (TmapClient, "TMAP_APP_KEY", "tmap_seoul.json", "tmap", "primary"),
        (KakaoClient, "KAKAO_REST_API_KEY", "kakao_transit_seoul.json", "kakao", "secondary"),
    ],
)
def test_P1_candidate_keys_match_mock(
    monkeypatch: pytest.MonkeyPatch,
    client_type: type[TmapClient] | type[KakaoClient],
    key_env: str,
    fixture: str,
    provider: str,
    tier: str,
) -> None:
    monkeypatch.setenv(key_env, TEST_KEY)
    body = json.loads((FIXTURES / fixture).read_text())
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=body))) as http:
        result = client_type(http).query(QUERY)

    festival = asyncio.run(find_festival("fst_000001"))
    assert festival is not None
    request = ReturnRouteRequest(
        request_id="provider-test-01",
        festival_id=festival.festival_id,
        destination=PlaceEndpoint(query="예시 장소"),
    )
    assert set(result.candidates[0]) == set(_candidate(request, festival, secondary=tier == "secondary"))
    assert result.provider == provider
    assert result.provider_tier == tier
    assert datetime.fromisoformat(result.queried_at).utcoffset() == timedelta(hours=9)
