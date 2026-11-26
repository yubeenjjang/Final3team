"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageCircle, User } from "lucide-react";
import { useSyncExternalStore } from "react";
import {
  getAuthUser,
  getAuthUserServerSnapshot,
  subscribeAuth,
} from "@/lib/api/auth";
import { BrandLogo } from "./BrandLogo";

const nicknameSegmenter = new Intl.Segmenter("ko", { granularity: "grapheme" });

export function Header() {
  const pathname = usePathname() ?? "/";
  const router = useRouter();
  const user = useSyncExternalStore(
    subscribeAuth,
    getAuthUser,
    getAuthUserServerSnapshot,
  );

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
              aria-label="채팅"
              className="flex h-11 w-11 items-center justify-center rounded-chip text-ink transition-colors hover:bg-surface-soft hover:text-brand"
            >
              <MessageCircle className="h-5 w-5" strokeWidth={1.9} aria-hidden="true" />
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
