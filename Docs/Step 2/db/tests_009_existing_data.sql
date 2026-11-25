-- T44~T48: 데이터가 이미 있는 DB에서 009 적용·실패 취소·되돌리기 (강사 11/20 DB 피드백 1). 008까지 적용된 DB에서 실행.
-- 시험용 기존 행: 사용자 3명(닉네임·친구 코드), 귀가 1·가는 길 1, 신고 1, RAG 1
INSERT INTO users(user_id,email,password_hash) VALUES
 ('00000000-0000-0000-0000-0000000000a1','a1@t.t','x'),('00000000-0000-0000-0000-0000000000a2','a2@t.t','x'),('00000000-0000-0000-0000-0000000000a3','a3@t.t','x');
INSERT INTO profiles(user_id,display_name,friend_code,nickname_searchable) VALUES
 ('00000000-0000-0000-0000-0000000000a1','오현','ABCD1234',true),('00000000-0000-0000-0000-0000000000a2','Dayoung',NULL,false),('00000000-0000-0000-0000-0000000000a3','태경',NULL,false);
INSERT INTO festivals(festival_id,title,region_code) VALUES ('fst_test0001','시험 축제','SEOUL');
INSERT INTO route_requests(route_request_id,request_id,direction,festival_id,festival_lat,festival_lng,user_place_hash,travel_mode,route_key,status,is_mock) VALUES
 ('rr_test000001','req-1','return','fst_test0001',37.5,126.9,'hmac_home','transit','k1','ready',true),
 ('rr_test000002','req-2','visit','fst_test0001',37.5,126.9,'hmac_start','transit','k2','ready',true);
