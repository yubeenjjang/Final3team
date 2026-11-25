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
import { dday } from "./dday";
import { FestivalCard } from "./FestivalCard";
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

  it("F6 and F7 switch D-day at Seoul midnight with a UTC clock", () => {
    vi.useFakeTimers();
    try {
      const day = "2026-11-22";
      vi.setSystemTime(new Date("2026-11-21T14:59:59Z"));
      expect(dday(day, day)).toBe("D-1");
      vi.setSystemTime(new Date("2026-11-21T15:00:00Z"));
      expect(dday(day, day)).toBe("진행 중");
    } finally {
      vi.useRealTimers();
    }
  });

  it.each(["filter change", "unmount"])("F6 cancels load more on %s and ignores its late response", async (action) => {
    const item = {
      festival_id: "fst_000001",
      name: "기존 축제",
      region_code: "SEOUL",
      event_status: "ongoing",
    };
    const oldPage = Promise.withResolvers<Response>();
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json({ items: [item], total: 2, page: 1 }))
      .mockReturnValueOnce(oldPage.promise)
      .mockResolvedValueOnce(Response.json({ items: [{ ...item, name: "새 필터 축제" }], total: 1, page: 1 }));
    globalThis.fetch = fetchMock;
    const { unmount } = render(<FestivalExploreView />);
    await screen.findByText("기존 축제");
    fireEvent.click(screen.getByRole("button", { name: "더 보기" }));

    if (action === "unmount") unmount();
    else {
      fireEvent.change(screen.getByLabelText("지역 선택"), { target: { value: "SEOUL" } });
      await screen.findByText("새 필터 축제");
    }
    expect(fetchMock.mock.calls[1][1]?.signal?.aborted).toBe(true);

    await act(async () => {
      oldPage.resolve(Response.json({ items: [{ ...item, festival_id: "old", name: "늦게 도착한 축제" }], total: 10, page: 2 }));
    });
    expect(screen.queryByText("늦게 도착한 축제")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "더 보기" })).not.toBeInTheDocument();
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

  it("F6 image error fallback", () => {
    render(
      <FestivalCard
        item={{
          festival_id: "fst_000010",
          name: "이미지 실패 테스트 축제",
          region_code: "SEOUL",
          venue_name: "서울 광장",
          lat: 37.566,
          lng: 126.978,
          start_date: "2026-12-05",
          end_date: "2026-12-07",
          event_status: "upcoming",
          thumbnail_url: "https://example.com/missing.jpg",
          image_credit: "한국관광공사",
          source: "tourapi",
          last_synced_at: "2026-11-22T00:00:00Z",
        }}
        today="2026-11-22"
      />,
    );

    const img = screen.getByAltText("이미지 실패 테스트 축제");
    expect(screen.getByText("출처: 한국관광공사")).toBeInTheDocument();

    fireEvent.error(img);

    expect(screen.getByText("이미지 준비 중")).toBeInTheDocument();
    expect(screen.queryByText("출처: 한국관광공사")).not.toBeInTheDocument();
    expect(screen.queryByAltText("이미지 실패 테스트 축제")).not.toBeInTheDocument();
  });

  it("opens login prompt sheet when guest clicks festival card heart", async () => {
    globalThis.fetch = vi.fn(async () =>
      Response.json({
        is_mock: true,
        items: [
          {
            festival_id: "fst_000011",
            name: "하트 테스트 축제",
            region_code: "SEOUL",
            venue_name: "서울 광장",
            lat: 37.566,
            lng: 126.978,
            start_date: "2026-12-05",
            end_date: "2026-12-07",
            event_status: "upcoming",
            thumbnail_url: null,
            image_credit: null,
            source: "tourapi",
            last_synced_at: "2026-11-22T00:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      }),
    ) as unknown as typeof fetch;

    render(<FestivalExploreView />);

    const heartButton = await screen.findByRole("button", {
      name: "하트 테스트 축제 찜하기",
    });
    fireEvent.click(heartButton);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "로그인하기" })).toHaveAttribute(
      "href",
      "/auth/login?next=%2Ffestivals",
    );
  });
});
