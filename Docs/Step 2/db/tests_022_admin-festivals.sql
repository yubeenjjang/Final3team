\if :applied
BEGIN;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.festivals (festival_id, title, region_code, category, source_class_level2)
VALUES ('fst_T22001', '관리자 등록 시험', 'SEOUL', 'festival', 'EV01');
INSERT INTO public.festival_sources (festival_id, source_id, source_item_id, raw_checksum, fetched_at)
VALUES ('fst_T22001', 'admin_manual', 'fst_T22001', 'test', now());
INSERT INTO public.festival_review_queue (festival_id, reason, proposed_value)
VALUES ('fst_T22001', 'duplicate', '{"title":"관리자 등록 시험"}');
INSERT INTO public.festival_change_history
  (festival_id, field, before_value, after_value, actor, changed_at, reason, actor_user_id)
VALUES ('fst_T22001', 'title', NULL, '"관리자 등록 시험"', 'admin', now(), '공식 일정 확인',
        '22220000-0000-0000-0000-000000000001');

DO $$ BEGIN
  IF (SELECT count(*) FROM public.festival_change_history WHERE festival_id = 'fst_T22001'
      AND reason = '공식 일정 확인' AND actor_user_id = '22220000-0000-0000-0000-000000000001') <> 1
    OR to_regclass('public.idx_festivals_registration_identity') IS NULL THEN
    RAISE EXCEPTION 'T022a FAIL: 감사 정보 또는 중복 검색 인덱스 누락';
  END IF;
  BEGIN
    INSERT INTO public.festival_change_history (festival_id, field, actor, changed_at, reason)
    VALUES ('fst_T22001', 'title', 'admin', now(), '불완전한 감사 기록');
    RAISE EXCEPTION 'T022a FAIL: 처리자 없는 신규 감사 기록 허용';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  RAISE NOTICE 'T022a PASS: 관리 출처·감사 이력·중복 검색 인덱스와 필수 사유/처리자 확인';
END $$;

SET LOCAL ROLE noldaga_app;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.festivals WHERE festival_id = 'fst_T22001')
     OR EXISTS (SELECT 1 FROM public.festival_sources WHERE festival_id = 'fst_T22001') THEN
    RAISE EXCEPTION 'T022b FAIL: 미게시 축제 또는 출처 노출';
  END IF;
  IF has_table_privilege(current_user, 'public.festival_review_queue', 'SELECT')
    OR has_table_privilege(current_user, 'public.festival_change_history', 'SELECT')
    OR has_table_privilege(current_user, 'public.festivals', 'UPDATE') THEN
    RAISE EXCEPTION 'T022b FAIL: 앱 계정의 관리자 테이블 접근 허용';
  END IF;
  RAISE NOTICE 'T022b PASS: 앱 계정의 미게시 행과 관리자 데이터 접근 차단';
END $$;

SET LOCAL ROLE noldaga_service;
UPDATE public.festivals SET review_status = 'approved', published_at = now()
WHERE festival_id = 'fst_T22001';
SET LOCAL ROLE noldaga_app;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.festival_sources
                 WHERE festival_id = 'fst_T22001' AND source_id = 'admin_manual') THEN
    RAISE EXCEPTION 'T022e FAIL: 게시된 관리자 출처의 공개 조회 실패';
  END IF;
  RAISE NOTICE 'T022e PASS: 게시된 축제의 관리 출처 공개 조회';
END $$;
ROLLBACK;
\else
DO $$ BEGIN
  IF to_regclass('public.idx_festivals_registration_identity') IS NOT NULL OR EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'festival_change_history'
      AND column_name IN ('actor_user_id', 'reason')
  ) THEN
    RAISE EXCEPTION 'T022c FAIL: 중복 검색 인덱스 또는 감사 칸이 되돌려지지 않음';
  END IF;
  RAISE NOTICE 'T022c PASS: 되돌리기 뒤 중복 검색 인덱스 및 신규 감사 칸 제거';
END $$;
\endif
