from uuid import uuid4

from fastapi.testclient import TestClient


def test_search_detail_return_result_same_festival(client: TestClient, monkeypatch):
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    monkeypatch.delenv("ROUTE_PROVIDER", raising=False)

    page = client.get("/api/v1/festivals", params={"q": "광화문"})
    assert page.status_code == 200
    selected = page.json()["items"][0]
    festival_id = selected["festival_id"]
    detail = client.get(f"/api/v1/festivals/{festival_id}")
    assert detail.status_code == 200
    assert detail.json()["festival_id"] == festival_id

    submitted = client.post("/api/v1/routes/return", json={
        "request_id": f"midterm-{uuid4().hex}", "festival_id": festival_id,
        "destination": {"query": "서울역"},
    })
    assert submitted.status_code == 202
    queued = submitted.json()
    token = queued["route_access_token"]
    assert token

    for _ in range(4):
        response = client.get(queued["status_url"], headers={"X-Route-Access-Token": token})
        assert response.status_code == 200
        result = response.json()
        if result["route_status"] == "ready":
            assert result["festival_id"] == festival_id
            assert result["route_candidates"]
            assert result["origin"]["lat"] == detail.json()["lat"]
            break
    else:
        raise AssertionError("경로 결과가 준비되지 않았습니다")
