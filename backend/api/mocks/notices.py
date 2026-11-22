from datetime import datetime

from api.schemas.festival_info import Notice

NOTICES = {
    "fst_000001": (
        Notice(
            notice_id="ntc_000001",
            type="traffic_control",
            title="세종대로 일부 차로 통제",
            content="축제 기간 세종대로 일부 차로를 통제합니다.(모의)",
            effective_from=datetime.fromisoformat("2026-11-20T18:00:00+09:00"),
            effective_to=datetime.fromisoformat("2026-12-31T23:00:00+09:00"),
            source="seoul_topis",
            published_at=datetime.fromisoformat("2026-11-20T09:00:00+09:00"),
            control_version="ctl-0001",
        ),
        Notice(
            notice_id="ntc_000002",
            type="operation",
            title="점등 시간 18:00~23:00 안내",
            content="축제 조명은 매일 18시부터 23시까지 켜집니다.(모의)",
            effective_from=datetime.fromisoformat("2026-11-20T00:00:00+09:00"),
            effective_to=datetime.fromisoformat("2026-12-31T23:59:00+09:00"),
            source="operator",
            published_at=datetime.fromisoformat("2026-11-19T12:00:00+09:00"),
        ),
        Notice(
            notice_id="ntc_000003",
            type="bus_detour",
            title="지난 우회 운행 안내(종료)",
            content="임시 버스 우회 운행이 종료되었습니다.(모의)",
            effective_from=datetime.fromisoformat("2026-11-01T00:00:00+09:00"),
            effective_to=datetime.fromisoformat("2026-11-10T23:59:00+09:00"),
            source="operator",
            published_at=datetime.fromisoformat("2026-10-31T12:00:00+09:00"),
        ),
    ),
}
