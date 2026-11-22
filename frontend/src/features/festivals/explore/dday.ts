import { getSeoulDate } from "../live-info/liveInfoUtils";

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function parseUtcDate(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const match = DATE_PATTERN.exec(value.trim());
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const timestamp = Date.UTC(year, month - 1, day);
  const check = new Date(timestamp);
  if (
    check.getUTCFullYear() !== year ||
    check.getUTCMonth() !== month - 1 ||
    check.getUTCDate() !== day
  ) {
    return null;
  }
  return timestamp;
}

function resolveTodayUtc(today?: string | Date): number | null {
  if (typeof today === "string") {
    return parseUtcDate(today);
  }
  const now = today instanceof Date ? today : new Date();
  if (Number.isNaN(now.getTime())) {
    return null;
  }
  return parseUtcDate(getSeoulDate(now));
}

/**
 * Compute Korean D-day badge label from festival start/end YYYY-MM-DD dates.
 */
export function dday(
  start: string | null | undefined,
  end: string | null | undefined,
  today?: string | Date,
): string {
  const startMs = parseUtcDate(start);
  if (startMs === null) {
    return "";
  }
  const todayMs = resolveTodayUtc(today);
  if (todayMs === null) {
    return "";
  }

  if (todayMs < startMs) {
    const diffDays = Math.round((startMs - todayMs) / MS_PER_DAY);
    return `D-${diffDays}`;
  }

  const endMs = parseUtcDate(end);
  if (endMs === null) {
    return todayMs === startMs ? "진행 중" : "";
  }

  if (todayMs <= endMs) {
    return "진행 중";
  }

  return "종료";
}

/**
 * Format festival period dates for display.
 */
export function formatFestivalPeriod(
  start: string | null | undefined,
  end: string | null | undefined,
): string {
  if (!start && !end) {
    return "일정 미정";
  }
  const formatDot = (raw: string) => raw.replaceAll("-", ".");
  if (start && end) {
    return start === end
      ? formatDot(start)
      : `${formatDot(start)} ~ ${formatDot(end)}`;
  }
  return formatDot(start ?? end ?? "");
}
