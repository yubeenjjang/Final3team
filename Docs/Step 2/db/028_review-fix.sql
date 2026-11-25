-- Cache metadata expires independently of the referencing route result.
ALTER TABLE public.route_results
  DROP CONSTRAINT route_results_cache_key_fkey,
  ADD CONSTRAINT route_results_cache_key_fkey
    FOREIGN KEY (cache_key) REFERENCES public.route_cache_entries(cache_key) ON DELETE SET NULL;

CREATE INDEX idx_route_results_cache_key ON public.route_results (cache_key)
  WHERE cache_key IS NOT NULL;
