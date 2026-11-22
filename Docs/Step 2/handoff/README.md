# 11/23 주간 인계 — 모의 API로 바로 시작하기 (2026-11-22, 권오현)

진짜 DB·외부 API가 준비되기 전에도 화면·에이전트를 만들 수 있게, **API 설계문서 v0.3.3과 같은 주소·같은 응답 모양**으로 답하는 **모의 API 서버**를 만들었습니다(`backend/api/`, 브랜치 `ohyun`). 모든 값은 가상이고 응답에 `is_mock: true`가 붙습니다. 나중에 실제 구현으로 바꿀 때 **주소와 응답 모양은 그대로, 안쪽만** 바뀝니다.

## 1분 실행
```sh
cd backend
uv run --with-requirements api/requirements.txt uvicorn api.main:app --reload --port 8000
# 브라우저: http://localhost:8000/docs  (모든 API를 눌러 볼 수 있음)
```
시험: `uv run --with-requirements api/requirements.txt pytest tests/api -q` → 112개 통과(11/22).

## 누가 무엇을 보나
| 팀원 | 문서 |
|---|---|
| 이수언·정예진 (화면) | [프론트_모의API_연결.md](프론트_모의API_연결.md) — 화면(수언님 UI 흐름도)별로 부를 API·시나리오 |
| 한다영 (에이전트) | [에이전트_도구_인계.md](에이전트_도구_인계.md) + [`tools/`](tools/) 도구 13개 JSON Schema |
| 신유빈·한태경 | 아래 '함께 쓰는 규칙' |

## 지금 되는 API (모의)
| API | 주소 | 비고 |
|---|---|---|
| A01 | `GET /api/v1/health` | |
| A02·A03 | `GET /api/v1/festivals`, `GET /api/v1/festivals/{id}` | 가짜 축제 6건(서울 2·부산 2·강원 1·좌표 없는 1) |
| A07·A09·A10 | `GET /api/v1/festivals/{id}/notices` · `/weather` · `/crowd` | 혼잡은 서울만, 그 밖은 '지원 안 함' |
| A04·A05 | `POST /api/v1/routes/return`, `GET /api/v1/routes/return/{id}` | 접수 → 처리 중 → 완료 |
| A25 | `POST /api/v1/routes/visit`, `GET /api/v1/routes/visit/{id}` | 축제 가는 길 |
| A06·A06-1 | `POST /api/v1/assistant/query`, `GET /api/v1/assistant/runs/{run_id}` | 챗봇 작업 |
| A11~A13 | `GET /api/v1/me/favorites`, `PUT`·`DELETE /api/v1/me/favorites/{id}` | 로그인 필요 |
| A32~A35 | `POST /api/v1/auth/signup`·`login`·`refresh`·`logout` | 메모리 저장(서버 끄면 사라짐) |

**아직 없음:** A08 주변 시설(유빈님 라우터), A36~A42 취향·추천·핫한 축제(유빈님), A57~A80 동행·친구·채팅·알림·마이페이지(권오현, 12월), 운영 A14~A21. 필요하면 같은 방식(`backend/Doc/SPEC.md`에 요구 추가 → 단계 추가)으로 늘립니다.

## 함께 쓰는 규칙
- 시험용 헤더 **`X-Mock-Scenario`**로 실패 화면을 미리 만들 수 있습니다(값은 `backend/api/MOCK_API.md`).
- 오류는 모두 `{"error": {code, message, request_id, retryable}}` 한 모양입니다.
- 새 라우터를 붙일 때는 `backend/api/main.py`에 등록만 하면 됩니다(`main.py` 취합: 권오현).
- 설계·작업 기록: `backend/Doc/`(REQUEST → TODO → SPEC → IMP-PLAN, Codex 작업 지시서).
