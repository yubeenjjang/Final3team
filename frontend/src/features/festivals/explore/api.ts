import { apiGet } from "@/lib/api/client";
import type { components, operations } from "@/lib/api/schema";

export type FestivalListItem = components["schemas"]["FestivalListItem"];
export type FestivalPage = components["schemas"]["FestivalPage"];
export type ListFestivalsQuery = NonNullable<
  operations["list_festivals_api_v1_festivals_get"]["parameters"]["query"]
>;

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
      status: query.status ?? undefined,
      sort: query.sort,
      page: query.page,
      page_size: query.page_size,
    },
    signal,
  });
}
