"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { BottomNav } from "./BottomNav";
import { Header } from "./Header";
import { MockBadge } from "./MockBadge";

export interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname() ?? "/";
  const isDark = pathname === "/";

  return (
    <div
      data-testid="app-shell"
      data-theme={isDark ? "dark" : "light"}
      className={
        isDark
          ? "min-h-dvh w-full bg-dark-bg text-surface"
          : "min-h-dvh w-full bg-bg text-ink"
      }
    >
      <div className="relative mx-auto flex min-h-dvh w-full max-w-[480px] flex-col">
        <Header isDark={isDark} />
        <main className="flex-1 pb-24">{children}</main>
        <MockBadge />
        <BottomNav isDark={isDark} />
      </div>
    </div>
  );
}
