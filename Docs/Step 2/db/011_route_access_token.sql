-- 011: 귀가 조회 토큰·DB 저장. psql -X -v ON_ERROR_STOP=1 -1 -f 로 한 파일씩 적용.
-- precheck_011_route_access_token.sql로 기존 행 수를 확인한 뒤 적용한다.
LOCK TABLE public.route_requests, public.route_results IN ACCESS EXCLUSIVE MODE;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'route_requests'
      AND column_name = 'destination_place_hash'
  ) OR NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public'
      AND tablename = 'festival_sources' AND policyname = 'festival_sources_public'
  ) THEN
    RAISE EXCEPTION '011 적용 중지: 009와 010이 필요합니다';
  END IF;
  IF (SELECT count(*) FROM pg_class
      WHERE oid IN ('public.route_requests'::regclass, 'public.route_results'::regclass)
        AND relrowsecurity) <> 2
     OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'noldaga_service' AND rolbypassrls)
     OR NOT has_table_privilege('noldaga_service', 'public.route_requests', 'SELECT')
     OR NOT has_table_privilege('noldaga_service', 'public.route_requests', 'INSERT')
     OR NOT has_table_privilege('noldaga_service', 'public.route_requests', 'UPDATE')
     OR NOT has_table_privilege('noldaga_service', 'public.route_results', 'SELECT')
     OR NOT has_table_privilege('noldaga_service', 'public.route_results', 'INSERT')
     OR NOT has_table_privilege('noldaga_service', 'public.route_results', 'UPDATE')
     OR has_any_column_privilege('noldaga_app', 'public.route_requests', 'SELECT, INSERT, UPDATE, REFERENCES')
     OR has_any_column_privilege('noldaga_app', 'public.route_results', 'SELECT, INSERT, UPDATE, REFERENCES')
     OR has_table_privilege('noldaga_app', 'public.route_requests', 'DELETE, TRUNCATE, TRIGGER')
     OR has_table_privilege('noldaga_app', 'public.route_results', 'DELETE, TRUNCATE, TRIGGER') THEN
    RAISE EXCEPTION '011 적용 중지: 경로 테이블 RLS와 접속 역할 권한을 확인하세요';
  END IF;
END $$;

ALTER TABLE public.route_requests
  ADD COLUMN access_token_hash TEXT,
  ADD COLUMN request_body_hash TEXT,
  ADD COLUMN error_detail JSONB;

-- 옛 행을 지우거나 토큰을 발급하지 않는다. POST/A05는 request_body_hash가 NULL인 옛 행을 제외한다.
UPDATE public.route_requests
SET access_token_hash = encode(sha256(convert_to(gen_random_uuid()::text, 'UTF8')), 'hex');

ALTER TABLE public.route_requests
  ALTER COLUMN access_token_hash SET NOT NULL,
  ADD CONSTRAINT route_requests_token_hash_check CHECK (access_token_hash ~ '^[0-9a-f]{64}$'),
  ADD CONSTRAINT route_requests_body_hash_check CHECK (request_body_hash ~ '^[0-9a-f]{64}$');

COMMENT ON COLUMN public.route_requests.access_token_hash IS 'A05 토큰의 SHA-256. RLS 우회 서비스 계정만 읽는다.';
COMMENT ON COLUMN public.route_requests.request_body_hash IS '정규화한 접수 본문의 HMAC-SHA256. 011 이전 행은 NULL.';
COMMENT ON COLUMN public.route_requests.error_detail IS 'API가 정한 오류 안내·재시도 정보. 공급원 오류 원문은 제외.';

-- A05는 기존 요청 PK로 읽는다. 토큰 해시 검색 색인은 필요 없다.
CREATE INDEX idx_route_results_tmap_pending_purge
  ON public.route_results (queried_at) WHERE provider = 'tmap' AND purged_at IS NULL;
