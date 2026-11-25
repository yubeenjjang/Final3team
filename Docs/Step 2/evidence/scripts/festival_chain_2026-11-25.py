import json, time, urllib.request, urllib.parse, datetime
B="http://127.0.0.1:8000/api/v1"
def get(path, **q):
    url=B+path+("?"+urllib.parse.urlencode(q) if q else "")
    t=time.perf_counter()
    with urllib.request.urlopen(url, timeout=20) as r:
        body=json.load(r); h={k.lower():v for k,v in r.headers.items()}; code=r.status
    return {"request": "GET /api/v1"+path+("?"+urllib.parse.urlencode(q) if q else ""), "http": code,
            "ms": round((time.perf_counter()-t)*1000,1), "x_mock": h.get("x-mock"), "has_request_id": "x-request-id" in h}, body
out={"executed_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
     "server": "학원 시연 노트북 API(주소 비공개), FESTIVAL_DATA=db · CROWD_PROVIDER=real", "steps": []}
meta, b = get("/festivals", q="서울빛초롱", status="ongoing,upcoming", region="SEOUL")
item = next(i for i in b["items"] if i["name"]=="서울빛초롱축제"); fid=item["festival_id"]
out["steps"].append({"step":"A02 검색", **meta, "total": b.get("total"), "picked": {k:item.get(k) for k in ("festival_id","name","event_status","start_date","end_date")}, "is_mock": b.get("is_mock")})
meta, b = get(f"/festivals/{fid}")
out["steps"].append({"step":"A03 상세", **meta, "festival_id": b.get("festival_id"), "name": b.get("name"), "venue_name": b.get("venue_name"), "event_status": b.get("event_status"), "is_mock": b.get("is_mock")})
meta, b = get(f"/festivals/{fid}/crowd")
out["steps"].append({"step":"A10 혼잡", **meta, "festival_id": b.get("festival_id"), "status": b.get("status"), "observed_at": b.get("observed_at"), "stale": b.get("stale"), "is_mock": b.get("is_mock"),
    "areas": [{k:a.get(k) for k in ("area_code","area_name","relation_type","congest_level","congest_color","distance_m","observed_at","is_estimate") if k in a} for a in b.get("areas") or []], "notices": b.get("notices")})
for nid in ("fst_01M835BS447VDC8PVAQNM8GKHF",):
    meta, b = get(f"/festivals/{nid}/crowd")
    out["steps"].append({"step":"A10 혼잡(서울 밖)", **meta, "festival_id": nid, "status": b.get("status"), "unsupported_reason": b.get("unsupported_reason"), "coverage": b.get("coverage"), "is_mock": b.get("is_mock")})
print(json.dumps(out, ensure_ascii=False, indent=2))
