"""검증된 SQL 001~009를 순서대로 적용하고 해시를 기록합니다."""

import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import find_dotenv, load_dotenv


SQL_DIR = Path(__file__).resolve().parents[3] / "Docs" / "Step 2" / "db"
LOCK_ID = 8726481


def migration_files() -> list[tuple[int, Path, str]]:
    """되돌리기 SQL은 제외하고 001~009 파일만 선택합니다."""
    files = [path for path in SQL_DIR.glob("[0-9][0-9][0-9]_*.sql") if not path.name.endswith("_down.sql")]
    files.sort()
    numbers = [int(path.name[:3]) for path in files]
    if numbers != list(range(1, 10)):
        raise RuntimeError(f"예상한 001~009 SQL 파일이 아닙니다: {numbers}")
    return [(number, path, hashlib.sha256(path.read_bytes()).hexdigest()) for number, path in zip(numbers, files)]


def apply_migrations(dsn: str) -> list[str]:
    """한 파일씩 트랜잭션으로 적용하고, 기존 파일 변경은 거부합니다."""
    results = []
    with psycopg.connect(dsn, autocommit=True) as connection:
        for number, path, checksum in migration_files():
            with connection.transaction():
                connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
                table_exists = connection.execute("SELECT to_regclass('migration_meta.schema_migrations')").fetchone()[0]
                applied = {}
                if table_exists:
                    applied = dict(connection.execute("SELECT version, checksum FROM migration_meta.schema_migrations").fetchall())
                elif number != 1:
                    raise RuntimeError("001 적용 이력 없이 다음 마이그레이션을 진행할 수 없습니다")

                if number in applied:
                    if applied[number] != checksum:
                        raise RuntimeError(f"적용된 SQL 파일 내용이 달라졌습니다: {path.name}")
                    results.append(f"건너뜀: {path.name}")
                    continue
                if any(version > number for version in applied):
                    raise RuntimeError(f"적용 이력에 순서 누락이 있습니다: {path.name}")

                # 관리 이력은 별도 스키마에 두어 앱 테이블 권한·시험에 섞이지 않게 합니다.
                connection.execute(path.read_text(encoding="utf-8"), prepare=False)
                if number == 1:
                    connection.execute("CREATE SCHEMA migration_meta")
                    connection.execute("REVOKE ALL ON SCHEMA migration_meta FROM PUBLIC")
                    connection.execute(
                        "CREATE TABLE migration_meta.schema_migrations ("
                        "version integer PRIMARY KEY, filename text NOT NULL UNIQUE, "
                        "checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
                    )
                connection.execute(
                    "INSERT INTO migration_meta.schema_migrations (version, filename, checksum) VALUES (%s, %s, %s)",
                    (number, path.name, checksum),
                )
                results.append(f"적용: {path.name}")
    return results


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True), override=False)
    dsn = os.environ.get("DB_MIGRATION_DSN", "").strip()
    if not dsn:
        raise SystemExit("DB_MIGRATION_DSN 환경변수가 필요합니다")
    for result in apply_migrations(dsn):
        print(result)


if __name__ == "__main__":
    main()
