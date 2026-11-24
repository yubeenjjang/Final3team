BEGIN;
\if :applied
INSERT INTO public.users (user_id, email, password_hash) VALUES
    ('d0220000-0000-0000-0000-000000000001', 'assistant-022-a@example.test', 'fixture'),
    ('d0220000-0000-0000-0000-000000000002', 'assistant-022-b@example.test', 'fixture');
INSERT INTO public.assistant_runs (
    run_id, request_id, conversation_id, user_id, message, execution_context,
    request_body_hash, anonymous_session_hash, used_tools, evidence, run_status
) VALUES (
    'run_T22001', 'assistant-022-1', 'cv_T220001', 'd0220000-0000-0000-0000-000000000001', 'fixture',
    '{"festival_id":"fst_000001"}', 'body-hash', 'session-hash', '[{"tool":"get_festival"}]',
    '[{"ref":"fst_000001"}]', 'queued'
);
INSERT INTO public.assistant_runs (run_id, request_id, conversation_id, run_token_hash, message)
VALUES ('run_T22002', 'assistant-022-2', 'cv_T220002', 'token-hash', 'fixture');

SET LOCAL ROLE noldaga_app;
SELECT set_config('app.user_id', 'd0220000-0000-0000-0000-000000000001', true);
DO $$
BEGIN
    IF (SELECT count(*) FROM public.assistant_runs WHERE run_id IN ('run_T22001', 'run_T22002')) <> 1 THEN
        RAISE EXCEPTION 'T022a FAIL: owner visibility';
    END IF;
    IF has_table_privilege('public.assistant_runs', 'UPDATE') THEN
        RAISE EXCEPTION 'T022a FAIL: app role can mutate assistant runs';
    END IF;
END;
$$;
SELECT set_config('app.user_id', 'd0220000-0000-0000-0000-000000000002', true);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.assistant_runs WHERE run_id IN ('run_T22001', 'run_T22002')) THEN
        RAISE EXCEPTION 'T022a FAIL: foreign row visibility';
    END IF;
    RAISE NOTICE 'T022a PASS: 본인 행만 조회, 앱 역할 상태 변경 불가';
END;
$$;
RESET ROLE;

SET LOCAL ROLE noldaga_service;
UPDATE public.assistant_runs SET message = NULL, answer = NULL, result = NULL, purged_at = now()
WHERE run_id = 'run_T22001';
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.assistant_runs WHERE run_id = 'run_T22001' AND message IS NULL
          AND purged_at IS NOT NULL AND error_code = 'AI_AGENT_FAILED' AND run_status = 'failed'
          AND execution_context IS NULL AND request_body_hash IS NULL AND anonymous_session_hash IS NULL
          AND used_tools = '[]' AND evidence = '[]' AND ended_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'T022b FAIL: purge left assistant content or active job';
    END IF;
    RAISE NOTICE 'T022b PASS: 탈퇴·보존 정리 시 문맥 삭제와 미완료 작업 종료';
END;
$$;
\else
DO $$
BEGIN
    IF to_regclass('public.idx_assistant_runs_due') IS NOT NULL
       OR to_regprocedure('public.assistant_notify_terminal()') IS NOT NULL
       OR EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'assistant_runs' AND column_name = 'execution_context'
       ) THEN
        RAISE EXCEPTION 'T022c FAIL: rollback left new objects';
    END IF;
    IF to_regclass('public.assistant_runs') IS NULL THEN
        RAISE EXCEPTION 'T022c FAIL: rollback lost existing table';
    END IF;
    RAISE NOTICE 'T022c PASS: 002·006을 유지하며 022 기능을 되돌림';
END;
$$;
\endif
ROLLBACK;
