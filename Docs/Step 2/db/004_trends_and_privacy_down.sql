-- 004 되돌리기 (라벨 칸은 비어 있는 채로 복원)
DROP TABLE IF EXISTS festival_trends;
ALTER TABLE route_requests ADD COLUMN IF NOT EXISTS user_place_label TEXT;
-- user_place_hash NOT NULL 복원은 NULL 행이 없을 때만 가능
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM route_requests WHERE user_place_hash IS NULL) THEN
    ALTER TABLE route_requests ALTER COLUMN user_place_hash SET NOT NULL;
  END IF;
END $$;
