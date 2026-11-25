ALTER TABLE public.route_results
  DROP CONSTRAINT route_results_cache_key_fkey,
  ADD CONSTRAINT route_results_cache_key_fkey
    FOREIGN KEY (cache_key) REFERENCES public.route_cache_entries(cache_key);

DROP INDEX public.idx_route_results_cache_key;
