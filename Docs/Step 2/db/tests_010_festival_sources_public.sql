-- 009 다음에 010 적용(applied=true) → 되돌리기(applied=false) → 재적용(reapplied=true).
BEGIN;

INSERT INTO public.data_sources (source_id, name, provider_org, scope, is_realtime, status)
VALUES ('test_010', '010 시험', 'TourAPI', 'national', false, 'verified');

INSERT INTO public.festivals (festival_id, title, region_code, category, review_status, published_at)
VALUES
  ('fst_T01001', '공개 축제', 'SEOUL', 'festival', 'approved', now()),
  ('fst_T01002', '미게시 축제', 'SEOUL', 'festival', 'approved', NULL),
  ('fst_T01003', '숨긴 축제', 'SEOUL', 'festival', 'hidden', now());

INSERT INTO public.festival_sources
  (festival_id, source_id, source_item_id, source_url, raw_checksum, fetched_at)
VALUES
  ('fst_T01001', 'test_010', 'item-01001', 'https://example.invalid/01001', 'test', now()),
  ('fst_T01002', 'test_010', 'item-01002', 'https://example.invalid/01002', 'test', now()),
  ('fst_T01003', 'test_010', 'item-01003', 'https://example.invalid/01003', 'test', now());

SET LOCAL ROLE noldaga_app;

\if :applied
DO $$
DECLARE
  internal_column text;
BEGIN
  IF (SELECT array_agg(source_item_id) FROM public.festival_sources
      WHERE source_id = 'test_010') IS DISTINCT FROM ARRAY['item-01001'] THEN
    RAISE EXCEPTION 'T010a FAIL: 공개 축제의 원본 번호만 조회되어야 합니다';
  END IF;
  RAISE NOTICE 'T010a PASS: 공개 축제 원본 번호만 조회';

  IF (SELECT array_agg(f.festival_id || ':' || s.source_url)
      FROM public.festivals f JOIN public.festival_sources s USING (festival_id)
      WHERE s.source_id = 'test_010') IS DISTINCT FROM
      ARRAY['fst_T01001:https://example.invalid/01001'] THEN
    RAISE EXCEPTION 'T010b FAIL: 공개 축제와 원본만 조인되어야 합니다';
  END IF;
  RAISE NOTICE 'T010b PASS: 공개 축제와 원본만 조인';

  FOREACH internal_column IN ARRAY ARRAY['raw_checksum','fetched_at','last_job_id'] LOOP
    BEGIN
      EXECUTE format('SELECT %I FROM public.festival_sources', internal_column);
      RAISE EXCEPTION 'T010c FAIL: 내부 컬럼 %의 조회가 허용되었습니다', internal_column;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END;
  END LOOP;
  RAISE NOTICE 'T010c PASS: 내부 컬럼 조회 차단';
END $$;
\else
DO $$
DECLARE
  public_column text;
BEGIN
  FOREACH public_column IN ARRAY ARRAY['festival_id','source_id','source_item_id','source_url'] LOOP
    BEGIN
      EXECUTE format('SELECT %I FROM public.festival_sources', public_column);
      RAISE EXCEPTION 'T010d FAIL: 되돌린 뒤에도 % 조회가 허용되었습니다', public_column;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END;
  END LOOP;

  IF EXISTS (SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'festival_sources'
        AND policyname = 'festival_sources_public') THEN
    RAISE EXCEPTION 'T010d FAIL: 되돌린 뒤에도 공개 정책이 남았습니다';
  END IF;
  RAISE NOTICE 'T010d PASS: 되돌리기 후 조회 권한과 공개 정책 제거';
END $$;
\endif

\if :reapplied
-- 재적용 뒤 앞의 조회·조인·권한 검사를 모두 다시 통과해야 한다.
\echo 'T010e PASS: 재적용 후 권한 및 공개 정책 복원'
\endif

ROLLBACK;
