-- 007 되돌리기
DROP TABLE IF EXISTS chat_admin_access, reports, notifications, chat_messages, chat_members, meeting_places,
  companion_applications, companion_posts, chat_rooms;
DROP FUNCTION IF EXISTS app_room_joined_at(TEXT), app_room_visible(TEXT);
