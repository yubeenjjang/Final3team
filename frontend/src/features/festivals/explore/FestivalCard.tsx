import Image from "next/image";
import Link from "next/link";
import { CalendarDays, ImageOff, MapPin } from "lucide-react";
import type { FestivalListItem } from "./api";
import { dday, formatFestivalPeriod } from "./dday";
import { getRegionLabel } from "./regions";

export interface FestivalCardProps {
  item: FestivalListItem;
  today?: string;
}

export function FestivalCard({ item, today }: FestivalCardProps) {
  const badge =
    item.event_status === "cancelled"
      ? "취소"
      : dday(item.start_date, item.end_date, today);
  const period = formatFestivalPeriod(item.start_date, item.end_date);
  const regionLabel = getRegionLabel(item.region_code);
  const locationText = item.venue_name
    ? `${regionLabel} · ${item.venue_name}`
    : regionLabel;

  return (
    <Link
      href={`/festivals/${item.festival_id}`}
      data-testid={`festival-card-${item.festival_id}`}
      className="group block overflow-hidden rounded-card border border-line-light bg-surface shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="relative h-44 w-full overflow-hidden bg-surface-soft/50">
        {item.thumbnail_url ? (
          <>
            <Image
              src={item.thumbnail_url}
              alt={item.name}
              fill
              sizes="(max-width: 480px) 100vw, 448px"
              unoptimized
              className="object-contain p-1 transition-transform duration-200 group-hover:scale-[1.02]"
            />
            <span className="absolute bottom-2 right-2 rounded-chip bg-ink/70 px-2 py-0.5 text-[10px] font-medium text-surface backdrop-blur-sm">
              출처: 한국관광공사
            </span>
          </>
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-1.5 text-muted">
            <ImageOff className="h-6 w-6" aria-hidden="true" />
            <span className="text-xs font-medium">이미지 준비 중</span>
          </div>
        )}

        {badge ? (
          <span className="absolute left-3 top-3 rounded-chip bg-brand px-2.5 py-1 text-xs font-bold text-surface shadow-sm">
            {badge}
          </span>
        ) : null}
      </div>

      <div className="space-y-1.5 p-3.5">
        <h2 className="line-clamp-1 text-base font-extrabold text-ink">
          {item.name}
        </h2>
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <CalendarDays className="h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
          <span className="truncate">{period}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-accent" aria-hidden="true" />
          <span className="truncate">{locationText}</span>
        </div>
      </div>
    </Link>
  );
}
