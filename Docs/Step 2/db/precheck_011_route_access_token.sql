-- 011 적용 전 읽기 전용 검사. 기존 행 수만 출력한다.
-- 기존 요청은 보존되며, 011 A05 조회 대상에서 제외된다.
SELECT count(*) AS legacy_route_requests FROM public.route_requests;
