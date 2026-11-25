\if :applied
BEGIN;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.data_sources (source_id, name, scope, is_realtime)
VALUES ('seoul_culture', '서울시 문화행사 정보', 'seoul_only', false)
ON CONFLICT (source_id) DO NOTHING;
INSERT INTO public.festivals
  (festival_id, title, region_code, category, source_class_level2, review_status, published_at)
VALUES
  ('fst_T027PUBLIC', '공개 축제', 'SEOUL', 'festival', 'EV01', 'approved', now()),
  ('fst_T027HELD', '미확인 축제', 'SEOUL', 'festival', NULL, 'pending', NULL);
INSERT INTO public.festival_sources
  (festival_id, source_id, source_item_id, source_url, source_image_url, raw_checksum, fetched_at)
VALUES
  ('fst_T027PUBLIC', 'seoul_culture', '0271', 'https://example.invalid/1', 'https://example.invalid/img', '0271', now()),
  ('fst_T027HELD', 'seoul_culture', '0272', 'https://example.invalid/2', NULL, '0272', now());
INSERT INTO public.festival_review_queue (festival_id, reason)
VALUES ('fst_T027HELD', 'class_unverified');
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.festival_sources
                 WHERE source_item_id = '0271' AND source_image_url = 'https://example.invalid/img') THEN
    RAISE EXCEPTION 'FAIL T027a: 서비스 역할의 이미지 근거 저장·조회 실패';
  END IF;
  RAISE NOTICE 'PASS T027a: 서비스 역할의 이미지 근거 저장·조회';
END $$;

RESET ROLE;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF has_column_privilege(current_user, 'public.festival_sources', 'source_image_url', 'SELECT')
     OR has_table_privilege(current_user, 'public.festival_review_queue', 'SELECT')
     OR NOT EXISTS (SELECT 1 FROM public.festival_sources
                    WHERE festival_id = 'fst_T027PUBLIC' AND source_id = 'seoul_culture')
     OR EXISTS (SELECT 1 FROM public.festivals WHERE festival_id = 'fst_T027HELD')
     OR EXISTS (SELECT 1 FROM public.festival_sources WHERE festival_id = 'fst_T027HELD') THEN
    RAISE EXCEPTION 'FAIL T027b: 공개·격리 행 RLS 또는 이미지 근거 권한 오류';
  END IF;
  RAISE NOTICE 'PASS T027b: 공개 원본 참조, 격리 RLS, 이미지 근거 비공개';
END $$;
ROLLBACK;
\else
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'festival_sources'
               AND column_name = 'source_image_url')
     OR NOT has_column_privilege('noldaga_app', 'public.festival_sources', 'source_url', 'SELECT') THEN
    RAISE EXCEPTION 'FAIL T027c: 이미지 근거 컬럼 제거 또는 010 권한 복원 실패';
  END IF;
  RAISE NOTICE 'PASS T027c: 이미지 근거 컬럼 제거와 기존 권한 유지';
END $$;
\endif
