"use client";

import Image from "next/image";
import Link from "next/link";
import { Heart, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { listFavorites, type FavoriteItem } from "./api";

export function FavoriteFestivalListView() {
  const [items, setItems] = useState<FavoriteItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setFailed(false);
    listFavorites(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setItems(result.items);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [attempt]);

  return (
    <RequireAuth nextPath="/festivals/favorites">
      <div className="space-y-6 px-4 py-5 md:px-8 md:py-8">
        <header>
          <h1 className="flex items-center gap-2 text-[28px] font-black text-ink">
            <Heart className="h-7 w-7 fill-brand text-brand" aria-hidden="true" />
            찜한 축제
          </h1>
          <p className="mt-2 text-sm text-muted">내가 찜한 축제를 한눈에 확인해 보세요.</p>
        </header>

        {failed ? (
          <button
            type="button"
            onClick={() => setAttempt((value) => value + 1)}
            className="flex w-full items-center justify-center gap-2 rounded-card-lg border border-line-light py-8 text-sm font-bold text-ink"
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            다시 불러오기
          </button>
        ) : !items ? (
          <div className="h-48 animate-pulse rounded-card-lg bg-surface-muted" />
        ) : items.length === 0 ? (
          <div className="rounded-card-lg bg-surface-soft px-4 py-16 text-center text-sm text-muted">
            아직 찜한 축제가 없어요.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-5">
            {items.map((item) => (
              <Link
                key={item.festival_id}
                href={`/festivals/${item.festival_id}`}
                className="overflow-hidden rounded-card-lg bg-surface shadow-card transition-shadow hover:shadow-md"
              >
                <div className="relative aspect-[3/2] overflow-hidden bg-surface-soft">
                  {item.thumbnail_url ? (
                    <Image
                      src={item.thumbnail_url}
                      alt={item.name}
                      fill
                      unoptimized
                      className="object-cover"
                    />
                  ) : (
                    <FestivalImagePlaceholder />
                  )}
                  <span className="absolute right-2 top-2 text-brand drop-shadow-sm">
                    <Heart className="h-6 w-6 fill-brand" aria-hidden="true" />
                  </span>
                </div>
                <p className="px-3 py-3 text-sm font-extrabold text-ink">{item.name}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </RequireAuth>
  );
}
