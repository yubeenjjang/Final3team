import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import ReturnRoutePage from "@/app/routes/return/page";
import { FestivalAiPrompt } from "@/features/festivals/detail/FestivalAiPrompt";
import { AssistantPrompt } from "./AssistantPrompt";

vi.mock("@/components/KakaoMap", () => ({ KakaoMap: () => null }));

const fetchApi = vi.fn<typeof fetch>();
const run = {
  run_id: "run_test01",
  conversation_id: "cv_test01",
  run_access_token: "fixture-run-token",
};
const route = { route_request_id: "rr_test01", route_access_token: "fixture-route-token" };

function reply(body: unknown, status = 200) {
  fetchApi.mockResolvedValueOnce(Response.json(body, { status }));
}

function submit(question: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "AI 질문 입력" }), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "AI에게 질문하기" }));
}

async function advance(ms: number) {
  await act(async () => vi.advanceTimersByTimeAsync(ms));
}

describe("F9 assistant flow", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    window.sessionStorage.clear();
    vi.useFakeTimers();
    fetchApi.mockReset();
    vi.stubGlobal("fetch", fetchApi);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("opens a route card from the home answer using both access tokens", async () => {
    reply({ items: [] });
    reply({ items: [] });
    render(<HomePage />);
    await advance(0);
    const festivalQuery = new URL(String(fetchApi.mock.calls[0][0]));
    expect(festivalQuery.searchParams.get("status")).toBe("ongoing,upcoming");
    expect(festivalQuery.searchParams.get("page_size")).toBe("4");

    reply(run, 202);
    reply({ run_status: "running" });
    reply({ run_status: "succeeded", answer: "경로를 찾았어요.", ...route });
    submit("서울역으로 귀가하는 길 알려줘");
    await advance(1000);
    expect(screen.getByRole("status")).toHaveTextContent("생각 중…");
    const [submitUrl, request] = fetchApi.mock.calls.find(([url]) => String(url).endsWith("/assistant/query"))!;
    expect(String(submitUrl)).toMatch(/\/assistant\/query$/);
    expect(JSON.parse(String(request?.body))).toMatchObject({ message: "서울역으로 귀가하는 길 알려줘" });
    const statusCall = fetchApi.mock.calls.find(([url]) => String(url).endsWith(`/assistant/runs/${run.run_id}`))!;
    expect(new Headers(statusCall[1]?.headers).get("X-Run-Access-Token")).toBe(run.run_access_token);

    await advance(1000);
    expect(screen.getByText("경로를 찾았어요.")).toBeInTheDocument();
    const href = screen
      .getAllByRole("link", { name: "귀가 경로 보기" })
      .map((link) => link.getAttribute("href"))
      .find((value) => value?.includes("?id="))!;
    const url = new URL(href, "http://localhost");
    expect(url.pathname).toBe("/routes/return");
    expect(Object.fromEntries(url.searchParams)).toEqual({ id: route.route_request_id });
    window.history.replaceState(null, "", href);

    cleanup();
    reply({
      route_request_id: route.route_request_id,
      route_status: "ready",
      completed_valid_route: true,
      route_preference: "fastest",
      travel_mode: "transit",
      origin: { name: "테스트광장" },
      destination: { name: "서울역" },
      route_candidates: [{ candidate_id: "test", summary: "테스트 귀가 경로", duration_min: 12, walk_m: 100, transfers: 0, legs: [] }],
    });
    render(await ReturnRoutePage({ searchParams: Promise.resolve(Object.fromEntries(url.searchParams)) }));
    await advance(0);
    const [routeUrl, routeRequest] = fetchApi.mock.calls.find(([calledUrl]) =>
      String(calledUrl).endsWith(`/routes/return/${route.route_request_id}`),
    )!;
    expect(String(routeUrl)).toMatch(/\/routes\/return\/rr_test01$/);
    expect(new Headers(routeRequest?.headers).get("X-Route-Access-Token")).toBe(route.route_access_token);
    expect(screen.getByRole("button", { name: /12분/ })).toBeInTheDocument();
  });

  it.each(["submission", "lookup"])("F9 aborts a stalled %s after ten seconds and offers retry", async (step) => {
    const lookup = step === "lookup";
    if (lookup) reply(run, 202);
    fetchApi.mockImplementationOnce(() => new Promise(() => {}));
    render(<AssistantPrompt />);
    submit("축제 찾아줘");
    if (lookup) await advance(1000);

    const signal = fetchApi.mock.lastCall?.[1]?.signal;
    await advance(9999);
    expect(screen.getByRole("status")).toHaveTextContent("생각 중…");
    await advance(1);
    expect(signal?.aborted).toBe(true);
    expect(screen.getByRole("alert")).toHaveTextContent("서버 응답 시간이 초과됐어요.");
    expect(screen.getByRole("button", { name: "다시 묻기" })).toBeEnabled();
  });

  it("preserves festival context and retries a failed answer with a new request ID", async () => {
    reply(run, 202);
    reply({ run_status: "failed", error: { message: "축제 정보를 조회하지 못했어요." } });
    render(<FestivalAiPrompt festivalId="fst_test01" />);
    submit("축제까지 어떻게 가요?");
    await advance(1000);
    expect(screen.getByRole("alert")).toHaveTextContent("축제 정보를 조회하지 못했어요.");

    reply(run, 202);
    reply({ run_status: "succeeded", answer: "축제 정보를 확인했어요." });
    fireEvent.click(screen.getByRole("button", { name: "다시 묻기" }));
    await advance(1000);
    const first = JSON.parse(String(fetchApi.mock.calls[0][1]?.body));
    const second = JSON.parse(String(fetchApi.mock.calls[2][1]?.body));
    expect(first.context).toEqual({ festival_id: "fst_test01" });
    expect(second).toEqual({ ...first, request_id: expect.any(String) });
    expect(second.request_id).not.toBe(first.request_id);
    expect(screen.getByRole("status")).toHaveTextContent("축제 정보를 확인했어요.");
  });

  it("continues follow-up questions in the same assistant conversation", async () => {
    reply(run, 202);
    reply({ run_status: "succeeded", answer: "첫 답변이에요." });
    render(<AssistantPrompt />);
    submit("이번 주말 축제 추천해줘");
    await advance(1000);
    expect(screen.getByRole("status")).toHaveTextContent("첫 답변이에요.");

    const nextRun = {
      run_id: "run_test02",
      conversation_id: run.conversation_id,
      run_access_token: "fixture-next-token",
    };
    reply(nextRun, 202);
    reply({ run_status: "succeeded", answer: "그중에는 이 축제를 추천해요." });
    submit("그중에 가장 가까운 건 뭐야?");
    await advance(1000);

    const submissions = fetchApi.mock.calls.filter(([url]) =>
      String(url).endsWith("/assistant/query"),
    );
    expect(submissions).toHaveLength(2);
    const [, followUpRequest] = submissions[1];
    expect(JSON.parse(String(followUpRequest?.body))).toMatchObject({
      conversation_id: run.conversation_id,
      message: "그중에 가장 가까운 건 뭐야?",
    });
    expect(new Headers(followUpRequest?.headers).get("X-Run-Access-Token"))
      .toBe(run.run_access_token);
    expect(screen.getByRole("status")).toHaveTextContent("그중에는 이 축제를 추천해요.");
  });

  it("polls at one-second intervals and allows a real assistant up to sixty seconds", async () => {
    reply(run, 202);
    for (let i = 0; i < 60; i += 1) {
      reply({ run_status: "running" });
    }
    render(<AssistantPrompt />);
    submit("축제 찾아줘");
    await advance(999);
    expect(fetchApi).toHaveBeenCalledTimes(1);
    await advance(59_001);
    expect(fetchApi).toHaveBeenCalledTimes(61);
    expect(screen.getByRole("alert")).toHaveTextContent("응답이 지연되고 있어요.");
    await advance(1000);
    expect(fetchApi).toHaveBeenCalledTimes(61);
  });
});
