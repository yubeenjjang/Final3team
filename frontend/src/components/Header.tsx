"use client";

import Link from "next/link";
import { User } from "lucide-react";
import { useSyncExternalStore } from "react";
import {
  getAuthUser,
  getAuthUserServerSnapshot,
  subscribeAuth,
} from "@/lib/api/auth";

export interface HeaderProps {
  isDark?: boolean;
}

const nicknameSegmenter = new Intl.Segmenter("ko", { granularity: "grapheme" });

export function Header({ isDark = false }: HeaderProps) {
  const user = useSyncExternalStore(
    subscribeAuth,
    getAuthUser,
    getAuthUserServerSnapshot,
  );

  const initial = nicknameSegmenter.segment(user?.displayName.trim() ?? "")[Symbol.iterator]().next().value?.segment;

  return (
    <header
      className={
        isDark
          ? "sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line-dark bg-dark-bg/95 px-4 backdrop-blur"
          : "sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line-light bg-bg/95 px-4 backdrop-blur"
      }
    >
      <Link
        href="/"
        className="flex items-baseline gap-1.5 font-display text-xl font-extrabold tracking-tight"
        aria-label="놀다가 홈"
      >
        <span>
          <span className="text-brand">N</span>
          <span className={isDark ? "text-surface" : "text-ink"}>OLDAGA</span>
        </span>
      </Link>

      <div className="flex items-center gap-2">
        {initial ? (
          <Link
            href="/auth/login"
            aria-label={`내 계정 (${user?.displayName ?? ""})`}
            className="flex h-9 w-9 items-center justify-center rounded-chip bg-brand text-sm font-bold text-surface transition-opacity hover:opacity-90"
          >
            {initial}
          </Link>
        ) : (
          <Link
            href="/auth/login"
            aria-label="로그인"
            className={
              isDark
                ? "flex h-9 w-9 items-center justify-center rounded-chip text-surface transition-colors hover:bg-dark-surface"
                : "flex h-9 w-9 items-center justify-center rounded-chip text-ink transition-colors hover:bg-surface-soft"
            }
          >
            <User className="h-5 w-5" aria-hidden="true" />
          </Link>
        )}
      </div>
    </header>
  );
}
