-- 028 다음에 파일 단위 트랜잭션으로 적용한다.
-- A83~A85 운영자 RAG 공식 문서 승인·반려와 개정본 대체 이력(W27 계약 3절).
-- 승인 쓰기는 API(운영자 인증) 뒤 noldaga_service만 한다. noldaga_app에는 권한을 주지 않는다.
CREATE TABLE public.rag_document_events (
  event_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  document_id  UUID NOT NULL REFERENCES public.rag_documents(document_id),
  action       TEXT NOT NULL CHECK (action IN ('approve','reject','supersede')),
  actor        UUID NOT NULL REFERENCES public.profiles(user_id),
  checksum     TEXT,
  before_value JSONB,
  after_value  JSONB,
  reason       TEXT CHECK (char_length(reason) <= 300),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (action <> 'reject' OR reason IS NOT NULL),
  CHECK (action = 'supersede' OR checksum IS NOT NULL)
);
CREATE INDEX idx_rag_document_events_document ON public.rag_document_events (document_id, created_at);
CREATE TRIGGER trg_rag_document_events_append_only BEFORE UPDATE OR DELETE ON public.rag_document_events
  FOR EACH ROW EXECUTE FUNCTION public.forbid_change();
ALTER TABLE public.rag_document_events ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT ON public.rag_document_events TO noldaga_service;

-- 같은 축제·원문 URL의 승인본을 찾는 개정본 대체 조회용
CREATE INDEX idx_rag_documents_approved_source ON public.rag_documents (festival_id, source_url)
  WHERE approval_status = 'approved';
