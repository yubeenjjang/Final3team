import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api/client";

export type RequestStatus = "pending" | "accepted" | "rejected" | "cancelled";
export type RequestAction = "accept" | "reject" | "cancel";
export type RequestBox = "received" | "sent";
export type FriendshipStatus =
  | "none"
  | "pending_sent"
  | "pending_received"
  | "friends";

export interface FriendSearchItem {
  user_id: string;
  display_name: string;
  friendship_status: FriendshipStatus;
}

export interface FriendSearchResult {
  items: FriendSearchItem[];
}

export interface FriendRequestResult {
  request_id: string;
  status: RequestStatus;
}

export interface FriendRequestItem extends FriendRequestResult {
  user_id: string;
  display_name: string | null;
  created_at: string;
}

export interface FriendRequestList {
  items: FriendRequestItem[];
}

export interface FriendItem {
  user_id: string;
  display_name: string | null;
  since: string;
}

export interface FriendList {
  items: FriendItem[];
}

export interface BlockResult {
  blocked: true;
}

export function searchUsersByNickname(
  nickname: string,
  signal?: AbortSignal,
): Promise<FriendSearchResult> {
  return apiGet<FriendSearchResult>("/users/search", {
    query: { nickname },
    signal,
  });
}

export function createFriendRequest(
  toUserId: string,
): Promise<FriendRequestResult> {
  return apiPost<FriendRequestResult>("/friend-requests", {
    to_user_id: toUserId,
  });
}

export function listFriendRequests(
  box: RequestBox = "received",
  signal?: AbortSignal,
): Promise<FriendRequestList> {
  return apiGet<FriendRequestList>("/me/friend-requests", {
    query: { box },
    signal,
  });
}

export function actOnFriendRequest(
  requestId: string,
  action: RequestAction,
): Promise<FriendRequestResult> {
  return apiPost<FriendRequestResult>(
    `/friend-requests/${encodeURIComponent(requestId)}/${action}`,
  );
}

export function listFriends(
  page = 1,
  signal?: AbortSignal,
): Promise<FriendList> {
  return apiGet<FriendList>("/me/friends", {
    query: { page },
    signal,
  });
}

export function deleteFriend(userId: string): Promise<void> {
  return apiDelete<void>(`/me/friends/${encodeURIComponent(userId)}`);
}

export function blockUser(userId: string): Promise<BlockResult> {
  return apiPut<BlockResult>(`/me/blocks/${encodeURIComponent(userId)}`);
}

export function unblockUser(userId: string): Promise<void> {
  return apiDelete<void>(`/me/blocks/${encodeURIComponent(userId)}`);
}
