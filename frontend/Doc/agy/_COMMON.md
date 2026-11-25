# agy 공통 규칙 (모든 단계)

- 작업 폴더: 저장소 `frontend/`. 명령은 `frontend/`에서.
- 읽을 문서: `frontend/Doc/SPEC.md`(해당 요구), `IMP-PLAN.md`(해당 단계), `DESIGN.md`, `openapi.json`. 시안 PNG는 `/home/koh15/work/LastPj/놀다가_설계/figma_1120/png/`(읽기만). API 설계문서 전체는 읽지 않는다.
- **IMP-PLAN의 '만들 파일' 밖은 만들거나 고치지 않는다.** `backend/`, `infra/`, `Docs/`, 저장소 루트 파일은 건드리지 않는다.
- 패키지는 `npm install`로 `frontend/` 안에만 설치(전역 설치 금지). 버전은 정확히 고정.
- 카카오 키·토큰을 코드·문서·로그에 쓰지 않는다. `.env.local`은 만들지 않는다(Claude가 넣음).
- 시안의 예시 데이터(축제 이름·숫자)를 코드에 넣지 않는다. 데이터는 API에서만.
- 화면 글은 한국어, 이름은 영어, TypeScript strict.
- 끝내는 조건: 해당 단계 체크리스트가 모두 되고 공통 확인 명령(`npm run typecheck && npm run lint && npm test && npm run build`)이 통과하면 체크박스를 `[x]`로 바꾸고 멈춘다. 같은 실패가 3번 반복되면 멈추고 보고한다.
- git: commit·push하지 않는다(Claude가 확인 뒤 commit).
- 마지막 답변: 만든 파일 / 확인 명령 결과 / SPEC과 다르게 한 곳과 이유.
