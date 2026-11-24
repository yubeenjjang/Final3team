"""새 SQL 번호와 이미 적용한 이력의 안전 검사를 확인합니다."""

import hashlib
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from backend.shared.db import migrate


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class _ExistingDatabase:
    def __init__(self, applied):
        self.applied = applied
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def transaction(self):
        return nullcontext()

    def execute(self, sql, params=None, **_):
        self.executed.append(sql)
        if "to_regclass" in sql:
            return _Rows([("migration_meta.schema_migrations",)])
        if "SELECT version, filename, checksum" in sql:
            return _Rows(self.applied)
        return _Rows([])


class MigrationFilesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.sql_dir = Path(self.directory.name)
        self.patcher = patch.object(migrate, "SQL_DIR", self.sql_dir)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _write(self, name, content="SELECT 1;"):
        path = self.sql_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_future_versions_are_selected_and_down_files_are_ignored(self):
        for number in range(1, 12):
            self._write(f"{number:03d}_change.sql")
        self._write("010_change_down.sql")
        self.assertEqual([number for number, _, _ in migrate.migration_files()], list(range(1, 12)))

    def test_missing_or_duplicate_number_is_rejected(self):
        self._write("001_first.sql")
        self._write("003_third.sql")
        with self.assertRaisesRegex(RuntimeError, "연속된"):
            migrate.migration_files()
        self._write("002_second.sql")
        self._write("002_duplicate.sql")
        with self.assertRaisesRegex(RuntimeError, "연속된"):
            migrate.migration_files()

    def test_applied_files_are_skipped_without_running_sql_again(self):
        paths = [self._write("001_first.sql"), self._write("002_second.sql")]
        applied = [(i, path.name, hashlib.sha256(path.read_bytes()).hexdigest())
                   for i, path in enumerate(paths, 1)]
        database = _ExistingDatabase(applied)
        with patch.object(migrate.psycopg, "connect", return_value=database):
            result = migrate.apply_migrations("unused-test-dsn")
        self.assertEqual(result, [f"건너뜀: {path.name}" for path in paths])
        self.assertNotIn("SELECT 1;", database.executed)

    def test_changed_or_missing_applied_file_is_rejected(self):
        first = self._write("001_first.sql")
        checksum = hashlib.sha256(first.read_bytes()).hexdigest()
        for recorded in ((1, first.name, "wrong-checksum"), (2, "002_missing.sql", checksum)):
            with self.subTest(recorded=recorded):
                database = _ExistingDatabase([recorded])
                with patch.object(migrate.psycopg, "connect", return_value=database):
                    with self.assertRaisesRegex(RuntimeError, "적용 이력"):
                        migrate.apply_migrations("unused-test-dsn")
                self.assertNotIn("SELECT 1;", database.executed)


if __name__ == "__main__":
    unittest.main()
