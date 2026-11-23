# IMP-PLAN — 귀가 경로 실제 조회

| 단계 | 담당 (도구·모델) | 요구 | 시작 조건 |
|---|---|---|---|
| 1 | Codex · gpt-6.2-sol · reasoning medium | P1~P8 (어댑터·한도, 연결 없음) | 합성 고정 파일 준비 ✅ 11/23 |
| 2 | Codex · gpt-6.2-sol · reasoning **high** (전환·동기/비동기·캐시·병합 규칙) | P9~P12 | 1단계 시험 통과 |
| 3-실행 | Claude | 실제 호출: **TMAP 3건 이내**(한태경 님 같은 날 사용 여부 먼저 확인)·카카오 대중교통 3건·장소 검색 3건 → 응답은 모양만 확인 후 **바로 삭제**(TMAP 24시간·카카오 저장 금지), 결과는 호출 기록 표로만. 노트북 시연에 `ROUTE_PROVIDER=real` 적용 여부는 오현 님이 결정 | 2단계 시험 통과 |

## 1단계 — 공통 형식·TMAP·카카오 어댑터·한도
**만들 파일(목록 밖 금지)**
- 채움: `api/providers/route_base.py`, `api/providers/tmap.py`, `api/providers/kakao.py`(지금 주석 한 줄)
- 새로: `api/providers/quota.py`
- 새로: `tests/routes/__init__.py`, `tests/routes/test_p1_base.py`, `tests/routes/test_p2_tmap.py`, `tests/routes/test_p5_kakao.py`, `tests/routes/test_p8_quota.py`
- 읽기만: `tests/routes/fixtures/*`(합성), `api/services/mock_routes.py`(`_candidate` 칸 이름 확인), `api/providers/tourapi.py`(키 숨김·클라이언트 주입 방식 참고)

**체크리스트**
- [ ] P1 내부 형식·오류 종류
- [ ] P2·P3·P4 TMAP 호출·오류 판정·변환(좌표 뒤집기·막차)
- [ ] P5·P6·P7 카카오 대중교통·오류·변환·장소 검색
- [ ] P8 한도 계산기(파일 잠금·날짜·동시성)
- [ ] 시험 전부 통과
- [ ] commit `feat(routes): TMAP/Kakao adapters, internal route format, daily quota guard`

## 2단계 — 실제 경로 서비스·A04/A05/A25 연결
**만들 파일**
- 새로: `api/services/real_routes.py`
- 고침: `api/routers/routes/routes.py`(`ROUTE_PROVIDER`로 mock/real 고르기만), `api/main.py`(`_serves_real_data`에 `ROUTE_PROVIDER=real`일 때 `/api/v1/routes/(return|visit)` 주소 추가만)
- 새로: `tests/routes/test_p9_real_routes.py`

**체크리스트**
- [ ] P9 켜기·응답 모양 유지
- [ ] P10 순서(장소 검색·HMAC 키·캐시·병합·1차→2차·오류 코드)
- [ ] P11 동기 3초/202·카카오 동기 전용·TMAP 60초 만료
- [ ] P12 시험 전부 + 기존 시험 그대로
- [ ] (Claude) 3-실행
- [ ] commit `feat(routes): real return/visit routes — TMAP primary, Kakao sync-only fallback, cache, singleflight, HMAC route key`

## 메모
- (11/23) TMAP 무료 하루 10건(오류도 셈)·유료 전환은 11/26 결정 대기(`TMAP_PAID_PLAN`) → 한도는 환경변수.
- (11/23) 한도·캐시·병합·결과 보관은 **메모리/파일 임시** — 유빈 님 Redis·DB 연결 뒤 `quota:{provider}`·`route:cache:{route_key}`·`route_results`로 옮김. 프로세스 여러 개로 띄우면 맞지 않음(지금 노트북 시연은 1개).
- (11/23) 카카오 도보 보완은 이번에 안 함(호출 아끼기).
