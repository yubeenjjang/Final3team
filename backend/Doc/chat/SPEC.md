# 채팅 API 구현 명세

- 기준은 API 설계서 6-4-5·6-4-6절, DB 설계서 6-8·7-0·19절이다.
- A67~A70은 1:1·친구 단체방, 방장 초대, 초대 응답·퇴장·방장 승계, 이름 변경을 처리한다. A66 목록은 A72의 읽지 않은 메시지 수를 보여 준다. 보낸 사람 자신의 메시지는 읽지 않은 수에서 제외한다.
- A71은 방별 `seq` 기준으로 페이지를 조회한다. 기본값은 최근 50개다. 먼저 읽은 순번보다 큰 메시지는 오름차순으로 가져온다. 이전 메시지는 최신 쪽부터 페이지를 선택한 뒤 페이지 안에서는 순번 오름차순으로 반환한다. A72는 현재 방 순번을 상한으로 읽음 위치를 전진시킨다.
- A73은 30초짜리 일회용 표를 발급한다. WS `subscribe.after_seq`로 이전 접속에서 받은 순번 이후를 재생한다. `send`의 ACK는 커밋 뒤에 발행한다. 같은 방·발신자·`client_message_id` 재시도는 원래 ACK를 돌려준다.
- A74는 20개씩 내 알림을 조회하고, A75는 해당 사용자에게 속한 미확인 알림을 읽음으로 표시한다. WS 알림의 바깥 `type`은 `notification`이고 내부 `notification.type`은 `room_invited` 등 알림 종류다. 접속 사이의 알림은 A74에서 조회한다.
- DB 조회는 앱 역할의 RLS, 방·멤버·순번을 바꾸는 쓰기는 서비스 트랜잭션을 사용한다. 021_chat의 차단 트리거와 016의 부분 고유 인덱스가 차단·해제 뒤 기존 1:1 방을 보존한다. 일반 퇴장으로 닫힌 1:1 방의 이력은 남은 멤버가 보존 기간 동안 조회할 수 있다. 019 적용 이전의 닫힌 1:1 방은 종료 사유를 알 수 없어 차단 종료와 같은 열람 제한을 적용한다.
- 차단은 1:1의 생성·송신·열람·구독을 제한한다. A49에 따라 공동 단체방·동행방 참여와 메시지에는 계속 접근할 수 있다.
- 단일 프로세스의 메모리 브로드캐스트는 변경 신호를 전달한다. 메시지 본문은 DB 모드에서 RLS를 거쳐 전송한다. 신호를 받지 못한 외부 상태 변경은 활성 연결에서 1초마다 확인한다. Redis용 `ChatBus`와 `TicketStore` 인터페이스를 둔다.

## 동행·친구 연동

`api.services.chat.ChatRooms`는 `api.routers.community.chat.ChatRooms`에서도 가져올 수 있다. 세 함수는 동기이며 UUID 또는 UUID 문자열을 받는다. DB 변경을 함께 커밋하려면 호출에 서비스 `Session`을 `db=`로 전달한다.

- `create_companion_room(post_id, owner_id)`는 동행 글에 연결할 `room_id`를 반환한다. 글 ID의 접두사를 바꾸어 재시도에서도 같은 방을 사용한다. 글 삽입과 방·방장 멤버 삽입을 같은 트랜잭션에 둔다.
- `add_member(room_id, user_id)`는 승인과 같은 트랜잭션에서 호출한다. 이미 입장한 멤버의 입장 시각과 읽음 위치는 유지한다.
- `close_direct_room_on_unblock(user_a, user_b)`는 남아 있는 차단 행과 같은 사용자 쌍의 열린 방을 닫는다. DB에서는 차단 행 삭제 트리거도 같은 변경을 보장하므로 삭제 전후로 호출할 수 있다. 모의 모드는 차단 행을 제거하기 전에 호출한다.
- 모의 친구·차단 자료는 `api.services.mock_chat.mock_rooms`의 `friendships`(UUID 두 개를 담은 frozenset)와 `blocks`(차단자·차단 대상 UUID 쌍)를 사용한다.

## WebSocket 서버 실행

저장소 루트에서 실행한다. WebSocket 프로토콜 라이브러리는 실제 실행용 요구사항에 포함되어 있다.

```bash
uv run --with-requirements backend/api/requirements-realtime.txt uvicorn --app-dir backend api.main:app --ws websockets-sansio --port 8000
```
