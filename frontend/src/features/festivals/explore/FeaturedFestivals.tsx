"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { FestivalCarousel } from "./FestivalCarousel";
import { listFestivals, type FestivalListItem } from "./api";

export function FeaturedFestivals({
  title = "인기있는 축제",
  status = "ongoing",
  moreLabel = "전체보기",
  moreHref = "/festivals/all?section=popular",
}: {
  title?: string;
  status?: "ongoing" | "upcoming";
  moreLabel?: string;
  moreHref?: string;
} = {}) {
  const [items, setItems] = useState<FestivalListItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    listFestivals({ status, page: 1, page_size: 4 }, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setItems(result.items.slice(0, 4));
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [attempt, status]);

  return (
    <section aria-labelledby="featured-title">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="featured-title" className="flex items-center gap-2 text-base font-extrabold tracking-tight text-ink">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          {title}
        </h2>
        <Link href={moreHref} className="flex shrink-0 items-center gap-0.5 text-xs font-semibold text-muted hover:text-brand">
          {moreLabel} <ChevronRight size={14} aria-hidden="true" />
        </Link>
      </div>

      {failed ? (
        <div className="flex min-h-24 items-center justify-between gap-2 rounded-card border border-line-light bg-surface px-4 text-sm text-ink shadow-sm">
          <p role="alert">축제를 불러오지 못했어요.</p>
          <button
            type="button"
            className="shrink-0 rounded-chip bg-brand px-3 py-1.5 text-xs font-bold text-surface"
            onClick={() => {
              setFailed(false);
              setAttempt((value) => value + 1);
            }}
          >
            다시 시도
          </button>
        </div>
      ) : !items ? (
        <div role="status" className="flex min-h-36 items-center justify-center rounded-card border border-line-light bg-surface-muted/50 text-sm text-muted">
          축제를 불러오는 중이에요.
        </div>
      ) : items.length === 0 ? (
        <div className="flex min-h-24 items-center justify-center rounded-card border border-line-light bg-surface-muted/50 px-4 text-sm text-muted">
          진행 중인 축제가 없어요.
        </div>
      ) : (
        <FestivalCarousel items={items} ariaLabel={title} />
      )}
    </section>
  );
}
