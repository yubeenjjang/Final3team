import { FACILITY_GROUPS, type FacilityCategory, type FacilityGroup } from "./api";

function isFacilityGroup(value: string | undefined): value is FacilityGroup {
  return value !== undefined && Object.prototype.hasOwnProperty.call(FACILITY_GROUPS, value);
}

// 축제 상세 '주변 정보'에서 넘어온 /map?festival=&group=&category= 값. 잘못된 값은 무시한다.
export function parseMapSelection(params: {
  festival?: string;
  group?: string;
  category?: string;
}): {
  festivalId: string | null;
  group: FacilityGroup;
  category: FacilityCategory | "all";
} {
  const group = isFacilityGroup(params.group) ? params.group : "transport";
  const categories: readonly string[] = FACILITY_GROUPS[group];
  const category =
    isFacilityGroup(params.group) && params.category && categories.includes(params.category)
      ? (params.category as FacilityCategory)
      : "all";
  const festivalId = params.festival?.trim() ? params.festival.trim().slice(0, 64) : null;
  return { festivalId, group, category };
}
