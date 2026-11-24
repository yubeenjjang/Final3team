import { apiGet, apiPatch, apiPost, apiPut } from "@/lib/api/client";

export type PostStatus = "open" | "full" | "ended" | "cancelled";
export type ApplicationStatus = "pending" | "approved" | "rejected" | "cancelled";
export type VisibleApplicationStatus = "pending" | "approved";
export type ApplicationAction = "approve" | "reject" | "cancel";
export type PostAction = "close" | "end" | "cancel";
export type AgePreference = "any" | "20s" | "30s" | "40s" | "50s_plus";
export type GenderPreference = "any" | "female" | "male";

export interface CompanionPostItem {
  post_id: string;
  author_display_name: string | null;
  meet_at: string;
  capacity: number;
  approved_count: number;
  age_pref: AgePreference | null;
  gender_pref: GenderPreference;
  memo: string | null;
  status: PostStatus;
}

export interface CompanionPostDetail extends CompanionPostItem {
  my_application_status: ApplicationStatus | null;
}

export interface CompanionPostList {
  items: CompanionPostItem[];
}

export interface CompanionPostCreateInput {
  festival_id: string;
  meet_at: string;
  capacity: number;
  age_pref?: AgePreference | null;
  gender_pref?: GenderPreference;
  memo?: string | null;
}

export interface CompanionPostCreated {
  post_id: string;
  room_id: string;
}

export interface CompanionPostUpdateInput {
  meet_at?: string;
  capacity?: number;
  age_pref?: AgePreference | null;
  gender_pref?: GenderPreference;
  memo?: string | null;
}

export interface CompanionPostChanged {
  post_id: string;
  status: PostStatus;
}

export interface CompanionApplicationCreateInput {
  message?: string | null;
}

export interface CompanionApplicationCreated {
  application_id: string;
  status: "pending";
}

export interface CompanionApplicationItem {
  application_id: string;
  applicant_display_name: string | null;
  applicant_age: number | null;
  applicant_gender: "male" | "female" | null;
  message: string | null;
  status: VisibleApplicationStatus;
  created_at: string;
}

export interface CompanionApplicationList {
  items: CompanionApplicationItem[];
}

export interface CompanionApplicationChanged {
  application_id: string;
  status: "approved" | "rejected" | "cancelled";
  post_status: PostStatus;
}

export interface MeetingPlaceInput {
  name: string;
  address?: string | null;
  lat?: number | null;
  lng?: number | null;
  guide?: string | null;
}

export interface MeetingPlaceDetail extends MeetingPlaceInput {
  updated_at: string;
}

export interface MeetingPlaceUndecided {
  status: "undecided";
}

export type MeetingPlaceResponse = MeetingPlaceDetail | MeetingPlaceUndecided;

export interface MeetingPlaceUpdated {
  post_id: string;
  updated_at: string;
}

export interface MyCompanionPostItem {
  post_id: string;
  festival_id: string;
  meet_at: string;
  capacity: number;
  approved_count: number;
  age_pref: AgePreference | null;
  gender_pref: GenderPreference;
  memo: string | null;
  status: PostStatus;
}

export interface MyCompanionApplicationItem {
  application_id: string;
  post_id: string;
  message: string | null;
  status: ApplicationStatus;
  created_at: string;
}

export function isMeetingPlaceUndecided(
  place: MeetingPlaceResponse,
): place is MeetingPlaceUndecided {
  return "status" in place && place.status === "undecided";
}

export function companionRoomIdFromPostId(postId: string): string {
  return postId.startsWith("cpo_") ? `crm_${postId.slice(4)}` : postId;
}

export function listCompanionPosts(
  festivalId: string,
  params: { status?: PostStatus; page?: number } = {},
  signal?: AbortSignal,
): Promise<CompanionPostList> {
  return apiGet<CompanionPostList>(
    `/festivals/${encodeURIComponent(festivalId)}/companion-posts`,
    {
      query: { status: params.status ?? "open", page: params.page ?? 1 },
      signal,
    },
  );
}

export function createCompanionPost(
  body: CompanionPostCreateInput,
): Promise<CompanionPostCreated> {
  return apiPost<CompanionPostCreated>("/companion-posts", body);
}

export function getCompanionPost(
  postId: string,
  signal?: AbortSignal,
): Promise<CompanionPostDetail> {
  return apiGet<CompanionPostDetail>(
    `/companion-posts/${encodeURIComponent(postId)}`,
    { signal },
  );
}

export function updateCompanionPost(
  postId: string,
  body: CompanionPostUpdateInput,
): Promise<CompanionPostChanged> {
  return apiPatch<CompanionPostChanged>(
    `/companion-posts/${encodeURIComponent(postId)}`,
    body,
  );
}

export function applyToCompanionPost(
  postId: string,
  body: CompanionApplicationCreateInput = {},
): Promise<CompanionApplicationCreated> {
  return apiPost<CompanionApplicationCreated>(
    `/companion-posts/${encodeURIComponent(postId)}/applications`,
    body,
  );
}

export function listCompanionApplications(
  postId: string,
  status?: VisibleApplicationStatus,
  signal?: AbortSignal,
): Promise<CompanionApplicationList> {
  return apiGet<CompanionApplicationList>(
    `/companion-posts/${encodeURIComponent(postId)}/applications`,
    { query: { status }, signal },
  );
}

export function decideCompanionApplication(
  applicationId: string,
  action: ApplicationAction,
): Promise<CompanionApplicationChanged> {
  return apiPost<CompanionApplicationChanged>(
    `/companion-applications/${encodeURIComponent(applicationId)}/${action}`,
  );
}

export function getMeetingPlace(
  postId: string,
  signal?: AbortSignal,
): Promise<MeetingPlaceResponse> {
  return apiGet<MeetingPlaceResponse>(
    `/companion-posts/${encodeURIComponent(postId)}/meeting-place`,
    { signal },
  );
}

export function setMeetingPlace(
  postId: string,
  body: MeetingPlaceInput,
): Promise<MeetingPlaceUpdated> {
  return apiPut<MeetingPlaceUpdated>(
    `/companion-posts/${encodeURIComponent(postId)}/meeting-place`,
    body,
  );
}

export function changeCompanionPost(
  postId: string,
  action: PostAction,
): Promise<CompanionPostChanged> {
  return apiPost<CompanionPostChanged>(
    `/companion-posts/${encodeURIComponent(postId)}/${action}`,
  );
}

export function listMyCompanionPosts(
  signal?: AbortSignal,
): Promise<{ items: MyCompanionPostItem[] }> {
  return apiGet<{ items: MyCompanionPostItem[] }>("/me/companion-activity", {
    query: { type: "posts" },
    signal,
  });
}

export function listMyCompanionApplications(
  signal?: AbortSignal,
): Promise<{ items: MyCompanionApplicationItem[] }> {
  return apiGet<{ items: MyCompanionApplicationItem[] }>("/me/companion-activity", {
    query: { type: "applications" },
    signal,
  });
}
