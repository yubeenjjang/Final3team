import logging

import httpx2
import pytest

from api.ingestion.facilities import client
from api.ingestion.facilities.normalize import (
    SOURCES, bike_stations, bus_stops, facility_id, hospitals, parking_lots, subway_stations, toilets, unique,
)

KEY = "synthetic/fac+key"


def test_bus_stops_keep_node_id_and_five_digit_ars():
    rows = [
        {"STOPS_NO": "101000003", "STOPS_NM": "서울역버스환승센터", "XCRD": "126.9722570849",
         "YCRD": "37.5551460158", "NODE_ID": "02003", "STOPS_TYPE": "중앙차로"},
        {"STOPS_NO": "123000689", "STOPS_NM": "한강버스.잠실선착장", "XCRD": "127.08", "YCRD": "37.51",
         "NODE_ID": "00001", "STOPS_TYPE": "한강선착장"},
        {"STOPS_NO": "101000999", "STOPS_NM": "좌표 없음", "XCRD": "0", "YCRD": "0", "NODE_ID": "02999"},
        {"STOPS_NO": "101000004", "STOPS_NM": "앞자리 0 빠짐", "XCRD": "126.97", "YCRD": "37.55", "NODE_ID": "2004"},
    ]
    items = bus_stops(rows)
    assert [(i.source_item_id, i.ref_code, i.lat, i.lng, i.region_code) for i in items] == [
        ("101000003", "02003", 37.555146, 126.972257, "SEOUL"),
        ("101000004", "02004", 37.55, 126.97, "SEOUL"),
    ]
    assert {i.category for i in items} == {"bus_stop"}


def test_subway_lines_become_one_station_and_far_namesakes_stay_apart():
    rows = [
        {"BLDN_ID": "0426", "BLDN_NM": "서울역", "ROUTE": "4호선", "LAT": "37.553", "LOT": "126.972"},
        {"BLDN_ID": "0150", "BLDN_NM": "서울역", "ROUTE": "1호선", "LAT": "37.555", "LOT": "126.970"},
        {"BLDN_ID": "2523", "BLDN_NM": "양평", "ROUTE": "5호선", "LAT": "37.5256", "LOT": "126.8861"},
        {"BLDN_ID": "1217", "BLDN_NM": "양평", "ROUTE": "경의중앙선", "LAT": "37.4928", "LOT": "127.4918"},
        {"BLDN_ID": "0228", "BLDN_NM": "서울대입구(관악구청)", "ROUTE": "2호선", "LAT": "37.4812", "LOT": "126.9527"},
    ]
    items = {i.source_item_id: i for i in subway_stations(rows)}
    assert set(items) == {"서울역", "양평#1217", "양평#2523", "서울대입구(관악구청)"}
    seoul = items["서울역"]
    assert (seoul.name, seoul.ref_code, seoul.lat, seoul.lng) == ("서울역", "0150", 37.554, 126.971)
    assert items["양평#2523"].name == "양평역"
    assert items["서울대입구(관악구청)"].name == "서울대입구역"
    assert all(i.region_code is None and i.category == "subway_station" for i in items.values())


def test_bike_toilet_parking_and_hospital_rows():
    bikes = bike_stations([
        {"RNTLS_ID": "ST-100", "ADDR1": "서울특별시 광진구 아차산로 262", "ADDR2": "더샵스타시티 C동 앞",
         "LAT": 37.536667, "LOT": 127.073593},
        {"RNTLS_ID": "ST-10", "ADDR1": "서울특별시 마포구 양화로 93", "ADDR2": "427", "LAT": 37.55, "LOT": 126.91},
        {"RNTLS_ID": "ST-1", "ADDR1": "주소", "ADDR2": "", "LAT": "", "LOT": ""},
    ])
    assert [(b.name, b.ref_code) for b in bikes] == [
        ("따릉이 더샵스타시티 C동 앞", "ST-100"), ("따릉이 서울특별시 마포구 양화로 93", "ST-10"),
    ]
    toilet = toilets([{"OBJECTID": 290041.0, "CONTS_NAME": "박미사랑마을회관", "COORD_X": 126.90752718,
                       "COORD_Y": 37.44056526, "ADDR_NEW": "서울특별시 금천구 시흥대로18길 65-4"}])
    assert [(t.source_item_id, t.category, t.address) for t in toilet] == [
        ("290041", "toilet", "서울특별시 금천구 시흥대로18길 65-4"),
    ]
    parking = parking_lots([
        {"PKLT_CD": "1", "PKLT_NM": "세종로 공영주차장", "ADDR": "종로구", "LAT": 37.57, "LOT": 126.97},
        {"PKLT_CD": "1", "PKLT_NM": "세종로 공영주차장", "ADDR": "종로구", "LAT": 37.57, "LOT": 126.97},
        {"PKLT_CD": "2", "PKLT_NM": "좌표 없음", "LAT": 0.0, "LOT": 0.0},
    ])
    assert [p.source_item_id for p in parking] == ["1"]
    medical = hospitals([
        {"HPID": "A1", "DUTYNAME": "서울대학교병원", "DUTYDIV": "A", "DUTYERYN": "1",
         "WGS84LAT": "37.5796", "WGS84LON": "126.9990", "DUTYADDR": "종로구 대학로 101"},
        {"HPID": "C1", "DUTYNAME": "동네의원", "DUTYDIV": "C", "DUTYERYN": "2", "WGS84LAT": "37.5", "WGS84LON": "127.0"},
        {"HPID": "B1", "DUTYNAME": "응급실 있는 의원", "DUTYDIV": "C", "DUTYERYN": "1",
         "WGS84LAT": "37.5", "WGS84LON": "127.0"},
    ])
    assert [(m.category, m.source_item_id) for m in medical] == [
        ("hospital", "A1"), ("emergency", "A1:emergency"), ("emergency", "B1:emergency"),
    ]


def test_ids_are_stable_and_duplicates_collapse():
    assert facility_id("seoul_bus_stop", "101000003") == facility_id("seoul_bus_stop", "101000003")
    assert facility_id("seoul_bus_stop", "1").startswith("fac_")
    assert facility_id("seoul_bus_stop", "1") != facility_id("seoul_hospital", "1")
    rows = [{"STOPS_NO": "1", "STOPS_NM": "가", "XCRD": "127", "YCRD": "37.5", "NODE_ID": "1"}] * 2
    items, duplicates = unique(bus_stops(rows))
    assert len(items) == 1 and duplicates == 1


def _body(service, rows, total):
    return {service: {"RESULT": {"CODE": "INFO-000"}, "list_total_count": total, "row": rows}}


def test_fetch_rows_pages_and_hides_key(monkeypatch, caplog):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    monkeypatch.setattr(client, "PAGE_SIZE", 2)
    service = SOURCES["seoul_bus_stop"].service
    seen = []

    def handler(request):
        seen.append(request.url.path)
        start = int(request.url.path.rstrip("/").split("/")[-2])
        rows = [{"STOPS_NO": str(n), "NOTE": f"echo {KEY}"} for n in range(start, min(start + 2, 4))]
        return httpx2.Response(200, json=_body(service, rows, 3))

    caplog.set_level(logging.DEBUG)
    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        rows = client.fetch_rows(service, http)
    assert [row["STOPS_NO"] for row in rows] == ["1", "2", "3"]
    assert [path.split("/json/", 1)[-1] for path in seen] == [f"{service}/1/2", f"{service}/3/3"]
    assert all(KEY not in row["NOTE"] for row in rows)
    assert KEY not in caplog.text


@pytest.mark.parametrize(("response", "code"), [
    (httpx2.Response(500), "HTTP_ERROR"),
    (httpx2.Response(200, json={"RESULT": {"CODE": "ERROR-500"}}), "RESULT_ERROR"),
    (httpx2.Response(200, json=_body("busStopLocationXyInfo", [{"STOPS_NO": "1"}], 5)), "INCOMPLETE_LISTING"),
])
def test_fetch_rows_rejects_partial_or_failed_listing(monkeypatch, response, code):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: response)) as http:
        with pytest.raises(client.FacilitySourceError) as error:
            client.fetch_rows("busStopLocationXyInfo", http)
    assert error.value.code == code


def test_fetch_rows_needs_key(monkeypatch):
    monkeypatch.delenv("SEOUL_OPEN_API_KEY", raising=False)
    with pytest.raises(client.FacilitySourceError) as error:
        client.fetch_rows("busStopLocationXyInfo")
    assert error.value.code == "NO_KEY"
