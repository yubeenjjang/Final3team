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
      if (url.includes("/festivals/fst_000001/companion-posts")) {
        return Response.json({
          items: [
            {
              post_id: "cpo_detail_1",
              author_display_name: "동행친구",
              meet_at: "2026-12-06T09:00:00Z",
              capacity: 4,
              approved_count: 2,
              age_pref: "any",
              gender_pref: "any",
              memo: "테스트 축제 같이 가요!",
              status: "open",
            },
          ],
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
      if (url.includes("/festivals/fst_000001/facilities")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                facility_id: "food_1",
                category: "food",
                name: "테스트 맛집",
                lat: 37.5762,
                lng: 126.9771,
                distance_m: 240,
                address: "서울특별시 종로구 맛집로 2",
                source: "kakao_local",
              },
            ],
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

    const companionPostLink = await screen.findByRole("link", {
      name: "테스트 축제 같이 가요! 상세보기",
    });
    expect(companionPostLink).toHaveAttribute("href", "/companions/cpo_detail_1");
    expect(screen.getByRole("link", { name: "모집 글쓰기" })).toHaveAttribute(
      "href",
      "/companions?festivalId=fst_000001&write=1",
    );
    expect(screen.getByRole("link", { name: /전체보기/ })).toHaveAttribute(
      "href",
      "/companions?festivalId=fst_000001",
    );

    // 주변 정보는 지도 탭으로 이동하지 않고 상세페이지 안에서 목록·상세를 연다 (A08)
    expect(
      screen.getByRole("link", { name: "지도 탭으로 이동해서 자세히 보기" }),
    ).toHaveAttribute("href", "/map?festival=fst_000001");
    const foodButton = screen.getByRole("button", { name: "주변 맛집 정보 보기" });
    expect(foodButton).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(foodButton);
    expect(foodButton).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => {
      expect(screen.getByText("테스트 맛집")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "테스트 맛집 상세 정보 보기" }));
    expect(screen.getByRole("article", { name: "테스트 맛집 상세 정보" })).toHaveTextContent(
      "서울특별시 종로구 맛집로 2",
    );
    expect(screen.queryByRole("link", { name: /주변 맛집/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/정보는 준비 중이에요/)).not.toBeInTheDocument();

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
