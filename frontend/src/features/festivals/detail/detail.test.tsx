import "@testing-library/jest-dom/vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest } from "@/lib/api/auth";
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

  it("F7 renders a landscape detail image, chips, nearby icons, map fallback, and return route banner", async () => {
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

    const heroImage = screen.getByAltText("테스트 문화 축제");
    const assistantInput = screen.getByRole("textbox");
    expect(
      assistantInput.compareDocumentPosition(heroImage) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(heroImage.className).toContain("object-cover");
    expect(heroImage.parentElement).toHaveClass("aspect-[3/1]");
    expect(screen.queryByLabelText("축제 목록으로")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("공유하기")).not.toBeInTheDocument();
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

    const favoriteButton = screen.getByRole("button", { name: "찜하기" });
    expect(favoriteButton).toHaveClass("bg-transparent");
    expect(favoriteButton).not.toHaveClass("rounded-chip");
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
    expect(screen.queryByText("출처: 한국관광공사")).not.toBeInTheDocument();

    fireEvent.error(heroImg);

    expect(screen.getByText("이미지 준비 중")).toBeInTheDocument();
    expect(screen.queryByText("출처: 한국관광공사")).not.toBeInTheDocument();
    expect(screen.queryByAltText("테스트 문화 축제")).not.toBeInTheDocument();
  });
});
