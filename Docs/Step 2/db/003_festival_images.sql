-- 놀다가 DB 마이그레이션 003: 축제 대표 이미지(썸네일·저작권 유형) 칸 추가 (API 설계서 v0.3.2 10절, 2026-11-20 TourAPI 원본 확인)
-- 적용 순서: 001 → 002 → 003. 되돌리기: 003_festival_images_down.sql
-- festivals.image_url(기존) = TourAPI firstimage(원본), thumbnail_url = firstimage2(작은 크기), image_copyright_type = cpyrhtDivCd
ALTER TABLE festivals
  ADD COLUMN thumbnail_url TEXT,
  ADD COLUMN image_copyright_type TEXT CHECK (image_copyright_type IN ('Type1','Type3')),
  ADD CONSTRAINT festivals_image_copyright_needed CHECK (image_url IS NULL OR image_copyright_type IS NOT NULL);
COMMENT ON COLUMN festivals.image_copyright_type IS 'TourAPI cpyrhtDivCd. Type1=출처 표시, Type3=출처 표시+변경 금지. 이미지가 있으면 반드시 있음';
