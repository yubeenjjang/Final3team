import { apiGet, apiPost } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { MOCK_FESTIVALS } from "../explore/mockFestivals";

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

function getMockFestivalDetail(festivalId: string): FestivalDetail | null {
  const festival = MOCK_FESTIVALS.find(
    (item) => item.festival_id === festivalId,
  );

  if (!festival) return null;

  return {
    ...festival,
    is_mock: true,
    address: festival.venue_name,
    overview: `${festival.name}에서 즐거운 축제의 순간을 만나보세요. 다채로운 볼거리와 즐길 거리가 준비되어 있습니다.`,
    fee_text: "무료",
    homepage_url: null,
    image_url: festival.thumbnail_url,
    image_copyright: null,
    source_ref: festival.festival_id,
  };
}

/**
 * Fetch single festival detail (A03).
 */
export function getFestivalDetail(
  festivalId: string,
  signal?: AbortSignal,
): Promise<FestivalDetail> {
  if (process.env.NEXT_PUBLIC_USE_MOCK_FESTIVALS === "1") {
    const mockFestival = getMockFestivalDetail(festivalId);
    if (mockFestival) return Promise.resolve(mockFestival);
  }

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
