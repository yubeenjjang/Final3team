"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { CalendarDays, MapPin } from "lucide-react";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
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
        className="group block overflow-hidden rounded-card border border-line-light bg-surface shadow-sm transition-shadow hover:shadow-md"
      >
        <div className="relative aspect-[1/1.414] w-full overflow-hidden bg-surface-soft/45">
          {showImage && item.thumbnail_url ? (
            <>
              <Image
                src={item.thumbnail_url}
                alt={item.name}
                fill
                sizes="(max-width: 359px) 40vw, (max-width: 767px) 29vw, 180px"
                unoptimized
                onError={() => setFailedSrc(item.thumbnail_url ?? null)}
                className="object-contain p-1 transition-transform duration-200 group-hover:scale-[1.02]"
              />
              <span className="absolute bottom-1.5 right-1.5 rounded-chip bg-ink/70 px-1.5 py-0.5 text-[8px] font-medium text-surface backdrop-blur-sm">
                출처: 한국관광공사
              </span>
            </>
          ) : (
            <FestivalImagePlaceholder />
          )}

          {badge ? (
            <span className="absolute left-1.5 top-1.5 rounded-chip bg-brand px-1.5 py-0.5 text-[10px] font-extrabold text-surface shadow-sm">
              {badge}
            </span>
          ) : null}
        </div>

        <div className="space-y-1 p-2">
          <h2 className="line-clamp-2 text-xs font-extrabold leading-tight text-ink">
            {item.name}
          </h2>
          <div className="flex items-center gap-1 text-[10px] text-muted">
            <CalendarDays className="h-3 w-3 shrink-0 text-brand" aria-hidden="true" />
            <span className="truncate">{period}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-muted">
            <MapPin className="h-3 w-3 shrink-0 text-brand" aria-hidden="true" />
            <span className="truncate">{locationText}</span>
          </div>
        </div>
      </Link>

    </div>
  );
}
