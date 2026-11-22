import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetMockDataDetected } from "@/lib/api/client";
import { MockBadge } from "@/components/MockBadge";
import { KakaoMap } from "@/components/KakaoMap";
import { ReturnRouteView } from "./ReturnRouteView";
import type { ReadyRoute, ReturnRouteRequest } from "./api";

vi.mock("@/components/KakaoMap", () => ({ KakaoMap: vi.fn(() => null) }));

const FESTIVAL = {
  festival_id: "fst_000001", name: "광화문 겨울빛 축제", venue_name: "광화문광장", lat: 37.5759, lng: 126.9768, is_mock: true,
};
const ACCESS = { id: "rr_route01", token: "rrt_test" };
const QUEUED = {
  route_request_id: ACCESS.id, route_status: "queued", route_access_token: ACCESS.token, retry_after_s: 2, is_mock: true,
};
const NOTICE = "공식 교통통제 반영 여부를 확인하지 못했어요.";
const ROUTE = {
  route_request_id: ACCESS.id,
  route_status: "ready",
  completed_valid_route: true,
  route_preference: "fastest",
  travel_mode: "transit",
  origin: { name: FESTIVAL.venue_name, lat: FESTIVAL.lat, lng: FESTIVAL.lng },
  destination: { label: "서울역" },
  route_candidates: [{
    candidate_id: "c1", summary: "지하철 1회 환승(모의)", duration_min: 38, walk_m: 650, transfers: 1,
    legs: [
      { mode: "walk", duration_min: 6, path: [[37.5759, 126.9768], [37.572, 126.979]] },
      { mode: "subway", duration_min: 24, line: "(모의)", path: [[37.572, 126.979], [37.5641, 126.9839]] },
    ],
  }],
  notices: [NOTICE],
  is_mock: true,
} satisfies ReadyRoute & { is_mock: boolean };
const fetchApi = vi.fn<typeof fetch>();
const map = vi.mocked(KakaoMap);

function reply(body: unknown, status = 200) {
  fetchApi.mockResolvedValueOnce(Response.json(body, { status }));
}

async function flush(ms = 0) {
  await act(async () => vi.advanceTimersByTimeAsync(ms));
}

async function openWithFestival() {
  reply(FESTIVAL);
  const rendered = render(<><ReturnRouteView festivalId={FESTIVAL.festival_id} /><MockBadge /></>);
  await flush();
  fireEvent.change(screen.getByLabelText("도착지"), { target: { value: "서울역" } });
  return rendered;
}

function findRoute() {
  fireEvent.click(screen.getByRole("button", { name: "집으로 가는 길 찾기" }));
}

function submittedRequest(callIndex: number) {
  return JSON.parse(String(fetchApi.mock.calls[callIndex]?.[1]?.body)) as ReturnRouteRequest;
}

describe("F8 return route flow", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", fetchApi);
    vi.stubEnv("NEXT_PUBLIC_API_BASE", "http://localhost:8000/api/v1");
    vi.stubEnv("NEXT_PUBLIC_SHOW_MOCK_TOOLS", "0");
    fetchApi.mockReset();
    map.mockClear();
    resetMockDataDetected();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("prefills the festival and renders the 38-minute result after polling", async () => {
    await openWithFestival();
    expect(screen.getByText(FESTIVAL.name)).toBeInTheDocument();
    expect(screen.queryByLabelText("시나리오")).not.toBeInTheDocument();
    expect(screen.queryByText("38분")).not.toBeInTheDocument();
    reply(QUEUED, 202);
    reply({ route_request_id: ACCESS.id, route_status: "processing", retry_after_s: 2 });
    reply(ROUTE);

    findRoute();
    await flush();
    expect(screen.getByText(/아직 확정된 경로가 아니에요/)).toHaveAttribute("role", "status");
    expect(submittedRequest(1)).toMatchObject({
      request_id: expect.stringMatching(/^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/),
      festival_id: FESTIVAL.festival_id,
      origin: { type: "festival" },
      destination: { type: "place", query: "서울역" },
      route_preference: "fastest",
    });
    expect(new Headers(fetchApi.mock.calls[1][1]?.headers).has("X-Mock-Scenario")).toBe(false);

    await flush(4000);

    expect(fetchApi).toHaveBeenCalledTimes(4);
    expect(fetchApi.mock.calls[2][0]).toBe(`http://localhost:8000/api/v1/routes/return/${ACCESS.id}`);
    expect(new Headers(fetchApi.mock.calls[2][1]?.headers).get("X-Route-Access-Token")).toBe(ACCESS.token);
    const card = screen.getByRole("button", { name: /38분/ });
    for (const label of ["추천", "도보 650m", "환승 1회", "지하철 (모의)"]) {
      expect(within(card).getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByRole("list", { name: "경로 안내" })).toHaveTextContent(NOTICE);
    expect(screen.getByText("모의 데이터")).toBeInTheDocument();
    expect(map.mock.lastCall?.[0]).toMatchObject({
      polylines: ROUTE.route_candidates[0].legs.map((leg) => leg.path),
      markers: [
        { lat: FESTIVAL.lat, lng: FESTIVAL.lng, title: `출발 · ${FESTIVAL.venue_name}` },
        { lat: 37.5641, lng: 126.9839, title: "도착 · 서울역" },
      ],
    });
  });

  it("searches and selects a festival, submits a custom origin and opens the sync result", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_MOCK_TOOLS", "1");
    render(<ReturnRouteView />);
    fireEvent.click(screen.getByRole("button", { name: /축제 검색 및 선택/ }));
    fireEvent.change(screen.getByRole("searchbox", { name: "축제 검색" }), { target: { value: "겨울빛" } });
    reply({ items: [FESTIVAL], total: 1, is_mock: true });
    await flush(250);
    expect(new URL(String(fetchApi.mock.calls[0][0])).searchParams.get("q")).toBe("겨울빛");
    fireEvent.click(screen.getByRole("button", { name: new RegExp(FESTIVAL.name) }));
    fireEvent.change(screen.getByLabelText("출발지"), { target: { value: "place" } });
    fireEvent.change(screen.getByLabelText("출발 장소"), { target: { value: "시청역" } });
    fireEvent.change(screen.getByLabelText("도착지"), { target: { value: "서울역" } });
    fireEvent.click(screen.getByLabelText("도보 최소"));
    fireEvent.change(screen.getByLabelText("시나리오"), { target: { value: "sync_ready" } });
    reply({ ...ROUTE, route_preference: "min_walk" });

    findRoute();
    await flush(5000);

    expect(fetchApi).toHaveBeenCalledTimes(2);
    expect(submittedRequest(1)).toMatchObject({
      festival_id: FESTIVAL.festival_id, origin: { type: "place", query: "시청역" }, route_preference: "min_walk",
    });
    expect(new Headers(fetchApi.mock.calls[1][1]?.headers).get("X-Mock-Scenario")).toBe("sync_ready");
    expect(screen.getByRole("button", { name: /38분/ })).toBeInTheDocument();
  });

  it.each([
    ["async_timeout", "timed_out", "경로를 찾는 시간이 초과됐어요."],
    ["async_unavailable", "unavailable", "경로 정보를 가져오지 못했어요."],
  ])("shows %s and retries with a new request ID", async (scenario, status, message) => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_MOCK_TOOLS", "1");
    await openWithFestival();
    fireEvent.change(screen.getByLabelText("시나리오"), { target: { value: scenario } });
    reply(QUEUED, 202);
    reply({ ...QUEUED, route_status: "processing" });
    reply({ route_status: status, error: { message }, notices: [NOTICE] });

    findRoute();
    await flush(4000);

    expect(new Headers(fetchApi.mock.calls[1][1]?.headers).get("X-Mock-Scenario")).toBe(scenario);
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("list", { name: "경로 안내" })).toHaveTextContent(NOTICE);
    expect(screen.getByLabelText("도착지")).toHaveValue("서울역");
    reply(ROUTE);
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await flush();
    expect(submittedRequest(4).request_id).not.toBe(submittedRequest(1).request_id);
    expect(screen.getByRole("button", { name: /38분/ })).toBeInTheDocument();
  });

  it.each([400, 404, 422, 503])("keeps the inputs and shows the error on HTTP %s", async (status) => {
    await openWithFestival();
    const code = status === 503 ? "ROUTE_OVERLOADED" : "INVALID";
    const message = "입력한 위치를 확인해 주세요.";
    reply({ error: { code, message } }, status);
    findRoute();
    await flush();

    expect(screen.getByRole("alert")).toHaveTextContent(status === 503 ? "요청이 많아요. 잠시 뒤 다시 시도해 주세요" : message);
    expect(screen.getByLabelText("도착지")).toHaveValue("서울역");
    expect(screen.getByText(FESTIVAL.name)).toBeInTheDocument();
  });

  it("shows a retry action after five pending lookups", async () => {
    await openWithFestival();
    reply(QUEUED, 202);
    for (let index = 0; index < 5; index += 1) reply({ ...QUEUED, route_status: "processing" });
    findRoute();
    await flush(20_000);

    expect(fetchApi).toHaveBeenCalledTimes(7);
    expect(screen.getByRole("alert")).toHaveTextContent("지금은 확인할 수 없어요");
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });

  it("opens an assistant route link with an immediate GET and updates the selected path", async () => {
    const first = ROUTE.route_candidates[0];
    const second = {
      ...first,
      candidate_id: "c2",
      summary: "다른 경로",
      legs: [{ mode: "bus", duration_min: 40, path: [[37.5759, 126.9768], [37.57, 126.98]] }],
    } satisfies (typeof ROUTE)["route_candidates"][number];
    reply({ ...ROUTE, route_candidates: [first, second] });
    render(<ReturnRouteView directRoute={ACCESS} />);
    await flush();

    expect(fetchApi).toHaveBeenCalledTimes(1);
    const [url, options] = fetchApi.mock.calls[0];
    expect(url).toBe(`http://localhost:8000/api/v1/routes/return/${ACCESS.id}`);
    expect(options?.method).toBe("GET");
    expect(new Headers(options?.headers).get("X-Route-Access-Token")).toBe(ACCESS.token);
    const card = screen.getByRole("button", { name: /다른 경로/, pressed: false });
    fireEvent.click(card);
    expect(card).toHaveAttribute("aria-pressed", "true");
    expect(map.mock.lastCall?.[0].polylines).toEqual(second.legs.map((leg) => leg.path));
  });

  it("stops lookups when leaving the page", async () => {
    const { unmount } = await openWithFestival();
    reply(QUEUED, 202);
    reply({ ...QUEUED, route_status: "processing" });
    findRoute();
    await flush(2000);
    const signal = fetchApi.mock.calls[2][1]?.signal;

    unmount();
    await flush(20_000);

    expect(signal?.aborted).toBe(true);
    expect(fetchApi).toHaveBeenCalledTimes(3);
  });
});
