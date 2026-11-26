\if :seed
INSERT INTO public.data_sources (source_id, name, provider_org, scope, is_realtime, key_site, status)
VALUES ('t018', '시험 원본', '시험', 'national', false, 'example.invalid', 'verified');

INSERT INTO public.festivals (
  festival_id, title, region_code, category, source_class_level2, review_status, published_at
) VALUES
  ('fst_T18001', '미분류', 'JEONNAM', 'festival', NULL, 'approved', '2026-11-01 09:00+09'),
  ('fst_T18002', '축제', 'SEOUL', 'festival', 'EV01', 'approved', '2026-11-01 09:00+09'),
  ('fst_T18003', '관리자 숨김', 'SEOUL', 'festival', NULL, 'hidden', '2026-11-01 09:00+09'),
  ('fst_T18004', '검토 중', 'SEOUL', 'festival', NULL, 'pending', NULL);

INSERT INTO public.festival_sources (festival_id, source_id, source_item_id, fetched_at, raw_checksum)
SELECT festival_id, 't018', festival_id, now(), 'test-018'
FROM public.festivals WHERE festival_id LIKE 'fst_T18%';
\else
BEGIN;
\if :applied
-- 018 이후 작성된 잘못된 'approved'도 RLS로 막는다.
INSERT INTO public.festivals (
  festival_id, title, region_code, category, source_class_level2, review_status, published_at
) VALUES
  ('fst_T18005', '새 미분류', 'SEOUL', 'festival', NULL, 'approved', now()),
  ('fst_T18006', '잘못 분류된 행사', 'SEOUL', 'festival', 'EV03', 'approved', now());
INSERT INTO public.festival_sources (festival_id, source_id, source_item_id, fetched_at, raw_checksum)
SELECT festival_id, 't018', festival_id, now(), 'test-018'
FROM public.festivals WHERE festival_id IN ('fst_T18005', 'fst_T18006');
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.festivals
    WHERE festival_id = 'fst_T18001' AND review_status = 'pending' AND published_at IS NULL)
    OR (SELECT count(*) FROM public.festival_change_history WHERE festival_id = 'fst_T18001'
        AND field = 'source_classification' AND after_value->>'reason' = 'class_unverified'
        AND (before_value->>'published_at')::timestamptz = '2026-11-01 09:00+09'::timestamptz) <> 1
    OR NOT EXISTS (SELECT 1 FROM public.festivals
      WHERE festival_id = 'fst_T18003' AND review_status = 'hidden' AND published_at IS NOT NULL)
    OR NOT EXISTS (SELECT 1 FROM public.festivals
      WHERE festival_id = 'fst_T18004' AND review_status = 'pending' AND published_at IS NULL) THEN
    RAISE EXCEPTION 'T018a FAIL: 미분류 게시 상태 또는 이력';
  END IF;
  UPDATE public.festivals SET latitude = 37.5, longitude = 127.1, coords_source = 'geocoded'
  WHERE festival_id = 'fst_T18001';
  BEGIN
    UPDATE public.festivals SET coords_source = 'geocoded' WHERE festival_id = 'fst_T18004';
    RAISE EXCEPTION 'T018b FAIL: 좌표 없는 보정 표기 허용';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  RAISE NOTICE 'T018a~b PASS: 미분류 전환·이력 및 좌표 출처 제약';
END $$;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF (SELECT array_agg(festival_id ORDER BY festival_id)
      FROM public.festivals WHERE festival_id LIKE 'fst_T18%')
      IS DISTINCT FROM ARRAY['fst_T18002']::text[]
    OR (SELECT array_agg(source_item_id ORDER BY source_item_id)
        FROM public.festival_sources WHERE source_id = 't018')
        IS DISTINCT FROM ARRAY['fst_T18002']::text[] THEN
    RAISE EXCEPTION 'T018c FAIL: EV01 축제 및 원본 공개 범위';
  END IF;
  RAISE NOTICE 'T018c PASS: 축제와 원본 RLS 모두 EV01만 공개';
END $$;
\else
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.festivals WHERE festival_id = 'fst_T18001'
    AND review_status = 'approved' AND published_at = '2026-11-01 09:00+09'::timestamptz)
    OR EXISTS (SELECT 1 FROM public.festival_change_history WHERE festival_id = 'fst_T18001')
    OR EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
      AND table_name = 'festivals' AND column_name = 'coords_source') THEN
    RAISE EXCEPTION 'T018d FAIL: 018 되돌리기 데이터 복원';
  END IF;
END $$;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF (SELECT array_agg(festival_id ORDER BY festival_id)
      FROM public.festivals WHERE festival_id LIKE 'fst_T18%')
      IS DISTINCT FROM ARRAY['fst_T18001', 'fst_T18002']::text[]
    OR (SELECT array_agg(source_item_id ORDER BY source_item_id)
        FROM public.festival_sources WHERE source_id = 't018')
        IS DISTINCT FROM ARRAY['fst_T18001', 'fst_T18002']::text[] THEN
    RAISE EXCEPTION 'T018d FAIL: 014 공개 정책 복원';
  END IF;
  RAISE NOTICE 'T018d PASS: 014 정책과 기존 게시 상태 복원';
END $$;
\endif
ROLLBACK;
\endif
