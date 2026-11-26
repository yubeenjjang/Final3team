import { apiGet, apiPost } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ReturnRouteRequest = components["schemas"]["ReturnRouteRequest"];
export type RoutePreference = ReturnRouteRequest["route_preference"];

export const MOCK_SCENARIOS = [
  { value: "", label: "기본" },
  { value: "sync_ready", label: "즉시 완료" },
  { value: "async_unavailable", label: "경로 없음" },
  { value: "async_timeout", label: "시간 초과" },
  { value: "overloaded", label: "요청 과부하" },
] as const;

export type MockScenario = (typeof MOCK_SCENARIOS)[number]["value"];

export interface RouteAccess {
  id: string;
  token: string;
}

export function storeRouteAccess({ id, token }: RouteAccess): void {
  window.sessionStorage.setItem(`noldaga.return-route.${id}`, token);
}

export function readRouteAccess(id?: string): RouteAccess | undefined {
  const url = new URL(window.location.href);
  const legacyToken = url.searchParams.get("token");
  if (legacyToken !== null) {
    url.searchParams.delete("token");
    window.history.replaceState(null, "", url);
  }

  if (!id) return undefined;
  if (legacyToken) {
    const access = { id, token: legacyToken };
    try {
      storeRouteAccess(access);
    } catch {
      // Legacy links still work when tab storage is unavailable.
    }
    return access;
  }

  try {
    const token = window.sessionStorage.getItem(`noldaga.return-route.${id}`);
    return token ? { id, token } : undefined;
  } catch {
    return undefined;
  }
}

export type RoutePoint = [lat: number, lng: number];

export interface RouteLeg {
  mode: string;
  duration_min: number | null;
  line?: string | null;
  path?: RoutePoint[] | null;
}

export interface RouteCandidate {
  candidate_id: string;
  summary: string;
  duration_min: number | null;
  walk_m: number | null;
  transfers: number | null;
  fare_krw?: number | null;
  legs: RouteLeg[];
}

interface RouteEndpoint {
  name?: string | null;
  label?: string | null;
  lat?: number | null;
  lng?: number | null;
}

// A04/A05 leave response bodies untyped in the generated OpenAPI schema.
interface RouteResponse {
  route_request_id: string;
  notices?: string[];
}

export interface ReadyRoute extends RouteResponse {
  route_status: "ready";
  completed_valid_route: boolean;
  route_preference: RoutePreference;
  travel_mode: ReturnRouteRequest["travel_mode"];
  provider?: string | null;
  provider_tier?: string | null;
  origin: RouteEndpoint;
  destination: RouteEndpoint;
  route_candidates: RouteCandidate[];
}

interface PendingRoute extends RouteResponse {
  route_status: "queued" | "processing";
  retry_after_s?: number;
}

export interface FailedRoute extends RouteResponse {
  route_status: "unavailable" | "timed_out" | "rejected";
  error?: { message: string } | null;
}

export type RouteStatus = PendingRoute | ReadyRoute | FailedRoute;
type RouteSubmission = ReadyRoute | FailedRoute | (PendingRoute & { route_access_token: string });

export function submitReturnRoute(
  body: ReturnRouteRequest,
  scenario: MockScenario,
  signal: AbortSignal,
): Promise<RouteSubmission> {
  return apiPost<RouteSubmission>("/routes/return", body, {
    headers: scenario ? { "X-Mock-Scenario": scenario } : undefined,
    signal,
    timeoutMs: 10_000,
  });
}

export function getReturnRoute(access: RouteAccess, signal: AbortSignal): Promise<RouteStatus> {
  return apiGet<RouteStatus>(`/routes/return/${encodeURIComponent(access.id)}`, {
    headers: { "X-Route-Access-Token": access.token },
    signal,
    timeoutMs: 10_000,
    skipAuthRefresh: true,
  });
}
