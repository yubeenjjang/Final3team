import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  updateAccessTokens,
} from "./auth";

const DEFAULT_API_BASE = "http://localhost:8000/api/v1";
const REQUEST_ID_ALPHABET =
  "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
const REQUEST_ID_LENGTH = 26;

export interface ApiErrorParams {
  status: number;
  code: string;
  message: string;
  requestId: string;
  retryable: boolean;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string;
  readonly retryable: boolean;

  constructor(params: ApiErrorParams) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.requestId = params.requestId;
    this.retryable = params.retryable;
  }
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  skipAuth?: boolean;
  skipAuthRefresh?: boolean;
}

let mockDataDetected = false;
const mockListeners = new Set<() => void>();

export function isMockDataDetected(): boolean {
  return mockDataDetected;
}

export function getMockDataServerSnapshot(): boolean {
  return false;
}

export function markMockDataDetected(): void {
  if (mockDataDetected) {
    return;
  }
  mockDataDetected = true;
  mockListeners.forEach((listener) => {
    listener();
  });
}

export function subscribeMockData(listener: () => void): () => void {
  mockListeners.add(listener);
  return () => {
    mockListeners.delete(listener);
  };
}

export function resetMockDataDetected(): void {
  if (!mockDataDetected) {
    return;
  }
  mockDataDetected = false;
  mockListeners.forEach((listener) => {
    listener();
  });
}

export function getApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE;
  if (configured && configured.trim().length > 0) {
    return configured.trim().replace(/\/+$/, "");
  }
  return DEFAULT_API_BASE;
}

export function createRequestId(): string {
  const bytes = new Uint8Array(REQUEST_ID_LENGTH);
  if (typeof globalThis.crypto !== "undefined" && globalThis.crypto.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < REQUEST_ID_LENGTH; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }

  let suffix = "";
  for (let i = 0; i < REQUEST_ID_LENGTH; i += 1) {
    suffix += REQUEST_ID_ALPHABET[bytes[i] % REQUEST_ID_ALPHABET.length];
  }
  return `req_${suffix}`;
}

function buildUrl(
  path: string,
  query?: Record<string, string | number | boolean | null | undefined>,
): string {
  const base = getApiBase();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${normalizedPath}`;

  if (!query) {
    return url;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }

  const serialized = params.toString();
  return serialized ? `${url}?${serialized}` : url;
}

interface RawErrorEnvelope {
  error?: {
    code?: unknown;
    message?: unknown;
    request_id?: unknown;
    retryable?: unknown;
  };
  detail?: unknown;
}

function toApiError(
  status: number,
  body: unknown,
  fallbackRequestId: string,
): ApiError {
  if (body && typeof body === "object") {
    const envelope = body as RawErrorEnvelope;
    if (envelope.error && typeof envelope.error === "object") {
      const err = envelope.error;
      return new ApiError({
        status,
        code: typeof err.code === "string" ? err.code : "HTTP_ERROR",
        message:
          typeof err.message === "string"
            ? err.message
            : "요청 처리에 실패했어요",
        requestId:
          typeof err.request_id === "string"
            ? err.request_id
            : fallbackRequestId,
        retryable: Boolean(err.retryable),
      });
    }

    if (status === 422 && "detail" in envelope) {
      let detailMessage = "입력값을 확인해 주세요";
      if (typeof envelope.detail === "string") {
        detailMessage = envelope.detail;
      } else if (
        Array.isArray(envelope.detail) &&
        envelope.detail.length > 0 &&
        typeof envelope.detail[0]?.msg === "string"
      ) {
        detailMessage = envelope.detail[0].msg;
      }
      return new ApiError({
        status,
        code: "VALIDATION_ERROR",
        message: detailMessage,
        requestId: fallbackRequestId,
        retryable: false,
      });
    }
  }

  return new ApiError({
    status,
    code: "HTTP_ERROR",
    message: "요청 처리에 실패했어요",
    requestId: fallbackRequestId,
    retryable: status >= 500,
  });
}

let activeRefreshPromise: Promise<boolean> | null = null;

async function tryRefreshTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }

  if (activeRefreshPromise) {
    return activeRefreshPromise;
  }

  activeRefreshPromise = (async () => {
    try {
      const response = await fetch(buildUrl("/auth/refresh"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": createRequestId(),
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        clearAuthSession();
        return false;
      }

      const data = (await response.json()) as Record<string, unknown>;
      if (data.is_mock === true) {
        markMockDataDetected();
      }

      const newAccess =
        typeof data.access_token === "string" ? data.access_token : null;
      const newRefresh =
        typeof data.refresh_token === "string" ? data.refresh_token : undefined;

      if (!newAccess) {
        clearAuthSession();
        return false;
      }

      updateAccessTokens({
        accessToken: newAccess,
        refreshToken: newRefresh,
      });
      return true;
    } catch {
      clearAuthSession();
      return false;
    } finally {
      activeRefreshPromise = null;
    }
  })();

  return activeRefreshPromise;
}

export async function apiFetch<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    query,
    body,
    headers: customHeaders,
    signal,
    skipAuth = false,
    skipAuthRefresh = false,
  } = options;

  const requestId = createRequestId();
  const headers = new Headers(customHeaders);
  headers.set("X-Request-ID", requestId);

  if (body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!skipAuth && !headers.has("Authorization")) {
    const token = getAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const url = buildUrl(path, query);
  let response: Response;

  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (
      signal?.aborted ||
      (error instanceof Error && error.name === "AbortError")
    ) {
      throw error;
    }
    throw new ApiError({
      status: 0,
      code: "NETWORK_ERROR",
      message: "서버에 연결할 수 없어요",
      requestId,
      retryable: true,
    });
  }

  const isAuthEndpoint =
    path.startsWith("/auth/refresh") || path.startsWith("/auth/login");

  if (
    response.status === 401 &&
    !skipAuth &&
    !skipAuthRefresh &&
    !isAuthEndpoint &&
    getRefreshToken()
  ) {
    const refreshed = await tryRefreshTokens();
    if (refreshed) {
      return apiFetch<T>(path, {
        ...options,
        skipAuthRefresh: true,
      });
    }
  }

  if (!response.ok) {
    let errorBody: unknown = null;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = null;
    }
    const headerRequestId = response.headers.get("X-Request-ID") ?? requestId;
    throw toApiError(response.status, errorBody, headerRequestId);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = (await response.json()) as T;
  if (
    data &&
    typeof data === "object" &&
    "is_mock" in data &&
    (data as Record<string, unknown>).is_mock === true
  ) {
    markMockDataDetected();
  }

  return data;
}

export function apiGet<T>(
  path: string,
  options?: Omit<ApiRequestOptions, "method" | "body">,
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: "GET" });
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  options?: Omit<ApiRequestOptions, "method" | "body">,
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: "POST", body });
}

export function apiPut<T>(
  path: string,
  body?: unknown,
  options?: Omit<ApiRequestOptions, "method" | "body">,
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: "PUT", body });
}

export function apiDelete<T = void>(
  path: string,
  options?: Omit<ApiRequestOptions, "method">,
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: "DELETE" });
}
