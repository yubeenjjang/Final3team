# W90 주변 시설 API 구현 기록

- 기준 브랜치: `yubeen`, 2026-11-25
- A26 `/festivals/{id}/transit`는 기존 구현을 확인했다. 서울 지하철·서울 버스·서울 밖 TAGO 조회와 지역 미지원 구분이 `backend/api/services/real_festival_info.py`에 있다.
- A08 `/festivals/{id}/facilities`를 추가했다. 분류·반경·분류별 건수 입력 검증, 축제 좌표 확인, DB 시설의 실제 거리 필터·정렬, 분류별 `ok`·`unverified`·`unsupported`·`unavailable`을 제공한다.
- `FACILITIES_PROVIDER=real`에서 `facilities` DB의 8개 정적 유형을 조회한다. `locker`·`pharmacy`는 설계대로 미지원이다. `food`·`attraction`은 카카오 로컬을 요청 때만 조회하고 결과를 DB·캐시에 저장하지 않는다. 키 부재·공급원 오류는 해당 분류를 `unavailable`로 표시한다.
- 기본 `mock` 모드는 시설 위치를 꾸며 내지 않고 `unverified`로 응답한다. 정적 시설이 DB에 없으면 `unverified`이며 전국 수집 완료로 간주하지 않는다.

## 검증 및 남은 조건

- Python 구문 검사와 `git diff --check` 통과.
- 로컬 Windows Python에 `httpx2`가 없어 pytest 수집 실패. WSL 시스템 Python에는 `pytest`가 없어 실행 불가. API 통합 시험은 의존성이 설치된 Linux/Docker 환경에서 재실행 필요.
- 현재 저장소에서 `facilities` 적재 작업은 발견되지 않았다. 실제 정적 시설을 제공하려면 공급원 원본 좌표·출처를 검증해 적재하고, 서울 정류장 ID와 A26 연결을 실DB에서 확인해야 한다.
- 카카오 장소 중계는 실키 호출·쿼터 동작을 확인하지 못했다. 실제 키와 분리된 시험 환경에서 응답·한도·오류를 확인해야 한다.

따라서 W90은 **API 코드 부분 완료, 실데이터·통합 시험 대기**다.
