# W65 로컬 Redis 연결 검증 — 2026-11-26

- 환경: Docker Desktop Linux 엔진, 별도 Compose 프로젝트 `codex-redis-verify`, PostgreSQL 17+pgvector·Redis 7·FastAPI.
- 설정: `FESTIVAL_DATA=db`, `REDIS_URL=redis://redis:6379/0`. 일회용 DB·무작위 시험 비밀번호를 사용했고 실제 데이터·운영 키·AWS 자원은 사용하지 않았다.
- API는 호스트 `127.0.0.1:18107`에만 열었다. Redis는 호스트 포트를 게시하지 않았다.

| 순서 | 조작 | `/api/v1/health` 결과 |
| --- | --- | --- |
| 1 | DB·Redis·API 기동 | HTTP 200, `status=ok`, `db=ok`, `redis=ok`, `is_mock=false` |
| 2 | Redis 컨테이너만 중단 | HTTP 503, `status=degraded`, `db=ok`, `redis=unavailable` |
| 3 | Redis 컨테이너 재시작 | HTTP 200, `status=ok`, `db=ok`, `redis=ok` |

`REDIS_URL`이 있을 때 API의 실제 `PING` 연결과 장애·복구 응답을 확인했다. 인증 세션·채팅·작업 큐가 Redis를 사용한다는 검증은 아니다. A06은 현재 PostgreSQL 큐를 사용하며 귀가 경로 A04·A05도 Redis 큐로 옮기지 않았다. AWS 내부 연결은 W65에서 별도로 확인한다.

시험 뒤 `codex-redis-verify` 컨테이너·네트워크·DB 볼륨 및 임시 환경 파일을 정리했다.
