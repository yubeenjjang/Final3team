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
  const immersive =
    pathname.startsWith("/auth/") ||
    pathname === "/onboarding" ||
    pathname.startsWith("/onboarding/") ||
    pathname === "/recommendations";

  return (
    <div
      data-testid="app-shell"
      data-theme="light"
      className="min-h-dvh w-full bg-canvas text-ink"
    >
      <div className="app-shell-frame relative mx-auto flex min-h-dvh flex-col overflow-x-clip bg-surface">
        {immersive ? null : <Header />}
        <main className={immersive ? "min-w-0 flex-1" : "app-main flex-1"}>{children}</main>
        <MockBadge />
        {immersive ? null : <BottomNav />}
      </div>
    </div>
  );
}
