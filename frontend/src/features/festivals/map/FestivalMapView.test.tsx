import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FestivalMapView } from "./FestivalMapView";

vi.mock("@/lib/kakao", () => ({ getKakaoJsKey: () => "" }));

describe("FestivalMapView", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
  });

  it("loads located festivals and moves the fallback map when a festival is selected", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/facilities")) {
        const food = url.includes("food%2Cattraction") || url.includes("food,attraction");
        return Response.json({
          items: [
            {
              facility_id: food ? "food_1" : "station_1",
              category: food ? "food" : "subway_station",
              name: food ? "한강뷰 카페" : "주변 지하철역",
              lat: 37.57,
              lng: 126.97,
              distance_m: 320,
            },
          ],
        });
      }
      if (url.includes("/crowd")) {
        return Response.json({
          status: "ok",
          areas: [
            {
              area_code: "area_1",
              area_name: "축제장 주변",
              relation_type: "contains",
              congest_level: "보통",
              congest_color: "yellow",
              congest_message: "보통 수준",
              population_min: 1000,
              population_max: 2000,
              observed_at: "2026-11-26T09:00:00+09:00",
              forecast: [],
            },
          ],
        });
      }
      return Response.json({
        is_mock: true,
        total: 2,
        page: 1,
        page_size: 100,
        items: [
          {
            festival_id: "fst_map_001",
            name: "광화문 겨울빛 축제",
            region_code: "SEOUL",
            venue_name: "광화문광장",
            lat: 37.5759,
            lng: 126.9768,
            start_date: "2026-11-20",
            end_date: "2026-12-31",
            event_status: "ongoing",
            thumbnail_url: null,
            image_credit: null,
            source: "tourapi",
            last_synced_at: "2026-11-26T09:00:00+09:00",
          },
          {
            festival_id: "fst_map_002",
            name: "해운대 빛축제",
            region_code: "BUSAN",
            venue_name: "해운대해수욕장",
            lat: 35.1587,
            lng: 129.1604,
            start_date: "2026-11-25",
            end_date: "2026-12-28",
            event_status: "ongoing",
            thumbnail_url: null,
            image_credit: null,
            source: "tourapi",
            last_synced_at: "2026-11-26T09:00:00+09:00",
          },
        ],
      });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalMapView />);

    expect(screen.getByRole("searchbox", { name: "축제명 또는 장소 검색" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /내 위치/ })).not.toBeInTheDocument();
    expect(await screen.findByRole("application", { name: "광화문 겨울빛 축제 지도" })).toBeInTheDocument();
    await screen.findByText("주변 지하철역");
    expect(await screen.findByText("보통")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "축제명 또는 장소 검색" }), {
      target: { value: "해운대" },
    });
    expect(screen.getByRole("application", { name: "해운대 빛축제 지도" })).toBeInTheDocument();
    expect(screen.getByText("해운대 빛축제 (부산)")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /맛집·관광/ }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /맛집·관광/ })).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByText("한강뷰 카페")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "한강뷰 카페 지도에서 보기" }));
    expect(screen.getByRole("application", { name: "한강뷰 카페 지도" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "한강뷰 카페 지도에서 보기" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
