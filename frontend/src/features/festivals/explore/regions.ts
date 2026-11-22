import type { components, operations } from "@/lib/api/schema";

export type RegionCode = components["schemas"]["FestivalListItem"]["region_code"];
export type RegionFilter = NonNullable<
  NonNullable<
    operations["list_festivals_api_v1_festivals_get"]["parameters"]["query"]
  >["region"]
>;
export type EventStatus = components["schemas"]["FestivalListItem"]["event_status"];
export type StatusFilter = "" | "ongoing" | "upcoming" | "ended";

export interface RegionOption {
  code: RegionFilter;
  label: string;
}

export const REGION_LABELS: Record<RegionCode, string> = {
  SEOUL: "서울",
  BUSAN: "부산",
  DAEGU: "대구",
  INCHEON: "인천",
  GWANGJU: "광주",
  DAEJEON: "대전",
  ULSAN: "울산",
  SEJONG: "세종",
  GYEONGGI: "경기",
  GANGWON: "강원",
  CHUNGBUK: "충북",
  CHUNGNAM: "충남",
  JEONBUK: "전북",
  JEONNAM: "전남",
  GYEONGBUK: "경북",
  GYEONGNAM: "경남",
  JEJU: "제주",
};

export const REGION_OPTIONS: RegionOption[] = [
  { code: "ALL", label: "전체" },
  ...(Object.entries(REGION_LABELS) as Array<[RegionCode, string]>).map(
    ([code, label]) => ({
      code,
      label,
    }),
  ),
];

export const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: "", label: "전체" },
  { value: "ongoing", label: "진행 중" },
  { value: "upcoming", label: "예정" },
  { value: "ended", label: "종료" },
];

/**
 * Convert an API region code to its Korean display name.
 */
export function getRegionLabel(code: RegionCode | "ALL"): string {
  if (code === "ALL") {
    return "전체";
  }
  return REGION_LABELS[code] ?? code;
}
