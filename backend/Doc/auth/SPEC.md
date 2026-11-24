# 자체 인증 A32~A35 명세

[API 설계서](../../../Docs/Step%202/API_설계문서.md)의 1·1-1·9-1절과 [DB 설계서](../../../Docs/Step%202/DB_스키마_설계서.md)의 권한·세션 수명주기·001·009를 따릅니다.

`AUTH_PROVIDER=mock`이 기본입니다. DB 모드는 `AUTH_PROVIDER=db`와 [DB 접속 설정](../../../.env.example)을 사용합니다. `JWT_SECRET`에 32바이트 이상 임의 비밀값을 주입합니다. 발급자는 `JWT_ISSUER`의 기본값 `noldaga-api`를 사용합니다. 기본 제한은 `ACCESS_JWT_TTL_MIN=30`, `REFRESH_TTL_DAYS=14`, `REFRESH_LOCK_TTL_S=5`, `AUTH_RATE_LIMIT_PER_MIN=10`입니다.

| API | 처리 |
|---|---|
| A32 | 이메일을 소문자로 비교합니다. Argon2id 비밀번호 해시를 가진 `users`와 가입 필드를 가진 `profiles`를 서비스 트랜잭션 하나에 저장합니다. 중복 이메일·닉네임은 409입니다. |
| A33 | IP를 HMAC으로 변환해 UTC 시각의 분 구간마다 10회까지 허용합니다. 정상 자격 증명으로 활성 계정에 로그인하면 `last_login_at`을 갱신하고 HS256 Access JWT와 14일 Refresh를 발급합니다. Refresh의 SHA-256 해시만 저장합니다. |
| A34 | `refresh:lock:{token_id}`와 PostgreSQL 트랜잭션 잠금으로 동시 교체를 막습니다. 교체 시 이전 Refresh를 폐기하며 폐기된 Refresh가 다시 오면 같은 계정의 모든 Refresh를 폐기한 뒤 401을 반환합니다. 발급·폐기는 계정 행 잠금으로 직렬화합니다. |
| A35 | Access JWT 서명·만료·발급자 및 `revoked:{jti}`를 검사합니다. 활성 상태는 서비스 계정으로, 역할은 JWT `sub`를 설정한 RLS 세션에서 확인합니다. 본인 Refresh를 폐기한 뒤 Access jti를 남은 유효 시간만큼 차단합니다. |

DB-19는 `api/deps.py`에 연결했습니다. 보호 API의 동작에 `get_current_user`·`require_role`을 사용하고 사용자 데이터를 `get_user_db`에서 받은 세션으로 조회합니다. A35는 이 인증 의존성을 사용합니다.

`AuthState`의 메모리 구현은 API 프로세스 수명 동안 키를 보관합니다. Redis 연결 뒤에는 새 어댑터가 연결·처리 오류를 `AuthStateUnavailable`으로 전달합니다. jti 확인 장애에서 보호 읽기는 DB 권한을 확인해 처리하고 쓰기·관리자 요청은 503을 반환합니다. 로그인 한도·갱신 잠금·로그아웃 차단 장애에서도 503을 반환합니다. 로그아웃 차단 기록에 실패하면 같은 요청을 다시 보내 차단 절차를 이어갈 수 있습니다.

비밀번호·JWT 서명 키·Access·Refresh 원문은 로그에 남기지 않습니다. 정상 응답은 모의에서 `is_mock=true`, DB에서 `is_mock=false`입니다. 로그아웃 응답은 본문 없는 204입니다.
