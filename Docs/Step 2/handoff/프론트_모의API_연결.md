# 화면 ↔ 모의 API 연결 (이수언·정예진, 2026-11-22)

기준: 수언님 UI 흐름도(11/20 17:22, Figma) · API 설계문서 v0.3.3. 서버 띄우는 법은 [README](README.md).

- 기본 주소: `http://localhost:8000/api/v1` (CORS 허용: `localhost:3000`, `localhost:5173`)
- 모든 응답에 `is_mock: true` → 화면 구석에 "모의 데이터" 표시를 권장
- 응답 헤더 `X-Request-ID` → 오류 신고할 때 이 값을 같이 알려 주세요

## 1. 화면별 API
| 화면 (UI 흐름도) | 부를 API | 모의 | 메모 |
|---|---|---|---|
| 회원가입 | `POST /auth/signup` `{email, password, display_name, birth_year, gender}` | ✅ | 닉네임 2~12자·중복이면 409 `NICKNAME_TAKEN`, 성별 `male`·`female` |
| 로그인 | `POST /auth/login` → `access_token`·`refresh_token` | ✅ | 이후 `Authorization: Bearer <access_token>` |
| 온보딩·취향 선택 완료 | A36·A37 | ❌ | 아직 없음 → 화면만 먼저 |
| 홈: AI 질문창 | `POST /assistant/query` → `GET /assistant/runs/{run_id}` | ✅ | 아래 3절 |
| 홈: AI 안심 귀가 버튼 | 귀가 화면으로 이동 → 2절 | ✅ | |
| 홈: 현장 정보(혼잡·날씨·교통) | `/festivals/{id}/crowd`·`/weather`·`/notices` | ✅ | 편의시설·주차장(A08)은 ❌ |
| 홈: 지금 주목할 축제 | A39/A42 | ❌ | 임시로 `GET /festivals?status=ongoing` 사용 가능 |
| 카드 하트(관심) | `PUT`/`DELETE /me/favorites/{id}`, 목록 `GET /me/favorites` | ✅ | 로그인 필요, 없으면 401 |
| 축제 메인(목록·필터) | `GET /festivals?region=&status=&date_from=&date_to=&q=&sort=&page=&page_size=` | ✅ | 지역 코드 `SEOUL`·`BUSAN` 등 |
| 축제 상세 | `GET /festivals/{id}` | ✅ | 이미지 아래 **"출처: 한국관광공사"**, `Type3`은 자르지 말고 `object-fit: contain` |
| AI 귀가 경로 1·2 | `POST /routes/return` → `GET /routes/return/{id}` | ✅ | 아래 2절 |
| 지도(편의·안전/맛집·관광) | A08 | ❌ | 교통 탭의 통제 공지는 `/notices` ✅ |
| 동행·채팅·마이페이지 | A57~A80 | ❌ | 12월 |

## 2. AI 안심 귀가 흐름
1. `POST /routes/return` 본문 `{request_id: <UUID 새로 만들기>, festival_id, destination: {query: "서울역"}}`
   - 출발을 바꾸려면 `origin: {query: "광화문역"}` 추가(기본은 축제 장소). 출발·도착이 둘 다 축제면 422
2. **202** → `route_access_token`을 보관하고 `status_url`을 2초마다 조회(헤더 `X-Route-Access-Token`)
3. `route_status`: `processing`(로딩) → `ready`(`route_candidates` 그리기, `path`는 **[위도, 경도]**) / `unavailable`·`timed_out`(오류 안내 + `notices`)
4. `completed_valid_route`가 true일 때만 "경로 안내 성공"으로 보여 주세요. `queued`·`processing`은 성공이 아닙니다.

| 실패 화면 만들기 (`X-Mock-Scenario` 헤더를 A04에 보냄) | 결과 |
|---|---|
| `sync_ready` | 바로 200 완료 |
| `async_unavailable` | 두 번째 조회에서 공급원 오류 |
| `async_timeout` | 두 번째 조회에서 시간 초과 |
| `overloaded` | 접수부터 503 "요청이 많아요" |

## 3. 홈 AI 질문창 흐름
1. `POST /assistant/query` `{request_id: <UUID>, message}` → **202** `run_id`·`run_access_token`
2. `GET /assistant/runs/{run_id}`(헤더 `X-Run-Access-Token`) → 1번째 `running` → 2번째 `succeeded`/`failed`
3. `route_request_id`가 있으면(질문에 "귀가"·"돌아가"·"가는 길") 그 값과 `route_access_token`으로 2절 결과 화면을 바로 엶
4. 질문에 "실패"를 넣으면 실패 화면 시험: "답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요."

## 4. 현장 정보 상태값
`status`: `ok`(값 표시) · `stale`(값 + "정보가 오래됐어요") · `unsupported`("이 지역은 아직 지원하지 않아요", **다른 지역 값으로 채우지 않기**) · `unavailable`(오류 안내). 혼잡 색: `green`·`yellow`·`orange`·`red`.
