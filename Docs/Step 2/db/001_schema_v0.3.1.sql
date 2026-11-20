-- 놀다가 DB 스키마 v0.3.1 DDL (DB_스키마_설계서.md 부록과 같은 내용, v0.3.2에서 DDL 변경 없음)
-- 운영 대상: AWS 위 Docker PostgreSQL 17 + pgvector (이미지 pgvector/pgvector:pg17) — D-037
-- 실행 확인: 같은 이미지를 로컬 Docker로 띄워 2026-11-19 실행·시험 (AWS 서버에서는 아직 실행 안 함).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ===== 접속 역할 (비밀번호는 서버 환경변수로 따로 설정, 저장소에 두지 않음) =====
CREATE ROLE noldaga_app LOGIN;                 -- API 서버: RLS 적용 대상
CREATE ROLE noldaga_service LOGIN BYPASSRLS;   -- 수집·감지·정책 코드: RLS 우회, 서버 안에서만
-- 요청한 사용자 ID: API 서버가 트랜잭션마다 SET LOCAL app.user_id = '<JWT의 sub>' 로 넣음
CREATE FUNCTION app_current_user() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$;

-- ===== 사용자 (자체 인증, Supabase Auth 대신) =====
CREATE TABLE users (
  user_id         UUID PRIMARY KEY,
  email           TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','deleted')),
  last_login_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
  token_id        TEXT PRIMARY KEY CHECK (token_id ~ '^rt_[0-9A-Za-z]{6,26}$'),
  user_id         UUID NOT NULL REFERENCES users(user_id),
  token_hash      TEXT NOT NULL UNIQUE,
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id);

CREATE TABLE profiles (
  user_id         UUID PRIMARY KEY REFERENCES users(user_id),
  role            TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','operator','admin')),
  display_name    TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== 외부 데이터 공급원 =====
CREATE TABLE data_sources (
  source_id       TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  provider_org    TEXT,
  scope           TEXT NOT NULL CHECK (scope IN ('national','seoul_only','region_specific')),
  region_codes    TEXT[] NOT NULL DEFAULT '{}',
  enabled_region_codes TEXT[] NOT NULL DEFAULT '{}',
  is_realtime     BOOLEAN NOT NULL,
  refresh_s       INT,
  key_site        TEXT,
  status          TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','key_issued','verified','disabled')),
  last_success_at TIMESTAMPTZ,
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== 축제 =====
CREATE TABLE festivals (
  festival_id     TEXT PRIMARY KEY CHECK (festival_id ~ '^fst_[0-9A-Za-z]{6,26}$'),
  title           TEXT NOT NULL,
  start_date      DATE,
  end_date        DATE,
  venue_name      TEXT,
  address         TEXT,
  latitude        NUMERIC(9,6) CHECK (latitude BETWEEN 33 AND 39),
  longitude       NUMERIC(9,6) CHECK (longitude BETWEEN 124 AND 132),
  region_code     TEXT NOT NULL,
  category        TEXT,
  summary         TEXT,
  admission_fee_text TEXT,
  description     TEXT,
  image_url       TEXT,
  official_url    TEXT,
  organizer       TEXT,
  event_status    TEXT NOT NULL DEFAULT 'upcoming' CHECK (event_status IN ('upcoming','ongoing','ended','cancelled','needs_review')),
  source_updated_at TIMESTAMPTZ,
  collected_at    TIMESTAMPTZ,
  last_synced_at  TIMESTAMPTZ,
  review_status   TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','approved','hidden')),
  published_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE INDEX idx_festivals_search ON festivals (region_code, start_date, end_date) WHERE published_at IS NOT NULL;
CREATE INDEX idx_festivals_status ON festivals (event_status) WHERE published_at IS NOT NULL;
CREATE INDEX idx_festivals_title_trgm ON festivals USING gin (title gin_trgm_ops);
CREATE INDEX idx_festivals_venue_trgm ON festivals USING gin (venue_name gin_trgm_ops);
CREATE INDEX idx_festivals_geo ON festivals (latitude, longitude);

CREATE TABLE ingestion_jobs (
  job_id          TEXT PRIMARY KEY,
  source_id       TEXT NOT NULL REFERENCES data_sources(source_id),
  started_at      TIMESTAMPTZ NOT NULL,
  ended_at        TIMESTAMPTZ,
  status          TEXT NOT NULL CHECK (status IN ('running','success','partial','failed')),
  scanned         INT NOT NULL DEFAULT 0,
  inserted        INT NOT NULL DEFAULT 0,
  updated         INT NOT NULL DEFAULT 0,
  rejected        INT NOT NULL DEFAULT 0,
  error           JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE festival_sources (
  id              BIGSERIAL PRIMARY KEY,
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  source_id       TEXT NOT NULL REFERENCES data_sources(source_id),
  source_item_id  TEXT NOT NULL,
  source_url      TEXT,
  raw_checksum    TEXT NOT NULL,
  fetched_at      TIMESTAMPTZ NOT NULL,
  last_job_id     TEXT REFERENCES ingestion_jobs(job_id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_item_id)
);

CREATE TABLE festival_change_history (
  change_id       BIGSERIAL PRIMARY KEY,
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  field           TEXT NOT NULL,
  before_value    JSONB,
  after_value     JSONB,
  source_id       TEXT,
  actor           TEXT NOT NULL CHECK (actor IN ('ingestion','admin')),
  changed_at      TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_change_history ON festival_change_history (festival_id, changed_at DESC);

CREATE TABLE festival_review_queue (
  queue_id        BIGSERIAL PRIMARY KEY,
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  reason          TEXT NOT NULL CHECK (reason IN ('duplicate','conflict','missing_location','date_unclear')),
  proposed_value  JSONB,
  approval_status TEXT NOT NULL DEFAULT 'pending' CHECK (approval_status IN ('pending','approved','rejected')),
  reviewer        UUID REFERENCES profiles(user_id),
  reviewed_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE favorites (
  user_id         UUID NOT NULL REFERENCES profiles(user_id),
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, festival_id)
);

CREATE TABLE festival_reviews (
  review_id       TEXT PRIMARY KEY CHECK (review_id ~ '^rv_[0-9A-Za-z]{6,26}$'),
  user_id         UUID NOT NULL REFERENCES profiles(user_id),
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
  body            TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 1000),
  status          TEXT NOT NULL DEFAULT 'visible' CHECK (status IN ('visible','hidden')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ
);

CREATE TABLE official_notices (
  notice_id       TEXT PRIMARY KEY,
  festival_id     TEXT REFERENCES festivals(festival_id),
  type            TEXT NOT NULL CHECK (type IN ('operation','traffic_control','no_stop','bus_detour','road_closure')),
  title           TEXT NOT NULL,
  content         TEXT,
  source_id       TEXT NOT NULL REFERENCES data_sources(source_id),
  source_url      TEXT,
  published_at    TIMESTAMPTZ,
  effective_from  TIMESTAMPTZ,
  effective_to    TIMESTAMPTZ,
  geometry        JSONB,
  control_version TEXT,
  approval_status TEXT NOT NULL DEFAULT 'pending' CHECK (approval_status IN ('pending','approved','rejected')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE facilities (
  facility_id     TEXT PRIMARY KEY,
  category        TEXT NOT NULL CHECK (category IN ('toilet','parking','locker','hospital','emergency','pharmacy',
                    'subway_station','bus_stop','bike_zone','taxi_stand','food','attraction')),
  name            TEXT NOT NULL,
  lat             NUMERIC(9,6) NOT NULL CHECK (lat BETWEEN 33 AND 39),
  lng             NUMERIC(9,6) NOT NULL CHECK (lng BETWEEN 124 AND 132),
  address         TEXT,
  region_code     TEXT,
  source_id       TEXT NOT NULL REFERENCES data_sources(source_id),
  source_item_id  TEXT NOT NULL,
  source_url      TEXT,
  ref_code        TEXT,
  festival_id     TEXT REFERENCES festivals(festival_id),
  collected_at    TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_item_id)
);
CREATE INDEX idx_facilities_festival ON facilities (festival_id, category);
CREATE INDEX idx_facilities_geo ON facilities (category, lat, lng);

CREATE TABLE realtime_snapshots (
  id              BIGSERIAL PRIMARY KEY,
  source_id       TEXT NOT NULL REFERENCES data_sources(source_id),
  data_type       TEXT NOT NULL CHECK (data_type IN ('crowd','subway_arrival','bus_arrival','bus_crowding',
                    'parking_live','traffic_incident','weather','visit_forecast','region_demand')),
  target_type     TEXT NOT NULL,
  target_id       TEXT NOT NULL,
  region_code     TEXT,
  observed_at     TIMESTAMPTZ,
  received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_until     TIMESTAMPTZ,
  payload         JSONB NOT NULL,
  payload_hash    TEXT NOT NULL,
  source_result_code TEXT,
  sample_kind     TEXT NOT NULL CHECK (sample_kind IN ('original','cache','mock')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_snapshots_latest ON realtime_snapshots (source_id, target_id, observed_at DESC);

CREATE TABLE population_areas (
  area_code       TEXT PRIMARY KEY,
  area_name       TEXT NOT NULL,
  data_source     TEXT NOT NULL DEFAULT 'OA-21778',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE festival_population_links (
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  area_code       TEXT NOT NULL REFERENCES population_areas(area_code),
  relation_type   TEXT NOT NULL CHECK (relation_type IN ('contains','adjacent','route_hub')),
  validated_by    UUID REFERENCES profiles(user_id),
  validated_at    TIMESTAMPTZ,
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (festival_id, area_code)
);

-- ===== RAG (pgvector) =====
CREATE TABLE rag_documents (
  document_id     UUID PRIMARY KEY,
  festival_id     TEXT REFERENCES festivals(festival_id),
  title           TEXT NOT NULL,
  category        TEXT NOT NULL CHECK (category IN ('operation_notice','safety','transport_guide','faq','tip')),
  source_url      TEXT NOT NULL,
  publisher       TEXT,
  published_at    TIMESTAMPTZ,
  effective_from  TIMESTAMPTZ,
  effective_to    TIMESTAMPTZ,
  collected_at    TIMESTAMPTZ NOT NULL,
  approval_status TEXT NOT NULL DEFAULT 'pending' CHECK (approval_status IN ('pending','approved','rejected')),
  approved_by     UUID REFERENCES profiles(user_id),
  approved_at     TIMESTAMPTZ,
  checksum        TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_url, checksum)
);
CREATE INDEX idx_rag_documents_festival ON rag_documents (festival_id, approval_status);

CREATE TABLE rag_chunks (
  chunk_id        UUID PRIMARY KEY,
  document_id     UUID NOT NULL REFERENCES rag_documents(document_id) ON DELETE CASCADE,
  chunk_index     INT NOT NULL,
  content         TEXT NOT NULL,
  embedding       VECTOR(1024) NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_version TEXT NOT NULL,
  metadata        JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, chunk_index)
);
CREATE INDEX idx_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops);

-- ===== [1차] 부하 시험·사건·경로 =====
CREATE TABLE load_simulations (
  simulation_id   TEXT PRIMARY KEY CHECK (simulation_id ~ '^sim_[0-9A-Za-z]{6,26}$'),
  idempotency_key TEXT NOT NULL UNIQUE,
  comparison_arm  TEXT NOT NULL CHECK (comparison_arm IN ('B0','B1','A1')),
  scenario        TEXT NOT NULL CHECK (scenario IN ('duplicate_keys','unique_keys','mixed')),
  concurrency     INT  NOT NULL CHECK (concurrency > 0),
  offered_requests INT,
  offered_rps     NUMERIC,
  duration_s      INT  NOT NULL CHECK (duration_s > 0),
  unique_route_keys INT NOT NULL CHECK (unique_route_keys > 0),
  fault           JSONB,
  seed            INT,
  cache_state     TEXT NOT NULL CHECK (cache_state IN ('cold','warm')),
  repeat_group    TEXT,
  run_index       INT  NOT NULL DEFAULT 1 CHECK (run_index >= 1),
  upstream        TEXT NOT NULL DEFAULT 'mock_adapter' CHECK (upstream = 'mock_adapter'),
  code_version    TEXT NOT NULL,
  result_ref      TEXT,
  report_ref      TEXT,
  created_by      UUID REFERENCES profiles(user_id),
  status          TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','stopped','finished','failed')),
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at        TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE incident_logs (
  incident_id     TEXT PRIMARY KEY CHECK (incident_id ~ '^inc_[0-9A-Za-z]{6,26}$'),
  failure_domain  TEXT NOT NULL CHECK (failure_domain IN ('internal_route','route_upstream','agent','crowd_upstream','ingestion')),
  detected_at     TIMESTAMPTZ NOT NULL,
  detection_rule  TEXT NOT NULL,
  simulation_id   TEXT REFERENCES load_simulations(simulation_id),
  injected_test   BOOLEAN NOT NULL,
  http_status     INT,
  upstream_result_code TEXT,
  upstream_result_message TEXT,
  before_metrics  JSONB NOT NULL,
  status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','diagnosing','recovering','validating','closed')),
  closed_at       TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_incident_status ON incident_logs (status, detected_at DESC);
CREATE INDEX idx_incident_sim ON incident_logs (simulation_id);
CREATE INDEX idx_incident_domain ON incident_logs (failure_domain);

CREATE TABLE incident_events (
  event_id        BIGSERIAL PRIMARY KEY,
  incident_id     TEXT NOT NULL REFERENCES incident_logs(incident_id),
  from_status     TEXT CHECK (from_status IN ('open','diagnosing','recovering','validating','closed')),
  to_status       TEXT NOT NULL CHECK (to_status IN ('open','diagnosing','recovering','validating','closed')),
  actor           TEXT NOT NULL CHECK (actor IN ('detector','service','rule_policy','recovery_agent','operator')),
  ref_id          TEXT,
  note            TEXT,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_incident_events ON incident_events (incident_id, occurred_at);

CREATE TABLE route_requests (
  route_request_id TEXT PRIMARY KEY CHECK (route_request_id ~ '^rr_[0-9A-Za-z]{6,26}$'),
  request_id      TEXT NOT NULL UNIQUE,
  run_id          TEXT CHECK (run_id ~ '^run_[0-9A-Za-z]{6,26}$'),
  direction       TEXT NOT NULL DEFAULT 'return' CHECK (direction IN ('return','visit')),
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  festival_lat    NUMERIC(9,6) NOT NULL,
  festival_lng    NUMERIC(9,6) NOT NULL,
  user_place_hash TEXT NOT NULL,
  user_place_label TEXT,
  travel_mode     TEXT NOT NULL CHECK (travel_mode IN ('transit','walk','car','taxi')),
  route_preference TEXT NOT NULL DEFAULT 'fastest' CHECK (route_preference IN ('fastest','less_crowded','accessible','min_walk','fewest_transfers')),
  constraints     JSONB NOT NULL DEFAULT '{}',
  route_key       TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('created','queued','processing','ready','unavailable','rejected','timed_out')),
  error_code      TEXT,
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  shared_from     TEXT REFERENCES route_requests(route_request_id),
  simulation_id   TEXT REFERENCES load_simulations(simulation_id),
  incident_id     TEXT REFERENCES incident_logs(incident_id),
  is_mock         BOOLEAN NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_route_requests_festival ON route_requests (festival_id, submitted_at DESC);
CREATE INDEX idx_route_requests_sim ON route_requests (simulation_id);
CREATE INDEX idx_route_requests_incident ON route_requests (incident_id);

CREATE TABLE route_cache_entries (
  cache_key       TEXT PRIMARY KEY,
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  route_hash      TEXT NOT NULL,
  provider        TEXT NOT NULL CHECK (provider IN ('tmap','mock_adapter')),   -- 카카오맵 응답은 캐시 안 함(D-038)
  control_version TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  verified_at     TIMESTAMPTZ,
  valid_until     TIMESTAMPTZ NOT NULL,
  hit_count       INT NOT NULL DEFAULT 0
);
CREATE INDEX idx_route_cache_festival ON route_cache_entries (festival_id, valid_until);

CREATE TABLE route_results (
  route_request_id TEXT PRIMARY KEY REFERENCES route_requests(route_request_id),
  provider        TEXT NOT NULL CHECK (provider IN ('tmap','kakao','mock_adapter')),
  provider_tier   TEXT NOT NULL CHECK (provider_tier IN ('primary','secondary','mock')),
  provider_ref    TEXT,
  candidates      JSONB,                       -- 카카오맵(2차) 응답은 저장 안 함 → NULL
  evidence        JSONB NOT NULL DEFAULT '{}',
  score_version   TEXT,
  route_hash      TEXT NOT NULL,
  source_type     TEXT NOT NULL CHECK (source_type IN ('fresh','cache','shared','alternate')),
  cache_key       TEXT REFERENCES route_cache_entries(cache_key),
  validity_check  JSONB,
  queried_at      TIMESTAMPTZ NOT NULL,
  validated_at    TIMESTAMPTZ,
  validation_status TEXT NOT NULL CHECK (validation_status IN ('verified_basic','constraint_unverified','control_unverified','failed')),
  is_mock         BOOLEAN NOT NULL,
  purged_at       TIMESTAMPTZ,                 -- 공급원 약관으로 경로 내용을 지운 시각(TMAP: 24시간 안)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (source_type NOT IN ('cache','alternate') OR validity_check IS NOT NULL),
  CHECK (provider <> 'kakao' OR candidates IS NULL),                         -- 카카오는 내용 저장 안 함
  CHECK (provider = 'kakao' OR candidates IS NOT NULL OR purged_at IS NOT NULL), -- 나머지는 내용 필수(지운 뒤만 NULL)
  CHECK (provider <> 'kakao' OR source_type = 'fresh')         -- 카카오 응답은 캐시·공유로 다시 쓰지 않음
);

CREATE TABLE route_query_metrics (
  metric_id       BIGSERIAL PRIMARY KEY,
  simulation_id   TEXT REFERENCES load_simulations(simulation_id),
  phase           TEXT NOT NULL DEFAULT 'live' CHECK (phase IN ('live','baseline','fault','after_action')),
  window_at       TIMESTAMPTZ NOT NULL,
  offered_requests INT NOT NULL, accepted_count INT NOT NULL, valid_completed_count INT NOT NULL,
  rejections INT NOT NULL, timeouts INT NOT NULL, errors INT NOT NULL,
  unique_route_keys INT NOT NULL, backend_execution_count INT NOT NULL,
  shared_request_count INT NOT NULL, cache_hits INT NOT NULL,
  duplicate_ratio NUMERIC(5,4),
  queue_depth_max INT, inflight_max INT,
  p50_ms NUMERIC, p95_ms NUMERIC, upstream_p95_ms NUMERIC, internal_p95_ms NUMERIC,
  is_mock BOOLEAN NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (simulation_id, phase, window_at)
);

-- ===== [1차] 에이전트·진단·복구 =====
CREATE TABLE agent_runs (
  agent_run_id    TEXT PRIMARY KEY CHECK (agent_run_id ~ '^ar_[0-9A-Za-z]{6,26}$'),
  run_id          TEXT CHECK (run_id ~ '^run_[0-9A-Za-z]{6,26}$'),
  incident_id     TEXT REFERENCES incident_logs(incident_id),
  agent_name      TEXT NOT NULL CHECK (agent_name IN ('supervisor','festival','route','diagnosis','recovery')),
  model           TEXT,
  prompt_version  TEXT,
  input_ref       TEXT,
  output_ref      TEXT,
  tool_calls      JSONB NOT NULL DEFAULT '[]',
  tokens_in       INT,
  tokens_out      INT,
  cost_usd        NUMERIC(10,6),
  status          TEXT NOT NULL CHECK (status IN ('ok','timeout','schema_error','failed')),
  started_at      TIMESTAMPTZ NOT NULL,
  ended_at        TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (run_id IS NOT NULL OR incident_id IS NOT NULL)
);
CREATE INDEX idx_agent_runs_incident ON agent_runs (incident_id);

CREATE TABLE incident_diagnostics (
  diagnostic_id   TEXT PRIMARY KEY CHECK (diagnostic_id ~ '^diag_[0-9A-Za-z]{6,26}$'),
  incident_id     TEXT NOT NULL REFERENCES incident_logs(incident_id),
  agent_run_id    TEXT REFERENCES agent_runs(agent_run_id),
  verified_facts  JSONB NOT NULL,
  hypotheses      JSONB NOT NULL,
  unknowns        JSONB NOT NULL,
  affected_features TEXT[],
  evidence_refs   TEXT[] NOT NULL CHECK (cardinality(evidence_refs) >= 1),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_diagnostics_incident ON incident_diagnostics (incident_id);

CREATE TABLE recovery_plans (
  plan_id         TEXT PRIMARY KEY CHECK (plan_id ~ '^rp_[0-9A-Za-z]{6,26}$'),
  incident_id     TEXT NOT NULL REFERENCES incident_logs(incident_id),
  agent_run_id    TEXT REFERENCES agent_runs(agent_run_id),
  idempotency_key TEXT NOT NULL UNIQUE,
  decided_by      TEXT NOT NULL CHECK (decided_by IN ('rule_policy','recovery_agent')),
  decision        TEXT NOT NULL CHECK (decision IN ('select','reject','defer','rollback')),
  action          TEXT CHECK (action IN ('singleflight_enable','bounded_queue_adjust','valid_cache_serve',
                    'fallback_provider_switch','safe_degrade','rollback')),
  rejected_actions JSONB NOT NULL DEFAULT '[]',
  reasons         JSONB NOT NULL,
  evidence_refs   TEXT[] NOT NULL CHECK (cardinality(evidence_refs) >= 1),
  stop_condition  JSONB,
  policy_verdict  TEXT NOT NULL CHECK (policy_verdict IN ('allowed','denied')),
  denied_reason   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (decided_by = 'rule_policy' OR agent_run_id IS NOT NULL),
  CHECK (decision NOT IN ('select','rollback') OR action IS NOT NULL),
  CHECK (decision <> 'select' OR stop_condition IS NOT NULL)
);

CREATE INDEX idx_recovery_plans_incident ON recovery_plans (incident_id);

CREATE TABLE recovery_attempts (
  attempt_id      TEXT PRIMARY KEY CHECK (attempt_id ~ '^ra_[0-9A-Za-z]{6,26}$'),
  plan_id         TEXT NOT NULL REFERENCES recovery_plans(plan_id),
  incident_id     TEXT NOT NULL REFERENCES incident_logs(incident_id),
  action          TEXT NOT NULL CHECK (action IN ('singleflight_enable','bounded_queue_adjust','valid_cache_serve',
                    'fallback_provider_switch','safe_degrade','rollback')),
  action_enabled_at  TIMESTAMPTZ,
  action_disabled_at TIMESTAMPTZ,
  after_metrics   JSONB,
  validation_result TEXT NOT NULL DEFAULT 'pending' CHECK (validation_result IN ('pending','improved','no_effect','worse')),
  stop_reason     TEXT CHECK (stop_reason IN ('improved','no_effect','worse','time_limit','no_allowed_action')),
  rollback_reason TEXT,
  validated_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recovery_attempts_incident ON recovery_attempts (incident_id);

CREATE TABLE incident_outcomes (
  incident_id     TEXT PRIMARY KEY REFERENCES incident_logs(incident_id),
  final_mode      TEXT NOT NULL CHECK (final_mode IN ('normal_recovered','valid_cache','alternate_source','degraded','unresolved')),
  responder_type  TEXT NOT NULL CHECK (responder_type IN ('none','rule','agent')),
  ui_data_mode    TEXT NOT NULL,
  verified_route_count INT NOT NULL,
  offered_requests INT NOT NULL CHECK (offered_requests >= verified_route_count),
  mttr_s          INT,
  evidence_refs   TEXT[] NOT NULL,
  closed_at       TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 감사 기록: 추가만 허용 (UPDATE·DELETE 차단)
CREATE FUNCTION forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% 테이블은 추가만 할 수 있습니다', TG_TABLE_NAME;
END $$;
CREATE TRIGGER trg_incident_events_append_only BEFORE UPDATE OR DELETE ON incident_events
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER trg_incident_diagnostics_append_only BEFORE UPDATE OR DELETE ON incident_diagnostics
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER trg_recovery_plans_append_only BEFORE UPDATE OR DELETE ON recovery_plans
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER trg_recovery_attempts_no_delete BEFORE DELETE ON recovery_attempts
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
-- 복구 시도: 결과(재측정·판정·종료 이유·끈 시각)는 'pending'일 때 한 번만 채울 수 있음
CREATE FUNCTION recovery_attempt_complete_once() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.validation_result <> 'pending' THEN
    RAISE EXCEPTION 'recovery_attempts: 판정이 끝난 시도는 바꿀 수 없습니다';
  END IF;
  IF (NEW.attempt_id, NEW.plan_id, NEW.incident_id, NEW.action, NEW.action_enabled_at, NEW.created_at)
     IS DISTINCT FROM (OLD.attempt_id, OLD.plan_id, OLD.incident_id, OLD.action, OLD.action_enabled_at, OLD.created_at) THEN
    RAISE EXCEPTION 'recovery_attempts: 결과 칸만 채울 수 있습니다';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_recovery_attempts_complete_once BEFORE UPDATE ON recovery_attempts
  FOR EACH ROW EXECUTE FUNCTION recovery_attempt_complete_once();
-- 사건: status·closed_at만 바꿀 수 있고 삭제 금지
CREATE FUNCTION incident_logs_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'incident_logs: 삭제할 수 없습니다'; END IF;
  IF (to_jsonb(NEW) - 'status' - 'closed_at') IS DISTINCT FROM (to_jsonb(OLD) - 'status' - 'closed_at') THEN
    RAISE EXCEPTION 'incident_logs: status·closed_at만 바꿀 수 있습니다';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_incident_logs_guard BEFORE UPDATE OR DELETE ON incident_logs
  FOR EACH ROW EXECUTE FUNCTION incident_logs_guard();
CREATE TRIGGER trg_incident_outcomes_append_only BEFORE UPDATE OR DELETE ON incident_outcomes
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER trg_agent_runs_append_only BEFORE UPDATE OR DELETE ON agent_runs
  FOR EACH ROW EXECUTE FUNCTION forbid_change();

-- ===== 권한: 테이블 접근 권한(GRANT) + 행 단위 정책(RLS) =====
-- 권한의 1차 검사는 FastAPI, DB는 2차 안전장치. 모든 테이블에 RLS를 켜서 정책이 없는 접근은 noldaga_app에게 거부.
DO $$ DECLARE t text; BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO noldaga_service;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO noldaga_service;

-- 공개 조회 (비로그인 포함: API 서버가 noldaga_app으로 읽음)
GRANT SELECT ON festivals, facilities, data_sources, official_notices, festival_reviews,
  population_areas, festival_population_links TO noldaga_app;
CREATE POLICY festivals_public ON festivals FOR SELECT TO noldaga_app USING (published_at IS NOT NULL);
CREATE POLICY facilities_public ON facilities FOR SELECT TO noldaga_app USING (true);
CREATE POLICY data_sources_public ON data_sources FOR SELECT TO noldaga_app USING (true);
CREATE POLICY notices_public ON official_notices FOR SELECT TO noldaga_app USING (approval_status = 'approved');
CREATE POLICY population_areas_public ON population_areas FOR SELECT TO noldaga_app USING (true);
CREATE POLICY population_links_public ON festival_population_links FOR SELECT TO noldaga_app USING (true);

-- 본인 것만: 관심 축제
GRANT SELECT, INSERT, DELETE ON favorites TO noldaga_app;
CREATE POLICY favorites_select_own ON favorites FOR SELECT TO noldaga_app
  USING (user_id = app_current_user());
CREATE POLICY favorites_insert_own ON favorites FOR INSERT TO noldaga_app
  WITH CHECK (user_id = app_current_user());
CREATE POLICY favorites_delete_own ON favorites FOR DELETE TO noldaga_app
  USING (user_id = app_current_user());

-- 프로필: 본인만 조회, 표시 이름만 수정(컬럼 권한으로 role 변경 차단)
GRANT SELECT ON profiles TO noldaga_app;
GRANT UPDATE (display_name) ON profiles TO noldaga_app;
CREATE POLICY profiles_select_own ON profiles FOR SELECT TO noldaga_app USING (user_id = app_current_user());
CREATE POLICY profiles_update_own ON profiles FOR UPDATE TO noldaga_app
  USING (user_id = app_current_user()) WITH CHECK (user_id = app_current_user());

-- 후기: 보이는 것은 누구나, 작성·수정·삭제는 본인(본문·평점만, status는 관리자=service)
GRANT INSERT, DELETE ON festival_reviews TO noldaga_app;
GRANT UPDATE (body, rating, updated_at) ON festival_reviews TO noldaga_app;
CREATE POLICY reviews_select ON festival_reviews FOR SELECT TO noldaga_app
  USING (status = 'visible' OR user_id = app_current_user());
CREATE POLICY reviews_insert_own ON festival_reviews FOR INSERT TO noldaga_app WITH CHECK (user_id = app_current_user());
CREATE POLICY reviews_update_own ON festival_reviews FOR UPDATE TO noldaga_app
  USING (user_id = app_current_user()) WITH CHECK (user_id = app_current_user());
CREATE POLICY reviews_delete_own ON festival_reviews FOR DELETE TO noldaga_app USING (user_id = app_current_user());

-- 운영자 조회: 사건
GRANT SELECT ON incident_logs TO noldaga_app;
CREATE POLICY incident_logs_select_operator ON incident_logs FOR SELECT TO noldaga_app
  USING (EXISTS (SELECT 1 FROM profiles p WHERE p.user_id = app_current_user() AND p.role IN ('operator','admin')));
-- profiles 정책 때문에 운영자 확인이 본인 행으로만 이뤄짐(본인 role 확인에는 충분)
-- noldaga_app에는 사건·경로·복구 테이블 쓰기 권한이 없음 → 기록은 noldaga_service만. 운영자 화면의 나머지 조회 정책은 v0.4.
