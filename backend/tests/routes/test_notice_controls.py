import asyncio
from datetime import timedelta
from uuid import uuid4

from api.mocks.notices import MemoryNoticeStore
from api.schemas.notices import NoticeCreate
from api.schemas.routes import ReturnRouteRequest
from api.services.real_routes import RealRouteService
from tests.routes.test_p9_real_routes import Clock, FakeProvider, FakeQuota


def test_real_route_key_cache_and_replay_follow_control_schedule():
    clock = Clock()
    provider = FakeProvider("tmap", clock)
    controls = MemoryNoticeStore(lambda: clock.now)
    service = RealRouteService(tmap=lambda: provider, quota=FakeQuota(), now=lambda: clock.now, controls=controls)
    festival_id = "fst_000001"
    actor = uuid4()
    controls.create("ntc_SCHEDULED", NoticeCreate(
        festival_id=festival_id, type="no_stop", title="시험 무정차", content="시험 본문",
        effective_from=clock.now + timedelta(seconds=10), effective_to=clock.now + timedelta(seconds=20),
        source_url="https://example.test/official",
    ), actor)
    controls.change("ntc_SCHEDULED", "approve", actor)

    async def submit(suffix):
        body = {"festival_id": festival_id, "request_id": f"scheduled-control-{suffix}",
                "destination": {"lat": 37.5, "lng": 126.9}}
        status, response = await service.create_route("return", ReturnRouteRequest(**body), body)
        assert status == 200
        return response

    async def scenario():
        before = await submit("before")
        assert before["route_status"] == "ready"
        assert (await submit("cache"))["route_status"] == "ready"
        assert len(provider.queries) == 1

        clock.now += timedelta(seconds=10)
        replay = await submit("before")
        assert replay["route_request_id"] == before["route_request_id"]
        assert replay["error"]["code"] == "ROUTE_CONTROL_CHANGED"
        during = await submit("during")
        assert "시험 무정차" in during["notices"][0]
        assert len(provider.queries) == 2
        clock.now += timedelta(seconds=10)
        after = await submit("after")
        assert all("시험 무정차" not in notice for notice in after["notices"])
        assert len(provider.queries) == 3
        keys = {service._records[item["route_request_id"]].route_key for item in (before, during, after)}
        assert len(keys) == 3 and all(key.startswith("v2:") for key in keys)

    asyncio.run(scenario())
