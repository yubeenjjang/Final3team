"use client";

import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { FestivalCard } from "./FestivalCard";
import type { FestivalListItem } from "./api";

export function FestivalCarousel({
  items,
  ariaLabel,
}: {
  items: FestivalListItem[];
  ariaLabel: string;
}) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const dragStartX = useRef(0);
  const dragStartScrollLeft = useRef(0);
  const dragged = useRef(false);
  const [dragging, setDragging] = useState(false);
  const [activePage, setActivePage] = useState(0);
  const dotCount = items.length > 2 ? Math.min(3, items.length - 1) : 0;

  function updateActivePage() {
    const scroller = scrollerRef.current;
    if (!scroller || dotCount < 2) return;
    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    if (maxScroll <= 0) {
      setActivePage(0);
      return;
    }
    setActivePage(Math.round((scroller.scrollLeft / maxScroll) * (dotCount - 1)));
  }

  function goToPage(page: number) {
    const scroller = scrollerRef.current;
    if (!scroller || dotCount < 2) return;
    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    const left = (maxScroll * page) / (dotCount - 1);
    setActivePage(page);
    if (typeof scroller.scrollTo === "function") {
      scroller.scrollTo({ left, behavior: "smooth" });
    } else {
      scroller.scrollLeft = left;
    }
  }

  function startMouseDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    const scroller = scrollerRef.current;
    if (!scroller) return;
    dragStartX.current = event.clientX;
    dragStartScrollLeft.current = scroller.scrollLeft;
    dragged.current = false;
    setDragging(true);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function moveMouseDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragging || event.pointerType !== "mouse") return;
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const distance = event.clientX - dragStartX.current;
    if (Math.abs(distance) > 3) dragged.current = true;
    scroller.scrollLeft = dragStartScrollLeft.current - distance;
    event.preventDefault();
    updateActivePage();
  }

  function finishMouseDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragging) return;
    setDragging(false);
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    updateActivePage();
  }

  return (
    <div className="space-y-3">
      <div
        ref={scrollerRef}
        role="region"
        aria-label={`${ariaLabel} 카드 목록`}
        className={`no-scrollbar -mx-4 flex touch-pan-x gap-2 overflow-x-auto px-4 pb-2 select-none md:mx-0 md:gap-4 md:px-0 ${
          dragging ? "cursor-grabbing snap-none" : "cursor-grab snap-x snap-mandatory"
        }`}
        onScroll={updateActivePage}
        onPointerDown={startMouseDrag}
        onPointerMove={moveMouseDrag}
        onPointerUp={finishMouseDrag}
        onPointerCancel={finishMouseDrag}
        onDragStart={(event) => event.preventDefault()}
        onClickCapture={(event) => {
          if (!dragged.current) return;
          event.preventDefault();
          event.stopPropagation();
          dragged.current = false;
        }}
      >
        {items.map((item) => (
          <FestivalCard
            key={item.festival_id}
            item={item}
            className="festival-carousel-card snap-start"
          />
        ))}
      </div>

      {dotCount > 0 ? (
        <div className="flex justify-center gap-2 md:hidden" aria-label={`${ariaLabel} 페이지 선택`}>
          {Array.from({ length: dotCount }, (_, page) => (
            <button
              key={page}
              type="button"
              aria-label={`${ariaLabel} ${page + 1}페이지로 이동`}
              aria-current={activePage === page ? "page" : undefined}
              className={`h-2 w-2 rounded-chip transition-colors ${
                activePage === page ? "bg-brand" : "bg-brand/25 hover:bg-brand/50"
              }`}
              onClick={() => goToPage(page)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
