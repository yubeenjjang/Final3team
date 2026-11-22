import { apiGet, apiPost, createRequestId } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import type { RouteAccess } from "@/features/routes/return/api";

type AssistantRequest = components["schemas"]["AssistantRequest"];
interface AssistantSubmission {
  run_id: string;
  run_access_token: string;
}

interface AssistantRun {
  run_status?: "queued" | "running" | "succeeded" | "failed";
  status?: AssistantRun["run_status"];
  answer?: string | null;
  reply?: string;
  message?: string;
  route_request_id?: string | null;
  route_access_token?: string | null;
  error?: { message?: string } | null;
}

export interface AssistantAnswer {
  text: string;
  route?: RouteAccess;
}

function waitForNextPoll(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", cancel);
      resolve();
    }, 1000);

    function cancel() {
      clearTimeout(timer);
      reject(signal.reason);
    }

    signal.addEventListener("abort", cancel, { once: true });
  });
}

export async function askAssistant(
  message: string,
  festivalId: string | undefined,
  signal: AbortSignal,
): Promise<AssistantAnswer> {
  const request: AssistantRequest = {
    request_id: createRequestId(),
    message,
    context: festivalId ? { festival_id: festivalId } : undefined,
  };
  const { run_id, run_access_token } = await apiPost<AssistantSubmission>(
    "/assistant/query", request, { signal },
  );

  for (let attempt = 0; attempt < 10; attempt += 1) {
    await waitForNextPoll(signal);
    const run = await apiGet<AssistantRun>(`/assistant/runs/${encodeURIComponent(run_id)}`, {
      headers: { "X-Run-Access-Token": run_access_token },
      signal,
      skipAuthRefresh: true,
    });
    const status = run.run_status ?? run.status;
    if (status === "failed") {
      throw new Error(run.error?.message ?? "답변을 생성하지 못했어요.");
    }
    if (status === "succeeded") {
      return {
        text: run.answer ?? run.reply ?? run.message ?? "답변을 확인했어요.",
        route: run.route_request_id && run.route_access_token
          ? { id: run.route_request_id, token: run.route_access_token }
          : undefined,
      };
    }
  }

  throw new Error("응답이 지연되고 있어요. 잠시 후 다시 물어봐 주세요.");
}
