#!/usr/bin/env python3
"""놀다가 외부 API 로컬 테스트 도구.

키는 메모리에서만 쓰고 파일에 저장하지 않는다. 결과는 JSON으로 저장한다.
"""
import datetime as dt
import json
import os
import secrets
import subprocess
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("NOLDAGA_OUT", BASE_DIR / "결과"))
SUMMARY = "_호출요약.json"
TOKEN = secrets.token_urlsafe(24)
MAX_BYTES = 5_000_000
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
# TMAP 약관(저장 후 24시간 이상 사용 불가)과 카카오 경로 저장 제한 때문에 경로 원본은 자동으로 지운다.
# 확인 주기(10분)가 있어도 24시간을 넘기지 않도록 23시간이 지나면 지운다.
RESTRICTED_PREFIXES = ("tmap_", "kakao-transit_", "kakao-walk_")
RETENTION = dt.timedelta(hours=23)
PURGE_INTERVAL_SECONDS = 600
SUMMARY_LOCK = threading.Lock()
SKIP_WALK = {"row", "item", "path", "FCST_PPLTN", "realtimeArrivalList", "documents"}

GWANGHWAMUN = ("126.9768", "37.5759")
SEOUL_STATION = ("126.9707", "37.5547")
BUSAN_STATION = ("129.0414", "35.1151")
SEOMYEON = ("129.0596", "35.1578")
TOUR = "https://apis.data.go.kr/B551011/KorService2"
KMA = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
TAGO_STOP = "https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getCrdntPrxmtSttnList"
TAGO_ARRIVAL = "https://apis.data.go.kr/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList"
TMAP_TRANSIT = "https://apis.openapi.sk.com/transit/routes"
KAKAO_ROUTE = "https://dapi.kakao.com/v2/routing"
SEOUL_BUS = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll"
KAKAO = "https://dapi.kakao.com/v2/local/search/category.json"
DATA_API = "https://apis.data.go.kr"
STANDARD_API = "https://api.data.go.kr/openapi"
UTIC = "http://www.utic.go.kr/guide/imsOpenData.do"


def query_url(base, params):
    return base + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def seoul_url(key, service, tail="", fmt="json", start=1, end=5):
    safe_key = urllib.parse.quote(key, safe="")
    safe_tail = urllib.parse.quote(tail, safe="")
    return f"http://openapi.seoul.go.kr:8088/{safe_key}/{fmt}/{service}/{start}/{end}/{safe_tail}"


def call(rank, group, name, slug, key_name, make, expect_error=False, note="", depends=None, once=False, tries=None):
    return {
        "rank": rank, "group": group, "name": name, "slug": slug, "key_name": key_name,
        "make": make, "expect_error": expect_error, "note": note, "depends": depends, "once": once, "tries": tries,
    }


def build_calls(now):
    today = now.strftime("%Y%m%d")
    base = now - dt.timedelta(hours=1)
    base_date, base_time = base.strftime("%Y%m%d"), base.strftime("%H00")
    last_month = (now.replace(day=1) - dt.timedelta(days=1)).strftime("%Y%m")
    week_ago = (now - dt.timedelta(days=7)).strftime("%Y%m%d")

    def tmap(start, end, depart=None):
        # 무료 한도가 하루 10건이라 가이드 3절의 같은 좌표 세트만 부른다.
        def make(key, _ctx=None):
            body = {"startX": start[0], "startY": start[1], "endX": end[0], "endY": end[1],
                    "count": 3, "lang": 0, "format": "json"}
            if depart:
                body["searchDttm"] = depart
            # 공식 이용절차 예시의 헤더(accept, appKey, content-type)를 그대로 보낸다.
            return TMAP_TRANSIT, {"Accept": "application/json", "appKey": key, "Content-Type": "application/json"}, body
        return make

    def kakao_route(kind, start, end):
        def make(key, _ctx=None):
            url = query_url(f"{KAKAO_ROUTE}/{kind}", {"start_x": start[0], "start_y": start[1], "end_x": end[0], "end_y": end[1]})
            return url, {"Authorization": f"KakaoAK {key}"}
        return make

    def festival(region):
        def make(key, _ctx=None):
            return query_url(f"{TOUR}/searchFestival2", {
                "serviceKey": key, "MobileOS": "ETC", "MobileApp": "NOLDAGA", "_type": "json",
                "eventStartDate": today, "numOfRows": 10, "pageNo": 1, "lDongRegnCd": region,
            }), {}
        return make

    def detail(content_id):
        def make(key, _ctx=None):
            return query_url(f"{TOUR}/detailIntro2", {
                "serviceKey": key, "MobileOS": "ETC", "MobileApp": "NOLDAGA", "_type": "json",
                "contentId": content_id, "contentTypeId": 15, "numOfRows": 10, "pageNo": 1,
            }), {}
        return make

    def overview(content_id):
        def make(key, _ctx=None):
            return query_url(f"{TOUR}/detailCommon2", {
                "serviceKey": key, "MobileOS": "ETC", "MobileApp": "NOLDAGA", "_type": "json",
                "contentId": content_id, "numOfRows": 10, "pageNo": 1,
            }), {}
        return make

    def seoul_bus(route_id):
        def make(key, _ctx=None):
            return query_url(SEOUL_BUS, {"serviceKey": key, "busRouteId": route_id, "resultType": "json"}), {}
        return make

    def weather(nx, ny):
        def make(key, _ctx=None):
            return query_url(KMA, {
                "serviceKey": key, "dataType": "JSON", "numOfRows": 10, "pageNo": 1,
                "base_date": base_date, "base_time": base_time, "nx": nx, "ny": ny,
            }), {}
        return make

    def people(place):
        return lambda key, _ctx=None: (seoul_url(key, "citydata_ppltn", place), {})

    def seoul(service, fmt="json"):
        return lambda key, _ctx=None: (seoul_url(key, service, fmt=fmt), {})

    def subway(key, _ctx=None):
        safe_key = urllib.parse.quote(key, safe="")
        station = urllib.parse.quote("서울", safe="")
        return f"http://swopenAPI.seoul.go.kr/api/subway/{safe_key}/json/realtimeStationArrival/0/5/{station}", {}

    def stops(point):
        def make(key, _ctx=None):
            return query_url(TAGO_STOP, {
                "serviceKey": key, "_type": "json", "numOfRows": 5, "pageNo": 1,
                "gpsLati": point[1], "gpsLong": point[0],
            }), {}
        return make

    def arrival(key, ctx):
        return query_url(TAGO_ARRIVAL, {
            "serviceKey": key, "_type": "json", "numOfRows": 10, "pageNo": 1,
            "cityCode": ctx["citycode"], "nodeId": ctx["nodeid"],
        }), {}

    def kakao(point):
        def make(key, _ctx=None):
            url = query_url(KAKAO, {"category_group_code": "FD6", "x": point[0], "y": point[1], "radius": 1000})
            return url, {"Authorization": f"KakaoAK {key}"}
        return make

    def data_api(url, key_param="serviceKey", **params):
        def make(key, _ctx=None):
            return query_url(url, {key_param: key, **params}), {}
        return make

    def standard(name):
        return data_api(f"{STANDARD_API}/{name}", pageNo=1, numOfRows=10, type="json")

    def tour_stat(path, **params):
        return data_api(f"{DATA_API}/B551011/{path}", MobileOS="ETC", MobileApp="NOLDAGA", _type="json", pageNo=1, numOfRows=10, **params)

    def address(path, region):
        def make(key, _ctx=None):
            return query_url(f"{DATA_API}/1741000/{path}", {
                "serviceKey": key, "pageNo": 1, "numOfRows": 10, "returnType": "json",
                "cond[LCTN_ROAD_NM_ADDR::LIKE]": region,
            }), {}
        return make

    def emergency(point):
        return data_api(f"{DATA_API}/B552657/ErmctInfoInqireService/getEgytLcinfoInqire", "ServiceKey",
                        WGS84_LON=point[0], WGS84_LAT=point[1], pageNo=1, numOfRows=10)

    # 관광 수요 강도는 월 1회(매월 16일) 갱신되고 최근 달은 비어 있을 수 있어 지난 18개월을 차례로 시도한다.
    # 공식 매뉴얼 예시가 2025-09라서 그 달까지 닿도록 범위를 잡았다.
    recent_months = []
    cursor = now.replace(day=1)
    for _ in range(18):
        cursor = (cursor - dt.timedelta(days=1)).replace(day=1)
        recent_months.append({"baseYm": cursor.strftime("%Y%m")})

    def demand(area, signgu=None, index=None, base_ym=None):
        def make(key, ctx=None):
            params = {
                "serviceKey": key, "MobileOS": "ETC", "MobileApp": "NOLDAGA", "_type": "json",
                "pageNo": 1, "numOfRows": 10, "baseYm": base_ym or (ctx or {}).get("baseYm", last_month), "areaCd": area,
            }
            if signgu:
                params["signguCd"] = signgu
            if index:
                params["tarSjrnDsIxCd"] = index
            return query_url(f"{DATA_API}/B551011/AreaTarDemDsService/areaTarSjrnDsList", params), {}
        return make

    def standard_filter(name):
        # 표준데이터 API는 응답 필드 이름으로 거를 수 있다. 어떤 필드가 먹히는지 차례로 시도한다.
        def make(key, ctx=None):
            return query_url(f"{STANDARD_API}/{name}", {"serviceKey": key, "pageNo": 1, "numOfRows": 10, "type": "json", **(ctx or {})}), {}
        return make

    # instt_nm은 제공기관명과 정확히 일치해야 한다(축제는 "부산광역시", 주차장은 구청 단위가 많음).
    busan_filters = [{"instt_nm": "부산광역시"}, {"instt_nm": "부산광역시 해운대구"}, {"instt_nm": "부산광역시 부산진구"}, {"instt_nm": "부산광역시 동구"}]
    tomorrow = (now + dt.timedelta(days=1)).strftime("%Y%m%d")

    def utic(key, _ctx=None):
        return query_url(UTIC, {"key": key}), {}

    code_note = "지역 코드는 후보값이라 참고문서 확인 필요"
    stop_seomyeon = "tago-정류소_서면"
    route_note = "카카오 경로 응답은 저장 제한: 시험 확인용으로만 보관"
    tmap_note = "무료 하루 10건: 같은 날 다시 부르지 않음"
    return [
        call(1, "TMAP 길찾기(1차)", "① 광화문→서울역 지금", "tmap_광화문-서울역", "tmap", tmap(GWANGHWAMUN, SEOUL_STATION), note=tmap_note, once=True),
        call(1, "TMAP 길찾기(1차)", "② 부산역→서면역 지금", "tmap_부산역-서면역", "tmap", tmap(BUSAN_STATION, SEOMYEON), note=tmap_note, once=True),
        call(1, "TMAP 길찾기(1차)", "③ 광화문→서울역 22:00", "tmap_광화문-서울역-2200", "tmap", tmap(GWANGHWAMUN, SEOUL_STATION, f"{today}2200"), note=tmap_note, once=True),
        call(1, "TMAP 길찾기(1차)", "④ 광화문→서울역 내일 03:00", "tmap_광화문-서울역-0300", "tmap", tmap(GWANGHWAMUN, SEOUL_STATION, f"{tomorrow}0300"), note="막차 이후 시각으로 searchDttm 적용 여부 확인. 오늘 TMAP 4번째 호출", once=True),
        call(1, "TMAP 길찾기(1차)", "오류: 키 오류", "tmap_오류-키오류", "tmap", tmap(GWANGHWAMUN, SEOUL_STATION), True, once=True),
        call(1, "카카오맵 대중교통(2차)", "① 광화문→서울역", "kakao-transit_광화문-서울역", "kakao", kakao_route("publictraffic", GWANGHWAMUN, SEOUL_STATION), note=route_note),
        call(1, "카카오맵 대중교통(2차)", "② 부산역→서면역", "kakao-transit_부산역-서면역", "kakao", kakao_route("publictraffic", BUSAN_STATION, SEOMYEON), note=route_note),
        call(1, "카카오맵 대중교통(2차)", "오류: 키 오류", "kakao-transit_오류-키오류", "kakao", kakao_route("publictraffic", GWANGHWAMUN, SEOUL_STATION), True),
        call(1, "카카오맵 도보(2차)", "광화문→서울역", "kakao-walk_광화문-서울역", "kakao", kakao_route("walk", GWANGHWAMUN, SEOUL_STATION), note=route_note),
        call(1, "서울 버스도착정보", "노선 100100118 전체 정류소", "seoul-bus_100100118", "data", seoul_bus("100100118"), note="공식 예시 노선. 혼잡=brdrde_Num1·rerdie_Div1, 정류소=arsId"),
        call(1, "서울 버스도착정보", "오류: 키 오류", "seoul-bus_오류-키오류", "data", seoul_bus("100100118"), True),
        call(1, "TourAPI 축제 검색", "서울", "tourapi_서울", "data", festival(11)),
        call(1, "TourAPI 축제 검색", "부산", "tourapi_부산", "data", festival(26)),
        call(1, "TourAPI 축제 검색", "오류: 키 오류", "tourapi_오류-키오류", "data", festival(11), True),
        call(1, "TourAPI 축제 상세", "서울 광화문 마켓", "tourapi-상세_광화문마켓", "data", detail(3035607)),
        call(1, "TourAPI 축제 상세", "부산 게임문화축제", "tourapi-상세_게임문화축제", "data", detail(3360113)),
        call(1, "TourAPI 축제 상세", "오류: 키 오류", "tourapi-상세_오류-키오류", "data", detail(3035607), True),
        call(1, "TourAPI 축제 소개", "서울 광화문 마켓", "tourapi-소개_광화문마켓", "data", overview(3035607), note="overview 필드 확인"),
        call(1, "TourAPI 축제 소개", "부산 게임문화축제", "tourapi-소개_게임문화축제", "data", overview(3360113), note="overview 필드 확인"),
        call(1, "서울 실시간 인구", "광화문·덕수궁", "seoul-ppltn_광화문덕수궁", "seoul", people("광화문·덕수궁")),
        call(1, "서울 실시간 인구", "서울역", "seoul-ppltn_서울역", "seoul", people("서울역")),
        call(1, "서울 실시간 인구", "오류: 없는 장소", "seoul-ppltn_오류-없는장소", "seoul", people("없는장소"), True, "정식 키에서만 의미 있음", "real_key"),
        call(1, "기상청 날씨", "서울 격자 60,127", "kma_서울", "data", weather(60, 127)),
        call(1, "기상청 날씨", "부산역 격자 97,74", "kma_부산", "data", weather(97, 74)),
        call(1, "기상청 날씨", "오류: 키 오류", "kma_오류-키오류", "data", weather(60, 127), True),
        call(2, "TAGO 버스 정류소", "광화문 근처", "tago-정류소_광화문", "data", stops(GWANGHWAMUN)),
        call(2, "TAGO 버스 정류소", "부산역 근처", "tago-정류소_부산역", "data", stops(BUSAN_STATION)),
        call(2, "TAGO 버스 정류소", "서면역 근처", stop_seomyeon, "data", stops(SEOMYEON)),
        call(2, "TAGO 버스 정류소", "오류: 키 오류", "tago-정류소_오류-키오류", "data", stops(GWANGHWAMUN), True),
        call(2, "TAGO 버스 도착", "서면역 근처 정류소", "tago-도착_서면", "data", arrival, depends=stop_seomyeon, note="서울 버스는 서울 버스도착정보로 확인"),
        call(2, "경찰청 교통 돌발", "전국", "police-incident", "utic", utic, note="UTIC 인증키와 IP 등록 필요. 응답에서 서울·부산 건 확인"),
        call(2, "경찰청 교통 돌발", "오류: 키 오류", "police-incident_오류-키오류", "utic", utic, True),
        call(2, "서울 지하철 도착", "서울역", "seoul-subway_서울역", "subway", subway),
        call(2, "서울 지하철 도착", "오류: 키 오류", "seoul-subway_오류-키오류", "subway", subway, True),
        call(2, "서울 시영주차장", "1~5건", "seoul-parking", "seoul", seoul("GetParkingInfo")),
        call(2, "서울 교통 돌발", "1~5건", "seoul-accinfo", "seoul", seoul("AccInfo", "xml"), note="원본 XML을 JSON으로 변환"),
        call(2, "서울 문화행사", "1~5건", "seoul-culture", "seoul", seoul("culturalEventInfo")),
        call(3, "전국문화축제표준데이터", "전국 10건", "festival-standard", "data", standard("tn_pubr_public_cltur_fstvl_api")),
        call(3, "전국문화축제표준데이터", "부산 필터", "festival-standard_부산", "data", standard_filter("tn_pubr_public_cltur_fstvl_api"), note="instt_nm·rdnmadr·lnmadr 순서로 부산 필터 시도", tries=busan_filters),
        call(3, "전국문화축제표준데이터", "오류: 키 오류", "festival-standard_오류-키오류", "data", standard("tn_pubr_public_cltur_fstvl_api"), True),
        call(3, "관광지 집중률 예측", "서울 종로구", "tourist-rate_서울", "data", tour_stat("TatsCnctrRateService/tatsCnctrRatedList", areaCd=11, signguCd=11110), note=code_note),
        call(3, "관광지 집중률 예측", "부산 해운대구", "tourist-rate_부산", "data", tour_stat("TatsCnctrRateService/tatsCnctrRatedList", areaCd=26, signguCd=26350), note=code_note),
        call(3, "관광지 집중률 예측", "오류: 키 오류", "tourist-rate_오류-키오류", "data", tour_stat("TatsCnctrRateService/tatsCnctrRatedList", areaCd=11, signguCd=11110), True),
        call(3, "지역별 관광 수요 강도", "서울 체류 강도", "tour-demand_서울", "data", demand(11), note="값이 있는 가장 최근 달을 찾아 호출(저장 주소의 baseYm 확인)", tries=recent_months),
        call(3, "지역별 관광 수요 강도", "부산 체류 강도", "tour-demand_부산", "data", demand(26), note="값이 있는 가장 최근 달을 찾아 호출(저장 주소의 baseYm 확인)", tries=recent_months),
        call(3, "지역별 관광 수요 강도", "매뉴얼 예시 그대로(서울 구로구)", "tour-demand_매뉴얼예시", "data", demand(11, 11530, 2101, "202509"), note="매뉴얼 예시: baseYm 202509·signguCd 11530·지표 2101"),
        call(3, "지역별 관광 수요 강도", "부산 해운대구·지표 2101", "tour-demand_부산-해운대", "data", demand(26, 26350, 2101), note="시군구·지표 코드를 넣고 최근 달부터 시도", tries=recent_months),
        call(3, "지역별 관광 수요 강도", "오류: 키 오류", "tour-demand_오류-키오류", "data", demand(11), True),
        call(3, "공중화장실", "서울 주소", "toilet_서울", "data", address("public_restroom_info_v2/info_v2", "서울")),
        call(3, "공중화장실", "부산 주소", "toilet_부산", "data", address("public_restroom_info_v2/info_v2", "부산")),
        call(3, "공중화장실", "오류: 키 오류", "toilet_오류-키오류", "data", address("public_restroom_info_v2/info_v2", "서울"), True),
        call(3, "전국주차장정보표준데이터", "전국 10건", "parking-standard", "data", standard("tn_pubr_prkplce_info_api")),
        call(3, "전국주차장정보표준데이터", "부산 필터", "parking-standard_부산", "data", standard_filter("tn_pubr_prkplce_info_api"), note="instt_nm·rdnmadr·lnmadr 순서로 부산 필터 시도", tries=busan_filters),
        call(3, "전국주차장정보표준데이터", "오류: 키 오류", "parking-standard_오류-키오류", "data", standard("tn_pubr_prkplce_info_api"), True),
        call(3, "병원·응급실", "광화문 근처", "emergency_광화문", "data", emergency(GWANGHWAMUN)),
        call(3, "병원·응급실", "부산역 근처", "emergency_부산역", "data", emergency(BUSAN_STATION)),
        call(3, "병원·응급실", "오류: 키 오류", "emergency_오류-키오류", "data", emergency(GWANGHWAMUN), True),
        call(3, "카카오 장소 검색", "광화문 음식점", "kakao_광화문-음식점", "kakao", kakao(GWANGHWAMUN)),
        call(3, "카카오 장소 검색", "부산역 음식점", "kakao_부산역-음식점", "kakao", kakao(BUSAN_STATION)),
        call(3, "카카오 장소 검색", "오류: 키 오류", "kakao_오류-키오류", "kakao", kakao(GWANGHWAMUN), True),
        call(4, "택시 승강장(조사)", "서울", "taxi-stand_서울", "data", standard_filter("tn_pubr_public_taxi_stand_api"), note="전국택시승강장표준데이터(15139230) 활용신청 필요", tries=[{"CTPV_NM": "서울특별시"}]),
        call(4, "택시 승강장(조사)", "부산", "taxi-stand_부산", "data", standard_filter("tn_pubr_public_taxi_stand_api"), note="전국택시승강장표준데이터(15139230) 활용신청 필요", tries=[{"CTPV_NM": "부산광역시"}]),
        call(4, "택시 승강장(조사)", "오류: 키 오류", "taxi-stand_오류-키오류", "data", standard_filter("tn_pubr_public_taxi_stand_api"), True),
        call(4, "자전거 대여소(조사)", "전국 공영자전거", "bike-station_전국", "data", data_api(f"{DATA_API}/B551982/pbdo_v2/inf_101_00010001_v2", pageNo=1, numOfRows=10, type="json"), note="행정안전부 전국 공영자전거 대여소"),
        call(4, "자전거 대여소(조사)", "서울 따릉이", "bike-station_서울", "seoul", seoul("tbCycleStationInfo"), note="서울 일반 인증키 사용"),
    ]


def xml_to_obj(element):
    children = list(element)
    if not children:
        return (element.text or "").strip()
    out = {}
    for child in children:
        value = xml_to_obj(child)
        if child.tag in out:
            if not isinstance(out[child.tag], list):
                out[child.tag] = [out[child.tag]]
            out[child.tag].append(value)
        else:
            out[child.tag] = value
    return out


def parse_body(text, content_type):
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except ValueError:
        pass
    try:
        root = ET.fromstring(stripped)
        return {"_sourceFormat": "xml", root.tag: xml_to_obj(root)}
    except ET.ParseError:
        return {"_sourceFormat": content_type or "text", "text": text}


def walk(obj, depth=0):
    if depth > 4:
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
        for key, value in obj.items():
            if key not in SKIP_WALK:
                yield from walk(value, depth + 1)
    elif isinstance(obj, list) and obj:
        yield from walk(obj[0], depth + 1)


def inspect(obj, http_status):
    code = message = count = None
    has_error = False
    for key, value in walk(obj):
        upper = key.upper()
        if upper == "ERRMSG" and value:
            has_error, code = True, str(value)
        elif upper == "ERROR" and value:
            has_error = True
        elif upper == "ERRORTYPE" and value:
            has_error, code = True, str(value)
        elif upper == "STATUS" and isinstance(value, int) and not isinstance(value, bool) and value != 200:
            # TMAP은 경로가 없을 때도 HTTP 200에 result.status(11~14)로 오류를 알린다.
            has_error, code = True, str(value)
        elif upper == "STATUS" and isinstance(value, str) and not value.isdigit():
            if value != "OK":
                has_error, code = True, value
        elif code is None and upper in {"RESULTCODE", "CODE", "RESULT.CODE", "HEADERCD"} and not isinstance(value, (dict, list)):
            code = str(value)
        elif message is None and upper in {"RESULTMSG", "MESSAGE", "RESULT.MESSAGE", "RETURNAUTHMSG", "HEADERMSG"} and not isinstance(value, (dict, list)):
            message = str(value)
        elif count is None and upper in {"TOTALCOUNT", "LIST_TOTAL_COUNT", "TOTAL_COUNT"} and not isinstance(value, (dict, list)):
            count = value
    # K0: 행정안전부 한국지역정보개발원 API의 정상 코드(resultMsg NORMAL_SERVICE)
    ok_codes = {None, "0", "00", "000", "0000", "200", "INFO-000", "K0"}
    success = http_status < 400 and not has_error and code in ok_codes
    return success, code, message, count


def nearby_stops(path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        items = obj["response"]["body"]["items"]["item"]
        items = items if isinstance(items, list) else [items]
        return [{"citycode": item["citycode"], "nodeid": item["nodeid"]} for item in items[:5]]
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return []


def scrub(text, secrets_to_hide):
    for value in secrets_to_hide:
        if value:
            text = text.replace(value, "{KEY}")
    return text


def fetch(url, headers, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method="POST" if data else "GET", headers={"User-Agent": BROWSER_UA, "Accept": "text/html,application/json,application/xml,*/*", "Accept-Language": "ko-KR,ko;q=0.9", **headers})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read(MAX_BYTES)
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read(MAX_BYTES)


def clean_key(value):
    value = unicodedata.normalize("NFKC", value or "")
    value = "".join(ch for ch in value if not ch.isspace() and unicodedata.category(ch) not in {"Cf", "Cc"})
    value = value.strip("'\"`")
    return urllib.parse.unquote(value) if "%" in value else value


def key_checks(raw_keys, keys):
    labels = {"data": "공공데이터포털", "seoul": "서울 일반", "subway": "서울 지하철", "tmap": "TMAP", "kakao": "카카오", "utic": "UTIC"}
    checks = []
    for name, label in labels.items():
        key = keys[name]
        if not key:
            continue
        same = [labels[other] for other in labels if other != name and keys[other] == key]
        checks.append({
            "label": label, "length": len(key), "head": key[:4], "tail": key[-4:],
            "cleaned": key != (raw_keys.get(name) or ""), "ascii": key.isascii(), "sameAs": same,
        })
    return checks


def is_restricted(filename):
    return filename.split("_", 1)[-1].startswith(RESTRICTED_PREFIXES)


def purge_restricted():
    """보관 기간이 지난 경로 원본을 지우고, 호출 요약에는 지운 시각만 남긴다."""
    if not OUT_DIR.exists():
        return []
    now = dt.datetime.now()
    removed = []
    for path in OUT_DIR.glob("*.json"):
        if path.name == SUMMARY or not is_restricted(path.name):
            continue
        saved_at = dt.datetime.fromtimestamp(path.stat().st_mtime)
        if now - saved_at >= RETENTION:
            path.unlink(missing_ok=True)
            removed.append(path.name)
    if removed:
        with SUMMARY_LOCK:
            summary = load_summary()
            for name in removed:
                if name in summary:
                    summary[name]["deletedAt"] = now.isoformat(timespec="seconds")
            (OUT_DIR / SUMMARY).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return removed


def purge_loop():
    while True:
        try:
            purge_restricted()
        except OSError:
            pass
        time.sleep(PURGE_INTERVAL_SECONDS)


def load_summary():
    try:
        return json.loads((OUT_DIR / SUMMARY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run_one(item, key, now, overwrite, previous):
    filename = f"{now:%Y-%m-%d}_{item['slug']}.json"
    path = OUT_DIR / filename
    row = {"group": item["group"], "name": item["name"], "file": filename, "note": item["note"]}
    if item["depends"] == "real_key" and key == "sample":
        return {**row, "verdict": "건너뜀: 샘플 키로는 확인 불가", "state": "skip"}
    contexts = item["tries"] or [None]
    dependent = item["depends"] and item["depends"] != "real_key"
    if dependent:
        contexts = nearby_stops(OUT_DIR / f"{now:%Y-%m-%d}_{item['depends']}.json")
        if not contexts:
            return {**row, "verdict": "건너뜀: 정류소 결과 없음", "state": "skip"}
    used_key = key[:-1] if item["expect_error"] and "없는" not in item["name"] else key
    safe_key = urllib.parse.quote(used_key, safe="")
    first = item["make"](used_key, contexts[0])
    first_url = first[0].replace(safe_key, "{KEY}")
    first_body = first[2] if len(first) > 2 else None
    prior = previous.get(filename) or {}
    failed_name = f"{now:%Y-%m-%d}_{item['slug']}_실패.json"
    if item["once"]:
        # 키 인증 실패(401·403)는 한도를 쓰지 않으므로 다시 시도할 수 있게 둔다.
        failed = previous.get(failed_name) or {}
        used_quota = prior.get("state") in {"ok", "warn"} or (
            failed and failed.get("http") not in {401, 403} and failed.get("code") != "INVALID_API_KEY")
        if used_quota:
            return {**row, "verdict": "오늘 이미 호출함(한도 보호)", "state": "skip"}
    same_request = dependent or (prior.get("url") == first_url and prior.get("body") == first_body)
    # 정상 판정이고 같은 조건일 때만 재사용한다. 빈 응답이나 조건이 바뀐 호출은 다시 부른다.
    if path.exists() and not overwrite and prior.get("state") == "ok" and same_request:
        return {**row, "verdict": "기존 파일 유지", "state": "skip"}
    hide = sorted({value for raw in (key, key[:-1]) if len(raw) >= 12
                   for value in (raw, urllib.parse.quote(raw, safe=""), urllib.parse.quote_plus(raw))}, key=len, reverse=True)
    for index, context in enumerate(contexts):
        made = item["make"](used_key, context)
        url, headers = made[0], made[1]
        request_body = made[2] if len(made) > 2 else None
        masked_url = url.replace(safe_key, "{KEY}")
        try:
            status, content_type, body = fetch(url, headers, request_body)
        except Exception as error:  # 네트워크 오류 메시지에도 키가 남지 않게 종류만 기록한다.
            return {**row, "url": masked_url, "verdict": f"연결 실패: {type(error).__name__}", "state": "bad"}
        text = scrub(body.decode("utf-8", "replace"), hide)
        obj = parse_body(text, content_type.split(";")[0])
        success, code, message, count = inspect(obj, status)
        if (success and str(count) != "0") or index == len(contexts) - 1:
            break
    empty = str(count) == "0"
    if item["depends"] == "real_key" and code == "INFO-100":
        verdict, state = "실패: 인증키 거부", "bad"
    elif item["expect_error"]:
        verdict, state = ("주의: 오류가 나지 않음", "warn") if success else ("오류 응답 확인", "ok")
    elif not success:
        verdict, state = "실패", "bad"
    elif empty:
        verdict, state = "빈 응답", "warn"
    else:
        verdict, state = "정상", "ok"
    # 실패 응답은 별도 이름으로 저장해야 다음 실행 때 다시 호출된다.
    if state == "bad" and "SERVICE_KEY" in str(code):
        row["note"] = "이 API의 활용신청·승인 상태 확인 필요"
    if state == "bad":
        filename, path = failed_name, OUT_DIR / failed_name
        row["file"] = filename
    else:
        (OUT_DIR / failed_name).unlink(missing_ok=True)
        row["replaces"] = failed_name
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if is_restricted(filename):
        delete_at = dt.datetime.now() + RETENTION
        row["note"] = " · ".join(x for x in (row["note"], f"원본은 {delete_at:%m-%d %H:%M}에 자동 삭제(필드는 그 전에 정리표로)") if x)
    if request_body is not None:
        row["body"] = request_body
    return {**row, "url": masked_url, "calledAt": dt.datetime.now().isoformat(timespec="seconds"),
            "http": status, "code": code, "message": message, "count": count, "verdict": verdict, "state": state}


def run_all(payload):
    purge_restricted()
    raw_keys = payload.get("keys", {})
    keys = {name: clean_key(raw_keys.get(name)) for name in ("data", "seoul", "subway", "tmap", "kakao", "utic")}
    ranks = {int(rank) for rank in payload.get("ranks", [])}
    overwrite = bool(payload.get("overwrite"))
    now = dt.datetime.now()
    results = []
    previous = load_summary()
    for item in build_calls(now):
        if item["rank"] not in ranks:
            continue
        key = keys[item["key_name"]]
        if not key:
            results.append({"group": item["group"], "name": item["name"], "file": "", "note": "", "verdict": "키 없음", "state": "skip"})
            continue
        if not key.isascii():
            # 한글 등이 섞인 값은 인증키가 아니므로 호출하지 않고 바로 알려 준다.
            results.append({"group": item["group"], "name": item["name"], "file": "", "note": "키 칸에 한글 등 다른 글자가 들어 있음", "verdict": "입력값이 키가 아님", "state": "bad"})
            continue
        results.append(run_one(item, key, now, overwrite, previous))
    with SUMMARY_LOCK:
        summary = load_summary()
        for row in results:
            if row.get("file") and row.get("http") is not None:
                summary.pop(row.pop("replaces", None), None)
                summary[row["file"]] = row
        if summary:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / SUMMARY).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 키 일부는 이 화면 확인용으로만 돌려주고 파일에는 쓰지 않는다.
    return {"folder": str(OUT_DIR), "results": results, "checks": key_checks(raw_keys, keys)}


PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>놀다가 API 테스트</title>
<style>
:root{color-scheme:light dark;--bg:#f6f7f9;--card:#fff;--text:#1d2430;--sub:#667085;--line:#dfe3e8;--accent:#2457d6;--ok:#167a4a;--warn:#a15c00;--bad:#c02c2c}
@media(prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2127;--text:#eceff3;--sub:#9aa4b2;--line:#323842;--accent:#7da2ff;--ok:#54c58d;--warn:#f0b35a;--bad:#ff8080}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}
main{max-width:980px;margin:auto;padding:28px 16px 48px}h1{font-size:24px;margin:0 0 4px}p{color:var(--sub);margin:0 0 20px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin-bottom:16px}
.keys{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}label{display:block;font-weight:600}label small{display:block;font-weight:400;color:var(--sub)}
.key{-webkit-text-security:disc}body.show .key{-webkit-text-security:none}input.key{width:100%;margin-top:6px;padding:9px 10px;border:1px solid var(--line);border-radius:7px;background:transparent;color:inherit;font:inherit}
.opts{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-top:16px}.opts label{font-weight:400}
button{border:0;border-radius:7px;padding:10px 16px;font:inherit;font-weight:600;background:var(--accent);color:#fff;cursor:pointer}button.alt{background:transparent;color:var(--accent);border:1px solid var(--line)}button:disabled{opacity:.55;cursor:wait}
.wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--sub);font-weight:600}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.skip{color:var(--sub)}td small{color:var(--sub)}
</style></head><body><main><h1>놀다가 API 테스트</h1><p>키를 넣고 실행하면 응답을 JSON 파일로 저장합니다. 키는 저장하지 않으며, 비워 둔 사이트는 건너뜁니다.</p>
<section><div class="keys">
<label>공공데이터포털 일반 인증키<small>TourAPI, 기상청, TAGO, 서울 버스도착</small><input id="data" class="key" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-lpignore="true" data-1p-ignore></label>
<label>서울 일반 인증키<small>실시간 인구, 주차장, 돌발, 문화행사</small><input id="seoul" class="key" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-lpignore="true" data-1p-ignore></label>
<label>TMAP 앱 키<small>길찾기 1차. 무료 하루 10건이라 같은 날 한 번만 호출</small><input id="tmap" class="key" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-lpignore="true" data-1p-ignore></label>
<label>서울 실시간 지하철 키<small>2순위</small><input id="subway" class="key" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-lpignore="true" data-1p-ignore></label>
<label>UTIC 인증키<small>경찰청 교통 돌발, IP 등록 필요</small><input id="utic" class="key" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-lpignore="true" data-1p-ignore></label>
<label>카카오 REST API 키<small>길찾기 2차(1순위), 장소 검색(3순위)</small><input id="kakao" class="key" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" data-lpignore="true" data-1p-ignore></label>
</div><div class="opts"><label><input type="checkbox" class="rank" value="1" checked> 1순위</label><label><input type="checkbox" class="rank" value="2"> 2순위</label><label><input type="checkbox" class="rank" value="3"> 3순위</label><label><input type="checkbox" class="rank" value="4"> 조사 항목</label><label><input type="checkbox" id="show"> 키 보기</label><label><input type="checkbox" id="overwrite"> 저장된 파일도 다시 호출(TMAP 제외)</label><button id="run">테스트 실행</button><button id="open" class="alt" type="button">결과 폴더 열기</button></div></section>
<section id="checkBox" hidden><strong>입력된 키 확인</strong><p style="margin:4px 0 8px">앞뒤 4자리와 길이를 발급 사이트의 키와 비교하세요. 이 정보는 파일에 저장되지 않습니다.</p><div id="checks"></div></section>
<section><strong id="status">아직 실행하지 않았습니다.</strong><div class="wrap"><table id="table" hidden><thead><tr><th>API</th><th>호출</th><th>판정</th><th>코드</th><th>건수</th><th>저장 파일</th></tr></thead><tbody id="rows"></tbody></table></div></section></main>
<script>
const token=new URLSearchParams(location.search).get('t');const $=id=>document.getElementById(id);
const post=(path,body)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Token':token},body:JSON.stringify(body||{})});
const cell=(tr,text,cls)=>{const td=document.createElement('td');td.textContent=text??'';if(cls)td.className=cls;tr.appendChild(td);return td};
$('run').onclick=async()=>{const ids=['data','seoul','subway','tmap','kakao','utic'],keys={};ids.forEach(id=>keys[id]=$(id).value);const ranks=[...document.querySelectorAll('.rank:checked')].map(x=>x.value);
$('run').disabled=true;$('status').textContent='호출 중입니다. 최대 몇 분 걸릴 수 있습니다.';
try{const res=await post('/run',{keys,ranks,overwrite:$('overwrite').checked});if(!res.ok)throw new Error();const data=await res.json();$('rows').textContent='';
for(const r of data.results){const tr=document.createElement('tr');cell(tr,r.group);const n=cell(tr,r.name);if(r.note){n.appendChild(document.createElement('br'));const s=document.createElement('small');s.textContent=r.note;n.appendChild(s)}cell(tr,r.verdict,r.state);cell(tr,r.code);cell(tr,r.count);cell(tr,r.file);$('rows').appendChild(tr)}
$('checks').textContent='';for(const c of data.checks||[]){const d=document.createElement('div');let t=`${c.label}: ${c.head}…${c.tail} (${c.length}자)`;if(c.cleaned)t+=' · 공백이나 숨은 문자를 제거함';if(!c.ascii)t+=' · 영문·숫자가 아닌 문자 포함';if(c.sameAs.length)t+=' · '+c.sameAs.join(', ')+' 키와 같음';d.textContent=t;$('checks').appendChild(d)}$('checkBox').hidden=false;$('table').hidden=false;$('status').textContent='완료: '+data.folder}catch(e){$('status').textContent='실행에 실패했습니다. 터미널 창이 열려 있는지 확인해 주세요.'}finally{$('run').disabled=false}};
$('show').onchange=e=>document.body.classList.toggle('show',e.target.checked);
$('open').onclick=()=>post('/open');
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        supplied = urllib.parse.parse_qs(parsed.query).get("t", [""])[0]
        if not self.allowed_host() or parsed.path != "/" or not secrets.compare_digest(supplied, TOKEN):
            self.send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        self.send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self):
        supplied = self.headers.get("X-Token", "")
        if not self.allowed_host() or not secrets.compare_digest(supplied, TOKEN):
            self.send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        if self.headers.get("Content-Type") != "application/json":
            self.send(415, b"unsupported", "text/plain; charset=utf-8")
            return
        length = min(int(self.headers.get("Content-Length") or 0), 100_000)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self.send(400, b"bad request", "text/plain; charset=utf-8")
            return
        if self.path == "/run":
            body = json.dumps(run_all(payload), ensure_ascii=False).encode("utf-8")
            self.send(200, body, "application/json; charset=utf-8")
        elif self.path == "/open":
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.run(["open", str(OUT_DIR)], check=False)
            self.send(204, b"", "text/plain")
        else:
            self.send(404, b"not found", "text/plain; charset=utf-8")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("NOLDAGA_PORT", "0"))), Handler)
    removed = purge_restricted()
    if removed:
        print(f"보관 기간이 지난 경로 원본 {len(removed)}개를 지웠습니다.", flush=True)
    threading.Thread(target=purge_loop, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/?t={TOKEN}"
    print("놀다가 API 테스트 페이지가 열렸습니다. 끝나면 이 창을 닫으세요.", flush=True)
    if os.environ.get("NOLDAGA_NO_BROWSER"):
        print(url, flush=True)
    else:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
