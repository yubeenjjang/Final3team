import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getReturnRoute } from "./api";
import { pollRoute } from "./pollRoute";

vi.mock("./api", () => ({ getReturnRoute: vi.fn() }));

const fetchStatus = vi.mocked(getReturnRoute);
const access = { id: "rr_test01", token: "rrt_test" };
const processing = { route_request_id: access.id, route_status: "processing", retry_after_s: 2 } as const;
const ready = {
  route_request_id: access.id,
  route_status: "ready",
  completed_valid_route: true,
  route_preference: "fastest",
  travel_mode: "transit",
  origin: {},
  destination: {},
  route_candidates: [],
} as const;

describe("F8 pollRoute", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fetchStatus.mockReset();
  });

  afterEach(() => vi.useRealTimers());

  it("waits for retry_after_s and stops after processing then ready", async () => {
    fetchStatus.mockResolvedValueOnce({ ...processing, retry_after_s: 3 });
    fetchStatus.mockResolvedValueOnce({ ...ready, route_candidates: [] });
    const { signal } = new AbortController();
    const result = pollRoute(access, signal);

    await vi.advanceTimersByTimeAsync(1999);
    expect(fetchStatus).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchStatus).toHaveBeenCalledExactlyOnceWith(access, signal);
    await vi.advanceTimersByTimeAsync(2999);
    expect(fetchStatus).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1001);

    await expect(result).resolves.toEqual({ type: "finished", response: ready });
    expect(fetchStatus).toHaveBeenCalledTimes(2);
  });

  it("returns unconfirmed after five processing responses", async () => {
    fetchStatus.mockResolvedValue(processing);
    const result = pollRoute(access, new AbortController().signal);

    await vi.advanceTimersByTimeAsync(20_000);

    await expect(result).resolves.toMatchObject({ type: "unconfirmed" });
    expect(fetchStatus).toHaveBeenCalledTimes(5);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("cancels the scheduled lookup on abort", async () => {
    fetchStatus.mockResolvedValue(processing);
    const controller = new AbortController();
    const result = pollRoute(access, controller.signal);
    const aborted = expect(result).rejects.toMatchObject({ name: "AbortError" });

    await vi.advanceTimersByTimeAsync(2000);
    controller.abort();
    await aborted;
    await vi.runAllTimersAsync();

    expect(fetchStatus).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("does not schedule a new lookup when an in-flight response finishes after abort", async () => {
    const controller = new AbortController();
    fetchStatus.mockImplementationOnce(async () => {
      controller.abort();
      return processing;
    });
    const result = pollRoute(access, controller.signal, 0);

    await expect(result).rejects.toMatchObject({ name: "AbortError" });
    expect(fetchStatus).toHaveBeenCalledExactlyOnceWith(access, controller.signal);
    expect(vi.getTimerCount()).toBe(0);
  });
});
