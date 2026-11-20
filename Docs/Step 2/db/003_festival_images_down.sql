-- 003 되돌리기
ALTER TABLE festivals DROP CONSTRAINT IF EXISTS festivals_image_copyright_needed,
  DROP COLUMN IF EXISTS image_copyright_type, DROP COLUMN IF EXISTS thumbnail_url;
