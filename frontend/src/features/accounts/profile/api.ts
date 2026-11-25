import { apiDelete, apiGet, apiPatch, apiPut } from "@/lib/api/client";

export type Scenario =
  | "family_relaxed"
  | "friends_activity"
  | "couple_photo"
  | "pet"
  | "solo";

export type OnboardingStatus = "pending" | "completed" | "skipped";

export interface Profile {
  user_id: string;
  display_name: string | null;
  birth_year: number | null;
  gender: "male" | "female" | null;
  onboarding_status: OnboardingStatus;
}

export interface FestivalPreferences {
  scenarios: Scenario[];
  onboarding_status: OnboardingStatus;
  updated_at: string | null;
}

export const SCENARIO_OPTIONS: {
  value: Scenario;
  tag: string;
  title: string;
  description: string;
}[] = [
  {
    value: "family_relaxed",
    tag: "가족과 함께",
    title: "가족과 즐기는 한가로운 축제",
    description: "아이와 부모님 모두 편하게 쉬어갈 수 있는 축제",
  },
  {
    value: "friends_activity",
    tag: "친구와 액티비티",
    title: "친구와 함께하는 체험·공연 축제",
    description: "직접 참여하고 즐길 거리가 풍부한 축제",
  },
  {
    value: "couple_photo",
    tag: "연인과 포토존",
    title: "연인과 남기는 포토존·야경 축제",
    description: "야경과 조명이 아름답고 사진 찍기 좋은 축제",
  },
  {
    value: "pet",
    tag: "반려견 동반",
    title: "반려견과 함께하는 축제",
    description: "반려견 동반 입장이 공식 안내된 축제",
  },
  {
    value: "solo",
    tag: "혼자 즐기기",
    title: "혼자서도 편하게 즐기는 축제",
    description: "전시·관람·야시장 등 혼자 둘러보기 좋은 축제",
  },
];

export function getProfile(signal?: AbortSignal): Promise<Profile> {
  return apiGet<Profile>("/me/profile", { signal });
}

export function updateProfile(displayName: string): Promise<Profile> {
  return apiPatch<Profile>("/me/profile", { display_name: displayName });
}

export function getFestivalPreferences(
  signal?: AbortSignal,
): Promise<FestivalPreferences> {
  return apiGet<FestivalPreferences>("/me/festival-preferences", { signal });
}

export function saveFestivalPreferences(body: {
  scenarios: Scenario[];
  skip: boolean;
}): Promise<FestivalPreferences> {
  return apiPut<FestivalPreferences>("/me/festival-preferences", body);
}

export function deleteAccount(password: string): Promise<void> {
  return apiDelete<void>("/me", { body: { password } });
}
