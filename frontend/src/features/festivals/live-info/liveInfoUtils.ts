import type { components } from "@/lib/api/schema";

export type CrowdColor = components["schemas"]["CrowdArea"]["congest_color"];
export type PrecipitationType =
  components["schemas"]["WeatherData"]["precipitation_type"];
export type NoticeType = components["schemas"]["Notice"]["type"];

const PRECIPITATION_LABELS: Record<PrecipitationType, string> = {
  none: "강수 없음",
  rain: "비",
  rain_snow: "비/눈",
  snow: "눈",
  drizzle: "빗방울",
  drizzle_snow: "빗방울/눈날림",
  snow_flurry: "눈날림",
};

const CROWD_COLOR_CLASSES: Record<CrowdColor, string> = {
  green: "bg-crowd-green text-surface",
  yellow: "bg-crowd-yellow text-ink",
  orange: "bg-crowd-orange text-surface",
  red: "bg-crowd-red text-surface",
};

const NOTICE_TYPE_LABELS: Record<NoticeType, string> = {
  operation: "운영 안내",
  traffic_control: "교통 통제",
  no_stop: "무정차",
  bus_detour: "버스 우회",
  road_closure: "도로 통제",
};

/**
 * Translate weather precipitation code to Korean text per SPEC F7.
 */
export function getPrecipitationLabel(type: PrecipitationType): string {
  return PRECIPITATION_LABELS[type] ?? "강수 없음";
}

/**
 * Map API crowd color token to Tailwind design token classes.
 */
export function getCrowdColorClass(color: CrowdColor): string {
  return CROWD_COLOR_CLASSES[color] ?? "bg-muted text-surface";
}

/**
 * Translate notice type code to Korean badge text.
 */
export function getNoticeTypeLabel(type: NoticeType): string {
  return NOTICE_TYPE_LABELS[type] ?? "안내";
}

/**
 * Format ISO datetime string to compact Korean month/day time string.
 */
export function formatDateTimeShort(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}.${day} ${hours}:${minutes}`;
}
