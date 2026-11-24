# IMP-PLAN — 귀가 경로 실제 조회

| 단계 | 담당 (도구·모델) | 요구 | 시작 조건 |
|---|---|---|---|
| 1 | Codex · gpt-6.2-sol · reasoning medium | P1~P8 (어댑터·한도, 연결 없음) | 합성 고정 파일 준비 ✅ 11/23 |
| 2 | Codex · gpt-6.2-sol · reasoning **high** (전환·동기/비동기·캐시·병합 규칙) | P9~P12 | 1단계 시험 통과 |
| STEP3 막차 처리 | Codex | P13~P15 (강사 API 2 · W36 일부) | 5절 규칙·합성 응답 대조 |
| STEP4 DB 저장 | Codex | P16~P19 (강사 DB 피드백 4) | 009·010과 A04·A05 동작 확인 |
| STEP5 공통 DB 연결 | Codex | P20·P21 (공통 서비스 세션·공통 시험 명령) | `origin/yubeen` 병합 확인 |
| 3-실행 | Claude | 실제 호출: **TMAP 3건 이내**(한태경 님 같은 날 사용 여부 먼저 확인)·카카오 대중교통 3건·장소 검색 3건 → 응답은 모양만 확인 후 **바로 삭제**(TMAP 24시간·카카오 저장 금지), 결과는 호출 기록 표로만. 노트북 시연에 `ROUTE_PROVIDER=real` 적용 여부는 오현 님이 결정 | 2단계 시험 통과 |

## 1단계 — 공통 형식·TMAP·카카오 어댑터·한도
**만들 파일(목록 밖 금지)**
- 채움: `api/providers/route_base.py`, `api/providers/tmap.py`, `api/providers/kakao.py`(지금 주석 한 줄)
- 새로: `api/providers/quota.py`
- 새로: `tests/routes/__init__.py`, `tests/routes/test_p1_base.py`, `tests/routes/test_p2_tmap.py`, `tests/routes/test_p5_kakao.py`, `tests/routes/test_p8_quota.py`
- 읽기만: `tests/routes/fixtures/*`(합성), `api/services/mock_routes.py`(`_candidate` 칸 이름 확인), `api/providers/tourapi.py`(키 숨김·클라이언트 주입 방식 참고)

**체크리스트**
- [x] P1 내부 형식·오류 종류
- [x] P2·P3·P4 TMAP 호출·오류 판정·변환(좌표 뒤집기·막차)
- [x] P5·P6·P7 카카오 대중교통·오류·변환·장소 검색
- [x] P8 한도 계산기(파일 잠금·날짜·동시성)
- [x] 시험 전부 통과
- [ ] commit `feat(routes): TMAP/Kakao adapters, internal route format, daily quota guard`

## 2단계 — 실제 경로 서비스·A04/A05/A25 연결
**만들 파일**
- 새로: `api/services/real_routes.py`
- 고침: `api/routers/routes/routes.py`(`ROUTE_PROVIDER`로 mock/real 고르기만), `api/main.py`(`_serves_real_data`에 `ROUTE_PROVIDER=real`일 때 `/api/v1/routes/(return|visit)` 주소 추가만)
- 새로: `tests/routes/test_p9_real_routes.py`

**체크리스트**
- [x] P9 켜기·응답 모양 유지
- [x] P10 순서(장소 검색·HMAC 키·캐시·병합·1차→2차·오류 코드)
- [x] P11 동기 3초/202·카카오 동기 전용·TMAP 60초 만료
- [x] P12 시험 전부 + 기존 시험 그대로
- [x] (Claude) 3-실행
- [ ] commit `feat(routes): real return/visit routes — TMAP primary, Kakao sync-only fallback, cache, singleflight, HMAC route key`

## 3-실행 결과 (11/23, 집 PC 로컬 서버 — AWS 아님, 응답 원본 저장 안 함)
| 시각대 | 조건 | 공급원 호출 | 결과 |
|---|---|---|---|
| 13시대 | 모의 축제 fst_000001(광화문) → "서울역" | 장소 검색 1 · **TMAP 1** | 200 `tmap/primary` 0.5초, 후보 3개(첫: 버스 1회 20분·1,500원·운행 중), 경로선 `[위도, 경도]` 확인 |
| | 같은 요청 다시(60초 안) | 장소 검색 1 · TMAP **0** | 200 0.1초 — **캐시 동작** |
| | fst_000003(부산 광복로) → "부산역" | 장소 검색 1 · **TMAP 1** | 200 `tmap/primary` 0.4초, 후보 3개 |
| | `ROUTE_TMAP_DAILY_LIMIT=0`으로 카카오 강제 | 장소 검색 1 · **카카오 대중교통 1** | 200 `kakao/secondary`, 후보 3개, 버스 혼잡 `unsupported`, 안내 3개 → A05 재조회 `unavailable`+`ROUTE_SECONDARY_SYNC_ONLY`, 본문 없음 |
- 합계: **TMAP 2건(하루 10건 중)**, 카카오 대중교통 1건, 카카오 장소 검색 4건. 서버 로그에 키 없음. `X-Mock` 없음·`is_mock:false` 확인.
- 남은 것: 카카오 경로선 좌표가 소수 8자리로 옴(TMAP은 6자리) — 화면에는 문제없음, 나중에 맞춤.

## STEP3 막차 처리

- 수정: `api/providers/{route_base,tmap,kakao}.py`, `api/services/real_routes.py`, `tests/routes/{test_p2_tmap,test_p5_kakao,test_p9_real_routes}.py`.
- 문서: 이 트랙의 TODO·SPEC·IMP-PLAN 및 `codex/STEP3.md`, `Docs/Step 2/API_설계문서.md`, `Docs/Step 2/handoff/API_연동_현황표.md`.
- [x] P13 TMAP 운행 판정·후보 제외·대체 노선명
- [x] P14 전체 종료 응답·카카오 막차 안내
- [x] P15 고정 파일 시험·전체 시험·설계서와 연동표 갱신
- 오프라인 `python -m pytest` 전체 결과는 335개 통과, 일회용 DB가 필요한 6개는 건너뜀. 현재 샌드박스에서는 TestClient 스레드 알림에 임시 파이프를 사용했다.

## STEP4 DB 저장

- SQL: `Docs/Step 2/db/precheck_011_route_access_token.sql`, `011_route_access_token.sql`, 되돌리기, `tests_011_route_access_token.sql`, `run_tests.sh`의 011 단계.
- API: `api/repositories/route_db.py`·`route_store.py`, `api/ingestion/db.py`, `api/services/real_routes.py`, `api/routers/routes/routes.py`.
- 시험: `tests/routes/test_p16_route_store.py`·`test_p18_route_store_db.py`, 공통 `db` 표시·건너뛰기 설정.
- 문서: TODO·SPEC·IMP-PLAN·`codex/STEP4.md`, API·DB 설계서, API 연동 현황표.

- [x] P16 011·사전 검사·되돌리기·T011a~d 작성
- [x] P17 DB 요청·상태·A05 토큰 검증 구현
- [x] P18 결과 저장·만료·카카오 동기 전용·시험 작성
- [x] P19 설계서·연동표·신유빈 확인 항목 기록
- [ ] 수정 뒤 일회용 PostgreSQL에서 011과 A02→A05 통합 시험 재실행
- [ ] 서비스 계정 설정·기존 행 처리·정리 실행 주체 확인(신유빈)
- 11/24 전체 오프라인 `python -m pytest` 377개 수집, 365개 통과, DB 표시 12개 건너뜀(P18 4개 포함). 샌드박스에서는 TestClient의 스레드 알림에 임시 파이프를 사용했다.
- 011 사전 검사 파일은 자동 적용본과 구분되도록 `precheck_`로 시작한다. 병합 시 공통 실행기의 번호 검색이 기존 `009_precheck.sql`을 적용본에서 제외하는지 확인한다.

**4-실행 결과 (11/23 밤 일회용 DB(로컬, AWS 아님))**

- `Docs/Step 2/db/run_tests.sh` 통과. 로그 PASS 156건은 기존 SQL·백업 149건, T011a~d 4건 및 재적용 T011a~c 3건이다. 별도 컨테이너에서도 001~011을 적용했다. 010 자체의 `BEGIN/COMMIT` 때문에 중복 트랜잭션 경고가 나왔다.
- 백엔드 `-m db` 9개 통과, 3개 실패. 귀가 경로 4개 중 011 적용·되돌리기·재적용 통과. A02→A05 상태·만료, 카카오 결과 미저장, TMAP 캐시 조기 정리 시험은 실패했다.
- 당시 시험 데이터의 서울 지역 코드 `11`이 API 규격 `SEOUL`과 달랐다. A02 응답 검증(`api/services/festival_store.py:122`)과 귀가 요청 중 축제 상세 검증(`api/services/festival_store.py:149`)에서 실패했다.

**11/24 검토 반영**

- 축제 시험 데이터를 `SEOUL`로 고쳤다. P18은 축제 조회에 `TEST_DB_APP_URL`의 `noldaga_app` 계정을 쓰고, 경로 저장과 시험 데이터 준비에 `TEST_DB_URL`을 쓴다. 011 되돌리기 SQL은 두 경로 테이블을 먼저 잠근다.
- A04·A25의 동일 요청 재전송은 조회 권한 만료 뒤에도 기존 경로 ID를 유지해야 한다. API 설계서가 이 시점의 응답을 지정하지 않아 200 `unavailable`·`ROUTE_ACCESS_EXPIRED`로 명시했다. 조회 토큰·후보·폴링 URL은 생략한다. 단위 시험은 기존 ID와 A05 401을 확인했고, P18에도 만료 재전송 검증을 추가했다.
- Docker SQL 실행기와 백엔드 DB 표시 시험 12개는 **재실행 대기**. 011 DDL 시험은 소유자 권한 또는 `TEST_DB_MIGRATION_URL`이 필요하다.

## STEP5 공통 DB 연결

- [x] P20 귀가 저장소의 별도 엔진을 공통 `service_db_session()`으로 교체했다. 단위 시험에서 A05가 결과 접근 전에 토큰을 검사하고 공통 DB 설정 오류를 기존 503으로 반환하는지 확인했다.
- [x] P21 `backend/tests/conftest.py`에서 두 실행 위치의 import 경로를 맞췄다. 설계서와 시험 안내를 저장소 루트 공통 명령으로 갱신했다. 루트와 `backend/`에서 각각 380개 통과, 16개 건너뜀, 하위 시험 2개 통과. 샌드박스에서는 asyncio 스레드 알림에 임시 파이프를 사용했다.
- [x] 직접 DB 연결 없이 적용 파일을 확인했다. 009 중복 때문에 실행기가 멈춘다. 사전 검사 파일을 제외한 선택 시험에서 011·012가 확인됐다. 적용 전 조치와 010의 트랜잭션 경계는 SPEC의 유빈님 확인 사항에 기록했다.
- [ ] `TEST_DB_URL`이 있는 일회용 환경에서 P18의 실제 PostgreSQL 저장·조회 흐름을 확인한다.

## 메모
- (11/23) TMAP 무료 하루 10건(오류도 셈)·유료 전환은 11/26 결정 대기(`TMAP_PAID_PLAN`) → 한도는 환경변수.
- (11/23) 한도·캐시·병합은 파일·메모리 방식. Redis 연동(`quota:{provider}`·`route:cache:{route_key}`)은 후속이다. STEP4의 DB 모드 상태와 저장 결과는 프로세스 간 공유된다.
- (11/23) 카카오 도보 보완은 이번에 안 함(호출 아끼기).
