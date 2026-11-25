# Codex 공통 규칙 — 프론트 (3단계부터, 11/22 사용자 결정으로 agy → Codex 전환)

- 작업 폴더: 저장소 `frontend/`. 명령은 `frontend/`에서.
- 읽을 문서: `frontend/Doc/SPEC.md`(해당 요구), `IMP-PLAN.md`(해당 단계), `DESIGN.md`, `openapi.json`. 시안 이미지는 실행 때 함께 첨부됨(추가로 필요하면 `/home/koh15/work/LastPj/놀다가_설계/figma_1120/png/`를 읽기만). API 설계문서 전체는 읽지 않는다.
- **먼저 앞 단계 코드를 읽고 그 방식을 따른다:** `src/lib/api/client.ts`·`auth.ts`, `src/lib/kakao.ts`, `src/components/`(AppShell·KakaoMap·MockBadge), `src/features/festivals/`(api.ts 패턴, `liveInfoUtils.ts`의 한국 시간 함수, 이미지 실패 처리).
- **IMP-PLAN의 '만들 파일' 밖은 만들거나 고치지 않는다.** `backend/`, `infra/`, `Docs/`, 저장소 루트는 건드리지 않는다.
- 새 npm 패키지를 넣지 않는다(이미 설치된 것만). 네트워크가 없다.
- 카카오 키·토큰을 코드·문서·로그에 쓰지 않는다. `.env.local`은 건드리지 않는다.
- 시안의 예시 데이터(축제 이름·숫자·노선 번호)를 코드에 넣지 않는다. 데이터는 API에서만.
- 화면 글은 한국어, 이름은 영어, TypeScript strict. 색은 토큰만(시험 `F2 no raw colors`).
- 시각은 `Asia/Seoul` 공통 함수로만 표시.
- 끝내는 조건: 해당 단계 체크리스트가 되고 `npm run typecheck && npm run lint && npm test && npm run build`가 통과하면 체크박스를 `[x]`로 바꾸고 멈춘다. 같은 실패가 3번 반복되면 멈추고 보고한다.
- git: commit·push하지 않는다(`.git`이 읽기 전용, Claude가 확인 뒤 commit).
- 마지막 답변: 만든 파일 / 확인 명령 결과 숫자 / SPEC과 다르게 한 곳과 이유.
