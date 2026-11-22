# Codex 작업 지시서 — 4단계 수정 1 (검토 반영, 아주 작은 수정)

규칙은 `Doc/codex/_COMMON.md`. 아래 2가지만 고친다. 다른 파일·다른 줄은 고치지 않는다.

1. `api/services/mock_auth.py`(또는 refresh 유효기간을 정한 곳): Refresh 토큰 유효기간을 **14일**로 한다(API 설계문서 9-1 `REFRESH_TTL_DAYS` = 14일, 지금 7일). 시험 `tests/api/test_step3_auth.py`에 `refresh_expires_at`이 로그인 시각에서 약 14일 뒤(13.9~14.1일)인지 확인하는 시험 `test_R16_refresh_ttl_14_days`를 추가한다.
2. `api/mocks/store.py`: `RouteRecord.access_token` 필드를 `AssistantRun.access_token`처럼 `field(repr=False)`로 바꿔 디버그 출력에 토큰이 안 찍히게 한다.
3. `Doc/IMP-PLAN.md` '메모'에 한 줄 추가: "R15: 형식은 맞지만 축제가 없거나 좌표가 없어 경로를 못 만들면 작업을 `failed`로 확정(조회는 200)."
4. 전체 시험 통과 확인 후 멈춘다(commit하지 않음).
