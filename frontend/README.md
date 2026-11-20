# Frontend

놀다가의 사용자 화면과 관리자 화면을 만드는 폴더입니다.

| 폴더 | 역할 |
| --- | --- |
| `public/` | 로고, 이미지, 아이콘 등 정적 파일 |
| `src/app/` | 화면 주소와 각 화면의 진입점 |
| `src/features/festivals/` | 축제 지도·검색·상세·현장 정보·추천 |
| `src/features/routes/` | 축제 가는 길, 귀가 경로, 조회 상태 |
| `src/features/accounts/` | 회원가입·로그인, 프로필, 관심 축제 |
| `src/features/community/` | 동행, 친구, 사용자 간 채팅, 앱 내 알림 |
| `src/features/assistant/` | AI 챗봇과 방문 코스 화면 |
| `src/features/admin/` | 축제 데이터 관리와 장애·복구 시연 화면 |
| `src/components/` | 여러 기능에서 함께 쓰는 화면 요소 |
| `src/lib/` | 공통 API 요청과 실시간 연결 등 공통 도구 |

`app/`은 화면의 위치를 정하고, 실제 화면 기능은 `features/`에 작성합니다.
프론트 코드 언어와 실행 명령은 팀에서 정한 뒤 이 문서에 추가합니다.
