# IMP-PLAN — 계약 기반 모의 API 서버

단계마다 **만들 파일만** 만들고, 확인(시험) → 체크 → commit 순서로 끝낸다. 한 단계가 끝나기 전에 다음 단계로 가지 않는다.

| 단계 | 담당 (도구·모델) | 요구 | 시작 조건 |
|---|---|---|---|
| 1 | Codex ① · gpt-6.2-sol · reasoning medium | R1~R9, R17(1단계 부분) | 없음 |
| 2 | Codex ② · gpt-6.2-sol · reasoning high | R10~R13 | 1단계 시험 통과 |
| 3 | Codex ③ · gpt-6.2-sol · reasoning medium | R14~R16, R17 완성 | 2단계 시험 통과 (3단계 R15가 2단계 귀갓길 서비스를 씀) |
| 4 | Claude(검토 통괄) + agy · Gemini 4 Hydrogen High(읽기 전용 검토) | 전체 | 3단계 시험 통과 |

## 1단계 — 공통 뼈대 + 축제
**만들 파일(이 목록 밖은 만들거나 고치지 않음)**
- `api/requirements.txt`, `api/main.py`, `api/errors.py`, `api/mocks/__init__.py`, `api/mocks/store.py`, `api/mocks/festivals.py`
- `api/schemas/common.py`, `api/schemas/festivals.py`
- `api/routers/health.py`, `api/routers/festivals/catalog.py`
- 빈 라우터(나중 단계용, `router = APIRouter()`만): `api/routers/routes/routes.py`, `api/routers/assistant/chatbot.py`, `api/routers/accounts/auth.py`
- `tests/api/__init__.py`, `tests/api/conftest.py`, `tests/api/test_step1_common.py`, `tests/api/test_step1_festivals.py`
- `api/MOCK_API.md`(실행·시험 명령, A01~A03, 가상 축제 표까지)

**체크리스트**
- [x] R1 앱·라우터 등록·CORS·`reset_store()`
- [x] R2 공통 오류(422·404 변환 포함)
- [x] R3 `X-Request-ID`
- [x] R4 `is_mock`·`X-Mock` 헤더
- [x] R5 외부 호출 없음 시험
- [x] R6 가상 축제 6건
- [x] R7 A02 필터·정렬·페이지
- [x] R8 A03 상세·이미지 규칙
- [x] R9 A01
- [x] 시험 전부 통과: `uv run --with-requirements api/requirements.txt pytest tests/api -q`
- [x] commit `feat(api): mock server step1 — common errors, request id, festivals A01-A03`

## 2단계 — 귀갓길·가는 길
**만들 파일**
- `api/schemas/routes.py`, `api/services/mock_routes.py`, `api/routers/routes/routes.py`(1단계 빈 파일 채우기)
- `tests/api/test_step2_routes.py`
- `api/MOCK_API.md`에 A04·A05·A25 절과 `X-Mock-Scenario` 표 추가(다른 절은 고치지 않음)
- `api/mocks/store.py`에 귀갓길 저장 칸 추가는 허용(1단계 칸 삭제·이름 변경 금지)

**체크리스트**
- [x] R10 입력 모델(Endpoint, 둘 다 축제 거부)
- [x] R11 A04 판단 순서·시나리오·멱등·200/202 본문
- [x] R12 A05 토큰·상태 진행·오류 본문
- [x] R13 A25
- [x] `api/services/mock_routes.py`에 3단계가 쓸 함수 `create_ready_route(festival_id: str, destination_query: str) -> tuple[str, str]`(route_request_id, route_access_token) 제공
- [x] 1단계 시험 포함 전부 통과
- [ ] commit `feat(api): mock server step2 — return/visit routes A04 A05 A25`

## 3단계 — 챗봇 작업·인증
**만들 파일**
- `api/schemas/assistant.py`, `api/schemas/auth.py`, `api/services/mock_assistant.py`, `api/services/mock_auth.py`
- `api/routers/assistant/chatbot.py`, `api/routers/accounts/auth.py`(1단계 빈 파일 채우기)
- `tests/api/test_step3_assistant.py`, `tests/api/test_step3_auth.py`, `tests/api/test_doc.py`(R17)
- `api/MOCK_API.md` A06·A06-1·A32~A35 절, `curl` 예시 3개 추가
- `api/mocks/store.py`에 작업·사용자 칸 추가 허용(기존 칸 변경 금지)

**체크리스트**
- [x] R14 A06 접수·멱등·대화 확인
- [x] R15 A06-1 상태 진행·질문별 결과·귀가 질문은 실제 귀갓길 요청 생성(`create_ready_route`)
- [x] R16 A32~A35
- [x] R17 문서 완성
- [x] 전체 시험 통과
- [ ] commit `feat(api): mock server step3 — assistant runs A06 and mock auth A32-A35`

## 4단계 — 검토·인계 (Claude)
- [ ] Claude가 전체 시험을 직접 다시 실행하고 서버를 띄워 `/docs`·`curl` 3개 확인
- [ ] agy(Gemini 4 Hydrogen High, 읽기 전용)로 SPEC ↔ 코드 대조 검토 → 틀린 곳만 Codex로 수정
- [ ] `ohyun` push, 병합 요청 문구, 팀원별 디스코드 안내(화면·에이전트가 쓰는 법)

## 메모 (구현 중 발견한 문서와의 차이)
- A04가 `sync_ready`로 200을 줄 때 A05 조회 토큰을 함께 준다(API 설계문서 2절 200 표에는 없음 — 다음 개정 때 문서에 추가).
