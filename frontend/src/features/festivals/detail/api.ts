import { apiGet, apiPost } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type FestivalDetail = components["schemas"]["FestivalDetail"];
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
