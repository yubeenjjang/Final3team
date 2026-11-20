-- 005 되돌리기
DROP TABLE IF EXISTS user_blocks, friendships, friend_requests, festival_engagement_daily, festival_tags, user_festival_preferences;
ALTER TABLE profiles DROP COLUMN IF EXISTS nickname_searchable, DROP COLUMN IF EXISTS friend_code;
