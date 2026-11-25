"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { CalendarDays, MapPin } from "lucide-react";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import type { FestivalListItem } from "./api";
import { dday, formatFestivalPeriod } from "./dday";
import { getRegionLabel } from "./regions";

export interface FestivalCardProps {
  item: FestivalListItem;
  today?: string;
  className?: string;
}

export function FestivalCard({
  item,
  today,
  className = "",
}: FestivalCardProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const badge =
    item.event_status === "cancelled"
      ? "취소"
      : dday(item.start_date, item.end_date, today);
  const period = formatFestivalPeriod(item.start_date, item.end_date);
  const regionLabel = getRegionLabel(item.region_code);
  const locationText = item.venue_name
    ? `${regionLabel} · ${item.venue_name}`
    : regionLabel;
  const showImage = Boolean(item.thumbnail_url) && failedSrc !== item.thumbnail_url;

  return (
    <div className={`relative ${className}`}>
      <Link
        href={`/festivals/${item.festival_id}`}
        data-testid={`festival-card-${item.festival_id}`}
        className="group block overflow-hidden rounded-card-lg bg-surface shadow-card transition-shadow hover:shadow-md"
      >
        <div className="relative aspect-[1/1.414] w-full overflow-hidden bg-surface-soft/45">
          {showImage && item.thumbnail_url ? (
            <>
              <Image
                src={item.thumbnail_url}
                alt={item.name}
                fill
                sizes="(max-width: 767px) 40vw, 180px"
                unoptimized
                onError={() => setFailedSrc(item.thumbnail_url ?? null)}
                className="bg-ink/5 object-cover object-center transition-transform duration-200 group-hover:scale-[1.02]"
              />
              <span className="absolute bottom-1 right-1 rounded-chip bg-ink/55 px-1.5 py-0.5 text-[7px] font-medium text-surface/80 backdrop-blur-sm">
                출처: 한국관광공사
              </span>
            </>
          ) : (
            <FestivalImagePlaceholder />
          )}

          {badge ? (
            <span className="absolute left-2 top-2 rounded-chip bg-brand px-2.5 py-1 text-[11px] font-extrabold text-surface shadow-sm">
              {badge}
            </span>
          ) : null}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink via-ink/85 to-transparent px-2.5 pb-3 pt-12 text-surface">
            <h2 className="line-clamp-2 text-[13px] font-black leading-tight">{item.name}</h2>
            <div className="mt-2 flex items-center gap-1 text-[9px] font-semibold text-surface/90">
              <CalendarDays className="h-3 w-3 shrink-0" aria-hidden="true" /><span className="truncate">{period}</span>
            </div>
            <div className="mt-0.5 flex items-center gap-1 text-[9px] font-semibold text-surface/90">
              <MapPin className="h-3 w-3 shrink-0" aria-hidden="true" /><span className="truncate">{locationText}</span>
            </div>
          </div>
        </div>
      </Link>
      <FavoriteButton festivalId={item.festival_id} className="absolute right-1.5 top-1.5 z-10" />
    </div>
  );
}
