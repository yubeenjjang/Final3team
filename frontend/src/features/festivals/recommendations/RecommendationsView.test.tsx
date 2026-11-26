import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { RecommendationsView } from "./RecommendationsView";

vi.mock("next/navigation", () => ({
  usePathname: () => "/recommendations",
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("RecommendationsView", () => {
  beforeEach(() => {
    resetAuthStateForTest();
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "user-1", displayName: "테스터" },
    });
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/me/festival-preferences")) {
        return Response.json({
          scenarios: ["family_relaxed", "friends_activity", "couple_photo", "pet", "solo"],
          onboarding_status: "completed",
          updated_at: "2026-11-26T10:00:00+09:00",
        });
      }
      return Response.json({
        total: 1,
        page: 1,
        page_size: 5,
        items: [{
          festival_id: "festival-1",
          name: "추천 축제",
          region_code: "SEOUL",
          venue_name: "서울광장",
          start_date: "2026-12-01",
          end_date: "2026-12-05",
          event_status: "upcoming",
          thumbnail_url: null,
          image_credit: null,
          source: "mock",
          last_synced_at: "2026-11-26T10:00:00+09:00",
        }],
      });
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    cleanup();
    resetAuthStateForTest();
    vi.restoreAllMocks();
  });

  it("shows every selected preference and provides drag-only carousel chrome and a home link", async () => {
    render(<RecommendationsView />);

    expect(await screen.findByRole("heading", { name: "취향에 맞는 축제를 찾았어요!" })).toBeInTheDocument();
    for (const label of ["가족과 함께", "친구와 액티비티", "연인과 포토존", "반려견 동반", "혼자 즐기기"]) {
      expect(screen.getByText((content) => content.includes(label))).toBeInTheDocument();
    }
    expect(screen.getByText("추천 축제").closest("div.no-scrollbar")).toBeInTheDocument();
    const detailLink = screen.getByRole("link", { name: /축제 상세보기/ });
    expect(detailLink).toHaveAttribute("href", "/festivals/festival-1");

    const carousel = detailLink.closest("div.no-scrollbar") as HTMLDivElement;
    const setPointerCapture = vi.fn();
    Object.defineProperty(carousel, "setPointerCapture", {
      configurable: true,
      value: setPointerCapture,
    });
    fireEvent.pointerDown(carousel, {
      pointerType: "mouse",
      pointerId: 1,
      button: 0,
      clientX: 200,
    });
    fireEvent.pointerUp(carousel, {
      pointerType: "mouse",
      pointerId: 1,
      clientX: 200,
    });
    expect(setPointerCapture).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: /메인페이지로 가기/ })).toHaveAttribute("href", "/");
  });
});
