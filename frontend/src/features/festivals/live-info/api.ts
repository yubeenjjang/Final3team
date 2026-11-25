import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type CrowdArea = components["schemas"]["CrowdArea"];

export interface NearbyCrowdArea {
  area_code: string;
  area_name: string;
  distance_m: number;
  status: "ok" | "stale" | "unavailable";
  data?: CrowdArea | null;
  is_estimate?: boolean | null;
  error?: components["schemas"]["SourceError"] | null;
}

export type CrowdResponse = components["schemas"]["CrowdResponse"] & {
  nearby_areas?: NearbyCrowdArea[];
  is_estimate?: boolean | null;
  unsupported_reason?: string | null;
  source_url?: string;
};

export type WeatherResponse = components["schemas"]["WeatherResponse"];
export type NoticeResponse = components["schemas"]["NoticeResponse"];

/**
 * Fetch festival crowd status (A10).
 */
export function getFestivalCrowd(
  festivalId: string,
  signal?: AbortSignal,
): Promise<CrowdResponse> {
  return apiGet<CrowdResponse>(`/festivals/${encodeURIComponent(festivalId)}/crowd`, {
    signal,
  });
}

/**
 * Fetch festival weather info (A09).
 */
export function getFestivalWeather(
  festivalId: string,
  signal?: AbortSignal,
): Promise<WeatherResponse> {
  return apiGet<WeatherResponse>(
    `/festivals/${encodeURIComponent(festivalId)}/weather`,
    { signal },
  );
}

/**
 * Fetch festival operational/traffic notices (A07).
 */
export function getFestivalNotices(
  festivalId: string,
  signal?: AbortSignal,
): Promise<NoticeResponse> {
  return apiGet<NoticeResponse>(
    `/festivals/${encodeURIComponent(festivalId)}/notices`,
    { signal },
  );
}
