-- 003 되돌리기
-- 실제 이미지가 있으면 저작권·썸네일 정보가 사라지므로 먼저 중단한다.
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM public.festivals
    WHERE image_url IS NOT NULL OR thumbnail_url IS NOT NULL OR image_copyright_type IS NOT NULL
  ) THEN
    RAISE EXCEPTION '003 되돌리기 중단: 축제 이미지·저작권 정보가 있는 행을 먼저 보존하거나 처리하세요';
  END IF;
END $$;
ALTER TABLE festivals DROP CONSTRAINT IF EXISTS festivals_image_copyright_needed,
  DROP COLUMN IF EXISTS image_copyright_type, DROP COLUMN IF EXISTS thumbnail_url;
