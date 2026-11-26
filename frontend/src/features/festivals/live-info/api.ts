import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export interface CrowdGeoPoint {
  lat: number;
  lng: number;
}

export type CrowdArea = components["schemas"]["CrowdArea"] & {
  center?: CrowdGeoPoint | null;
  boundary?: CrowdGeoPoint[][] | null;
};

export interface NearbyCrowdArea {
  area_code: string;
  area_name: string;
  distance_m: number;
  status: "ok" | "stale" | "unavailable";
  data?: CrowdArea | null;
  is_estimate?: boolean | null;
  error?: components["schemas"]["SourceError"] | null;
  center?: CrowdGeoPoint | null;
  boundary?: CrowdGeoPoint[][] | null;
}

export type CrowdResponse = Omit<components["schemas"]["CrowdResponse"], "areas"> & {
  areas?: CrowdArea[];
  nearby_areas?: NearbyCrowdArea[];
  is_estimate?: boolean | null;
  unsupported_reason?: string | null;
  source_url?: string;
};

export type WeatherResponse = components["schemas"]["WeatherResponse"];
export type NoticeResponse = components["schemas"]["NoticeResponse"];

export interface TransitArrival {
  line: string;
  direction?: string | null;
  eta_s?: number | null;
  message?: string | null;
  remaining_stops?: number | null;
  crowding?: "여유" | "보통" | "혼잡" | "unverified" | null;
}

export interface TransitStation {
  type: "subway" | "bus";
  station_id: string;
  name: string;
  lat: number;
  lng: number;
  distance_m: number;
  status: "ok" | "stale" | "unavailable" | "unsupported" | "unverified";
  arrivals: TransitArrival[];
  observed_at?: string | null;
}

export interface TransitResponse {
  is_mock: boolean;
  festival_id: string;
  status: "ok" | "stale" | "unavailable" | "unsupported" | "unverified";
  stations: TransitStation[];
  error?: components["schemas"]["SourceError"] | null;
}

/**
 * Fetch festival crowd status (A10).
 */
export function getFestivalCrowd(
  festivalId: string,
  signal?: AbortSignal,
): Promise<CrowdResponse> {
  return apiGet<CrowdResponse>(`/festivals/${encodeURIComponent(festivalId)}/crowd`, {
    signal,
    timeoutMs: 12_000,
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

/** Fetch nearby bus and subway realtime arrivals (A26). */
export function getFestivalTransit(
  festivalId: string,
  signal?: AbortSignal,
): Promise<TransitResponse> {
  if (
    process.env.NEXT_PUBLIC_USE_MOCK_FESTIVALS === "1" &&
    festivalId.startsWith("fst_design_")
  ) {
    return Promise.resolve({
      is_mock: true,
      festival_id: festivalId,
      status: "ok",
      stations: [
        {
          type: "bus",
          station_id: `${festivalId}-bus`,
          name: "축제장 인근 정류장",
          lat: 0,
          lng: 0,
          distance_m: 180,
          status: "ok",
          arrivals: [
            { line: "700번", direction: "축제장 방면", eta_s: 240 },
            { line: "9709번", direction: "시내 방면", eta_s: 660 },
          ],
        },
      ],
    });
  }

  return apiGet<TransitResponse>(
    `/festivals/${encodeURIComponent(festivalId)}/transit`,
    { query: { mode: "all", radius_m: 500, limit: 6 }, signal },
  );
}
