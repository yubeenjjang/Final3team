# IMP-PLAN — 축제 실제 수집·저장·조회

단계마다 만들 파일만 만들고 → 시험 → 체크 → (Claude 실제 실행·검증) → commit. 앞 단계가 끝나기 전에 다음 단계로 가지 않는다.

| 단계 | 담당 (도구·모델) | 요구 | 시작 조건 |
|---|---|---|---|
| 1 | Codex · gpt-6.2-sol · reasoning medium | I1~I8 | 고정 파일 준비(✅ 11/23) |
| 1-실행 | Claude | 실제 수집 `--since 2026-01-01`(목록 9회 + 상세 약 1,740회 → 기능별 1,000 한도 안) → report 확인 | 1단계 시험 통과 |
| 2 | Codex · gpt-6.2-sol · reasoning high (업서트·변경 이력·재실행 규칙) | I9~I11 | 1-실행 끝, Claude가 `sqlalchemy`·`psycopg[binary]`·`python-ulid`를 requirements에 넣고 캐시 준비 |
| 2-실행 | Claude | **학원 노트북 DB**(`noldaga-db`, `pgvector/pgvector:pg17`, 001~009 적용 ✅ 11/23, 노트북 안 `127.0.0.1:5432`만, 집 PC는 SSH 터널) → `-m db` 시험 → 실제 저장 2회(재실행 중복 0 확인) | 2단계 시험 통과 |
| 3 | Codex · gpt-6.2-sol · reasoning medium | I12 | 2-실행 끝 |
| 3-실행 | Claude | `FESTIVAL_DATA=db`로 서버 → A02·A03 실제 응답 확인, 웹 화면(ohyun-web) 확인, 노트북 시연 최신화 | 3단계 시험 통과 |

## 1단계 — TourAPI 클라이언트 + 정규화·검사 + 수집 실행기(DB 없음)
**만들 파일(목록 밖 금지)**
- 채움: `api/providers/tourapi.py`(지금은 주석 한 줄)
- 새로: `api/ingestion/festivals/__init__.py`, `api/ingestion/festivals/normalize.py`, `api/ingestion/festivals/collect.py`
- 새로: `tests/ingestion/__init__.py`, `tests/ingestion/test_i1_tourapi_client.py`, `tests/ingestion/test_i4_normalize.py`, `tests/ingestion/test_i8_collect.py`
- 읽기만: `tests/ingestion/fixtures/*`(고치지 않음)

**체크리스트**
- [x] I1 설정·키 숨김·재시도
- [x] I2 목록 전체 페이지·상세·오류 코드(KEY_ERROR 포함)
- [x] I3 출력 모양
- [x] I4 지역 코드(`12` 나누기 포함)
- [x] I5 날짜·좌표·이미지·상태·체크섬
- [x] I6 상세 칸 정리
- [x] I7 공개 판정
- [x] I8 수집 명령·보고서·한도 보호
- [x] `tests/ingestion` + `tests/api` 전부 통과
- [ ] commit `feat(ingestion): TourAPI client, festival normalize/validate, offline collector`

## 2단계 — DB 저장 (I9~I11)
**준비(Claude, ✅ 11/23):** `api/requirements.txt`에 `sqlalchemy==2.0.45`, `psycopg[binary]==3.3.2`, `python-ulid==3.1.0` 추가·캐시. 1단계 실제 수집 결과: 870건(공개 869·검토 1), 오류 0.

**만들 파일(목록 밖 금지)**
- 새로: `api/ingestion/db.py`(I9), `api/ingestion/festivals/store.py`(I10)
- 고침: `api/ingestion/festivals/collect.py`(`--db` 옵션·I11만 추가, 기존 동작 유지)
- 새로: `tests/ingestion/conftest.py`(`db` 표시 등록, DB 시험용 fixture), `tests/ingestion/test_i9_db.py`, `tests/ingestion/test_i10_store.py`, `tests/ingestion/test_i11_changed_only.py`
- 읽기만: `Docs/Step 2/db/001_schema_v0.3.1.sql`의 `data_sources`·`festivals`·`festival_sources`·`ingestion_jobs`·`festival_change_history` 블록, `003_festival_images.sql`(이미지 칸)

**DB 시험 규칙**
- `@pytest.mark.db` 시험은 환경변수 **`TEST_DB_URL`**(예: `postgresql+psycopg://noldaga_service:...@127.0.0.1:55432/noldaga`)이 없으면 **건너뜀**. Codex 샌드박스에서는 건너뛴 상태로 끝나도 된다(Claude가 일회용 도커 DB로 실행).
- 시험마다 대상 표를 비우고 시작(`TRUNCATE festival_change_history, festival_sources, festivals, ingestion_jobs RESTART IDENTITY CASCADE`). **개발 DB(학원 노트북)에서는 시험을 돌리지 않는다.**
- DB 없이도 돌아가는 부분(업서트 판단 로직: 새로/같음/바뀜 판정, 바뀐 칸 목록 계산, 공개 규칙)은 **순수 함수로 분리해 일반 시험**으로도 확인한다.
- `data_sources` 기본 행: `source_id='tourapi'`, `name='한국관광공사 TourAPI'`, `provider_org='한국관광공사'`, `scope='national'`, `is_realtime=false`, `refresh_s=86400`, `key_site='data.go.kr'`, `status='verified'`. 수집 성공 때 `last_success_at` 갱신.

**체크리스트**
- [x] I9 연결 한 곳·비밀번호 숨김
- [x] I10 업서트(새로·같음·바뀜·hidden 유지·이력·작업 기록)
- [x] I11 바뀐 축제만 상세
- [x] 일반 시험 전부 통과(DB 시험은 건너뜀 표시)
- [x] (Claude) 일회용 DB에서 `-m db` 전부 통과
- [x] (Claude) 학원 노트북 DB에 실제 저장 2회: 1회차 inserted 870, 2회차 inserted 0·updated 0·상세 호출 0
- [x] commit `feat(ingestion): festival upsert to DB with change history, ingestion jobs, changed-only detail refetch`

**2-실행 결과(11/23, 로컬 = 학원 노트북 DB, AWS 아님):** 일회용 DB `-m db` 4개 통과(Claude 수정 2곳: 시험 정리 `TRUNCATE`→`DELETE` — 수집 계정에 TRUNCATE 권한 없음이 맞음, DB에서 읽은 시각을 KST로). 1회차는 **오늘 상세 호출 한도(기능별 1,000) 보호**를 위해 1단계 결과 `festivals.jsonl`을 API 재호출 없이 저장 → inserted 870. 2회차 `collect --db` 실제 실행 → 목록 9회·**상세 0회**, inserted 0·updated 0. DB: festivals 870·published 869·pending 1·history 0·jobs 2건 success.

## 3단계 — A02·A03 DB 조회 (I12)
**만들 파일** — 3단계 시작 때 Claude가 확정해서 적는다.

## 메모
- (11/23) 지역 코드 `12`(전남광주통합특별시)를 구(200~399)=광주·나머지=전남으로 나눈 것은 **임시 규칙** — 팀 확인 필요(API 0-1 지역 코드에 통합 코드를 둘지).
- (11/23) `published_at` 자동 공개(`approved`)는 관리자 검토 화면(나중) 전까지의 임시 규칙.
- (11/23) I11의 수정 시각은 DDL에 따라 `festival_sources`와 연결된 `festivals.source_updated_at`에서 읽는다. I7의 검토 대상 중 제목·지역 코드가 없는 건은 두 컬럼의 `NOT NULL` 제약 때문에 작업의 `rejected`로 집계한다. 날짜·좌표가 누락된 건은 제목과 지역 코드가 있으면 `pending`으로 저장한다.
- (11/23) 상세 요청이 실패하거나 생략된 건은 기존 상세와 저장된 수정 시각을 유지한다. 다음 실행은 유효한 목록 수정 시각이 저장된 값보다 새로우면 상세를 다시 요청한다.
