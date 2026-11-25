import { describe, expect, it } from "vitest";
import { listMockFestivals, MOCK_FESTIVALS } from "./mockFestivals";

describe("design mock festivals", () => {
  it("provides enough cards to preview all festival sections", () => {
    expect(MOCK_FESTIVALS).toHaveLength(12);
    expect(listMockFestivals({ page: 1, page_size: 20 }).items).toHaveLength(12);
  });

  it("supports the filters used by the festival screens", () => {
    const seoul = listMockFestivals({ region: "SEOUL", page: 1, page_size: 20 });
    const upcoming = listMockFestivals({ status: "upcoming", page: 1, page_size: 4 });
    const search = listMockFestivals({ q: "해운대", page: 1, page_size: 20 });

    expect(seoul.items.every((festival) => festival.region_code === "SEOUL")).toBe(true);
    expect(upcoming.items).toHaveLength(4);
    expect(upcoming.items.every((festival) => festival.event_status === "upcoming")).toBe(true);
    expect(search.items.map((festival) => festival.name)).toEqual(["해운대 빛축제"]);
  });
});
