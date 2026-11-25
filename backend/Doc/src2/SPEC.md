# src2 서울시 문화행사 축제 보강 명세

- 공급원은 서울 열린데이터광장 OA-15486 `culturalEventInfo`다. 매일 06:00 KST 회차에서 TourAPI 작업 뒤 실행한다. `SEOUL_CULTURE_ENABLED=true`일 때 `SEOUL_OPEN_API_KEY`로 페이지를 읽는다.
- `CODENAME`의 `축제`, `축제-문화/예술`, `축제-전통/역사`, `축제-자연/경관`, `축제-시민화합`, `축제-기타`를 통과시킨다. `HMPG_ADDR`의 `cultcode`가 원본 키다. `STRTDATE`·`END_DATE`를 검증하고 누락·잘못된 날짜·역전은 A23에서 `DATE_INVALID`로 집계한다.
- 서울 소재 TourAPI EV01 축제 중 NFKC, 대소문자 통일, 비문자·비숫자 제거로 제목이 같고 기간이 겹치는 행을 찾는다. 위경도 두 쌍이 모두 유효하고 거리가 500m 이내인 후보가 한 건이며 좌표 불명 후보가 없을 때 병합한다.
- 확정 병합은 `festival_sources`에 `seoul_culture` 원본 링크를 저장한다. `ORG_LINK`와 `USE_FEE`(또는 명시적 무료)를 공식 홈페이지·요금의 빈 칸에만 넣고 필드별 이력을 남긴다. A55·A56 관리자 이력이 있는 칸은 보호하며 빈 칸의 충돌 제안은 A24로 보낸다. TourAPI가 빈 값을 다시 받으면 마지막 서울시 보강값을 보존한다.
- 다중 후보·거리 초과·좌표 불명 건은 A24 `duplicate`, 기간과 제목이 일치하는 TourAPI 후보가 없는 건은 `class_unverified`로 검토한다. 대기열의 축제 FK는 게시 시각과 EV01 분류가 없는 보류 행을 가리킨다. 같은 원본 재수집은 기존 연결과 운영자 결정에 따라 유지한다.
- `MAIN_IMG`는 `festival_sources.source_image_url`에 서비스 역할용 근거로 저장한다. A02·A03은 현재 이미지 저작권 규칙과 `source`·`source_ref` 형식을 그대로 사용한다. 서울시 보강 축제의 주 출처는 TourAPI이고 원본 번호는 TourAPI contentid다.
- 수집 회차, 출처 갱신과 검토 이력은 PostgreSQL에 저장한다. 응답 본문·키는 이력과 로그에서 제외한다. 페이지 오류는 해당 목록을 저장하지 않고 실패 이력을 남긴다.
