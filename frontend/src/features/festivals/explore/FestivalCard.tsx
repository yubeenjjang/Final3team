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
    <div className={`relative min-w-0 ${className}`}>
      <Link
        href={`/festivals/${item.festival_id}`}
        data-testid={`festival-card-${item.festival_id}`}
        className="group block w-full min-w-0 overflow-hidden rounded-card-lg bg-surface shadow-card transition-shadow hover:shadow-md"
      >
        <div className="relative aspect-[3/2] w-full overflow-hidden bg-surface-soft/45">
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
              <span className="absolute bottom-7 right-1 rounded-chip bg-ink/35 px-1.5 py-0.5 text-[6px] font-medium text-surface/90 backdrop-blur-sm">
                출처: {item.image_credit ?? "제공 이미지"}
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
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/70 via-ink/25 to-transparent px-2.5 pb-2 pt-5 text-surface">
            <h2 className="truncate text-[12px] font-black leading-tight">{item.name}</h2>
          </div>
        </div>
        <div className="space-y-1 px-2.5 py-2 text-ink">
          <div className="flex items-center gap-1 text-[9px] font-semibold">
            <CalendarDays className="h-3 w-3 shrink-0" aria-hidden="true" />
            <span className="truncate">{period}</span>
          </div>
          <div className="flex items-center gap-1 text-[9px] font-semibold text-muted">
            <MapPin className="h-3 w-3 shrink-0" aria-hidden="true" />
            <span className="truncate">{locationText}</span>
          </div>
        </div>
      </Link>
      <FavoriteButton
        festivalId={item.festival_id}
        appearance="icon"
        className="absolute right-0 top-0 z-10"
      />
    </div>
  );
}
