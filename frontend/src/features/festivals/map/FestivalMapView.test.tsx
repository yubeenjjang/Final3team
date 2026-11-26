import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FestivalMapView } from "./FestivalMapView";
import { parseMapSelection } from "./selection";

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
      const festivalPage = {
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
      };
      const q = new URL(url, "http://localhost").searchParams.get("q");
      if (q) {
        return Response.json({
          ...festivalPage,
          items: festivalPage.items.filter((item) => item.name.includes(q)),
        });
      }
      return Response.json(festivalPage);
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
    expect(await screen.findByRole("application", { name: "해운대 빛축제 지도" })).toBeInTheDocument();
    expect(screen.getByText("해운대 빛축제 (부산)")).toBeInTheDocument();
    const searchUrl = fetchMock.mock.calls
      .map(([input]) => new URL(String(input), "http://localhost"))
      .find((url) => url.pathname.endsWith("/festivals") && url.searchParams.has("q"));
    expect(searchUrl?.searchParams.get("q")).toBe("해운대");
    expect(searchUrl?.searchParams.get("status")).toBe("ongoing,upcoming,ended");

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

  it("searches festivals outside the default list through A02 q", async () => {
    const located = {
      region_code: "SEOUL",
      venue_name: "청계천",
      start_date: "2025-12-01",
      end_date: "2025-12-31",
      thumbnail_url: null,
      image_credit: null,
      source: "tourapi",
      last_synced_at: "2026-11-26T09:00:00+09:00",
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname.includes("/facilities")) return Response.json({ items: [] });
      if (url.pathname.includes("/crowd")) return Response.json({ status: "ok", areas: [] });
      const q = url.searchParams.get("q");
      const items = q === "없는축제"
        ? []
        : q
        ? [{ ...located, festival_id: "fst_map_ended", name: "지난 겨울 등불축제", lat: 37.57, lng: 126.98, event_status: "ended" }]
        : [{ ...located, festival_id: "fst_map_now", name: "지금 축제", lat: 37.5, lng: 127.0, event_status: "ongoing" }];
      return Response.json({ is_mock: false, total: items.length, page: 1, page_size: 20, items });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalMapView />);
    expect(await screen.findByRole("application", { name: "지금 축제 지도" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "축제명 또는 장소 검색" }), {
      target: { value: "등불" },
    });
    expect(await screen.findByRole("application", { name: "지난 겨울 등불축제 지도" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "축제명 또는 장소 검색" }), {
      target: { value: "없는축제" },
    });
    // 결과가 없으면 지도는 그대로 두고 안내만 보여 준다
    expect(await screen.findByText("검색 조건에 맞는 축제가 없어요.")).toBeInTheDocument();
    expect(screen.getByRole("application", { name: "지난 겨울 등불축제 지도" })).toBeInTheDocument();
  });
  it("shows a search error instead of 'no results' when the search API fails", async () => {
    const located = {
      region_code: "SEOUL",
      venue_name: "청계천",
      start_date: "2026-12-01",
      end_date: "2026-12-31",
      thumbnail_url: null,
      image_credit: null,
      source: "mock",
      last_synced_at: "2026-11-26T09:00:00+09:00",
    };
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/facilities")) return Response.json({ items: [] });
      if (url.pathname.endsWith("/crowd")) return Response.json({ status: "ok", areas: [] });
      if (url.searchParams.get("q")) return new Response("boom", { status: 500 });
      return Response.json({
        is_mock: false,
        total: 1,
        page: 1,
        page_size: 100,
        items: [{ ...located, festival_id: "fst_map_now", name: "지금 축제", lat: 37.5, lng: 127.0, event_status: "ongoing" }],
      });
    }) as unknown as typeof fetch;

    render(<FestivalMapView />);
    expect(await screen.findByRole("application", { name: "지금 축제 지도" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "축제명 또는 장소 검색" }), {
      target: { value: "등불" },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("검색 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.");
    expect(screen.queryByText("검색 조건에 맞는 축제가 없어요.")).not.toBeInTheDocument();
    expect(screen.getByRole("application", { name: "지금 축제 지도" })).toBeInTheDocument();
  });
  it("opens with the festival and facility category from the detail page link", async () => {
    const base = {
      region_code: "SEOUL",
      venue_name: "청계천",
      start_date: "2025-12-01",
      end_date: "2025-12-31",
      thumbnail_url: null,
      image_credit: null,
      source: "tourapi",
      last_synced_at: "2026-11-26T09:00:00+09:00",
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname.includes("/facilities")) {
        return Response.json({
          items: [
            { facility_id: "toilet_1", category: "toilet", name: "청계광장 화장실", lat: 37.569, lng: 126.978, distance_m: 82 },
            { facility_id: "hospital_1", category: "hospital", name: "강북삼성병원", lat: 37.568, lng: 126.968, distance_m: 858 },
          ],
        });
      }
      if (url.pathname.includes("/crowd")) return Response.json({ status: "ok", areas: [] });
      if (url.pathname.endsWith("/festivals/fst_map_ended")) {
        return Response.json({
          ...base, is_mock: false, festival_id: "fst_map_ended", name: "지난 겨울 등불축제",
          lat: 37.57, lng: 126.98, event_status: "ended", address: null, overview: null,
          fee_text: null, homepage_url: null, image_url: null, image_copyright: null, source_ref: null,
        });
      }
      const items = [{ ...base, festival_id: "fst_map_now", name: "지금 축제", lat: 37.5, lng: 127.0, event_status: "ongoing" }];
      return Response.json({ is_mock: false, total: 1, page: 1, page_size: 100, items });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FestivalMapView initialFestivalId="fst_map_ended" initialGroup="safety" initialCategory="toilet" />);

    // 기본 목록에 없는 축제는 A03으로 받아 선택한다
    expect(await screen.findByRole("application", { name: "지난 겨울 등불축제 지도" })).toBeInTheDocument();
    expect(await screen.findByText("청계광장 화장실")).toBeInTheDocument();
    expect(screen.queryByText("강북삼성병원")).not.toBeInTheDocument();
    const facilityUrl = fetchMock.mock.calls
      .map(([input]) => new URL(String(input), "http://localhost"))
      .find((url) => url.pathname.endsWith("/festivals/fst_map_ended/facilities"));
    expect(facilityUrl?.searchParams.get("categories")).toBe("toilet,parking,hospital,emergency");
  });

  it("ignores invalid map query values", () => {
    expect(parseMapSelection({ festival: "fst_1", group: "safety", category: "hospital" })).toEqual({
      festivalId: "fst_1", group: "safety", category: "hospital",
    });
    expect(parseMapSelection({ group: "nope", category: "toilet" })).toEqual({
      festivalId: null, group: "transport", category: "all",
    });
    expect(parseMapSelection({ festival: "  ", group: "food", category: "toilet" })).toEqual({
      festivalId: null, group: "food", category: "all",
    });
  });
});
