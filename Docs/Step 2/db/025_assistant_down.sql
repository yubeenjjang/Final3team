DROP TRIGGER assistant_notify_terminal ON public.assistant_runs;
DROP FUNCTION public.assistant_notify_terminal();
DROP TRIGGER assistant_clear_purged_run ON public.assistant_runs;
DROP FUNCTION public.assistant_clear_purged_run();
DROP INDEX public.idx_assistant_runs_retention;
DROP INDEX public.idx_assistant_runs_due;
ALTER TABLE public.assistant_runs
    DROP COLUMN error_retryable,
    DROP COLUMN evidence,
    DROP COLUMN used_tools,
    DROP COLUMN next_attempt_at,
    DROP COLUMN execution_context,
    DROP COLUMN anonymous_session_hash,
    DROP COLUMN request_body_hash;
