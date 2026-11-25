import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "./auth";
import {
  ApiError,
  apiGet,
  createRequestId,
  isMockDataDetected,
  resetMockDataDetected,
} from "./client";

describe("F4 API client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    resetAuthStateForTest();
    resetMockDataDetected();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("F4 returns parsed JSON body on 200 and sends valid X-Request-ID header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", is_mock: false }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await apiGet<{ status: string; is_mock: boolean }>("/health");

    expect(result).toEqual({ status: "ok", is_mock: false });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [calledUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toBe("http://localhost:8000/api/v1/health");
    const headers = new Headers(init.headers);
    expect(headers.get("X-Request-ID")).toMatch(/^req_[0-9A-Za-z]{26}$/);
    expect(isMockDataDetected()).toBe(false);
  });

  it("F4 throws ApiError with VALIDATION_ERROR and server message on 422", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "VALIDATION_ERROR",
            message: "축제 ID 형식이 올바르지 않아요",
            request_id: "req_12345678901234567890123456",
            retryable: false,
          },
        }),
        {
          status: 422,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(apiGet("/festivals/bad-id")).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      code: "VALIDATION_ERROR",
      message: "축제 ID 형식이 올바르지 않아요",
      requestId: "req_12345678901234567890123456",
      retryable: false,
    });
  });

  it("F4 throws NETWORK_ERROR when fetch fails", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await apiGet("/health");
      expect.unreachable("should have thrown ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.code).toBe("NETWORK_ERROR");
      expect(apiError.message).toBe("서버에 연결할 수 없어요");
      expect(apiError.status).toBe(0);
      expect(apiError.retryable).toBe(true);
      expect(apiError.requestId).toMatch(/^req_[0-9A-Za-z]{26}$/);
    }
  });

  it("F4 automatically adds Authorization Bearer header when logged in", async () => {
    setAuthSession({
      accessToken: "sample-access-value",
      refreshToken: "sample-refresh-value",
      user: { userId: "usr_1", displayName: "테스터" },
    });

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], is_mock: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await apiGet("/me/favorites");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer sample-access-value");
    expect(isMockDataDetected()).toBe(true);
  });

  it("F4 createRequestId always matches ^req_[0-9A-Za-z]{26}$", () => {
    for (let i = 0; i < 10; i += 1) {
      expect(createRequestId()).toMatch(/^req_[0-9A-Za-z]{26}$/);
    }
  });
});
