"""보관된 TourAPI 실호출 응답을 DB에 적재하는 W100 검증 도구."""

import argparse
import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.ingestion.festivals.admin_edits import protect_admin_edits

EVIDENCE = Path(__file__).resolve().parents[3] / "Docs" / "Step 2" / "evidence" / "responses"
KST = ZoneInfo("Asia/Seoul")
REGIONS = {"11": "SEOUL", "26": "BUSAN"}  # 원본으로 확인된 지역만 적재
SOURCE_ID = "tourapi"


def _items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    response = data.get("response", {})
    if response.get("header", {}).get("resultCode") != "0000":
        raise ValueError(f"TourAPI 성공 응답이 아닙니다: {path.name}")
    items = response.get("body", {}).get("items", {}).get("item", [])
    return items if isinstance(items, list) else [items]


def _details(kind: str) -> dict[str, dict]:
    result = {}
    for path in EVIDENCE.glob(f"2026-11-19_tourapi-{kind}_*.json"):
        if "오류" in path.name:
            continue
        for item in _items(path):
            result[str(item["contentid"])] = item
    return result


def _date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _coordinate(value: str, low: int, high: int) -> Decimal | None:
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("좌표 형식 오류") from exc
    if not low <= number <= high:
        raise ValueError("좌표 범위 오류")
    return number.quantize(Decimal("0.000001"))


def _clean(value: object) -> str | None:
    return str(value).strip() or None if value is not None else None


def normalize(item: dict, intro: dict, common: dict, today: date) -> tuple[dict, str]:
    """실호출 필드를 DB 칸으로 바꾸고, 검증하지 못한 값은 채우지 않습니다."""
    source_item_id = str(item.get("contentid", ""))
    if not source_item_id.isdigit() or not 6 <= len(source_item_id) <= 26:
        raise ValueError("원본 축제 ID 오류")
    title = _clean(item.get("title"))
    region = REGIONS.get(str(item.get("lDongRegnCd", "")))
    if not title or not region:
        raise ValueError("축제명 또는 검증된 지역 코드 없음")
    start, end = _date(item["eventstartdate"]), _date(item["eventenddate"])
    if end < start:
        raise ValueError("축제 종료일이 시작일보다 빠름")
    image = _clean(item.get("firstimage"))
    copyright_type = _clean(item.get("cpyrhtDivCd"))
    if image and copyright_type not in {"Type1", "Type3"}:
        raise ValueError("이미지 저작권 유형 미확인")
    raw = {"list": item, "intro": intro, "common": common}
    checksum = hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    values = {
        "festival_id": f"fst_{source_item_id}",
        "source_item_id": source_item_id,
        "title": title,
        "start_date": start,
        "end_date": end,
        "venue_name": _clean(intro.get("eventplace")),
        "address": _clean(item.get("addr1")),
        "latitude": _coordinate(item.get("mapy", ""), 33, 39),
        "longitude": _coordinate(item.get("mapx", ""), 124, 132),
        "region_code": region,
        "summary": _clean(common.get("overview")),
        "admission_fee_text": _clean(intro.get("usetimefestival")),
        "image_url": image,
        "thumbnail_url": _clean(item.get("firstimage2")),
        "image_copyright_type": copyright_type,
        "organizer": _clean(intro.get("sponsor1")),
        "event_status": "upcoming" if today < start else "ended" if today > end else "ongoing",
    }
    return values, checksum


def load_snapshot(today: date | None = None) -> tuple[list[tuple[dict, str]], list[str]]:
    """서울 첫 페이지 10건과 부산 6건만 포함한 증빙 부분본입니다."""
    today = today or datetime.now(KST).date()
    intro, common = _details("상세"), _details("소개")
    calls = json.loads((EVIDENCE / "_호출요약.json").read_text(encoding="utf-8"))
    prepared, rejected, seen = [], [], set()
    for region in ("서울", "부산"):
        path = EVIDENCE / f"2026-11-19_tourapi_{region}.json"
        fetched_at = datetime.fromisoformat(calls[path.name]["calledAt"]).replace(tzinfo=KST)
        for item in _items(path):
            source_item_id = str(item.get("contentid", ""))
            if source_item_id in seen:
                rejected.append(f"{source_item_id}: 중복 원본 ID")
                continue
            seen.add(source_item_id)
            try:
                values, checksum = normalize(item, intro.get(source_item_id, {}),
                                             common.get(source_item_id, {}), today)
                values["source_fetched_at"] = fetched_at
                prepared.append((values, checksum))
            except (KeyError, ValueError) as exc:
                rejected.append(f"{source_item_id}: {exc}")
    return prepared, rejected


def ingest(session: Session, records: list[tuple[dict, str]], rejected: list[str]) -> dict[str, int]:
    """원본 ID·체크섬으로 중복을 막고 변경 필드만 갱신합니다."""
    now = datetime.now(timezone.utc)
    job_id = f"ing_{uuid4().hex}"
    session.execute(text("""
        INSERT INTO data_sources (source_id, name, provider_org, scope, region_codes,
          enabled_region_codes, is_realtime, status, notes)
        VALUES (:source_id, 'TourAPI 2026-11-19 증빙', '한국관광공사', 'national',
          ARRAY['SEOUL','BUSAN'], ARRAY[]::text[], false, 'verified',
          '실호출 증빙 부분본: 서울 첫 페이지 10건·부산 6건. 현재 수집 상태 아님')
        ON CONFLICT (source_id) DO NOTHING
    """), {"source_id": SOURCE_ID})
    session.execute(text("""
        INSERT INTO ingestion_jobs (job_id, source_id, started_at, status)
        VALUES (:job_id, :source_id, :started_at, 'running')
    """), {"job_id": job_id, "source_id": SOURCE_ID, "started_at": now})
    inserted = updated = 0
    fields = ("title", "start_date", "end_date", "venue_name", "address", "latitude",
              "longitude", "region_code", "summary", "admission_fee_text", "image_url",
              "thumbnail_url", "image_copyright_type", "organizer", "event_status")
    for values, checksum in records:
        festival_id = values["festival_id"]
        existing = session.execute(text("SELECT * FROM festivals WHERE festival_id=:festival_id FOR UPDATE"),
                                   {"festival_id": festival_id}).mappings().first()
        if existing is None:
            columns = ", ".join(fields)
            params = ", ".join(f":{field}" for field in fields)
            session.execute(text(f"""
                INSERT INTO festivals (festival_id, {columns}, collected_at, last_synced_at)
                VALUES (:festival_id, {params}, :now, :snapshot_at)
            """), {**values, "now": now, "snapshot_at": values["source_fetched_at"]})
            inserted += 1
        else:
            changed = {field: values[field] for field in fields if existing[field] != values[field]}
            protect_admin_edits(session, festival_id, existing, changed)
            if changed:
                assignments = ", ".join(f"{field}=:{field}" for field in changed)
                session.execute(text(f"UPDATE festivals SET {assignments}, last_synced_at=:snapshot_at "
                                     "WHERE festival_id=:festival_id"),
                                {**changed, "festival_id": festival_id,
                                 "snapshot_at": values["source_fetched_at"]})
                for field, after in changed.items():
                    session.execute(text("""
                        INSERT INTO festival_change_history
                          (festival_id, field, before_value, after_value, source_id, actor, changed_at)
                        VALUES (:festival_id, :field, CAST(:before AS jsonb), CAST(:after AS jsonb),
                                :source_id, 'ingestion', :changed_at)
                    """), {"festival_id": festival_id, "field": field,
                           "before": json.dumps(existing[field], default=str),
                           "after": json.dumps(after, default=str),
                           "source_id": SOURCE_ID, "changed_at": now})
                updated += 1
        session.execute(text("""
            INSERT INTO festival_sources
              (festival_id, source_id, source_item_id, source_url, raw_checksum, fetched_at, last_job_id)
            VALUES (:festival_id, :source_id, :source_item_id, :source_url,
                    :checksum, :snapshot_at, :job_id)
            ON CONFLICT (source_id, source_item_id) DO UPDATE SET
              raw_checksum=EXCLUDED.raw_checksum, fetched_at=EXCLUDED.fetched_at,
              last_job_id=EXCLUDED.last_job_id
        """), {"festival_id": festival_id, "source_id": SOURCE_ID,
               "source_item_id": values["source_item_id"],
               "source_url": f"https://apis.data.go.kr/B551011/KorService2/detailCommon2?contentId={values['source_item_id']}",
               "checksum": checksum, "snapshot_at": values["source_fetched_at"],
               "job_id": job_id})
    session.execute(text("""
        UPDATE ingestion_jobs SET ended_at=:ended_at, status=:status, scanned=:scanned,
          inserted=:inserted, updated=:updated, rejected=:rejected, error=CAST(:error AS jsonb)
        WHERE job_id=:job_id
    """), {"ended_at": now, "status": "partial" if rejected else "success",
           "scanned": len(records) + len(rejected), "inserted": inserted,
           "updated": updated, "rejected": len(rejected),
           "error": json.dumps(rejected, ensure_ascii=False) if rejected else None,
           "job_id": job_id})
    return {"scanned": len(records) + len(rejected), "inserted": inserted,
            "updated": updated, "rejected": len(rejected)}


def main() -> None:
    parser = argparse.ArgumentParser(description="TourAPI 실호출 증빙 부분본 적재")
    parser.add_argument("--apply", action="store_true", help="테스트 DB에 실제로 기록")
    args = parser.parse_args()
    records, rejected = load_snapshot()
    if not args.apply:
        print(f"미리보기: 적재 후보 {len(records)}건, 제외 {len(rejected)}건")
        for reason in rejected:
            print(f"제외: {reason}")
        return
    if os.environ.get("APP_ENV") not in {"local", "test"}:
        parser.error("증빙 부분본 적재는 APP_ENV=local 또는 test에서만 허용합니다")
    # API 서버의 backend/ 실행과 저장소 루트 CLI 실행을 모두 지원합니다.
    if __package__ == "api.ingestion":
        from shared.db.session import service_db_session
    else:
        from backend.shared.db.session import service_db_session
    with service_db_session() as session:
        result = ingest(session, records, rejected)
    print(result)


if __name__ == "__main__":
    main()
