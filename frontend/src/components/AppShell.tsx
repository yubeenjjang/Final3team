"use client";

import type { ReactNode } from "react";
import { BottomNav } from "./BottomNav";
import { Header } from "./Header";
import { MockBadge } from "./MockBadge";

export interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div
      data-testid="app-shell"
      data-theme="light"
      className="min-h-dvh w-full bg-bg text-ink"
    >
      <div className="relative mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-surface shadow-[0_0_24px_rgba(10,16,31,0.05)]">
        <Header />
        <main className="flex-1 pb-24">{children}</main>
        <MockBadge />
        <BottomNav />
      </div>
    </div>
  );
}
