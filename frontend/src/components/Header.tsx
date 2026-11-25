"use client";

import Link from "next/link";
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
        className="flex items-center self-stretch"
        aria-label="놀다가 홈"
      >
        <BrandLogo priority className="h-11 w-auto max-w-[184px] object-left" />
      </Link>

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
              aria-label={`내 계정 (${user?.displayName ?? ""})`}
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
