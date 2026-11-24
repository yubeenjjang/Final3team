-- 017 적용 후 파일 단위 트랜잭션에서 실행한다.
ALTER TABLE public.festivals
  ADD COLUMN coords_source TEXT,
  ADD CONSTRAINT festivals_coords_source_check CHECK (
    coords_source IS NULL OR (
      coords_source IN ('tourapi', 'geocoded') AND latitude IS NOT NULL AND longitude IS NOT NULL
    )
  );

COMMENT ON COLUMN public.festivals.coords_source IS
  'tourapi: 원본 좌표, geocoded: 카카오 주소 검색 보정, NULL: 출처 미기록 또는 좌표 없음';

-- 010의 원본 참조 정책도 festivals RLS가 허용하는 행만 읽는다.
ALTER POLICY festivals_public ON public.festivals
  USING (
    category = 'festival' AND source_class_level2 = 'EV01'
    AND review_status = 'approved' AND published_at IS NOT NULL
  );

-- 변경 전 상태를 이력에 남겨 이 마이그레이션이 보류한 행만 복원할 수 있게 한다.
WITH held AS (
  INSERT INTO public.festival_change_history
    (festival_id, field, before_value, after_value, source_id, actor, changed_at)
  SELECT festival_id, 'source_classification',
         jsonb_build_object('review_status', review_status, 'published_at', published_at),
         '{"reason":"class_unverified","migration":"018"}'::jsonb,
         'tourapi', 'ingestion', now()
  FROM public.festivals
  WHERE category = 'festival' AND review_status = 'approved' AND published_at IS NOT NULL
    AND nullif(btrim(source_class_level2), '') IS NULL
  RETURNING festival_id
)
UPDATE public.festivals f
SET review_status = 'pending', published_at = NULL
FROM held WHERE held.festival_id = f.festival_id;
