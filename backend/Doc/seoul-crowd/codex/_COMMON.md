# Codex 공통 규칙 — W89 서울 축제 주변 지역 혼잡

- 저장소는 `~/work/Final3team`, 브랜치는 `ohyun`입니다.
- [SPEC](../SPEC.md)과 [IMP-PLAN](../IMP-PLAN.md), 구현에 닿는 A10·한도·테스트 코드부터 읽습니다. 기존 A10 공개 키와 모의 동작을 유지합니다.
- 키는 서버 환경변수 `SEOUL_OPEN_API_KEY`에서만 가져옵니다. 실호출은 별도 적용 단계의 일입니다. 구현 시험에는 가짜 HTTP와 시각을 사용합니다. URL을 남기는 자리에서는 키를 `***`로 가립니다.
- [고정 파일](../../../tests/crowd/fixtures/)에는 실제 공급원 예시에서 A10 사용 필드를 남겼습니다. 관측값과 대체값의 차이를 유지합니다.
- [공식 구역 경계](../../../api/data/seoul_areas.json)를 사용합니다. [연결 초안](../../../api/data/seoul_crowd_mapping.json)은 1단계 참고 자료입니다.
- 실제 모드 문구는 ‘주변 지역 혼잡’으로 시작하고 집계 장소, 기준 시각, 출처를 담습니다. 도구·화면과 의견이 필요한 점은 구현 완료 보고에 적습니다.
- 저장소 루트 공통 시험은 `python -m pytest backend/tests -q`로 실행합니다. uv 환경에서는 `uv run --offline --with-requirements backend/api/requirements.txt python -m pytest backend/tests -q`를 사용합니다. 실행 결과와 명세와의 차이를 보고합니다. 커밋과 푸시는 다음 사용자 요청에 따릅니다.
