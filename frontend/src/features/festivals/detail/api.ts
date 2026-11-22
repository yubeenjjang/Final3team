import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type FestivalDetail = components["schemas"]["FestivalDetail"];
export type FavoriteSave = components["schemas"]["FavoriteSave"];
export type FavoritesPage = components["schemas"]["FavoritesPage"];
export type AssistantRequest = components["schemas"]["AssistantRequest"];

export interface AssistantRunSubmitResult {
  run_id: string;
  run_access_token: string;
  status?: string;
}

export interface AssistantRunStatusResult {
  run_id?: string;
  status: "queued" | "running" | "succeeded" | "failed" | string;
  answer?: string;
  reply?: string;
  message?: string;
  route_request_id?: string | null;
  route_access_token?: string | null;
  error?: {
    message?: string;
  } | null;
}

/**
 * Fetch single festival detail (A03).
 */
export function getFestivalDetail(
  festivalId: string,
  signal?: AbortSignal,
): Promise<FestivalDetail> {
  return apiGet<FestivalDetail>(`/festivals/${encodeURIComponent(festivalId)}`, {
    signal,
  });
}

/**
 * Fetch user's favorite festivals (A12 list).
 */
export function listMyFavorites(
  signal?: AbortSignal,
): Promise<FavoritesPage> {
  return apiGet<FavoritesPage>("/me/favorites", {
    query: { page: 1, page_size: 100 },
    signal,
  });
}

/**
 * Save a festival as favorite (A12).
 */
export function saveFavorite(festivalId: string): Promise<FavoriteSave> {
  return apiPut<FavoriteSave>(`/me/favorites/${encodeURIComponent(festivalId)}`);
}

/**
 * Remove a festival from favorites (A13).
 */
export function deleteFavorite(festivalId: string): Promise<void> {
  return apiDelete<void>(`/me/favorites/${encodeURIComponent(festivalId)}`);
}

/**
 * Submit an assistant query scoped to a festival (A06).
 */
export function submitFestivalAssistantQuery(
  body: AssistantRequest,
  signal?: AbortSignal,
): Promise<AssistantRunSubmitResult> {
  return apiPost<AssistantRunSubmitResult>("/assistant/query", body, { signal });
}

/**
 * Poll assistant run status (A06).
 */
export function fetchAssistantRunStatus(
  runId: string,
  runAccessToken: string,
  signal?: AbortSignal,
): Promise<AssistantRunStatusResult> {
  return apiGet<AssistantRunStatusResult>(
    `/assistant/runs/${encodeURIComponent(runId)}`,
    {
      headers: {
        "X-Run-Access-Token": runAccessToken,
      },
      signal,
    },
  );
}
