# 채팅 구현 순서와 검증

1. API 라우터는 공통 인증을 사용한다. RLS 세션으로 목록·이력·알림을 열고, 서비스 트랜잭션으로 채팅방과 참여 상태를 쓴다.
2. 같은 1:1 사용자 쌍의 방 생성과 차단 변경에 동일한 DB 트랜잭션 잠금을 사용한다. 방 행을 잠근 후 멤버 변경·순번 발급·메시지 저장을 처리한다.
3. 커밋 뒤 ACK와 변경 신호를 발행한다. 구독자는 자기 RLS 권한과 마지막 순번으로 신규 메시지를 가져온다.
4. DB 시험은 001~018에 019_chat을 추가한다. SQL 실행기는 019_chat 적용·되돌리기·재적용과 두 차례 RLS 시험을 연결한다. 일회용 DB에 `TEST_DB_URL`을 설정하면 `test_chat_postgres.py`의 순번·중복·열람 시험도 실행된다.
5. 배포 운영에서 `PYTHONPATH=backend python -m api.jobs.purge_chat`을 주기적으로 실행한다. 친구 채팅 30일·동행 종료 후 3일이 지난 본문은 NULL로 정리하고 순번을 보존한다. 90일 지난 알림은 삭제한다. API는 정리 전에도 만료된 내용을 반환하지 않는다.

오프라인 회귀 명령은 저장소 루트에서 실행한다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```
