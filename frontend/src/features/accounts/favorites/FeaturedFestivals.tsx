"use client";

import Image from "next/image";
import Link from "next/link";
import { CalendarDays, ChevronRight, Heart, MapPin } from "lucide-react";
import { useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { LoginPromptSheet } from "@/components/LoginPromptSheet";
import { getAuthUser, getAuthUserServerSnapshot, subscribeAuth } from "@/lib/api/auth";
import { listFestivals, type FestivalListItem } from "@/features/festivals/explore/api";
import { dday, formatFestivalPeriod } from "@/features/festivals/explore/dday";
import { getRegionLabel } from "@/features/festivals/explore/regions";
import { useFestivalFavorites } from "./useFestivalFavorites";

function FeaturedCard({ item, heart }: { item: FestivalListItem; heart: ReactNode }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const period = formatFestivalPeriod(item.start_date, item.end_date);
  const region = getRegionLabel(item.region_code);
  const badge =
    item.event_status === "cancelled"
      ? "취소"
      : dday(item.start_date, item.end_date);
  const hasPhoto = Boolean(item.thumbnail_url) && failedSrc !== item.thumbnail_url;

  return (
    <li className="relative w-[138px] shrink-0 snap-start overflow-hidden rounded-card border border-line-light bg-surface shadow-md sm:w-[144px]">
      <Link href={`/festivals/${encodeURIComponent(item.festival_id)}`} className="block">
        <div className="relative h-[186px] w-full overflow-hidden">
          {hasPhoto && item.thumbnail_url ? (
            <Image
              src={item.thumbnail_url}
              alt=""
              fill
              sizes="150px"
              unoptimized
              onError={() => setFailedSrc(item.thumbnail_url)}
              className="object-cover"
            />
          ) : (
            <FestivalImagePlaceholder compact className="pb-16" />
          )}

          {badge && (
            <span className="absolute left-2 top-2 rounded-chip bg-brand px-2 py-0.5 text-[10px] font-extrabold text-surface shadow-sm">
              {badge}
            </span>
          )}

          <div
            className={`absolute inset-x-0 bottom-0 px-2.5 pb-2.5 ${
              hasPhoto
                ? "bg-gradient-to-t from-ink/90 via-ink/60 to-transparent pt-10 text-surface"
                : "border-t border-line-light bg-surface/95 pt-2 text-ink"
            }`}
          >
            <h3 className="line-clamp-2 text-xs font-extrabold leading-tight sm:text-[13px]">
              {item.name}
            </h3>
            <div
              className={`mt-1.5 flex items-center justify-between gap-1 text-[10px] leading-tight ${
                hasPhoto ? "text-surface/90" : "text-muted"
              }`}
            >
              <span className="flex min-w-0 items-center gap-0.5" title={period}>
                <CalendarDays size={10} className="shrink-0" aria-hidden="true" />
                <span className="truncate">{period}</span>
              </span>
              <span className="flex shrink-0 items-center gap-0.5" title={region}>
                <MapPin size={10} className="shrink-0" aria-hidden="true" />
                <span>{region}</span>
              </span>
            </div>
          </div>
        </div>
      </Link>
      <div className="absolute right-1.5 top-1.5">{heart}</div>
    </li>
  );
}

const heartClass =
  "grid h-7 w-7 place-items-center rounded-chip bg-ink/35 text-surface backdrop-blur-sm transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-60";

function SignedInCards({ items }: { items: FestivalListItem[] }) {
  const ids = useMemo(() => items.map((item) => item.festival_id), [items]);
  const { savedIds, busyIds, error, toggle } = useFestivalFavorites(ids);

  return (
    <>
      {error && <p role="alert" className="mb-2 text-xs font-medium text-brand">{error}</p>}
      <ul className="flex snap-x snap-mandatory gap-2.5 overflow-x-auto pb-1">
        {items.map((item) => {
          const saved = savedIds?.has(item.festival_id) ?? false;
          return (
            <FeaturedCard
              key={item.festival_id}
              item={item}
              heart={
                <button
                  type="button"
                  className={heartClass}
                  aria-label={`${item.name} ${saved ? "찜 해제" : "찜하기"}`}
                  aria-pressed={saved}
                  disabled={!savedIds || busyIds.has(item.festival_id)}
                  onClick={() => void toggle(item.festival_id)}
                >
                  <Heart
                    size={15}
                    className={saved ? "fill-brand text-brand" : "text-surface"}
                    aria-hidden="true"
                  />
                </button>
              }
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
  const [loginPromptOpen, setLoginPromptOpen] = useState(false);

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
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="featured-title" className="flex items-center gap-2 text-base font-extrabold tracking-tight text-ink">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          지금, 여기서 열리는 축제
        </h2>
        <Link
          href="/festivals"
          className="flex shrink-0 items-center gap-0.5 text-xs font-semibold text-muted transition-colors hover:text-brand"
        >
          전체보기 <ChevronRight size={14} aria-hidden="true" />
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
        <div role="status" className="flex min-h-[186px] items-center justify-center rounded-card border border-line-light bg-surface-muted/50 text-sm text-muted">
          축제를 불러오는 중이에요.
        </div>
      ) : items.length === 0 ? (
        <div className="flex min-h-24 items-center justify-center rounded-card border border-line-light bg-surface-muted/50 px-4 text-sm text-muted">
          진행 중인 축제가 없어요.
        </div>
      ) : user ? (
        <SignedInCards key={user.userId} items={items} />
      ) : (
        <ul className="flex snap-x snap-mandatory gap-2.5 overflow-x-auto pb-1">
          {items.map((item) => (
            <FeaturedCard
              key={item.festival_id}
              item={item}
              heart={
                <button
                  type="button"
                  onClick={() => setLoginPromptOpen(true)}
                  className={heartClass}
                  aria-label={`${item.name} 찜하기`}
                >
                  <Heart size={15} className="text-surface" aria-hidden="true" />
                </button>
              }
            />
          ))}
        </ul>
      )}
      <LoginPromptSheet
        open={loginPromptOpen}
        onClose={() => setLoginPromptOpen(false)}
        nextPath="/"
      />
    </section>
  );
}
