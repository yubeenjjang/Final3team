"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CalendarDays, Heart, MapPin, RotateCcw } from "lucide-react";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { handleAuthError, RequireAuth } from "@/components/RequireAuth";
import {
  listFavorites,
  type FavoriteListItem,
} from "@/features/accounts/profile/api";
import { deleteFavorite } from "@/features/festivals/detail/api";
import { dday, formatFestivalPeriod } from "@/features/festivals/explore/dday";
import { getRegionLabel } from "@/features/festivals/explore/regions";
import { ApiError } from "@/lib/api/client";

export function FavoritesSection({ embedded = false }: { embedded?: boolean }) {
  const [sort, setSort] = useState<"-saved_at" | "start_date">("-saved_at");
  const [items, setItems] = useState<FavoriteListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [removingId, setRemovingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await listFavorites(
          { page: 1, page_size: 20, sort },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setItems(res.items);
        setTotal(res.total);
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        setItems([]);
        setError(
          cause instanceof ApiError
            ? cause.message
            : "관심 축제 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [sort, reloadTick]);

  async function handleRemove(festivalId: string) {
    if (removingId) return;
    setRemovingId(festivalId);
    setError(null);
    try {
      await deleteFavorite(festivalId);
      setItems((prev) => prev.filter((item) => item.festival_id !== festivalId));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError
          ? cause.message
          : "관심 축제를 해제하지 못했어요.",
      );
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <section className={embedded ? "space-y-3" : "space-y-4 px-4 py-4"}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          <h2 className="text-base font-extrabold text-ink">
            관심 축제 {!loading && !error ? `(${total})` : ""}
          </h2>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-pressed={sort === "-saved_at"}
            onClick={() => setSort("-saved_at")}
            className={
              sort === "-saved_at"
                ? "rounded-chip bg-brand px-2.5 py-1 text-[11px] font-bold text-surface"
                : "rounded-chip border border-line-light bg-surface px-2.5 py-1 text-[11px] font-semibold text-muted"
            }
          >
            최근 저장순
          </button>
          <button
            type="button"
            aria-pressed={sort === "start_date"}
            onClick={() => setSort("start_date")}
            className={
              sort === "start_date"
                ? "rounded-chip bg-brand px-2.5 py-1 text-[11px] font-bold text-surface"
                : "rounded-chip border border-line-light bg-surface px-2.5 py-1 text-[11px] font-semibold text-muted"
            }
          >
            시작일순
          </button>
        </div>
      </div>

      {loading ? (
        <div role="status" className="space-y-2.5">
          {[0, 1].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-card bg-surface-muted" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <p role="alert" className="text-sm font-semibold text-ink">
            {error}
          </p>
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
        </div>
      ) : items.length === 0 ? (
        <div className="space-y-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <p className="text-sm font-bold text-ink">저장한 관심 축제가 없어요</p>
          <p className="text-xs text-muted">
            마음에 드는 축제의 하트를 눌러 모아 볼 수 있어요.
          </p>
          <Link
            href="/festivals"
            className="inline-flex rounded-chip bg-brand px-4 py-2 text-xs font-extrabold text-surface"
          >
            축제 둘러보기
          </Link>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {items.map((item) => {
            const badge =
              item.event_status === "cancelled"
                ? "취소"
                : dday(item.start_date, item.end_date);
            return (
              <li
                key={item.festival_id}
                className="flex items-center gap-3 rounded-card border border-line-light bg-surface p-3 shadow-sm"
              >
                <Link
                  href={`/festivals/${encodeURIComponent(item.festival_id)}`}
                  className="relative h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-surface-soft/50"
                >
                  {item.thumbnail_url ? (
                    <Image
                      src={item.thumbnail_url}
                      alt={item.name}
                      fill
                      sizes="80px"
                      unoptimized
                      className="object-cover"
                    />
                  ) : (
                    <FestivalImagePlaceholder compact />
                  )}
                </Link>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-1.5">
                    {badge ? (
                      <span className="rounded-chip bg-brand px-2 py-0.5 text-[10px] font-extrabold text-surface">
                        {badge}
                      </span>
                    ) : null}
                    <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-muted">
                      <MapPin className="h-3 w-3 text-brand" aria-hidden="true" />
                      {getRegionLabel(item.region_code)}
                    </span>
                  </div>
                  <Link
                    href={`/festivals/${encodeURIComponent(item.festival_id)}`}
                    className="block truncate text-sm font-extrabold text-ink hover:text-brand"
                  >
                    {item.name}
                  </Link>
                  <p className="flex items-center gap-1 text-[11px] text-muted">
                    <CalendarDays className="h-3 w-3 shrink-0 text-brand" aria-hidden="true" />
                    <span className="truncate">
                      {formatFestivalPeriod(item.start_date, item.end_date)}
                    </span>
                  </p>
                </div>
                <button
                  type="button"
                  disabled={removingId === item.festival_id}
                  onClick={() => void handleRemove(item.festival_id)}
                  aria-label={`${item.name} 찜 해제`}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-chip bg-surface-soft text-brand hover:bg-brand/15 disabled:opacity-60"
                >
                  <Heart className="h-4 w-4 fill-brand text-brand" aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function FavoritesView() {
  return (
    <RequireAuth nextPath="/favorites">
      <FavoritesSection />
    </RequireAuth>
  );
}
