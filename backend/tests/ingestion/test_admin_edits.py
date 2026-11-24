from datetime import date

from api.ingestion.festivals.admin_edits import conflicting_fields


def test_source_changes_protect_admin_fields_and_keep_related_values_consistent():
    previous = {"start_date": date(2026, 12, 4), "end_date": date(2026, 12, 10)}
    changes = {
        "title": "공급원 이름", "summary": "수집 소개", "address": "수집 주소", "longitude": 127.2,
        "start_date": date(2026, 12, 1), "end_date": date(2026, 12, 3), "image_url": "new",
    }
    edited = {"title", "latitude", "start_date", "image_copyright_type"}
    assert conflicting_fields(previous, changes, edited) == {
        "title", "address", "longitude", "start_date", "end_date", "image_url",
    }
    changes["end_date"] = date(2026, 12, 5)
    assert "end_date" not in conflicting_fields(previous, changes, edited)
