-- 006 되돌리기
DROP TABLE IF EXISTS notice_events;
ALTER TABLE assistant_runs DROP CONSTRAINT IF EXISTS assistant_runs_result_purge,
  DROP CONSTRAINT IF EXISTS assistant_runs_result_kind, DROP COLUMN IF EXISTS result, DROP COLUMN IF EXISTS run_kind;
