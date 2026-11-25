-- TourAPI 목록 분류 보관 및 A02·A03과 DB 공개 범위 통일. 파일 단위 트랜잭션으로 적용한다.
ALTER TABLE public.festivals
  ADD COLUMN source_class_level1 TEXT,
  ADD COLUMN source_class_level2 TEXT,
  ADD COLUMN source_class_code TEXT;

COMMENT ON COLUMN public.festivals.source_class_level1 IS 'TourAPI searchFestival2 lclsSystm1';
COMMENT ON COLUMN public.festivals.source_class_level2 IS 'TourAPI searchFestival2 lclsSystm2';
COMMENT ON COLUMN public.festivals.source_class_code IS 'TourAPI searchFestival2 lclsSystm3';

-- 010의 festival_sources 공개 정책은 festivals RLS가 허용하는 행을 조인한다.
ALTER POLICY festivals_public ON public.festivals
  USING (category = 'festival' AND review_status = 'approved' AND published_at IS NOT NULL);
