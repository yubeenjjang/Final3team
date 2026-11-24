import "@testing-library/jest-dom/vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { FestivalDetailView } from "./FestivalDetailView";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

function buildDetailResponse(overrides: Record<string, unknown> = {}) {
  return {
    is_mock: true,
    festival_id: "fst_000001",
    name: "테스트 문화 축제",
    region_code: "SEOUL",
    venue_name: "테스트 광장",
    lat: 37.5759,
    lng: 126.9768,
    start_date: "2026-12-05",
    end_date: "2026-12-07",
    event_status: "upcoming",
    thumbnail_url: "https://example.com/thumb.jpg",
    image_url: "https://example.com/hero.jpg",
    image_credit: "한국관광공사",
    image_copyright: {
      type: "Type1",
      credit: "한국관광공사",
      modify_allowed: true,
    },
    source: "tourapi",
    source_ref: "tour_1",
    last_synced_at: "2026-11-22T00:00:00Z",
    address: "서울특별시 종로구 테스트로 1",
    overview: "테스트 한 줄 소개입니다.",
    fee_text: "무료",
    homepage_url: "https://example.com",
    ...overrides,
  };
}

describe("F7 festival detail", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    pushMock.mockReset();
    resetAuthStateForTest();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
  });

  it("F7 renders detail image with object-contain, chips, nearby icons, map fallback, and return route banner", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/festivals/fst_000001")) {
        return new Response(JSON.stringify(buildDetailResponse()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.endsWith("/crowd")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
            source: "seoul_citydata",
            areas: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/weather")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "national", region_code: "SEOUL", supported: true },
            source: "kma",
            data: {
              observed_at: "2026-11-22T14:00:00+09:00",
              temperature_c: 6,
              precipitation_mm: 0,
              precipitation_type: "none",
              grid: { nx: 60, ny: 127 },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          is_mock: true,
          festival_id: "fst_000001",
          status: "ok",
          coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
          source: "operator",
          items: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalDetailView festivalId="fst_000001" />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "테스트 문화 축제" }),
      ).toBeInTheDocument();
    });

    expect(screen.getByAltText("테스트 문화 축제").className).toContain(
      "object-contain",
    );
    expect(screen.getByText("테스트 한 줄 소개입니다.")).toBeInTheDocument();
    expect(screen.getByText("무료")).toBeInTheDocument();
    expect(screen.getByText("서울")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "화장실" }));
    expect(screen.getByRole("status")).toHaveTextContent("준비 중이에요");

    const returnLink = screen.getByRole("link", { name: /귀가 경로 보기/ });
    expect(returnLink).toHaveAttribute(
      "href",
      "/routes/return?festivalId=fst_000001",
    );

    fireEvent.click(screen.getByRole("button", { name: "찜하기" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "로그인하기" })).toHaveAttribute(
      "href",
      "/auth/login?next=%2Ffestivals%2Ffst_000001",
    );
  });

  it("F7 toggles favorite via PUT and DELETE when logged in", async () => {
    setAuthSession({
      accessToken: "token-access",
      refreshToken: "token-refresh",
      user: { userId: "usr_1", displayName: "테스터" },
    });

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";

        if (url.includes("/me/favorites/fst_000001")) {
          if (method === "PUT") {
            return new Response(
              JSON.stringify({
                is_mock: true,
                festival_id: "fst_000001",
                saved_at: "2026-11-22T15:00:00Z",
              }),
              { status: 201, headers: { "Content-Type": "application/json" } },
            );
          }
          if (method === "DELETE") {
            return new Response(null, { status: 204 });
          }
        }
        if (url.includes("/me/favorites")) {
          return new Response(
            JSON.stringify({
              is_mock: true,
              items: [],
              total: 0,
              page: 1,
              page_size: 100,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (url.endsWith("/festivals/fst_000001")) {
          return new Response(
            JSON.stringify(buildDetailResponse({ lat: null, lng: null })),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
            source: "operator",
            items: [],
            areas: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      },
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalDetailView festivalId="fst_000001" />);

    await waitFor(() => {
      expect(screen.getByText("위치 정보가 없어요")).toBeInTheDocument();
    });

    const heartButton = screen.getByRole("button", { name: "찜하기" });
    fireEvent.click(heartButton);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "찜 해제" })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "찜 해제" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "찜하기" })).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });
  });

  it("F7 locks the heart during lookup, checks page two, and ignores a previous session's late lookup", async () => {
    function signIn(id: string) {
      setAuthSession({ accessToken: id, refreshToken: id, user: { userId: id, displayName: id } });
    }

    signIn("previous");
    const previous = Promise.withResolvers<Response>();
    const secondPage = Promise.withResolvers<Response>();
    const fetchMock = vi.fn<typeof fetch>((input, init) => {
      const url = new URL(String(input));
      if (init?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
      if (url.pathname.endsWith("/me/favorites")) {
        if (new Headers(init?.headers).get("Authorization") === "Bearer previous") return previous.promise;
        if (url.searchParams.get("page") === "2") return secondPage.promise;
        return Promise.resolve(Response.json({ items: [{ festival_id: "other" }], page: 1, page_size: 100, total: 101 }));
      }
      if (url.pathname.endsWith("/festivals/fst_000001")) {
        return Promise.resolve(Response.json(buildDetailResponse({ lat: null, lng: null })));
      }
      return Promise.resolve(Response.json({ status: "ok", items: [], areas: [] }));
    });
    globalThis.fetch = fetchMock;
    render(<FestivalDetailView festivalId="fst_000001" />);
    const heart = await screen.findByRole("button", { name: "찜하기" });
    expect(heart).toBeDisabled();
    fireEvent.click(heart);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);

    act(() => signIn("current"));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => new URL(String(url)).searchParams.get("page") === "2")).toBe(true));
    expect(heart).toBeDisabled();
    await act(async () => secondPage.resolve(Response.json({ items: [{ festival_id: "fst_000001" }], page: 2, page_size: 100, total: 101 })));
    fireEvent.click(screen.getByRole("button", { name: "찜 해제" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "찜하기" })).toBeEnabled());

    await act(async () => previous.resolve(Response.json({ items: [{ festival_id: "fst_000001" }], page: 1, page_size: 100, total: 1 })));
    expect(screen.getByRole("button", { name: "찜하기" })).toHaveAttribute("aria-pressed", "false");
  });

  it("F7 shows not found message and link to list on 404", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          error: {
            code: "FESTIVAL_NOT_FOUND",
            message: "축제를 찾을 수 없어요",
            request_id: "req_12345678901234567890123456",
            retryable: false,
          },
        }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalDetailView festivalId="fst_999999" />);

    await waitFor(() => {
      expect(screen.getByText("축제를 찾을 수 없어요")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "목록으로" })).toHaveAttribute(
      "href",
      "/festivals",
    );
  });

  it("F7 falls back to placeholder on hero image error and allows period chip wrapping", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/festivals/fst_000001")) {
        return new Response(
          JSON.stringify(
            buildDetailResponse({
              start_date: "2026-11-20",
              end_date: "2026-11-22",
              image_url: "https://example.com/missing-hero.jpg",
            }),
          ),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          is_mock: true,
          festival_id: "fst_000001",
          status: "unsupported",
          coverage: { scope: "seoul_only", region_code: "SEOUL", supported: false },
          source: "seoul_citydata",
          items: [],
          areas: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalDetailView festivalId="fst_000001" />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "테스트 문화 축제" }),
      ).toBeInTheDocument();
    });

    const periodEl = screen.getByText("2026.11.20 ~ 2026.11.22");
    expect(periodEl.className).not.toContain("truncate");

    const heroImg = screen.getByAltText("테스트 문화 축제");
    expect(screen.getByText("출처: 한국관광공사")).toBeInTheDocument();

    fireEvent.error(heroImg);

    expect(screen.getByText("이미지 준비 중")).toBeInTheDocument();
    expect(screen.queryByText("출처: 한국관광공사")).not.toBeInTheDocument();
    expect(screen.queryByAltText("테스트 문화 축제")).not.toBeInTheDocument();
  });
});
