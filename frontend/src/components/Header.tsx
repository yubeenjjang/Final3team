"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageCircle, User } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { listChatRooms } from "@/features/community/chats/api";
import {
  getAuthUser,
  getAuthUserServerSnapshot,
  subscribeAuth,
} from "@/lib/api/auth";
import { BrandLogo } from "./BrandLogo";

const nicknameSegmenter = new Intl.Segmenter("ko", { granularity: "grapheme" });
const UNREAD_REFRESH_INTERVAL_MS = 15_000;

export function Header() {
  const pathname = usePathname() ?? "/";
  const router = useRouter();
  const user = useSyncExternalStore(
    subscribeAuth,
    getAuthUser,
    getAuthUserServerSnapshot,
  );
  const [unreadState, setUnreadState] = useState({ userId: "", count: 0 });
  const unreadCount =
    user && unreadState.userId === user.userId ? unreadState.count : 0;

  useEffect(() => {
    if (!user) return;

    const controller = new AbortController();
    let disposed = false;
    let refreshing = false;

    const refreshUnreadCount = async () => {
      if (refreshing || controller.signal.aborted) return;
      refreshing = true;
      try {
        const response = await listChatRooms("all", controller.signal);
        if (disposed) return;
        const total = response.items.reduce((sum, room) => {
          if (room.my_status !== "joined") return sum;
          const roomUnread = Number.isFinite(room.unread_count)
            ? Math.max(0, room.unread_count)
            : 0;
          return sum + roomUnread;
        }, 0);
        setUnreadState({ userId: user.userId, count: total });
      } catch {
        // Keep the last successful count when a background refresh fails.
      } finally {
        refreshing = false;
      }
    };

    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") {
        void refreshUnreadCount();
      }
    };

    void refreshUnreadCount();
    const interval = window.setInterval(
      () => void refreshUnreadCount(),
      UNREAD_REFRESH_INTERVAL_MS,
    );
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);

    return () => {
      disposed = true;
      controller.abort();
      window.clearInterval(interval);
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [pathname, user]);

  const initial = nicknameSegmenter
    .segment(user?.displayName.trim() ?? "")
    [Symbol.iterator]()
    .next().value?.segment;

  return (
    <header className="app-header sticky top-0 z-30 flex items-center justify-between bg-surface/95 backdrop-blur-md">
      <Link
        href="/"
        onClick={(event) => {
          event.preventDefault();
          router.push("/");
        }}
        className="flex items-center self-stretch"
        aria-label="놀다가 홈"
      >
        <BrandLogo priority className="h-11 w-auto max-w-[184px] object-left" />
      </Link>

      <nav className="hidden h-full items-stretch md:flex" aria-label="데스크톱 주요 메뉴">
        {[
          { href: "/", label: "홈", active: pathname === "/" },
          { href: "/festivals", label: "축제", active: pathname.startsWith("/festivals") },
          { href: "/companions", label: "동행", active: pathname.startsWith("/companions") },
          { href: "/routes/return", label: "귀가", active: pathname.startsWith("/routes/return") },
          { href: "/map", label: "지도", active: pathname.startsWith("/map") },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-label={`${item.label} 메뉴`}
            aria-current={item.active ? "page" : undefined}
            className={`relative grid min-w-20 place-items-center px-4 text-sm font-bold transition-colors after:absolute after:inset-x-4 after:bottom-0 after:h-[3px] after:rounded-t-chip after:content-[''] ${
              item.active
                ? "text-brand after:bg-brand"
                : "text-muted after:bg-transparent hover:text-brand"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="flex items-center gap-1.5">
        {initial ? (
          <>
            <Link
              href="/chats"
              aria-label={
                unreadCount > 0
                  ? `채팅, 안 읽은 메시지 ${unreadCount}개`
                  : "채팅"
              }
              className="relative flex h-11 w-11 items-center justify-center rounded-chip text-ink transition-colors hover:bg-surface-soft hover:text-brand"
            >
              <MessageCircle className="h-5 w-5" strokeWidth={1.9} aria-hidden="true" />
              {unreadCount > 0 ? (
                <span
                  aria-hidden="true"
                  className="absolute right-0 top-0 flex h-[19px] min-w-[19px] items-center justify-center rounded-full border-2 border-surface bg-brand px-1 text-[10px] font-black leading-none text-surface shadow-sm"
                >
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              ) : null}
            </Link>
            <Link
                href="/me"
                aria-label={`마이페이지 (${user?.displayName ?? ""})`}
                className="flex h-11 w-11 items-center justify-center rounded-chip bg-brand text-sm font-bold text-surface shadow-sm transition-opacity hover:opacity-90"
              >
                {initial}
            </Link>
          </>
        ) : (
          <Link
            href="/auth/login"
            aria-label="로그인"
            className="flex h-11 w-11 items-center justify-center rounded-chip text-ink transition-colors hover:bg-surface-soft hover:text-brand"
          >
            <User className="h-5 w-5" strokeWidth={1.9} aria-hidden="true" />
          </Link>
        )}
      </div>
    </header>
  );
}
