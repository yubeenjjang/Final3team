-- -v applied=true|false. 014의 공개 정책·010 원본 조회·되돌리기를 확인한다.
BEGIN;

INSERT INTO public.data_sources (source_id, name, provider_org, scope, is_realtime, status)
VALUES ('test_014', '014 시험', 'TourAPI', 'national', false, 'verified');

INSERT INTO public.festivals (festival_id, title, region_code, category, review_status, published_at)
VALUES
  ('fst_T14001', '축제', 'SEOUL', 'festival', 'approved', now()),
  ('fst_T14002', '공연', 'SEOUL', 'performance', 'approved', now()),
  ('fst_T14003', '행사', 'SEOUL', 'event', 'approved', now()),
  ('fst_T14004', '미분류', 'SEOUL', 'unknown', 'approved', now()),
  ('fst_T14005', '검토 대기 축제', 'SEOUL', 'festival', 'pending', now()),
  ('fst_T14006', '관리자 숨김 축제', 'SEOUL', 'festival', 'hidden', now()),
  ('fst_T14007', '미게시 축제', 'SEOUL', 'festival', 'approved', NULL),
  ('fst_T14008', '분류 미기록', 'SEOUL', NULL, 'approved', now());

INSERT INTO public.festival_sources (festival_id, source_id, source_item_id, raw_checksum, fetched_at)
SELECT festival_id, 'test_014', festival_id, 'test', now()
FROM public.festivals WHERE left(festival_id, 8) = 'fst_T140';

\if :applied
UPDATE public.festivals
SET source_class_level1 = 'EV', source_class_level2 = 'EV01', source_class_code = 'EV010600'
WHERE festival_id = 'fst_T14001';

SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF (SELECT array_agg(festival_id ORDER BY festival_id) FROM public.festivals
      WHERE left(festival_id, 8) = 'fst_T140') IS DISTINCT FROM ARRAY['fst_T14001'] THEN
    RAISE EXCEPTION 'T014a 축제 공개 RLS 오류';
  END IF;
  IF (SELECT array_agg(source_item_id ORDER BY source_item_id) FROM public.festival_sources
      WHERE source_id = 'test_014') IS DISTINCT FROM ARRAY['fst_T14001'] THEN
    RAISE EXCEPTION 'T014b 원본 참조 공개 범위 오류';
  END IF;
END $$;
\else
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
      AND table_name = 'festivals'
      AND column_name IN ('source_class_level1', 'source_class_level2', 'source_class_code')) THEN
    RAISE EXCEPTION 'T014c 원본 코드 칸 되돌리기 오류';
  END IF;
END $$;

SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF (SELECT array_agg(festival_id ORDER BY festival_id) FROM public.festivals
      WHERE left(festival_id, 8) = 'fst_T140') IS DISTINCT FROM
          ARRAY['fst_T14001', 'fst_T14002', 'fst_T14003', 'fst_T14004', 'fst_T14005', 'fst_T14008'] THEN
    RAISE EXCEPTION 'T014d 008 공개 RLS 복구 오류';
  END IF;
  IF (SELECT count(source_item_id) FROM public.festival_sources WHERE source_id = 'test_014') <> 6 THEN
    RAISE EXCEPTION 'T014e 010 원본 참조 공개 범위 복구 오류';
  END IF;
END $$;
\endif

ROLLBACK;
\echo 'T014 PASSED'
