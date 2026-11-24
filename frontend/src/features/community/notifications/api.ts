import { apiGet, apiPost } from "@/lib/api/client";

export interface NotificationItem {
  notification_id: number;
  type: string;
  ref_type: string;
  ref_id: string;
  created_at: string;
  read_at: string | null;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  unread_count: number;
}

export function listNotifications(
  params: { unread_only?: boolean; page?: number } = {},
  signal?: AbortSignal,
): Promise<NotificationsResponse> {
  return apiGet<NotificationsResponse>("/me/notifications", {
    query: {
      unread_only: params.unread_only ? true : undefined,
      page: params.page ?? 1,
    },
    signal,
  });
}

export function markNotificationsRead(ids: number[]): Promise<void> {
  return apiPost<void>("/me/notifications/read", { ids });
}

export function markAllNotificationsRead(): Promise<void> {
  return apiPost<void>("/me/notifications/read", { all: true });
}
