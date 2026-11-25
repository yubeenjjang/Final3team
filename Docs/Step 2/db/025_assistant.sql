-- 002·006의 작업 행을 DB 큐로 사용한다. 질문은 기존 message에만 저장한다.
ALTER TABLE public.assistant_runs
    ADD COLUMN request_body_hash TEXT,
    ADD COLUMN anonymous_session_hash TEXT,
    ADD COLUMN execution_context JSONB,
    ADD COLUMN next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN used_tools JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN evidence JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN error_retryable BOOLEAN NOT NULL DEFAULT true;

CREATE INDEX idx_assistant_runs_due ON public.assistant_runs (next_attempt_at, run_id)
    WHERE run_kind = 'chat' AND run_status IN ('queued', 'retrying') AND purged_at IS NULL;
CREATE INDEX idx_assistant_runs_retention ON public.assistant_runs (queued_at, run_id)
    WHERE purged_at IS NULL;

-- 기존 A80과 30일 정리 양쪽에서 추가 대화 메타데이터도 함께 없앤다.
CREATE FUNCTION public.assistant_clear_purged_run() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    NEW.execution_context := NULL;
    NEW.request_body_hash := NULL;
    NEW.anonymous_session_hash := NULL;
    NEW.used_tools := '[]';
    NEW.evidence := '[]';
    NEW.route_request_id := NULL;
    IF NEW.run_status IN ('queued', 'running', 'retrying') THEN
        NEW.run_status := 'failed';
        NEW.error_code := 'AI_AGENT_FAILED';
        NEW.ended_at := clock_timestamp();
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER assistant_clear_purged_run
BEFORE UPDATE OF purged_at ON public.assistant_runs
FOR EACH ROW WHEN (NEW.purged_at IS NOT NULL)
EXECUTE FUNCTION public.assistant_clear_purged_run();

-- 진행 신호만 발행한다. API는 작업 조회 권한 확인 후 DB에서 답변을 읽는다.
CREATE FUNCTION public.assistant_notify_terminal() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    PERFORM pg_notify('assistant_' || NEW.run_id, 'terminal');
    RETURN NEW;
END;
$$;
CREATE TRIGGER assistant_notify_terminal
AFTER UPDATE ON public.assistant_runs
FOR EACH ROW WHEN (OLD.run_status IS DISTINCT FROM NEW.run_status AND NEW.run_status IN ('succeeded', 'failed'))
EXECUTE FUNCTION public.assistant_notify_terminal();
