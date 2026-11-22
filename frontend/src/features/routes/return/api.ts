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

export type RoutePoint = [lat: number, lng: number];

export interface RouteLeg {
  mode: string;
  duration_min: number;
  line?: string | null;
  path?: RoutePoint[] | null;
}

export interface RouteCandidate {
  candidate_id: string;
  summary: string;
  duration_min: number;
  walk_m: number;
  transfers: number;
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
  origin: RouteEndpoint;
  destination: RouteEndpoint;
  route_candidates: RouteCandidate[];
}

interface PendingRoute extends RouteResponse {
  route_status: "queued" | "processing";
  retry_after_s?: number;
}

interface FailedRoute extends RouteResponse {
  route_status: "unavailable" | "timed_out" | "rejected";
  error?: { message: string } | null;
}

export type RouteStatus = PendingRoute | ReadyRoute | FailedRoute;
type RouteSubmission = ReadyRoute | (PendingRoute & { route_access_token: string });

export function submitReturnRoute(
  body: ReturnRouteRequest,
  scenario: MockScenario,
  signal: AbortSignal,
): Promise<RouteSubmission> {
  return apiPost<RouteSubmission>("/routes/return", body, {
    headers: scenario ? { "X-Mock-Scenario": scenario } : undefined,
    signal,
  });
}

export function getReturnRoute(access: RouteAccess, signal: AbortSignal): Promise<RouteStatus> {
  return apiGet<RouteStatus>(`/routes/return/${encodeURIComponent(access.id)}`, {
    headers: { "X-Route-Access-Token": access.token },
    signal,
    skipAuthRefresh: true,
  });
}
