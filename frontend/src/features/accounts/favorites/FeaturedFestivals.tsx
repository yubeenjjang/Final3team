"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, CalendarDays, Heart, ImageOff, MapPin } from "lucide-react";
import { useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { getAuthUser, getAuthUserServerSnapshot, subscribeAuth } from "@/lib/api/auth";
import { listFestivals, type FestivalListItem } from "@/features/festivals/explore/api";
import { formatFestivalPeriod } from "@/features/festivals/explore/dday";
import { getRegionLabel } from "@/features/festivals/explore/regions";
import { useFestivalFavorites } from "./useFestivalFavorites";

function FeaturedCard({ item, heart }: { item: FestivalListItem; heart: ReactNode }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const period = formatFestivalPeriod(item.start_date, item.end_date);
  const location = item.venue_name || getRegionLabel(item.region_code);

  return (
    <li className="relative min-w-0 snap-start overflow-hidden rounded-2xl border border-line-dark bg-dark-surface">
      <Link href={`/festivals/${encodeURIComponent(item.festival_id)}`} className="block">
        <div className="relative flex aspect-[1.24] items-center justify-center bg-gradient-to-br from-accent/30 to-dark-bg">
          {item.thumbnail_url && failedSrc !== item.thumbnail_url ? (
            <Image
              src={item.thumbnail_url}
              alt=""
              fill
              sizes="(max-width: 480px) 33vw, 150px"
              unoptimized
              onError={() => setFailedSrc(item.thumbnail_url)}
              className="object-cover"
            />
          ) : (
            <ImageOff className="text-dark-muted" size={22} aria-hidden="true" />
          )}
          {item.event_status === "ongoing" && (
            <span className="absolute left-1.5 top-1.5 rounded-chip bg-neon px-1.5 py-0.5 text-[10px] font-extrabold text-ink">
              진행 중
            </span>
          )}
          <h3 className="absolute inset-x-0 bottom-0 line-clamp-2 bg-gradient-to-t from-dark-bg via-dark-bg/85 to-transparent px-2 pb-1.5 pt-5 text-xs font-extrabold leading-tight sm:text-sm">
            {item.name}
          </h3>
        </div>
        <div className="space-y-1 px-2 py-2 text-[10px] leading-tight text-surface/85">
          <p className="flex items-start gap-1" title={period}>
            <CalendarDays size={12} className="shrink-0" aria-hidden="true" />
            <span className="min-w-0 break-words">{period}</span>
          </p>
          <p className="flex items-center gap-1" title={location}>
            <MapPin size={12} className="shrink-0" aria-hidden="true" />
            <span className="truncate">{location}</span>
          </p>
        </div>
      </Link>
      <div className="absolute right-0.5 top-0.5">{heart}</div>
    </li>
  );
}

const heartClass = "grid h-8 w-8 place-items-center rounded-chip bg-dark-bg/60 text-surface focus-visible:ring-2 focus-visible:ring-neon disabled:opacity-60";

function SignedInCards({ items }: { items: FestivalListItem[] }) {
  const ids = useMemo(() => items.map((item) => item.festival_id), [items]);
  const { savedIds, busyIds, error, toggle } = useFestivalFavorites(ids);

  return (
    <>
      {error && <p role="alert" className="mb-2 text-xs text-surface">{error}</p>}
      <ul className="grid grid-cols-3 gap-2">
        {items.map((item) => {
          const saved = savedIds?.has(item.festival_id) ?? false;
          return (
            <FeaturedCard
              key={item.festival_id}
              item={item}
              heart={(
                <button
                  type="button"
                  className={heartClass}
                  aria-label={`${item.name} ${saved ? "찜 해제" : "찜하기"}`}
                  aria-pressed={saved}
                  disabled={!savedIds || busyIds.has(item.festival_id)}
                  onClick={() => void toggle(item.festival_id)}
                >
                  <Heart size={17} className={saved ? "fill-neon text-neon" : ""} aria-hidden="true" />
                </button>
              )}
            />
          );
        })}
      </ul>
    </>
  );
}

export function FeaturedFestivals() {
  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUserServerSnapshot);
  const [items, setItems] = useState<FestivalListItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    // 추천 API가 연결될 때까지 진행 중인 축제 중 앞의 세 개를 사용한다.
    listFestivals({ status: "ongoing", page: 1, page_size: 3 }, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setItems(result.items.slice(0, 3));
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [attempt]);

  return (
    <section aria-labelledby="featured-title">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 id="featured-title" className="flex items-center gap-2 text-lg font-black tracking-tight">
          <span className="h-4 w-1.5 rounded-chip bg-neon" aria-hidden="true" />
          지금 주목할 축제
        </h2>
        <Link href="/festivals" className="flex shrink-0 items-center gap-1 text-xs font-semibold">
          더보기 <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </div>

      {failed ? (
        <div className="flex min-h-24 items-center justify-between gap-2 rounded-card border border-line-dark px-3 text-sm">
          <p role="alert">축제를 불러오지 못했어요.</p>
          <button type="button" className="shrink-0 text-neon" onClick={() => {
            setFailed(false);
            setAttempt((value) => value + 1);
          }}>
            다시 시도
          </button>
        </div>
      ) : !items ? (
        <p role="status" className="min-h-24 py-4 text-sm text-dark-muted">축제를 불러오는 중이에요.</p>
      ) : items.length === 0 ? (
        <p className="min-h-24 py-4 text-sm text-dark-muted">진행 중인 축제가 없어요.</p>
      ) : user ? (
        <SignedInCards key={user.userId} items={items} />
      ) : (
        <ul className="grid grid-cols-3 gap-2">
          {items.map((item) => (
            <FeaturedCard key={item.festival_id} item={item} heart={(
              <Link href="/auth/login?next=%2F" className={heartClass} aria-label={`${item.name} 찜하기`}>
                <Heart size={17} aria-hidden="true" />
              </Link>
            )} />
          ))}
        </ul>
      )}
    </section>
  );
}
