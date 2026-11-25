import type {
  AgePreference,
  ApplicationStatus,
  GenderPreference,
  PostStatus,
} from "./api";

export const POST_STATUS_META: Record<
  PostStatus,
  { label: string; className: string }
> = {
  open: {
    label: "모집 중",
    className: "bg-surface-soft text-brand",
  },
  full: {
    label: "정원 마감",
    className: "bg-banner-dark text-surface",
  },
  ended: {
    label: "종료",
    className: "bg-surface-muted text-muted",
  },
  cancelled: {
    label: "취소됨",
    className: "bg-surface-muted text-muted",
  },
};

export const AGE_PREF_OPTIONS: { value: AgePreference; label: string }[] = [
  { value: "any", label: "연령 무관" },
  { value: "20s", label: "20대" },
  { value: "30s", label: "30대" },
  { value: "40s", label: "40대" },
  { value: "50s_plus", label: "50대 이상" },
];

export const GENDER_PREF_OPTIONS: { value: GenderPreference; label: string }[] = [
  { value: "any", label: "성별 무관" },
  { value: "female", label: "여성" },
  { value: "male", label: "남성" },
];

export const APPLICATION_STATUS_LABEL: Record<ApplicationStatus, string> = {
  pending: "승인 대기",
  approved: "승인 완료",
  rejected: "거절됨",
  cancelled: "취소됨",
};

export function getAgePrefLabel(value: AgePreference | null): string {
  if (!value) return "연령 무관";
  return AGE_PREF_OPTIONS.find((item) => item.value === value)?.label ?? "연령 무관";
}

export function getGenderPrefLabel(value: GenderPreference): string {
  return GENDER_PREF_OPTIONS.find((item) => item.value === value)?.label ?? "성별 무관";
}

export function formatKstDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function toKstIsoString(localDateTime: string): string {
  if (!localDateTime) return "";
  return localDateTime.length === 16 ? `${localDateTime}:00+09:00` : `${localDateTime}+09:00`;
}
