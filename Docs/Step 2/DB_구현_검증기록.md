# DB 구현·검증 기록

놀다가(NOLDAGA) / 3팀 수다수다 | 짝 문서: [DB 스키마 설계서](DB_스키마_설계서.md) v0.7 | 작성 2026-11-25 · 권오현(백엔드)

> DB 스키마 설계서 v0.6까지 한 문서에 있던 **검토 기록·강사 피드백 반영표·실제 데이터 근거·다른 문서 연결·실행 확인 기록·결정 기록**을 v0.7에서 이 문서로 옮겼습니다. 설계서는 학원 산출물 양식(04. 데이터베이스 스키마 설계서, 1~7절)만 남깁니다. 절 번호는 옮기기 전 번호를 그대로 씁니다.

## 검토 기록 (설계서 v0.6까지)

| 일자 | 검토자 | 범위 | 결과·수정 내용 |
|---|---|---|---|
| 2026-11-19 | 권오현 (AI 초안 작성) | 전체 | v0.3 작성: 수업 가이드 체크리스트·강사 피드백·D-033~D-037 반영, DDL 실행·시험 |
| 2026-11-19 | AI 교차 검토(Gemini 4 Neon) | 전체 | 20건 지적 → 복구 시도 결과 기록 트리거, 캐시 테이블 축제 ID, 모든 테이블 RLS, 컬럼 권한, 인덱스, 공지 제목 등 반영. 이후 Supabase → AWS Docker 전환(D-037) |
| 2026-11-19 | 신유빈(인프라·R06 검토) | 전체 | 검토 완료 → 택시 범위·추적 ID·대조표·신규 기능 표기 반영 |
| 2026-11-19 | 정예진(기획) | 기획서와 대조 | 경로 5유형·택시·created·대조표·추적 ID → 반영 |
| 2026-11-20 | AI 교차 검토 3종(Claude Opus 5.5 · Codex gpt-6.2-sol · agy Gemini 4 Hydrogen XHigh) | 전체 + `db/` | 마이그레이션 008(권한·숨김 축제·검색 경로·동행 글 숨김·복구 조치 해제 기록·부하 시험 칸·공개 표시 이름), 시험 T42(12개), 탈퇴·보존·Redis·RLS 범위 문장 정리, 한태경 11/20 15:03(카카오 저장 불가 공식 답변·공식 한도) → v0.3.3. 제출 뒤 처리는 API 구현·검증 기록 11-1절 |
| 2026-11-20 | 팀 답변(한태경 보존 검토 · 정예진 권한 정책안 · 신유빈 보존·열람·크롤링) | 7-0·7-1·6-4·10절 | 목적지 라벨 DB 제거·해시 HMAC, 챗봇 마스킹·탈퇴 삭제, 로그 IP, 동행 3일·친구 30일, 채팅 열람 참여자·관리자, 권한 기준안, `festival_trends`(004) → v0.3.3 |
| 2026-11-20 | 강사(11/19 피드백 7건) · 권오현 | 전체 | 1차 반영(v0.3.2): 정본 파일명(`DB_스키마_설계서.md`)·짝 문서 버전, 옛 Supabase 문장, 길찾기·택시·자전거 실호출 결과. **4번 반영**: 7-0 보존·만료 통합표. **1·2·3·5·6번 반영**: 시험 SQL 분리·재실행(10절), 연결 재사용 시험·규칙(3절), AWS 예정일, 13개 검증 범위, RAG 결정일. **7번**: 기획서·WBS와 DB·인증 일치 확인, 파일명 정리. 13개 테이블 DDL은 005·007로 완료. **남은 것**: AWS 실행(W65), 임베딩 결정(11/25) — 권오현 개인 정리본(공유본은 이 표) |
| 2026-11-23 | 강사(11/20 DB 피드백 6건) · 권오현 | 전체 + `db/` + 실행 코드 | **v0.4**: 0-A 반영표, 데이터가 있는 DB 시험 T44~T48(009 사전 검사·파일 단위 트랜잭션·안전한 되돌리기), 마이그레이션 010, `route_key` HMAC, 7-2 열람 범위, 10-A 시험 환경 구분, 개인 PC 경로 제거. 팀 검토 기록은 API 구현·검증 기록 19절(11/23)과 이 문서 19절(11/24) 참고 |
| 2026-11-23 | 신유빈(Discord 답변) | D1 DB 접근 방식·011 조회 토큰 해시·실제 수집 담당·연결 반납 시 `RESET ALL` | 각 항목의 합의 범위·구현과 재검증 상태는 API 구현·검증 기록 19절. 011에서 `user_id`를 두지 않는 정리는 재확인 대기 |

## 0-A. 강사 11/20 피드백 반영표 (v0.5, 2026-11-24)

| # | 피드백 | 상태 | 반영 위치 | 근거(다시 확인하는 방법) |
|---|---|---|---|---|
| 1 | **데이터가 있는 DB**에서 009 적용·되돌리기와 손실 조건 확인 | ✅ 로컬 확인 | **10-A-2절** T44~T48, `db/009_precheck.sql` | 기존 데이터 시험 13개 PASS. 009 적용·되돌리기는 `psql -1 -v ON_ERROR_STOP=1`, 010은 SQL 파일 내부의 `BEGIN`/`COMMIT`으로 처리(10절) |
| 2 | `route_key` HMAC, 삭제·익명화 뒤 남는 정보, 신고 채팅 관리자 열람·차단/탈퇴·에이전트 범위 | 🟡 일부 | 4절, 7-2절, API 설계서 3-1절 | HMAC 키(11/24 `route_key` v2: 조건·통제 버전·공급원 포함, 좌표 원문 없음)·API 로그·메모리 만료·일회용 DB 신규 행 원문 시험 통과. DB와 API 공개 조건은 014로 통일(승인·게시된 축제 EV01만, T014a~e). 11/24 보존 기간·운영자 서버 조회·차단 해제 뒤 기존 1:1 방 유지 정책을 3·6-8·7-0·7-2절과 19절에 반영. **남은 것(막힌 이유)** — 차단 해제 후 새 방 개설을 지원하는 구현·시험 · Redis 시험: 공통 Redis 연결(신유빈) 뒤 · 관리자 열람 범위와 접근 기록 서버 시험: 신고·관리자 API가 12월 구현 범위 |
| 3 | 로컬·AWS·실서비스 시험과 재실행 기준 구분 | 🟡 일부 | **10-A절** 환경 구분표 | **11/24 로컬 확인** — 001~028 SQL·백업 실행기 출력 PASS 표기 265줄(개별 시험 PASS 260건 + 요약 5줄), FAIL 0, 010 전용 시험(T010a~e)과 로그 확인, DB 표시 pytest 16개 통과, 한태경 실DB 연결 풀·권한·동시 실행 시험 17개 통과(tk `649d50b`, 일회용 PG17 + `ohyun` 001~013 + `yubeen` 세션 코드). **남은 것(막힌 이유)** — AWS W65(12/07~10, 신유빈 관리) 별도 시험 DB 재실행: AWS 구성 뒤 |
| 4 | 핵심 흐름의 최신 DB 구조 연결(축제 조회→귀가 요청→처리 상태→결과 저장) | 🟡 **일회용 DB 통합 시험 통과** | 10-A절(실제 축제 적재·A02/A03 DB 조회, 시험 축제로 P18 A02→A05 연속 실행), 8·10절(011~013과 A04/A05·정리 명령 연결) | 11/24 학원 DB에 011~014 적용 후 축제(EV01) 521건 재수집. **남은 것(막힌 이유)** — 화면 검증: 12/8 첫 시연(정예진·권오현) · 에이전트·워커 연동: A06 워커(W14·W27, 한다영·신유빈) 구현 뒤 · 정리 명령 시간당 실행: W64·W65(신유빈) |
| 5 | RAG 모델·차원·검색·재적재 방법과 문서 범위 확정 | ✅ 결정 완료(11/24) | 2절, API 구현·검증 기록 19절, WBS W27 | 모델 `text-embedding-3-small`·`dimensions=1024`, `VECTOR(1024)`, HNSW 코사인·필터 먼저, 청크 500자·50자 겹침, 모델 변경 시 전체 재적재, 문서 범위 축제 공식 안내문. **확인 결과** — 별도 pgvector DB(`pgvector/pgvector:pg17` 일회용 `rag_scratch`)에서 실제 OpenAI `text-embedding-3-small`·1024차원 임베딩과 HNSW 코사인 검색·필터 시험 **10/10 통과**(한다영 `dayoung` `bd9a014`·`feabaf5`, 11/24): 정상 질문 Q01~Q04는 선택 축제의 문서가 1위(서울빛초롱축제·청계천의 빛), Q05·Q06은 다른 축제 문서가 축제 ID 필터로 제외, Q07은 만료 문서 제외, 미승인 문서는 검색 제외, 같은 문서 중복 적재 없음([시험 기록](https://github.com/yubeenjjang/Final3team/blob/dayoung/Docs/Step%202/RAG_공식축제문서_샘플검색_준비.md)). 서비스 DB 적재·검색 API·답변 생성과 근거 부족 시 보류 판단은 W27 구현 범위(한다영) |
| 6 | 문서·시험·제출본 같은 기준(커밋·적용 순서·검토 기록) | 🟡 일부 | 10절 파일표·10-A절 결과(SQL·DB 시험 기준 `ohyun` `719484d`), 문서 정보 | 팀 결정 14건은 신유빈 확인과 함께 19절에 기록. **완료(11/24)** — 010 전용 시험과 11/24 로그 확인(10-A-3). A42 점수는 신유빈 11/24 B안(두 출처 합산)을 따르고, 네이버는 데이터랩 검색어 트렌드를 사용합니다. 약관상 네이버 검색 결과는 A81 표시에만 사용합니다(권오현 확정). A42의 데이터랩 증가율·신호는 017에 저장하고, A81 Redis 캐시를 적용합니다. **남은 것** — 병합 뒤 제출 기준 커밋·대시보드 링크와 접수 확인, 기획서의 옛 경로·버전을 담당자와 맞추기 |

### 0-A-1. 강사 11/23 일지 피드백 중 DB 반영 (2026-11-24)

| # | 피드백 | 상태 | 반영 위치·근거 |
|---|---|---|---|
| 4 | 7일 백업에서 TMAP 경로 본문 제외 및 증빙 보존(SK 회신 없이 적용하는 확정 기준) | T013a~d·T25a~c 11/24 로컬 통과(`719484d`, 전체 집계는 10-A절). AWS 적용·검증은 W65 AWS 구성 뒤 같은 실행기로 다시 실행(AWS 환경 신유빈 관리) | 7-0 ④, 012·013, 복원 시험(10절), [11/24 SQL 로그](db/results_2026-11-24.log) |

## 8. 실제 데이터 근거·미확인 항목

> **마이그레이션 011(11/24 로컬 적용·되돌리기·재적용 통과):** `route_requests`에 `access_token_hash TEXT NOT NULL`과 64자리 해시 제약을 추가했습니다. `request_body_hash`는 멱등 비교, `error_detail`은 오류 안내에 사용합니다. `user_id` 칸 없이 로그인·비로그인 A05에서 같은 방식으로 검증합니다. 기존 RLS와 `noldaga_service` 접근 권한을 검사하고, TMAP 정리용 부분 색인을 만듭니다.

- `precheck_011_route_access_token.sql`로 기존 행 수를 확인합니다. 신유빈 님 11/24 10:29 답변에 따라 011 이전 요청·결과 행은 보존하고 조회 토큰은 재발급하지 않습니다. 011 이전 요청을 조회하려면 새 요청을 접수해야 합니다. 적용과 되돌리기는 각 파일을 `psql -X -v ON_ERROR_STOP=1 -1 -f`로 실행합니다.
- API 컨테이너에는 `.env.example`의 `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER_USERNAME`, `DB_USER_PASSWORD`, `DB_SERVICE_USERNAME`, `DB_SERVICE_PASSWORD`를 전달합니다. `DB_MIGRATION_DSN`은 관리자용 실행 환경에만 둡니다. 011 부분 색인을 쓰는 TMAP 정리 명령과 감시 기준은 7-0절에 있습니다.

**마이그레이션 013(한태경 님 11/24 검토).** 012 적용 DB에서 `route_results`를 제외하는 백업에 삭제 시각을 남기기 위해 `route_requests.result_purged_at`을 추가합니다. 기존 삭제 시각은 이관하고 새 삭제 시각은 트리거로 기록합니다. 기존 RLS와 역할 권한을 유지하며 `noldaga_app`은 삭제 시각을 조회·수정할 수 없습니다. 013을 되돌리면 요청 행의 삭제 시각 칸과 트리거가 제거되고 결과 행의 `purged_at`은 보존됩니다. T013·T25c는 11/24 로컬에서 통과했습니다.

**마이그레이션 016(권오현, 11/24 설계 반영).** 차단 해제 후 다시 친구가 된 사용자가 대화를 시작하면 새 1:1 방을 개설합니다. 007의 전역 `direct_key` UNIQUE는 닫힌 방이 같은 키를 계속 사용하므로 새 방을 막습니다. 016은 `status <> 'closed'` 부분 UNIQUE로 교체해 닫힌 방과 그 메시지를 보존하고, 사용자 쌍마다 닫히지 않은 방을 하나만 허용합니다. 015 적용 다음, A49·A50·A67의 채팅방 개설 기능 적용 전에 실행합니다(사전 검사·되돌리기는 10절).

**확보한 원본:** 서울시 `citydata_ppltn` 광화문·덕수궁 응답(2026-11-16 샘플 키, 11/19 정식 키 재호출 `evidence/responses/2026-11-19_seoul-ppltn_광화문덕수궁.json`) → 혼잡 `payload`의 필드(`AREA_CD`·`AREA_CONGEST_LVL`·`AREA_PPLTN_MIN/MAX`·`PPLTN_TIME`·`FCST_PPLTN[]`)를 이 원본으로 정했습니다. 나머지 공급원은 API 구현·검증 기록 10-1절 '최소 실호출 계획'으로 확인합니다.

| 항목 | 현재 상태 | 확인 담당 | 확인 시점 |
|---|---|---|---|
| TourAPI 실제 필드 → `festivals`·`festival_sources` 대응표 | API 구현·검증 기록 10절 표 참조. 014는 `lclsSystm1`·`lclsSystm2`·`lclsSystm3`를 `festivals`에 보관하며 `lclsSystm2=EV01`만 공개 대상으로 분류 | 한태경·권오현 | 11/24 |
| TMAP(1차)·카카오맵(2차) 응답 → `route_results.candidates` 구조, TMAP `stationID` ↔ 서울 버스 `arsId`, TMAP 응답 저장 조건 | ✅ **11/19 실호출 완료**(서울·부산, 한태경): TMAP 정류장 목록 키 `stations`·`stationID` 6자리 / 카카오는 정류장 이름만 / 서울 버스 `arsId` 5자리 → **같은 값 아님, 이름+거리로 연결**. 원본은 24시간·저장 금지 규칙으로 삭제, 합성 예시로 `candidates` 구조 확정 예정 | 권오현·한태경 | 11/20 |
| 지하철·버스·돌발·날씨·자전거 응답 → `realtime_snapshots.payload` | **11/19 일부 확인**(서울 지하철·TOPIS·기상청·TAGO 부산). TOPIS 좌표는 GRS80 TM → 위경도 변환, 서울 버스는 서울시 버스도착정보. 주차는 A08 `facilities`의 위치만 사용 | 권오현·한태경 | 11/20~ |
| 버스 차내 혼잡 공급원 | 서울시 버스도착정보 15000314. A05 선택 후보에 표시하며 정류장 매칭과 캐시는 6-4·7-0절을 따름 | 권오현 | 저장 응답으로 검증 |
| 자전거 존·택시 승강장 공급원 | ✅ **둘 다 전국**(11/19 실호출): 자전거 = 행안부 전국 공영자전거(6,314건), 택시 = 전국택시승강장표준데이터 15139230(서울 268·부산 87). 택시·일부 주차장은 **위경도 없음** → 카카오 주소 검색으로 좌표 변환 후 `facilities` 적재 | 권오현·한태경 | 정함 |
| 서비스 범위 → 수집 대상 | ✅ D-022·D-036: 한 공급원에서 전국을 받으면 전국, 아니면 서울만 | 팀 | 정함 |
| DB 운영 방식 | ✅ **AWS 위 Docker PostgreSQL + 자체 JWT**(D-037). **기획서·WBS 최신본(GitHub main, 11/20 대조)과 일치**(Supabase 0건) | 권오현 | 정함 |
| AWS 서버에서 DDL 실행 | **아직 없음** — 로컬 실행 기록은 10·10-A절. AWS 시험 DB에서 001~009와 010을 각 절차대로 다시 확인 | 신유빈 | **W65 12/07–10** |
| 임베딩 모델·차원·RAG 사용 범위 | ✅ 11/24 확정(2절) · 별도 pgvector 샘플 검색 10/10 통과(한다영 `feabaf5`) | 한다영·권오현 | 11/24 |
| **챗봇 작업 테이블 `assistant_runs`** (A06 비동기 작업, 03 문서 7-6) | ✅ **11/20 마이그레이션 002로 추가·시험(T24)**. 처음 설계: 작업 1건 = 1행: `run_id` PK(`^run_`)·`request_id` UNIQUE(멱등)·`conversation_id`·`run_status`(queued·running·retrying·succeeded·failed)·`answer`(카카오 경로 내용 금지)·`error_code`·`queued_at`/`started_at`/`ended_at`, RLS 본인·service. 48개 테이블·시험 T24·T34에 포함 | 권오현 | 완료 |
| TTL·보존 기간 | 확정(11/24 팀 결정). 7-0 보존표 기준(캐시 60초, 요청 30일, 라벨 24시간, 실시간 값 7일, 체크포인트 7일, 알림 90일 등) | 7-0 담당 | 표에 적힌 시험 일정은 적용 검증 |
| `EXPLAIN ANALYZE` 전후 결과 | 모의 데이터 2만 건으로 축제 검색 1개 측정(5절, `db/explain_v0.3.2.sql`로 다시 잼). 실제 데이터로 재측정 필요 | 권오현 | 축제 수집 후(W98) |
| 기획서 5.4에 없는 테이블 | 9절 표 | 정예진(기획 5.4 반영) | 팀 검토 |
| 과거 구간 혼잡 DB(BFCL NLD-12) | 기능 없음 → 테이블 설계 안 함 (BFCL과 같음, 새로 넣지 않음) | — | 기능 추가 결정 시 |
| ERD 그림 형식 | mermaid(GitHub에서 바로 보임) — docx 제출 시 이미지로 변환 | 권오현 | 제출 전 |

---

## 9. 다른 문서와의 연결

| 연결 | 위치 | 내용 |
|---|---|---|
| API 필드 ↔ DB 컬럼 | 03 문서 6-2절 | 1차 필수 API의 필드가 어느 컬럼에 저장되는지 |
| ID 형식·추적 | 03 문서 0절 · 이 문서 7절 | 두 문서 같은 접두사, DB는 CHECK로 강제. **별도 `trace_id`는 두지 않음** — `X-Request-ID`(로그) → `route_requests.run_id`·`agent_runs.run_id`/`agent_run_id` → `route_request_id`·`incident_id`로 이어서 추적(기획서 최신본 5.16과 같음) |
| 권한 | 03 문서 1절·각 API의 403 조건 · 이 문서 3절 | FastAPI 1차, DB 2차. 12/18 AI 보안 가드레일 문서도 이 표를 기준으로 씀 |
| 운영비·평가 | API 구현·검증 기록 9-2·4-7절 | 축제 하루 방문자 1만 명·1인 1.5회는 운영비 계산용 가정. BFCL 30문항 원본은 한다영 브랜치, 채점은 API 최신판(v0.5) |
| 지금 핫한 축제(A42) | API 설계서 7-15·8-2·기록 13절 · 이 문서 6-4·7-0절 | `festival_trends`(004·017)의 증가율·신호·순위로 두 출처 점수를 계산. 가중치·수집 주기·만료·검색 신호 하한·네이버 키 환경변수는 API 설계서 8-2 기준 |
| 요즘 올라온 글(A81) | API 설계서 7-15·8-2·기록 13절 · 이 문서 4·7-0절 | Redis `posts:{festival_id}`에 10분 캐시 |
| 복구 기록 | 03 문서 7-0·7-4·7-5 · 이 문서 6-2 | 구간(`phase`), 대응 방식(`comparison_arm` → 종료 뒤 `incident_outcomes.responder_type`), 재검증·종료(`stop_reason`) |

**API 이름과 DB 이름이 다른 것 (전체)** — API 이름이 화면·도구 기준, DB 이름은 아래와 같습니다.

| API (03 문서) | DB 컬럼 |
|---|---|
| `name` · `lat` / `lng`(축제) · `overview` · `fee_text` · `homepage_url` | `festivals.title` · `latitude` / `longitude` · `summary` · `admission_fee_text` · `official_url` |
| `destination` / `origin`(사용자 장소) | `route_requests.origin_type`·`destination_type` + `origin_place_hash`·`destination_place_hash`(HMAC, 009) + Redis `route:label:{id}`(24시간, DB 칸 없음) |
| `user_constraints` | `route_requests.constraints` |
| `items[].score`(A42) | 같은 회차의 `festival_trends.trend_ratio`·`source_rank`를 각각 정규화해 계산. 두 점수의 가중합 또는 사용 가능한 한쪽 점수 |
| `items[].signal`(A42) | 네이버 점수를 반영했으면 `ok`, 네이버 점수가 없으면 `no_signal`. 데이터랩 수집 행의 신호는 `festival_trends.signal`(017), 출처 실패·오래됨은 회차 상태로 판단 |
| `items[].sources`·`items[].partial_sources`(A42) | 점수에 반영한 `festival_trends.source_id`를 `trend_naver_datalab` ↔ `naver_datalab`, `trend_visitkorea` ↔ `visitkorea`로 매핑. 한 출처만 반영했으면 `partial_sources: true` |
| `route_status` | `route_requests.status` |
| `route_candidates[]` · 후보별 근거 | `route_results.candidates` · `route_results.evidence` |
| `verification_status` | `route_results.validation_status` |
| `test_mode`(A15) | `incident_logs.injected_test` |
| `responder_type`(A15, 사건 진행 중) | `load_simulations.comparison_arm`에서 계산(B0→none, B1→rule, A1→agent), 종료 뒤 `incident_outcomes.responder_type` |

**기획서 최신본(11/19 05:18 신유빈 님 공유) 5.4·5.19와 대조** (강사 일일 피드백 1)

| 구분 | 내용 | 판정 |
|---|---|---|
| DB 플랫폼 | 기획서: AWS Docker PostgreSQL 17 + pgvector(`pgvector/pgvector:pg17`) 확정 | ✅ 같음(D-037) |
| 기본 테이블 | 기획서: 기본 30개·FK 43개·로컬 시험 20개 통과 보고 | ✅ 같음 |
| 이 문서가 기획서 v2.8 5.4에 더한 테이블 | `users`·`refresh_tokens`, `load_simulations`·`incident_events`, `data_sources`·`facilities`, `festival_reviews` | ✅ 기획서 최신본에 반영됨 |
| 후속으로 뺀 테이블 | `crowd_prediction_signals` | ✅ |
| **신규 13개 테이블 후보** | 기획서 5.19(추천 3·동행 3·친구 3·채팅 3·알림 1) | ✅ **13개 + 2개 모두 완료(005·007, T29~T41)** |

**강사 피드백 3(출처 미확인 부가 정보 보류)**: 버스 차내 혼잡(`bus_crowding`)은 멘토님 의견(D-024)과 팀 결정(D-033)으로 서울의 교통수단 선택 근거에 사용합니다. 11/19 실호출에서 공급원을 확인했고 A05 선택 흐름과 정류장 매칭은 저장 응답으로 검증했습니다. 자전거 존·택시 승강장(D-036)은 **위치만**(`facilities`) 넣습니다. 11/19 실호출로 **둘 다 전국 공급원 확인**(택시는 좌표 변환 필요), 적재 전에는 지도에 '준비 중'으로 둡니다. 둘 다 핵심 흐름(전국 축제 탐색·귀가 경로)이 없어도 동작하는 부가 정보입니다.

---

## 10. 실행 확인 기록 (2026-11-23 밤 로컬 기록 포함)

**강사 11/19 DB 피드백 1:** 기본 시험과 기존 데이터가 있는 009 시험은 아래 실행기로 재실행할 수 있습니다. 이번에 연결한 010 전용 시험(T010a~e)과 015 시험(T015a~d)도 11/24 실행해 통과했습니다.

적용 순서는 001→…→008→009 사전 검사→009→010→011 사전 검사→011→012→013→014→015 사전 검사→015→016 사전 검사→016→017→018입니다. 001~009와 011~018의 적용·되돌리기는 파일 단위로 `psql -1 -v ON_ERROR_STOP=1 -f <파일>`을 사용합니다(표의 기본 시험은 빈 DB에 적용). 010은 적용·되돌리기 SQL에 `BEGIN`/`COMMIT`이 있어 `psql -v ON_ERROR_STOP=1 -f <파일>`로 실행합니다. 011~013 적용·되돌리기는 트랜잭션 안에서 두 경로 테이블을 먼저 잠급니다.

| 순서 | 파일 (GitHub `Docs/Step 2/db/`) | 내용 |
|---|---|---|
| 1 | `db/001_schema_v0.3.1.sql` (기본 마이그레이션 001, 001 DDL(`db/001_schema_v0.3.1.sql`)) | 기본 30개 테이블·외래키 43·RLS·트리거·권한 |
| 2 | `db/002_assistant_runs.sql` (되돌리기 `002_assistant_runs_down.sql`) | 챗봇 작업 테이블 1개 + 외래키 2 + RLS (03 문서 7-6) |
| 2-1 | `db/003_festival_images.sql` (되돌리기 `003_festival_images_down.sql`) | `festivals`에 썸네일·저작권 유형 칸 2개 (03 문서 7-13 이미지 규칙) |
| 2-2 | `db/004_trends_and_privacy.sql` (되돌리기 `004_trends_and_privacy_down.sql`) | `festival_trends`(A42) 1개 + 외래키 3, 목적지 라벨 칸 삭제·장소 해시 NULL 허용(개인정보) |
| 2-3 | `db/005_recommend_and_friends.sql` (되돌리기 `005_recommend_and_friends_down.sql`) | 추천 3개·친구 3개 테이블 + `profiles` 친구 코드 칸 + 외래키 10 + RLS |
| 2-4 | `db/006_visit_course_and_notices.sql` (되돌리기 `006_visit_course_and_notices_down.sql`) | `assistant_runs`에 `run_kind`·`result`(AI 방문 코스), `notice_events`(공지 관리 이력, 추가만) + 외래키 2 |
| 2-5 | `db/007_companion_chat_notifications.sql` (되돌리기 `007_companion_chat_notifications_down.sql`) | 동행 3·채팅 3·알림 1·신고 1·관리자 열람 기록 1 = 9개 테이블 + 외래키 19 + RLS·멤버 확인 함수 2개 |
| 2-6 | `db/008_review_fixes.sql` (되돌리기 `008_review_fixes_down.sql`) | 교차 검토 반영: 프로필 검색 허용 권한, 숨긴 축제 공개 제외, 권한 함수 검색 경로 고정, 동행 글 숨김 칸 + 외래키 1, 복구 조치 해제 기록, 부하 시험 칸 3개, 공개 표시 이름 함수 |
| 2-7 사전 검사 | `db/009_precheck.sql` | 기존 DB의 닉네임 제약 위반·삭제되는 값 확인. 결과를 보고 009 적용 여부 결정(10-A-2) |
| 2-7 | `db/009_scenario_v1.sql` (되돌리기 `009_scenario_v1_down.sql`) | 기능 상세 시나리오(11/20 신유빈 초안 + 사용자 결정): 귀갓길·가는 길 출발·도착 선택(`origin_type`·`destination_type`·장소 해시 2칸, `user_place_hash` 대체), `profiles.birth_year`·`gender`, 닉네임 2~12자·중복 금지(친구 코드·검색 허용 칸 삭제), 신청자 정보·닉네임 검색 함수, 신고 대상 `chat_room`, RAG `app_guide` |
| 2-8 | `db/010_festival_sources_public.sql` (되돌리기 `010_festival_sources_public_down.sql`) | 공개 축제 원본 컬럼 읽기 권한·RLS. 적용·되돌리기는 각 파일 내부 트랜잭션. 010 증빙은 10-A-3 |
| 2-9 사전 검사 | `db/precheck_011_route_access_token.sql` | 기존 경로 요청 건수 확인 |
| 2-9 | `db/011_route_access_token.sql` (되돌리기 `011_route_access_token_down.sql`) | 토큰·본문 해시, 오류 상세, TMAP 정리 색인 추가 |
| 2-10 | `db/012_route_backup_evidence.sql` (되돌리기 `012_route_backup_evidence_down.sql`) | 요청에 결과의 공급원·조회 시각 이관 및 동기화. 복원 후 `ready` 요청의 결과 행이 없으면 유효 토큰으로 조회한 A05는 `ROUTE_RESULT_EXPIRED`(`retryable=false`)와 새 경로 요청 안내를 반환(7-0 ④) |
| 2-11 | `db/013_route_purge_evidence.sql` (되돌리기 `013_route_purge_evidence_down.sql`) | 요청의 `result_purged_at`에 기존 삭제 시각 이관 및 이후 정리와 같은 트랜잭션에서 기록 |
| 2-12 | [`db/014_tourapi_festival_class.sql`](db/014_tourapi_festival_class.sql) (되돌리기 `014_tourapi_festival_class_down.sql`) | TourAPI 분류 원본 3개 컬럼 추가와 공개 축제 RLS를 A02·A03 범위로 변경 |
| 2-13 사전 검사 | [`db/precheck_015_friendships_request_unique.sql`](db/precheck_015_friendships_request_unique.sql) | NULL을 제외한 중복 신청 ID 그룹의 수 확인. 0건이면 적용 가능 |
| 2-13 | [`db/015_friendships_request_unique.sql`](db/015_friendships_request_unique.sql) (되돌리기 `015_friendships_request_unique_down.sql`) | `friendships`를 잠근 뒤 중복을 다시 확인하고 `UNIQUE (request_id)` 추가. 중복이 있으면 적용 중단. 되돌리기는 UNIQUE만 제거 |
| 2-14 사전 검사 | [`db/precheck_016_direct_room_key_partial_unique.sql`](db/precheck_016_direct_room_key_partial_unique.sql) | 적용 전 `duplicate_keys_for_up`, 되돌리기 전 `duplicate_keys_for_down`이 0인지 확인 |
| 2-14 | [`db/016_direct_room_key_partial_unique.sql`](db/016_direct_room_key_partial_unique.sql) (되돌리기 [`016_direct_room_key_partial_unique_down.sql`](db/016_direct_room_key_partial_unique_down.sql)) | `chat_rooms`를 잠근 뒤 `status <> 'closed'` 부분 UNIQUE로 교체. 되돌릴 때 닫힌 방을 포함해 같은 키가 남아 있으면 DB가 전역 UNIQUE 복원을 거부하고 행과 부분 색인을 보존 |
| 2-15 | [`db/017_festival_trends_signal.sql`](db/017_festival_trends_signal.sql) (되돌리기 [`017_festival_trends_signal_down.sql`](db/017_festival_trends_signal_down.sql)) | `festival_trends` 증가율·신호 추가 및 004 CHECK 교체. 되돌리면 새 컬럼 값이 사라지고, 004 제약에 맞지 않는 행이 남아 있으면 되돌리기가 중단됨 |
| 2-16 | [`db/018_festival_publication.sql`](db/018_festival_publication.sql) (되돌리기 [`018_festival_publication_down.sql`](db/018_festival_publication_down.sql)) | EV01 RLS, `coords_source` 추가, 기존 미분류 공개 행 검토 대기 및 이전 게시 상태 이력. 되돌릴 때 이후 게시·분류 변경이 없는 018 대상만 복원하고 좌표 출처 컬럼을 제거합니다. 저장된 위경도 값은 유지됩니다. |
| 2-17 | [`db/019_admin-review.sql`](db/019_admin-review.sql) (되돌리기 [`019_admin-review_down.sql`](db/019_admin-review_down.sql)) | A24 대기열 사유 제약 확장, 인덱스와 기존 TourAPI 보류 사유 이관. 새 사유를 처리한 결정이 있으면 되돌리기를 중단합니다. |
| 2-20 | [`db/026_jobs.sql`](db/026_jobs.sql) (되돌리기 [`026_jobs_down.sql`](db/026_jobs_down.sql)) | 서비스 전용 성공 회차와 경로 요청 만료 외래 키·인덱스. 적용·되돌리기·재적용은 [`tests_026_jobs.sql`](db/tests_026_jobs.sql)에서 확인합니다. |
| 2-21 | [`db/027_src2.sql`](db/027_src2.sql) (되돌리기 [`027_src2_down.sql`](db/027_src2_down.sql)) | 서울시 문화행사의 이미지 URL 검토 근거를 추가합니다. [`tests_027_src2.sql`](db/tests_027_src2.sql)에서 RLS·컬럼 권한·되돌리기·재적용을 확인합니다. |
| 2-22 | [`db/028_review-fix.sql`](db/028_review-fix.sql) (되돌리기 [`028_review-fix_down.sql`](db/028_review-fix_down.sql)) | 경로 캐시 메타 삭제 시 경로 결과의 참조만 NULL로 변경합니다. [`tests_028_review-fix.sql`](db/tests_028_review-fix.sql)에서 적용·되돌리기를 확인합니다. |
| 3 | `db/tests_v0.3.2.sql` → `db/tests_v0.3.2_after_backup.sql` | 시험 T1~T43 (스스로 판정: 기대와 다르면 `FAIL`로 멈춤) |
| 4 | [`db/tests_010_festival_sources_public.sql`](db/tests_010_festival_sources_public.sql) | 공개 원본 조회·조인, 내부 컬럼 차단, 되돌리기·재적용(T010a~e). **11/24 통과** |
| 4 | `db/tests_011_route_access_token.sql` | 기존 행 보존·해시 제약·일반 계정 차단·되돌리기·재적용(T011a~d) |
| 5 | `db/tests_012_route_backup_evidence.sql` · `db/backup_long_term.sh` | 012 이관·신규 기록·되돌리기·재적용, 7일 백업을 빈 DB에 복원해 경로 내용 제외와 증빙 보존 확인(T25a·b). **11/24 로컬 통과** |
| 5 | `db/tests_013_route_purge_evidence.sql` | 013 이관·트리거·권한·되돌리기·재적용(T013a~d), 복원 뒤 삭제 시각 보존(T25c). **11/24 통과** |
| 5-1 | `db/tests_014_tourapi_festival_class.sql` | 014 분류 저장 컬럼·공개 축제 RLS·010 원본 참조 범위·되돌리기·재적용(T014a~e). **11/24 통과** |
| 5-2 | [`db/tests_015_friendships_request_unique.sql`](db/tests_015_friendships_request_unique.sql) | 중복 신청 참조 거부·복수 NULL 허용·되돌리기·재적용 및 기존 중복 사전 검사·적용 중단(T015a~d). **11/24 통과** |
| 5-3 | [`db/tests_016_direct_room_key_partial_unique.sql`](db/tests_016_direct_room_key_partial_unique.sql) | 닫힌 방 보존과 새 방 개설·활성 방 중복과 재개 거부·되돌리기와 재적용·중복 키가 있는 경우 되돌리기 차단(T016a~e). **11/24 통과** |
| 5-4 | [`db/tests_017_festival_trends_signal.sql`](db/tests_017_festival_trends_signal.sql) | 증가율·신호 제약, 기존 행·공개 조회 정책 보존, 되돌리기·재적용, 004 제약에 맞지 않는 행이 있을 때 되돌리기 중단(T017a~e). 실행 결과는 10-A-4절 |
| 5-5 | [`db/tests_018_festival_publication.sql`](db/tests_018_festival_publication.sql) | 미분류 데이터 정리·이력, 축제 및 원본 RLS, 좌표 출처 제약, 되돌리기·재적용(T018a~d) |
| 5-6 | [`db/tests_019_admin-review.sql`](db/tests_019_admin-review.sql) | 기존 행 이관·사유 제약·앱 역할 접근 제한·되돌리기·재적용과 처리된 결정의 되돌리기 차단(T019a~d) |
| 5-9 | [`db/023_notice.sql`](db/023_notice.sql)·[`db/023_notice_down.sql`](db/023_notice_down.sql)·[`db/tests_023_notice.sql`](db/tests_023_notice.sql) | 공지 수동 종료·축제별 효력 전이·캐시 무효화·공개 RLS와 이력 보존(T022a~e). 021 적용 뒤 적용·되돌리기·재적용 |
| 6 | `db/explain_v0.3.2.sql` | 축제 검색 인덱스 전후 실행 계획(데이터 생성 SQL 포함) |
| — | `db/run_tests.sh` | 새 컨테이너에서 001~009와 기존 시험 실행 후 010~019 적용·시험 및 7일 백업 복원. 009 기존 데이터 사전 검사는 별도 실행기 사용 |
| — | `backend/tests/routes/test_p18_route_store_db.py` | `TEST_DB_APP_URL`의 `noldaga_app`으로 축제 조회, `TEST_DB_URL`로 시험 데이터 준비·경로 저장. 접수→상태→TMAP 저장·조회·만료, 토큰 만료 후 A04 재전송, 카카오 미저장, A05·정기 정리의 삭제 시각 일치. 011 시험에는 소유자 권한 또는 `TEST_DB_MIGRATION_URL` 필요. **11/24 기존 P18 4개 로컬 통과**. 신규 DB 행 원문·삭제 시각 검사는 013 적용 일회용 DB에서 실행 |
| — | `db/run_tests_009_existing.sh` · `db/tests_009_existing_data.sql` | 기존 데이터로 사전 검사→적용→실패 시 취소→되돌리기·다시 적용(T44~T48) |
| — | `db/results_2026-11-20.log` · `db/results_2026-11-23.log` | 11/20 기본 SQL·백업 PASS 149건. 11/23 밤 PASS 156건(기본 149건 + T011a~d 4건 + 재적용 T011a~c 3건) |
| — | `db/results_2026-11-23_009_existing.log` | 기존 데이터 시험 T44~T48, PASS 13개 |
| — | [`db/results_2026-11-24.log`](db/results_2026-11-24.log) | `ohyun` `719484d` 이후 실행기 출력 PASS 표기 265줄(개별 시험 PASS 260건 + 요약 5줄), FAIL 0. 001~028 적용·010~015 되돌리기·재적용 및 T25a~c 복원 포함 |

| 항목 | 내용 |
|---|---|
| 환경 | 집 컴퓨터 Docker `pgvector/pgvector:pg17`(digest `sha256:b513c485…`) — **PostgreSQL 17.12**, `vector` 0.8.7, `pg_trgm` 1.6. **운영(AWS)과 같은 이미지** |
| 결과 | 001 뒤 테이블 30·외래키 43 → 002 적용 → **되돌리기 확인(테이블 사라짐)** → 다시 적용 → 003~009도 각각 적용·되돌리기·다시 적용 → 테이블 48·외래키 80·**RLS 48개 모두 켬**. **확인 149개 모두 PASS, FAIL 0** (`db/results_2026-11-20.log`) |
| AWS | **미실행.** 같은 이미지·DDL·시험을 AWS에서 다시 돌릴 예정: WBS W65(AWS Docker·DB 운영 구성, 신유빈, 12/07–12/10). 로컬 통과를 배포 환경 검증으로 쓰지 않습니다(강사 피드백 3) |
| 코드 위치 | `Docs/Step 2/db/`에 설계 검증 SQL·시험·로그를 둡니다. `ohyun` 실행기는 017까지 포함합니다. `yubeen` 실행기와 병합 뒤 적용 범위는 신유빈이 확인합니다(W17, API 구현·검증 기록 19절) |

11/24 SQL·DB 시험 기준 커밋은 `ohyun` `719484d`입니다. 이 커밋 이후 집 PC 일회용 `pgvector/pgvector:pg17` 컨테이너에서 `run_tests.sh`로 001~028를 적용하고 010~015 되돌리기·재적용과 T25a~c 백업 복원을 확인했습니다. 실행기 출력 PASS 표기 265줄(개별 시험 PASS 260건 + 요약 5줄), FAIL 0입니다. 001~014 적용 후 저장소 루트에서 `python -m pytest backend/tests -m db -q`는 16개 통과, 오프라인 `python -m pytest backend/tests -q`는 490개 통과·25개 건너뜀입니다. AWS 검증은 W65 AWS 구성 뒤 같은 실행기로 다시 실행합니다(AWS 환경 신유빈 관리). [11/24 SQL 로그](db/results_2026-11-24.log)

| 시험 | 기대 | 결과(11/20) |
|---|---|---|
| T1 사용자 A가 `favorites` 조회 | 본인 것 1행만 | ✅ 1행 |
| T2 사용자 A가 B의 이름으로 관심 저장 | RLS 거부 | ✅ `new row violates row-level security policy` |
| T3 / T4 일반 사용자 / 운영자가 `incident_logs` 조회 | 0행 / 1행 | ✅ 0행 / 1행 |
| T5 운영자(API 역할)가 `incident_logs`에 직접 추가 | 거부 | ✅ `permission denied` |
| T6 `incident_events` 수정 | 트리거 거부 | ✅ "추가만 할 수 있습니다" |
| T7 ID `INC-003`으로 사건 추가 | CHECK 거부 | ✅ `incident_logs_incident_id_check` |
| T8 캐시로 제공했는데 `validity_check` 없음 | CHECK 거부 | ✅ `route_results_check` |
| T9 `select` 결정에 `stop_condition` 없음 | CHECK 거부 | ✅ `recovery_plans_check2` |
| T10 `created_at` 없는 테이블 | 0개 | ✅ 0개(48개 모두 있음) |
| T11 외래키 수 | 43 + 2 + 3 + 10 + 2 + 19 + 1 = 80 (009는 0) | ✅ 80 |
| T12 API 역할이 `users`(비밀번호 해시) 조회 | 거부 | ✅ `permission denied` |
| T13 서비스 역할이 사건 기록 | 성공(RLS 우회) | ✅ 1행 |
| T14 복구 시도 결과 수정 | `pending`일 때 1회 성공, 두 번째 거부 | ✅ 1행 / "판정이 끝난 시도는 바꿀 수 없습니다" |
| T15 사건의 `detection_rule` 수정·삭제 | 둘 다 거부 | ✅ "status·closed_at만", "삭제할 수 없습니다" |
| T16 사용자가 자기 `role`을 `admin`으로 | 거부 | ✅ `permission denied`(컬럼 권한) |
| T17 비공개 축제 조회 | 게시된 1건만 | ✅ 1행 |
| T18 카카오 결과에 경로 내용 저장 / 캐시 등록 / 내용 없이 저장 | 거부 / 거부 / 성공 | ✅ `route_results_check1` / `route_cache_entries_provider_check` / 1행 |
| T19 TMAP 결과에 경로 내용 없이 저장 | 거부 | ✅ `route_results_check2` |
| T20 TMAP 경로 내용을 `purged_at` 없이 지움 / 함께 지움 / 당시 23시간 기준 SQL 쿼리 | 거부 / 성공 / 실행됨 | ✅ `route_results_check2` / 1행 / 0행 |
| **T21 DB 연결 재사용(새)** — 같은 연결에서 요청 A → 사용자 정보 없는 요청 → 요청 B → 오류로 롤백된 요청 → 다음 요청 | 앞 요청의 사용자가 남지 않음, 사용자 정보 없으면 본인 데이터 0행·쓰기 거부, B는 B 것만 | ✅ A 다음 요청 `app_current_user()` = NULL, `favorites`·`profiles` 0행, 저장 거부, B 요청 B 1행·A 0행, 롤백 뒤 NULL |
| **T22 금지 패턴 확인(새)** — `LOCAL` 없이 `SET app.user_id` | 다음 요청에 **남음**(그래서 코드에서 금지) | ✅ 남는 것 확인 → 3절 규칙의 근거 |
| **T23 다른 사람 데이터 수정·삭제(새)** | 0행(안 보이므로 안 바뀜), 본인 것은 1행 | ✅ B 표시 이름 수정 0행·B 관심 삭제 0행·본인 수정 1행, B 값 그대로 |
| **T24 챗봇 작업 `assistant_runs`(새, 002)** | 같은 `request_id` 거부, 두 워커 동시 선점 시 1명만, 답변 없이 성공·오류 코드 없이 실패 거부, 70초 넘은 `running` 정리, 보존 정리 규칙, 본인 작업만 조회, API 역할 상태 변경 거부 | ✅ 11개 확인 모두 통과 |
| **T25a·b 7일 백업 복원(7-0 ④)** | 원본 DB에 합성 후보·공급원 원본 표식이 있는 상태에서 백업. 복원 DB의 `route_results` 0행, 요청의 공급원·조회 시각·상태·오류 코드 일치 | ✅ 11/24 로컬 복원 통과. [SQL 로그](db/results_2026-11-24.log) |
| **T25c 7일 백업 복원(013)** | 복원 DB에서 정리한 요청의 `result_purged_at`이 원본 삭제 시각과 일치. 미정리 요청과 결과가 없었던 요청은 NULL | 11/24 통과 |
| **T27 지금 핫한 축제 `festival_trends`(새, 004)** | 연결·미연결 저장, matched인데 축제 없음 거부, 순위·언급 수 둘 다 없음 거부, 공개 역할은 연결된 것만 조회·추가 거부 | ✅ 6개 확인 통과 |
| **T28 목적지 라벨 DB에 없음·장소 해시 지우기(새, 004)** | `user_place_label` 칸 0개, 사건 연결 행의 해시만 NULL | ✅ 0개 / 1행 |
| **T29 취향(새, 005)** | 모르는 값 거부, 아무것도 안 고르고 완료 거부, 본인 저장 성공, 남의 취향 저장 거부, 다른 사용자 조회 0행 | ✅ 5개 |
| **T30 축제 태그 분류(새, 005)** | 근거 없이 검증 거부, LLM 검증인데 모델·프롬프트 없음 거부, 반려견을 예측 데이터로 검증 거부, 근거와 함께 검증 성공, 공개 역할은 검증된 것만·직접 추가 거부 | ✅ 7개 |
| **T31 일간 지표(새, 005)** | 음수 거부 | ✅ |
| **T32 친구 신청(새, 005·009)** | 닉네임 1글자 거부·대소문자만 다른 닉네임 거부, 자기 자신 거부, 반대 방향 대기 신청 중복 거부, 응답 시각 없이 수락 거부, 관계 순서 거꾸로 거부 | ✅ 6개 |
| **T33 친구 권한(새, 005)** | 당사자는 봄, 앱 역할이 직접 관계 생성 거부, 제3자 0행, 차단당한 사람은 차단 사실 못 봄, 차단한 사람은 봄 | ✅ 5개 |
| **T34 AI 방문 코스(새, 006)** | 챗봇 작업에 코스 결과 거부, 코스 작업·결과 저장 성공, 보존 정리 때 결과를 남기면 거부 | ✅ 4개 |
| **T35 공지 관리 이력(새, 006)** | 등록 이력 성공, 이유 없는 반려 거부, 이력 수정 거부(추가만), 앱 역할 직접 기록 거부, 미승인 공지 공개 조회 0행 | ✅ 5개 |
| **T36 동행 신청·정원(새, 007)** | 대기 중 재신청 거부, 결정 시각 없이 승인 거부, **정원 초과 승인 거부(동시 승인 재현)** | ✅ 3개 |
| **T37 동행 권한(새, 007)** | 승인 전: 장소·메시지 0행, 자기 신청·공개 글은 봄, 앱 역할 직접 승인 거부 / 승인 뒤: 장소 봄, **입장 뒤 메시지만** / 멤버 아니면 방·멤버·메시지·장소 0행 | ✅ 8개 |
| **T38 채팅 저장 규칙(새, 007)** | 같은 순서 번호 거부, **같은 `client_message_id` 재전송 거부(중복 방지)**, 보낸 사람 없는 일반 메시지 거부, 1:1 방 중복 거부, 이름 없는 단체방 거부, **초대만 받은 사람은 메시지 0행** | ✅ 6개 |
| **T39 알림(새, 007)** | 본인 읽음 처리, 읽음 외 칸 수정 거부, 남의 알림 0행 | ✅ 3개 |
| **T40 신고·관리자 열람(새, 007)** | 처리자 없이 완료 거부, 관리자 열람 기록, 기록 삭제 거부, 신고자는 자기 신고만 | ✅ 4개 |
| **T41 채팅 보존(새, 007)** | 동행 종료 3일 지난 메시지 정리(3행), 지우지 않고 내용만 비움 거부, 종료 시각 없이 읽기 전용 거부 | ✅ 3개 |
| **T42 교차 검토 반영(새, 008)** | 본인 닉네임 변경(1행), 게시 뒤 숨긴 축제 안 보임(0행), 권한 함수 3개 검색 경로 `pg_temp` 맨 뒤, 처리자 없는 글 숨김 거부, 숨긴 글은 남에게 0행·작성자 1행, `improved` 뒤 조치 끈 시각 1회 기록·두 번째 거부, 실패 원인 없는 실패 시험 거부, 남의 프로필 행 0행·공개 함수로 이름만, 탈퇴 덮어쓰기 뒤 이름 NULL | ✅ 12개 |
| **T43 기능 상세 시나리오(새, 009)** | 성별 값 제한, 작성자는 신청자 나이·성별 봄·남은 0행, 닉네임 정확히 일치 1명·일부만 0명·결과에 나이·성별 없음, 출발·도착 둘 다 축제 거부, 출발을 사용자 장소로 1행, 축제 장소인데 해시 거부, 채팅방 신고 1행, 앱 사용법 문서 버전 없음 거부, **차단 관계 양쪽 검색 제외·차단 없는 사람은 찾음**, 함수 결과 칸 직접 비교 | ✅ 15개 |
| **T26 축제 대표 이미지(새, 003)** | 이미지 주소만 있고 저작권 유형 없음 거부, 모르는 유형 거부, 셋 함께 저장 성공 | ✅ `festivals_image_copyright_needed` / `festivals_image_copyright_type_check` / 1행 |

- T21의 '같은 연결'은 시험 파일 전체가 DB 연결 1개로 실행되는 것으로 재현했습니다(연결 풀이 같은 연결을 다음 요청에 다시 주는 상황). 공통 연결 풀은 SQLAlchemy 2 + psycopg 3(`yubeen` 브랜치)입니다. `ohyun` 병합·연결 뒤 W18과 DB-09에서 서버 경로를 다시 확인합니다(3절 ⑤).
- 시험 데이터는 모두 가짜(`@test.local`)이고 시험 컨테이너는 끝나면 지웁니다.

---

- DB-14 사용자 풀은 기본 연결 5개와 추가 연결 10개를 사용합니다. SQLAlchemy가 30초 동안 연결을 얻지 못해 대기 시간 초과를 발생시키면 API는 503 `DB_POOL_TIMEOUT`, `retryable=true`, `Retry-After: 1`로 응답합니다. P24 단위 시험은 풀 시간 초과를 모의합니다(API 6절).
- A01은 DB를 사용하는 API 설정에서 앱 계정(`DB_USER_USERNAME`, 기본 `noldaga_app`)으로 별도 연결해 `SELECT 1`을 실행합니다. 연결과 쿼리에 총 1초를 허용합니다. 오류나 시간 초과 시 503과 `db: unavailable`을 반환합니다. 공통 Redis 연결이 준비될 때까지 `redis: not_configured`를 반환합니다(API 6절).

## 10-A. 11/23~24 추가 실행 확인 (강사 11/20 DB 피드백 1·3·4)

### 10-A-1. 시험 환경 구분
| 환경 | 무엇을 | 언제 | 데이터 | 결과 |
|---|---|---|---|---|
| **일회용 로컬 Docker**(집 PC, `pgvector/pgvector:pg17`) | 기본 SQL·백업, 010~015 적용·되돌리기·재적용 및 T25a~c 백업 복원(`run_tests.sh`) | 11/24 | 시험 데이터만 | 실행기 출력 PASS 표기 265줄(개별 시험 PASS 260건 + 요약 5줄), FAIL 0. 11/23 밤 기록은 PASS 156건. [11/24 SQL 로그](db/results_2026-11-24.log) |
| 일회용 로컬 Docker | **T44~T48 데이터가 있는 DB에서 009**(`run_tests_009_existing.sh`) | 11/23 | 사용자 3·경로 2(귀가·가는 길)·신고·RAG 시험 행 | 13개 PASS — `results_2026-11-23_009_existing.log` |
| 일회용 로컬 Docker | 마이그레이션 010 T010a~e | 11/23 | 시험용 공개·비공개 축제(세부 입력 기록 없음) | 구현 계획에 5개 통과 기록(10-A-3) |
| 일회용 로컬 Docker | 010 전용 T010a~e 및 015 T015a~d(`run_tests.sh`) | 11/24 | 가상 축제·원본 및 친구 신청·관계 | 통과(T010a~e·T015a~d, 위 전체 집계에 포함) |
| 일회용 로컬 Docker | 001~014 적용 후 루트 `python -m pytest backend/tests -m db -q`(수집·축제 조회, 경로 P18) | 11/24 | 시험 축제·경로 | **16개 통과**. 11/23 밤 9개 통과·3개 실패 뒤 축제 지역 코드와 조회 계정을 수정. [귀가 경로 구현 계획](../../backend/Doc/route-providers/IMP-PLAN.md#step4-db-저장) |
| **학원 노트북 개발 DB**(로컬, 노트북 안에서만 열림) | 001~010 적용 + **TourAPI 실제 870건 적재** → 재수집 | 11/23 | 실제 축제(공개 869·검토 1) | 1회차 inserted 870 · 2회차 inserted 0·updated 0·상세 재호출 0, `schema_migrations` 001~010 |
| **AWS(시험 DB)** | 기본·기존 데이터 시험은 같은 이미지와 실행기로 재실행. 010은 별도 적용·되돌리기 및 권한 시험 절차와 증빙 확인 후 재실행 | **예정 W65(12/07~10, 신유빈)** | 별도 시험 데이터 | 미실행. 환경·입력·기대·실제와 결과 로그 기록 예정 |
- `ohyun`의 A04·A05는 공통 `backend/shared/db/session.py` 서비스 세션을 사용합니다. 실제 서버 연결 풀·동시 실행·권한 확인은 DB-09 등에서 이어갑니다. `backend/tests/db/test_session.py`의 세션 시험 6개는 위 DB 표시 pytest 16개와 별도입니다.

### 10-A-2. 데이터가 있는 DB에서 009 (T44~T48)
| 시험 | 입력 | 기대 | 실제 |
|---|---|---|---|
| T44 | 정상 기존 데이터 + `009_precheck.sql` | 실패 원인 0건, 손실 안내(friend_code 1·검색 허용 1) | PASS |
| T45a~c | 대소문자만 다른 닉네임 2개('Dayoung'·'dayoung') | 사전 검사가 찾음 → `psql -1` 적용 실패 → **전부 취소**(새 칸 없음·옛 칸 그대로) | PASS |
| T45d (대조) | 같은 데이터, `-1` 없이 | 일부만 바뀐 채 남음 → **`-1` 필수의 근거** | PASS(일부 적용 확인) |
| T46a·b | 정상 데이터에 `-1` 적용 | 성공, 귀가 행 → 도착 해시·가는 길 행 → 출발 해시로 옮겨짐 | PASS |
| T47a·b | 009 뒤 '출발·도착 둘 다 사용자' 경로 + 좌표 없는 축제 → 되돌리기 | **멈춤**(이유 메시지) → 전부 취소 | PASS |
| T47c·d·e | 축제 좌표가 있으면 → 되돌리기 | 성공, **손실**: chat_room 신고·app_guide 문서 삭제, 출생연도·성별 칸 삭제, '둘 다 사용자' 경로는 장소 해시 하나만 남음 | PASS |
| T48 | 되돌린 뒤 다시 적용 | 성공 | PASS |

**되돌릴 수 없는(손실) 조건 정리:** ① 009 적용 = `friend_code`·`nickname_searchable` 값 삭제(사전 검사가 건수 안내) ② 009 되돌리기 = `app_guide` 문서·`chat_room` 신고·출생연도·성별 삭제, 출발·도착 둘 다 사용자인 경로는 해시 하나만 남음, 좌표 없는 축제의 그런 경로가 있으면 되돌리기 불가(멈춤). → AWS 적용 전 **사전 검사 → `psql -1` 적용 → 결과 로그** 순서를 지킴.

### 10-A-3. 마이그레이션 010 (부록 10)

11/23 일회용 DB의 T010a~e 5개 통과와 학원 노트북 DB의 공개 축제 869건 조인 확인은 수집 구현 계획에 기록돼 있습니다. [수집 구현 계획 3단계](../../backend/Doc/festival-ingestion/IMP-PLAN.md#3단계--a02a03-db-조회-i12i13)

이번에 추가한 전용 시험 SQL은 `run_tests.sh`에서 009 다음에 010을 적용·되돌리기·재적용해 아래 기대 결과를 확인합니다. [010 전용 시험](db/tests_010_festival_sources_public.sql)

| 시험 | 확인 입력 | 기대 결과 | 전용 SQL 상태 |
|---|---|---|---|
| T010a | `noldaga_app`으로 공개·비공개 축제의 원본 번호 조회 | DB RLS로 보이는 축제의 원본 번호만 반환 | 11/24 통과 |
| T010b | `noldaga_app`으로 축제와 원본 조인 | DB RLS로 보이는 축제만 조인 | 11/24 통과 |
| T010c | `noldaga_app`으로 `raw_checksum` 등 내부 칸 조회 | 권한 거부 | 11/24 통과 |
| T010d | 010 되돌린 뒤 앱 계정으로 원본 조회 | 권한 거부 | 11/24 통과 |
| T010e | 010 다시 적용 | 권한·정책 복원 | 11/24 통과 |

### 10-A-4. 마이그레이션 017

| 시험 | 기대 결과 | 실행 결과 |
|---|---|---|
| T017a | 기존 순위·언급 수가 보존되고 신호 기본값은 `ok` || 11/24 통과 |
| T017b | 증가율·`no_signal` 저장, 앱 역할은 연결된 행만 조회 || 11/24 통과 |
| T017c | 음수 증가율·미정의/NULL 신호·지표 없는 `ok` 거부 || 11/24 통과 |
| T017d | 되돌리면 두 컬럼이 사라지고 004 CHECK와 기존 행이 유지됨. 재적용 뒤 T017a~c 재실행 || 11/24 통과 |
| T017e | 004 제약을 위반하는 행이 있으면 되돌리기 중단 || 11/24 통과 |

## 19. 결정 반영 기록

| 결정 | 상태 | 반영 위치 | 확인 |
|---|---|---|---|
| 1. TMAP 무료 유지 — Free 하루 10건(오류 포함), 한도 도달 시 카카오 2차(하루 1,000건). 부하 시험은 모의 응답. 유료 전환 안 함 | 확정(11/24 팀 결정) | 4·7절 | 11/24 신유빈 확인 |
| 2. A27 실시간 주차 빈자리 — 채택 안 함(11/24). A08 시설에서 주차장 위치만 제공 | 확정(11/24 팀 결정) | 6-3·6-4절 | 11/24 신유빈 확인 |
| 3. A42 점수는 신유빈 11/24 B안(두 출처 합산)을 따르고, 네이버는 데이터랩 검색어 트렌드를 사용합니다. 약관상 네이버 검색 결과는 A81 표시에만 사용합니다. 데이터랩 증가율·신호와 구석구석 순위는 기존 004·017을 사용해 저장하고 30일 보존. A81 글은 Redis에 10분 캐시 | 확정(11/24 권오현) | 0-A·3·4·6-4·7-0·10절 · API 7-15·8-2 | API 신유빈 · 화면 정예진 |
| 4. 마이페이지 — 마이페이지 API는 비밀번호 변경·탈퇴·관심 축제만 제공. 운영 공지·이용약관은 고정 문서 링크(별도 API 없음) | 확정(11/24 팀 결정) | 6-3절 | 11/24 신유빈 확인 |
| 5. TMAP 지도 표시 — TMAP 경로를 카카오 지도 위에 그림(①). 카카오 공식 답변(11/20)은 타사 지도 위 표시 허용, SK는 회신 없음. 경로 아래 **경로 정보: TMAP** 표기. SK가 금지 회신하면 TMAP 경로를 소요 시간·환승·정류장 목록으로 표시합니다. | 확정(11/24 팀 결정) | 7절 | 11/24 신유빈 확인 |
| 6. 서울 혼잡 시연(W89) — 서울빛초롱축제(`fst_01M835B57450M888RBNEFVRWWA`) · 광화문·덕수궁 POI009, 시의회 앞 POI130, 명동 관광특구 POI003. 숭례문 파수의식은 TourAPI EV03 행사로 범위에서 제외 | 확정(11/24 팀 결정) | 6-4절 | 11/24 신유빈 확인 |
| 7. 인증 — 비밀번호 해시 argon2id, Access JWT 30분, Refresh 14일, 로그인 IP당 분당 10회 | 확정(11/24 팀 결정) | 4·6-3절 | 11/24 신유빈 확인 |
| 8. 보존 기간 — DB 7-0의 보존 기준 확정. 대화 체크포인트 7일, 알림 90일, 경로 요청 30일 뒤 삭제(사건 연결 행은 보존표에 따라 처리) | 확정(11/24 팀 결정) | 2-1·7-0절 | 11/24 신유빈 확인 |
| 9. 운영자 화면 DB 조회 — FastAPI에서 권한 확인 후 서버 계정 `noldaga_service`를 경유해서만 조회 | 확정(11/24 팀 결정) | 3·7-2절 | 11/24 신유빈 확인 |
| 10. 차단 해제 뒤 1:1 채팅방 — 차단을 해제해도 기존 1:1 채팅방은 닫힌 채 유지. 다시 대화하려면 새 방에서 시작 | 확정(11/24 팀 결정) | 6-8·7-1·7-2·8·10절(016) | 11/24 신유빈 확인 |
| 11. 장애 감지·복구 초기 SLO — 귀가 조회 p95가 3초를 초과한 상태가 30초 이어지면 장애, 3초 이하가 5분 유지되면 복구. W96 계측 뒤 숫자만 조정하며, 조정 시 설정 버전(`LIMITS_VERSION`)을 올림 | 확정(11/24 팀 결정) | 6-2·7절 | 11/24 신유빈 확인 |
| 12. 운영비 — 축제 하루 방문자 1만 명·1인 1.5회는 계산용 가정 | 확정(11/24 팀 결정) | 9절(API 9-2 연계) | 11/24 신유빈 확인 |
| 13. 추천 API A36~A41 담당 — 신유빈(협업 규칙) | 확정(11/24 팀 결정) | 6-6·7-1절 | 11/24 신유빈 확인 |
| 14. BFCL 30문항 채점 — API 설계서 최신판(v0.5) 기준. 원본은 한다영 브랜치 | 확정(11/24 팀 결정) | 9절(API 4-7 연계) | 11/24 신유빈 확인 |

---
