-- 008의 공개 정책으로 되돌리고 014의 원본 코드 칸을 제거한다.
ALTER POLICY festivals_public ON public.festivals
  USING (published_at IS NOT NULL AND review_status <> 'hidden');

ALTER TABLE public.festivals
  DROP COLUMN source_class_code,
  DROP COLUMN source_class_level2,
  DROP COLUMN source_class_level1;
