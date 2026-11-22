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
  green: "bg-crowd-green text-ink",
  yellow: "bg-crowd-yellow text-ink",
  orange: "bg-crowd-orange text-ink",
  red: "bg-crowd-red text-ink",
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
  return CROWD_COLOR_CLASSES[color] ?? "bg-surface-soft text-ink";
}

/**
 * Translate notice type code to Korean badge text.
 */
export function getNoticeTypeLabel(type: NoticeType): string {
  return NOTICE_TYPE_LABELS[type] ?? "안내";
}

const SEOUL_TIME_ZONE = "Asia/Seoul";

const SEOUL_DATE_FORMATTER = new Intl.DateTimeFormat("en-CA", {
  timeZone: SEOUL_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

export function getSeoulDate(date = new Date()): string {
  const parts = SEOUL_DATE_FORMATTER.formatToParts(date);
  return ["year", "month", "day"]
    .map((type) => parts.find((part) => part.type === type)?.value)
    .join("-");
}

const KST_SHORT_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: SEOUL_TIME_ZONE,
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/**
 * Format ISO datetime string to compact Korean month/day time string in Asia/Seoul.
 */
export function formatDateTimeShort(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const parts = KST_SHORT_FORMATTER.formatToParts(date);
  const map: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== "literal") {
      map[part.type] = part.value;
    }
  }
  const month = map.month ?? "";
  const day = map.day ?? "";
  const hour = map.hour === "24" ? "00" : (map.hour ?? "");
  const minute = map.minute ?? "";
  return `${month}.${day} ${hour}:${minute}`;
}
