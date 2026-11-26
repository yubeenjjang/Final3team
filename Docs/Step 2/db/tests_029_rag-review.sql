BEGIN;
INSERT INTO public.users (user_id, email, password_hash)
VALUES ('00000000-0000-0000-0000-00000000a029', 't029@example.test', '!');
INSERT INTO public.profiles (user_id, role) VALUES ('00000000-0000-0000-0000-00000000a029', 'operator');
INSERT INTO public.rag_documents (document_id, title, category, source_url, collected_at, checksum)
VALUES ('00000000-0000-0000-0000-00000000d029', '시험 안내', 'faq', 'https://example.test/t029', now(), 'c029');

\if :applied
SET LOCAL ROLE noldaga_service;
INSERT INTO public.rag_document_events (document_id, action, actor, checksum, reason)
VALUES ('00000000-0000-0000-0000-00000000d029', 'approve', '00000000-0000-0000-0000-00000000a029', 'c029', NULL);
RESET ROLE;
DO $$
BEGIN
  IF has_table_privilege('noldaga_service', 'public.rag_document_events', 'UPDATE')
     OR has_table_privilege('noldaga_service', 'public.rag_document_events', 'DELETE') THEN
    RAISE EXCEPTION 'T029a FAIL: 서비스 계정에 승인 이력 수정·삭제 권한이 있음';
  END IF;
  UPDATE public.rag_document_events SET reason = '변경' WHERE document_id = '00000000-0000-0000-0000-00000000d029';
  RAISE EXCEPTION 'T029a FAIL: 승인 이력 수정이 허용됨';
EXCEPTION WHEN raise_exception THEN
  IF SQLERRM LIKE 'T029a FAIL%' THEN RAISE; END IF;
  RAISE NOTICE 'T029a PASS: 승인 이력은 추가만 가능(서비스 계정 수정·삭제 권한 없음, 소유자 수정도 거부)';
END $$;
SET LOCAL ROLE noldaga_service;
DO $$
BEGIN
  INSERT INTO public.rag_document_events (document_id, action, actor, checksum)
  VALUES ('00000000-0000-0000-0000-00000000d029', 'reject', '00000000-0000-0000-0000-00000000a029', 'c029');
  RAISE EXCEPTION 'T029b FAIL: 사유 없는 반려 이력이 허용됨';
EXCEPTION WHEN check_violation THEN
  RAISE NOTICE 'T029b PASS: 반려 이력은 사유 필수';
END $$;
RESET ROLE;
DO $$
BEGIN
  IF has_table_privilege('noldaga_app', 'public.rag_document_events', 'SELECT')
     OR has_table_privilege('noldaga_app', 'public.rag_document_events', 'INSERT')
     OR has_table_privilege('noldaga_app', 'public.rag_documents', 'UPDATE')
     OR to_regclass('public.idx_rag_documents_approved_source') IS NULL THEN
    RAISE EXCEPTION 'T029c FAIL: 앱 계정 권한이 열렸거나 개정본 조회 인덱스 없음';
  END IF;
  RAISE NOTICE 'T029c PASS: 앱 계정은 승인 이력·문서 승인 쓰기 권한 없음, 개정본 조회 인덱스 있음';
END $$;
\else
DO $$
BEGIN
  IF to_regclass('public.rag_document_events') IS NOT NULL
     OR to_regclass('public.idx_rag_documents_approved_source') IS NOT NULL THEN
    RAISE EXCEPTION 'T029d FAIL: 되돌리기 후 승인 이력 테이블·인덱스가 남음';
  END IF;
  RAISE NOTICE 'T029d PASS: 되돌리기 후 승인 이력 테이블·인덱스 없음';
END $$;
\endif
ROLLBACK;
