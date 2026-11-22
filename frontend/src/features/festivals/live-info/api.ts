import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type CrowdResponse = components["schemas"]["CrowdResponse"];
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
