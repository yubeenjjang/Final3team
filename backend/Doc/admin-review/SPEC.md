# A24 관리자 축제 검토

`GET`·`POST /api/v1/admin/festivals/review-queue`는 operator·admin 전용입니다. DB 모드는 `get_current_user`가 JWT의 사용자 ID로 연 RLS 세션에서 `profiles.role`을 조회하고, 라우터가 권한을 확인한 뒤 `noldaga_service`로 대기열에 접근합니다. 기본 모의 모드는 프로세스 메모리 저장소를 사용합니다. 시연 시 32바이트 이상의 `MOCK_ADMIN_REVIEW_TOKEN`을 서버에 설정하고 Bearer 헤더로 전달하면 모의 운영자로 동작합니다.

GET은 상태(기본 `pending`)·사유·페이지를 받으며 생성 시각과 대기열 ID 내림차순으로 반환합니다. 019는 기존 네 가지 사유에 비축제·미분류·원본 누락·좌표 문제 사유를 추가하고, 기존 TourAPI 보류 데이터를 채웁니다.

POST에는 `queue_id`, `decision`(`approve`·`reject`·`hide`), 공백 제외 1~200자의 `note`가 필요합니다. `reason`은 `note`의 별칭입니다. 승인 시 `value` 또는 대기열의 `proposed_value`에 포함된 축제 필드를 적용해 EV01 분류와 좌표를 검증합니다. 위경도는 대한민국 범위의 한 쌍이어야 합니다. 주소와 위경도가 모두 비어 있는 경우에는 공개할 수 있습니다. 게시 시각이 비어 있으면 승인 시각을 넣습니다. 거절은 축제 행을 변경하지 않습니다. 숨김은 게시 시각을 비우고 `review_status='hidden'`을 유지하도록 수집 규칙과 맞춥니다. 대기열에서 거절·숨김은 `rejected`로 기록하고 감사 이력의 결정으로 두 동작을 구별합니다.

대기열 처리자·시각, 축제 변경, `festival_change_history` 1행은 함께 커밋됩니다. 404 `QUEUE_ITEM_NOT_FOUND`는 존재하지 않는 항목, 409 `ALREADY_REVIEWED`는 이미 처리한 항목, 422 `VALIDATION_ERROR`는 입력 형식 또는 게시 조건을 충족하지 못한 상태입니다.
