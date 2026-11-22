import "@testing-library/jest-dom/vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { dday } from "./dday";
import { FestivalExploreView } from "./FestivalExploreView";
import { getRegionLabel, REGION_OPTIONS } from "./regions";

describe("F6 festival explore", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
  });

  it("F6 dday returns D-n before start, 진행 중 during period, 종료 after end, and empty when missing", () => {
    expect(dday("2026-12-05", "2026-12-07", "2026-11-22")).toBe("D-13");
    expect(dday("2026-11-20", "2026-11-25", "2026-11-22")).toBe("진행 중");
    expect(dday("2026-11-22", "2026-11-22", "2026-11-22")).toBe("진행 중");
    expect(dday("2026-11-10", "2026-11-15", "2026-11-22")).toBe("종료");
    expect(dday(null, null, "2026-11-22")).toBe("");
    expect(dday(undefined, "2026-11-30", "2026-11-22")).toBe("");
  });

  it("F6 maps region codes to Korean labels", () => {
    expect(REGION_OPTIONS).toHaveLength(18);
    expect(getRegionLabel("ALL")).toBe("전체");
    expect(getRegionLabel("SEOUL")).toBe("서울");
    expect(getRegionLabel("BUSAN")).toBe("부산");
    expect(getRegionLabel("JEJU")).toBe("제주");
  });

  it("F6 renders cards with object-contain and credit, filters by region/status/search, and paginates", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      const region = url.searchParams.get("region");
      const status = url.searchParams.get("status");
      const q = url.searchParams.get("q");
      const page = Number(url.searchParams.get("page") ?? "1");

      if (q === "없는축제") {
        return new Response(
          JSON.stringify({
            is_mock: true,
            items: [],
            total: 0,
            page: 1,
            page_size: 20,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (region === "SEOUL") {
        return new Response(
          JSON.stringify({
            is_mock: true,
            items: [
              {
                festival_id: "fst_000001",
                name: "한강 축제 테스트",
                region_code: "SEOUL",
                venue_name: "여의도 한강공원",
                lat: 37.528,
                lng: 126.932,
                start_date: "2026-12-05",
                end_date: "2026-12-07",
                event_status: "upcoming",
                thumbnail_url: "https://example.com/thumb1.jpg",
                image_credit: "한국관광공사",
                source: "tourapi",
                last_synced_at: "2026-11-22T00:00:00Z",
              },
              {
                festival_id: "fst_000002",
                name: "도심 야간 축제",
                region_code: "SEOUL",
                venue_name: "광장",
                lat: 37.575,
                lng: 126.976,
                start_date: "2026-11-20",
                end_date: "2026-11-25",
                event_status: "ongoing",
                thumbnail_url: null,
                image_credit: null,
                source: "tourapi",
                last_synced_at: "2026-11-22T00:00:00Z",
              },
            ],
            total: 2,
            page: 1,
            page_size: 20,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (page === 2) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            items: [
              {
                festival_id: "fst_000003",
                name: "추가 축제",
                region_code: "BUSAN",
                venue_name: "해운대",
                lat: 35.158,
                lng: 129.16,
                start_date: "2026-11-21",
                end_date: "2026-11-24",
                event_status: status ?? "ongoing",
                thumbnail_url: null,
                image_credit: null,
                source: "tourapi",
                last_synced_at: "2026-11-22T00:00:00Z",
              },
            ],
            total: 2,
            page: 2,
            page_size: 20,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      return new Response(
        JSON.stringify({
          is_mock: true,
          items: [
            {
              festival_id: "fst_000001",
              name: "첫 번째 축제",
              region_code: "SEOUL",
              venue_name: "서울 광장",
              lat: 37.566,
              lng: 126.978,
              start_date: "2026-12-05",
              end_date: "2026-12-07",
              event_status: status ?? "upcoming",
              thumbnail_url: "https://example.com/a.jpg",
              image_credit: "한국관광공사",
              source: "tourapi",
              last_synced_at: "2026-11-22T00:00:00Z",
            },
          ],
          total: 2,
          page: 1,
          page_size: 20,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalExploreView />);

    await waitFor(() => {
      expect(screen.getByText("첫 번째 축제")).toBeInTheDocument();
    });

    const image = screen.getByAltText("첫 번째 축제");
    expect(image.className).toContain("object-contain");
    expect(screen.getByText("출처: 한국관광공사")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "더 보기" }));
    await waitFor(() => {
      expect(screen.getByText("추가 축제")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("지역 선택"), {
      target: { value: "SEOUL" },
    });
    await waitFor(() => {
      expect(screen.getByText("한강 축제 테스트")).toBeInTheDocument();
      expect(screen.getByText("도심 야간 축제")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "진행 중" }));
    await waitFor(() => {
      const lastUrl = String(
        fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0],
      );
      expect(lastUrl).toContain("status=ongoing");
    });

    fireEvent.change(screen.getByLabelText("축제 검색"), {
      target: { value: "없는축제" },
    });
    fireEvent.click(screen.getByRole("button", { name: "검색" }));

    await waitFor(() => {
      expect(
        screen.getByText("조건에 맞는 축제가 없어요"),
      ).toBeInTheDocument();
    });
  });
});
