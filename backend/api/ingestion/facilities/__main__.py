"""python -m api.ingestion.facilities [source_id ...] — 서울 정적 시설 위치를 적재한다."""
import sys
from datetime import datetime

from api.ingestion.db import create_ingestion_engine
from api.ingestion.facilities.collect import load_source
from api.ingestion.facilities.normalize import SOURCES
from api.ingestion.festivals.normalize import KST


def main(argv: list[str]) -> int:
    names = argv or list(SOURCES)
    unknown = [name for name in names if name not in SOURCES]
    if unknown:
        print(f"알 수 없는 공급원: {', '.join(unknown)} (가능: {', '.join(SOURCES)})", file=sys.stderr)
        return 2
    engine = create_ingestion_engine()
    failed = False
    try:
        for name in names:
            try:
                result = load_source(engine, name, datetime.now(KST))
            except RuntimeError as error:
                failed = True
                print(f"{name}: 실패 — {error}", file=sys.stderr)
                continue
            print(f"{name}: 원본 {result.scanned} · 새로 {result.inserted} · 갱신 {result.updated} · 적재 안 함(대상 아님·좌표 없음·역 묶음) {result.rejected}")
    finally:
        engine.dispose()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
