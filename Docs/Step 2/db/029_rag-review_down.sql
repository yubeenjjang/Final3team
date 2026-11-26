-- 승인·반려 감사 이력을 버리지 않도록 이력이 없을 때만 되돌린다.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.rag_document_events) THEN
    RAISE EXCEPTION '029_rag-review: 보존해야 하는 RAG 문서 승인 이력이 있습니다';
  END IF;
END;
$$;

DROP INDEX public.idx_rag_documents_approved_source;
DROP TABLE public.rag_document_events;
