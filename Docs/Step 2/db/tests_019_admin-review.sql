\if :seed
INSERT INTO public.data_sources (source_id, name, scope, is_realtime)
VALUES ('tourapi', 'TourAPI', 'national', false)
ON CONFLICT (source_id) DO NOTHING;

INSERT INTO public.festivals (festival_id, title, region_code, category, source_class_level2, address, review_status)
VALUES
  ('fst_T19001', '미분류', 'SEOUL', 'unknown', NULL, NULL, 'pending'),
  ('fst_T19002', '비축제', 'SEOUL', 'performance', 'EV02', NULL, 'pending'),
  ('fst_T19003', '좌표 보류', 'SEOUL', 'festival', 'EV01', '서울', 'pending'),
  ('fst_T19004', '원본 누락', 'SEOUL', 'festival', 'EV01', NULL, 'pending'),
  ('fst_T19005', '관리자 숨김', 'SEOUL', 'unknown', NULL, NULL, 'hidden'),
  ('fst_T19006', '원본 복귀', 'SEOUL', 'festival', 'EV01', NULL, 'pending');
INSERT INTO public.festival_sources (festival_id, source_id, source_item_id, raw_checksum, fetched_at)
SELECT festival_id, 'tourapi', festival_id, 'test-019', now()
FROM public.festivals WHERE festival_id LIKE 'fst_T19%';

INSERT INTO public.festival_review_queue (festival_id, reason) VALUES ('fst_T19001', 'duplicate');
INSERT INTO public.festival_change_history (festival_id, field, after_value, source_id, actor, changed_at)
VALUES
  ('fst_T19004', 'source_presence', '{"reason":"missing_from_source"}', 'tourapi', 'ingestion', now()),
  ('fst_T19006', 'source_presence', '{"reason":"missing_from_source"}', 'tourapi', 'ingestion', now());
INSERT INTO public.festival_change_history (festival_id, field, after_value, source_id, actor, changed_at)
VALUES ('fst_T19006', 'source_presence', '{"reason":"reappeared_in_source"}', 'tourapi', 'ingestion', now());
\else
BEGIN;
\if :applied
SET LOCAL ROLE noldaga_service;
DO $$
BEGIN
  IF (SELECT array_agg(reason ORDER BY festival_id, reason) FROM public.festival_review_queue
      WHERE festival_id LIKE 'fst_T19%') IS DISTINCT FROM ARRAY[
        'class_unverified', 'duplicate', 'not_festival_class', 'coords_out_of_range', 'missing_from_source'
      ]::text[] THEN
    RAISE EXCEPTION 'T019a FAIL: 기존 검토 항목과 보류 사유 이관';
  END IF;
  BEGIN
    INSERT INTO public.festival_review_queue (festival_id, reason) VALUES ('fst_T19001', 'invalid');
    RAISE EXCEPTION 'T019a FAIL: 잘못된 사유가 저장됨';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  RAISE NOTICE 'T019a PASS: 기존 검토 항목과 보류 사유 이관 및 사유 제약';
END $$;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  BEGIN
    PERFORM queue_id FROM public.festival_review_queue WHERE festival_id = 'fst_T19001';
    RAISE EXCEPTION 'T019b FAIL: 앱 역할 검토 대기열 열람';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  IF EXISTS (SELECT 1 FROM public.festivals WHERE festival_id LIKE 'fst_T19%') THEN
    RAISE EXCEPTION 'T019b FAIL: 앱 역할에 보류 또는 숨김 축제가 보임';
  END IF;
  RAISE NOTICE 'T019b PASS: 앱 역할의 검토 대기열 및 비공개 축제 접근 제한';
END $$;
\else
DO $$
BEGIN
  IF (SELECT array_agg(reason) FROM public.festival_review_queue
      WHERE festival_id LIKE 'fst_T19%') IS DISTINCT FROM ARRAY['duplicate']::text[] THEN
    RAISE EXCEPTION 'T019c FAIL: 되돌리기 뒤 기존 검토 항목';
  END IF;
  BEGIN
    INSERT INTO public.festival_review_queue (festival_id, reason) VALUES ('fst_T19001', 'class_unverified');
    RAISE EXCEPTION 'T019c FAIL: 이전 사유 제약 복원 실패';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  RAISE NOTICE 'T019c PASS: 되돌리기 뒤 기존 검토 항목과 사유 제약 복원';
END $$;
\endif
ROLLBACK;
\endif
