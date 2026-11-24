# 공식 공지와 경로 통제

[API 설계서 6-2·6-6절](../../../Docs/Step%202/API_설계문서.md)과 [DB 설계서 6-7·7절](../../../Docs/Step%202/DB_스키마_설계서.md)을 따릅니다.

| 요청 | 정상 응답 | 처리 |
|---|---|---|
| `POST /api/v1/admin/notices` | 201 `notice_id`, `approval_status` | 새 공지를 `pending`으로 등록합니다. |
| `PATCH /api/v1/admin/notices/{notice_id}` | 200 `notice_id`, `approval_status` | 바꿀 필드를 지정합니다. 수정 후 재검토가 필요합니다. |
| `POST /api/v1/admin/notices/{notice_id}/review` | 200 `notice_id`, `approval_status`, `control_version` | `approve` 또는 `reject`를 받습니다. 반려 사유는 필수입니다. |
| `POST /api/v1/admin/notices/{notice_id}/end` | 200 `notice_id`, `approval_status`, `control_version` | 승인 공지의 효력을 즉시 종료합니다. 사유는 선택이며 300자 이하입니다. |

- 운영자와 관리자만 위 API를 쓸 수 있습니다. 등록에는 공지 종류, 1~200자 제목, 내용, 시간대가 포함된 효력 시작·종료 시각, HTTP(S) 출처 URL이 필요합니다. 종료는 시작보다 뒤여야 합니다.
- 공지 종류는 `operation`, `traffic_control`, `no_stop`, `bus_detour`, `road_closure`입니다. `festival_id`를 비우면 공통 공지입니다.
- A07은 승인 공지를 조회합니다. 기본 조회는 시작 시각을 포함하고 종료 시각을 제외합니다. `active_only=false`에서는 예정·종료 공지도 조회하며, 수동 종료된 공지에는 실제 종료 시각을 표시합니다.
- 승인, 승인 공지의 수정으로 인한 재검토, 수동 종료, 효력 전이마다 해당 범위의 버전이 증가합니다. 공통 공지는 모든 축제 버전에 반영합니다. 예정 공지가 수정되거나 조기 종료되면 이전 일정의 미래 전이를 제거합니다.
- A04/A25는 `route_key` v2에 통제 버전을 넣습니다. 이전 버전의 경로를 재전송하거나 상태 조회하면 기존 요청 ID로 `ROUTE_CONTROL_CHANGED`를 돌려줍니다. 새 요청 ID로 조회하면 최신 버전을 적용합니다. 활성 통제 공지는 A07 경로와 함께 `notices[]`에 표시하고, 통제 구간의 충돌 검증 상태는 `control_unverified`입니다.
