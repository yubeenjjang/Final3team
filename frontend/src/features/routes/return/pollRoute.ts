import { getReturnRoute, type RouteAccess, type RouteStatus } from "./api";

const DEFAULT_RETRY_SECONDS = 2;
const MAX_ATTEMPTS = 5;

function wait(seconds: number, signal: AbortSignal): Promise<void> {
  signal.throwIfAborted();
  if (seconds === 0) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    function abort() {
      clearTimeout(timer);
      reject(signal.reason);
    }

    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, seconds * 1000);

    signal.addEventListener("abort", abort, { once: true });
  });
}

export async function pollRoute(
  access: RouteAccess,
  signal: AbortSignal,
  initialDelaySeconds = DEFAULT_RETRY_SECONDS,
) {
  let delay = initialDelaySeconds;
  let notices: RouteStatus["notices"];

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    await wait(delay, signal);
    signal.throwIfAborted();
    const response = await getReturnRoute(access, signal);
    signal.throwIfAborted();

    if (response.route_status !== "queued" && response.route_status !== "processing") {
      return { type: "finished", response } as const;
    }

    notices = response.notices ?? notices;
    delay = response.retry_after_s ?? DEFAULT_RETRY_SECONDS;
  }

  return { type: "unconfirmed", notices } as const;
}
