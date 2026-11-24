# 동행 API 구현 및 검증

1. 공개·로그인 조회는 `user_db_session`과 007·008 RLS를 사용한다. A61은 009의 `app_applicant_profile`로 신청자 프로필을 조회하고 한국 기준 올해에서 출생연도를 뺀 값만 보낸다.
2. 변경은 JWT의 검증된 `sub`로 서비스 세션에서 권한을 다시 확인한다. 정원에 영향을 주는 작업은 모집 글을 먼저 잠근다. 신청 승인, 정원 증가, 방 입장, 시스템 메시지, 알림은 같은 트랜잭션에서 커밋한다. 채팅 작업이 제공할 `ChatRooms.create_companion_room`과 `ChatRooms.add_member`의 기본 DB 구현은 `api/services/companion_chat.py`에 있다.
3. 기본 mock 모드는 저장소 인터페이스로 프로세스 메모리를 사용한다. 실제 모드는 `AUTH_PROVIDER=db`에서 활성화한다. `020_companions.sql`에는 수동 마감 표시, 정리 대상 인덱스와 72시간 경과 후 장소·채팅 메시지 RLS를 둔다.
4. 배포 시 팀 보존 작업에서 저장소 루트 기준 `PYTHONPATH=backend python -m api.jobs.maintain_companions`를 시간마다 실행한다. 자동 종료의 보존 기산 시각은 실제 실행 시각과 무관하게 만남 시각 + 설정 시간이다. 명령은 종료·정리 건수를 기록하며 0은 성공, 1은 실패, 3은 이미 다른 실행이 진행 중임을 뜻한다.
5. `Docs/Step 2/db/run_tests.sh`는 019 적용·되돌리기·재적용과 72시간 RLS를 확인한다. 일회용 PostgreSQL에 001~019를 적용하고 `TEST_DB_URL`을 설정한 뒤 `pytest backend/tests/api/test_companions_postgres.py -m db -q`를 실행한다. 두 서비스 연결의 PID와 실제 잠금 대기를 확인하고, 첫 승인 커밋 전후의 참가자 RLS와 두 번째 승인 거절을 검사한다.
