-- 026 뒤 파일 단위 트랜잭션으로 적용한다. 010의 앱 역할 컬럼 권한을 유지한다.
ALTER TABLE public.festival_sources ADD COLUMN source_image_url TEXT;
COMMENT ON COLUMN public.festival_sources.source_image_url IS
  'OA-15486 MAIN_IMG 원본 URL(서비스 역할 검토용). A02·A03 대표 이미지에는 사용하지 않는다.';
