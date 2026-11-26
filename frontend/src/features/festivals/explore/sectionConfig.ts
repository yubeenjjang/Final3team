export const FESTIVAL_SECTION_ORDER = ["popular", "personal", "new", "all"] as const;

export type FestivalSectionKey = (typeof FESTIVAL_SECTION_ORDER)[number];

export const FESTIVAL_SECTION_CONFIG: Record<
  FestivalSectionKey,
  { title: string; description?: string }
> = {
  popular: {
    title: "인기있는 축제",
    description: "지금 가장 많은 관심을 받는 축제예요!",
  },
  personal: {
    title: "나만을 위한 축제",
    description: "나의 취향과 선택에 맞춘 축제를 추천드려요!",
  },
  new: {
    title: "새로 올라온 축제",
    description: "최근 등록된 따끈한 축제 소식이에요!",
  },
  all: {
    title: "전체 축제",
  },
};

export function isFestivalSectionKey(value: string | undefined): value is FestivalSectionKey {
  return FESTIVAL_SECTION_ORDER.includes(value as FestivalSectionKey);
}
