# 친구 API 구현 및 검증 계획

1. `community/friends.py`에 A43~A50을 등록하고 기존 계정 인증 의존성과 연결합니다.
2. DB 조회는 사용자 세션에서 실행합니다. 서비스 트랜잭션은 005·009·015·016을 활용하여 친구 요청·관계·차단과 1:1 방 닫기를 처리합니다.
3. 기본 mock 저장소와 사용자별 검색 한도를 구현합니다. 실제 차단 해제에는 채팅 연동 함수 호출을 연결합니다.
4. 30일 보존 기준을 목록·신청 처리에 적용하고 정리 작업을 독립 실행할 수 있게 합니다.
5. mock API 시험과 일회용 PostgreSQL 시험을 작성합니다. DB 시험은 RLS 타인 행 차단, 서비스 쓰기 롤백, 교차 요청과 동시 수락·차단, 016 새 방 키 사용 및 정리를 확인합니다.

저장소 루트에서 전체 시험을 실행합니다. PostgreSQL 시험에는 001~018을 적용한 일회용 DB의 `TEST_DB_URL`을 사용합니다. `TEST_DB_APP_URL`은 앱 역할로 직접 접속할 때 사용합니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

거절·취소 후 30일이 지난 행을 정리하는 명령입니다. DB 연결은 기존 서비스 계정 설정을 사용합니다.

```bash
PYTHONPATH=backend uv run --offline --with-requirements backend/api/requirements.txt python -m api.jobs.purge_friend_requests
```
