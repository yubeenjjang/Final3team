import { apiGet } from "@/lib/api/client";
import type { components, operations } from "@/lib/api/schema";

export type FestivalListItem = components["schemas"]["FestivalListItem"];
export type FestivalPage = components["schemas"]["FestivalPage"];
export type ListFestivalsQuery = NonNullable<
  operations["list_festivals_api_v1_festivals_get"]["parameters"]["query"]
>;

/** 기본 목록: 진행 중 + 예정 */
export const DEFAULT_STATUSES = "ongoing,upcoming";

/**
 * Fetch paginated festival list from A02.
 */
export function listFestivals(
  query: ListFestivalsQuery,
  signal?: AbortSignal,
): Promise<FestivalPage> {
  return apiGet<FestivalPage>("/festivals", {
    query: {
      region: query.region,
      q: query.q ?? undefined,
      // 상태를 고르지 않으면 끝난 축제는 빼고 진행 중·예정만 (A02 여러 상태 필터 I13)
      status: (query.status ?? DEFAULT_STATUSES) as ListFestivalsQuery["status"],
      sort: query.sort,
      page: query.page,
      page_size: query.page_size,
    },
    signal,
  });
}
