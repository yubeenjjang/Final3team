"""실호출 증빙의 필드 매핑과 입력 검증 시험."""

import unittest
from datetime import date

from backend.api.ingestion.tourapi_snapshot import load_snapshot, normalize


class SnapshotTests(unittest.TestCase):
    def test_evidence_contains_two_regions_and_stable_ids(self):
        records, rejected = load_snapshot(date(2026, 11, 23))
        self.assertEqual(rejected, [])
        self.assertEqual(len(records), 16)
        self.assertEqual({record["region_code"] for record, _ in records}, {"SEOUL", "BUSAN"})
        self.assertEqual(len({record["festival_id"] for record, _ in records}), 16)
        by_id = {record["source_item_id"]: record for record, _ in records}
        self.assertEqual(by_id["3035607"]["venue_name"], "광화문광장 및 세종로공원 일대")
        self.assertEqual(by_id["3035607"]["admission_fee_text"], "무료")
        self.assertIsNotNone(by_id["3035607"]["summary"])
        self.assertEqual(by_id["3035607"]["source_fetched_at"].isoformat(),
                         "2026-11-19T17:23:26+09:00")

    def test_unverified_image_license_is_rejected(self):
        item = {
            "contentid": "123456", "title": "시험 축제", "lDongRegnCd": "11",
            "eventstartdate": "20261201", "eventenddate": "20261202",
            "firstimage": "https://example.org/image.jpg", "cpyrhtDivCd": "unknown",
        }
        with self.assertRaisesRegex(ValueError, "저작권"):
            normalize(item, {}, {}, date(2026, 11, 23))

    def test_source_checksum_does_not_change_between_runs(self):
        first, _ = load_snapshot(date(2026, 11, 23))
        second, _ = load_snapshot(date(2026, 11, 23))
        self.assertEqual(first, second)
