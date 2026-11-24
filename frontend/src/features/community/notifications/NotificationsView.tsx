"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bell, CheckCheck, RotateCcw } from "lucide-react";
import { handleAuthError, RequireAuth } from "@/components/RequireAuth";
import { ApiError } from "@/lib/api/client";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationsRead,
  type NotificationItem,
} from "./api";

function notificationLabel(type: string): string {
  switch (type) {
    case "room_invited":
      return "새 단체 채팅방에 초대됐어요";
    case "companion_applied":
      return "내 동행 모집 글에 새 신청이 왔어요";
    case "companion_approved":
      return "동행 신청이 승인됐어요";
    case "companion_rejected":
      return "동행 신청이 거절됐어요";
    case "meeting_place_changed":
      return "동행 만남 장소가 변경됐어요";
    case "companion_ended":
      return "동행 일정이 종료됐어요";
    case "companion_cancelled":
      return "동행 모집이 취소됐어요";
    default:
      return "새 알림이 도착했어요";
  }
}

function notificationHref(item: NotificationItem): string | null {
  if (item.ref_type === "chat_room") {
    return `/chats/${encodeURIComponent(item.ref_id)}`;
  }
  if (item.ref_type === "companion_post") {
    return `/companions/${encodeURIComponent(item.ref_id)}`;
  }
  if (item.ref_type === "companion_application") {
    return "/companions?tab=mine";
  }
  return null;
}

function formatNotifTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

export function NotificationsSection({ embedded = false }: { embedded?: boolean }) {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await listNotifications(
          { unread_only: unreadOnly, page: 1 },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setItems(res.items);
        setUnreadCount(res.unread_count);
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        setItems([]);
        setError(
          cause instanceof ApiError
            ? cause.message
            : "알림 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [unreadOnly, reloadTick]);

  async function handleReadOne(id: number) {
    if (busy) return;
    setBusy(true);
    try {
      await markNotificationsRead([id]);
      const nowIso = new Date().toISOString();
      setItems((prev) =>
        unreadOnly
          ? prev.filter((item) => item.notification_id !== id)
          : prev.map((item) =>
              item.notification_id === id ? { ...item, read_at: nowIso } : item,
            ),
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError
          ? cause.message
          : "알림 읽음 처리에 실패했어요.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleReadAll() {
    if (busy || unreadCount === 0) return;
    setBusy(true);
    try {
      await markAllNotificationsRead();
      const nowIso = new Date().toISOString();
      setItems((prev) =>
        unreadOnly
          ? []
          : prev.map((item) => ({ ...item, read_at: item.read_at ?? nowIso })),
      );
      setUnreadCount(0);
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError
          ? cause.message
          : "전체 읽음 처리에 실패했어요.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={embedded ? "space-y-3" : "space-y-4 px-4 py-4"}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          <h2 className="text-base font-extrabold text-ink">
            알림 {unreadCount > 0 ? `(안 읽음 ${unreadCount})` : ""}
          </h2>
        </div>
        <button
          type="button"
          disabled={busy || unreadCount === 0}
          onClick={() => void handleReadAll()}
          className="inline-flex items-center gap-1 rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand disabled:opacity-50"
        >
          <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
          <span>모두 읽음</span>
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-pressed={!unreadOnly}
          onClick={() => setUnreadOnly(false)}
          className={
            !unreadOnly
              ? "rounded-chip bg-brand px-3 py-1 text-xs font-bold text-surface"
              : "rounded-chip border border-line-light bg-surface px-3 py-1 text-xs font-semibold text-muted"
          }
        >
          전체
        </button>
        <button
          type="button"
          aria-pressed={unreadOnly}
          onClick={() => setUnreadOnly(true)}
          className={
            unreadOnly
              ? "rounded-chip bg-brand px-3 py-1 text-xs font-bold text-surface"
              : "rounded-chip border border-line-light bg-surface px-3 py-1 text-xs font-semibold text-muted"
          }
        >
          안 읽은 알림
        </button>
      </div>

      {loading ? (
        <div role="status" className="space-y-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-card bg-surface-muted" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <p role="alert" className="text-sm font-semibold text-ink">
            {error}
          </p>
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
        </div>
      ) : items.length === 0 ? (
        <div className="space-y-2 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <Bell className="mx-auto h-7 w-7 text-muted/60" aria-hidden="true" />
          <p className="text-sm font-bold text-ink">
            {unreadOnly ? "안 읽은 알림이 없어요" : "받은 알림이 없어요"}
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => {
            const unread = item.read_at === null;
            const href = notificationHref(item);
            return (
              <li
                key={item.notification_id}
                className={`rounded-card border p-3.5 shadow-sm ${
                  unread
                    ? "border-brand/35 bg-surface-soft/55"
                    : "border-line-light bg-surface"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 space-y-1">
                    <p className="text-sm font-bold text-ink">
                      {notificationLabel(item.type)}
                    </p>
                    <p className="text-[11px] text-muted">
                      {formatNotifTime(item.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {unread ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void handleReadOne(item.notification_id)}
                        className="rounded-chip bg-brand px-2.5 py-1 text-[11px] font-extrabold text-surface disabled:opacity-60"
                      >
                        읽음
                      </button>
                    ) : (
                      <span className="text-[11px] font-semibold text-muted">
                        읽음
                      </span>
                    )}
                    {href ? (
                      <Link
                        href={href}
                        className="rounded-chip border border-line-light bg-surface px-2.5 py-1 text-[11px] font-bold text-ink hover:text-brand"
                      >
                        보기
                      </Link>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function NotificationsView() {
  return (
    <RequireAuth nextPath="/notifications">
      <NotificationsSection />
    </RequireAuth>
  );
}
