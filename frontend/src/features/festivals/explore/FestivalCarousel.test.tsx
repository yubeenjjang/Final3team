import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FestivalCarousel } from "./FestivalCarousel";
import { MOCK_FESTIVALS } from "./mockFestivals";

describe("FestivalCarousel", () => {
  it("moves to the selected dot and updates the active page", () => {
    render(<FestivalCarousel items={MOCK_FESTIVALS.slice(0, 4)} ariaLabel="인기있는 축제" />);
    const scroller = screen.getByRole("region", { name: "인기있는 축제 카드 목록" });
    const scrollTo = vi.fn(({ left }: ScrollToOptions) => {
      Object.defineProperty(scroller, "scrollLeft", { configurable: true, value: left ?? 0 });
      fireEvent.scroll(scroller);
    });
    Object.defineProperties(scroller, {
      clientWidth: { configurable: true, value: 400 },
      scrollWidth: { configurable: true, value: 1000 },
      scrollTo: { configurable: true, value: scrollTo },
    });

    const dots = screen.getAllByRole("button", { name: /페이지로 이동/ });
    expect(dots).toHaveLength(3);
    fireEvent.click(dots[1]);

    expect(scrollTo).toHaveBeenCalledWith({ left: 300, behavior: "smooth" });
    expect(dots[1]).toHaveAttribute("aria-current", "page");
  });

  it("scrolls cards when dragged with a mouse", () => {
    render(<FestivalCarousel items={MOCK_FESTIVALS.slice(0, 4)} ariaLabel="나만을 위한 축제" />);
    const scroller = screen.getByRole("region", { name: "나만을 위한 축제 카드 목록" });
    Object.defineProperties(scroller, {
      clientWidth: { configurable: true, value: 400 },
      scrollWidth: { configurable: true, value: 1000 },
      scrollLeft: { configurable: true, writable: true, value: 200 },
      setPointerCapture: { configurable: true, value: vi.fn() },
      releasePointerCapture: { configurable: true, value: vi.fn() },
    });

    fireEvent.pointerDown(scroller, { pointerType: "mouse", pointerId: 1, button: 0, clientX: 200 });
    fireEvent.pointerMove(scroller, { pointerType: "mouse", pointerId: 1, clientX: 140 });
    fireEvent.pointerUp(scroller, { pointerType: "mouse", pointerId: 1, clientX: 140 });

    expect(scroller.scrollLeft).toBe(260);
  });
});
