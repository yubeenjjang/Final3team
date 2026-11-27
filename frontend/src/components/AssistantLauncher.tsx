"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Sparkles } from "lucide-react";

export function AssistantLauncher() {
  const pathname = usePathname() ?? "/";

  if (pathname === "/assistant") return null;

  return (
    <Link
      href="/assistant"
      aria-label="AI 챗봇 열기"
      className="assistant-launcher group fixed z-40 grid h-14 w-14 place-items-center rounded-full border-2 border-surface bg-brand text-surface shadow-[0_10px_28px_rgba(247,79,133,0.38)] transition-transform hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand/25"
    >
      <Bot className="h-7 w-7" strokeWidth={2.2} aria-hidden="true" />
      <Sparkles
        className="absolute -right-1 -top-1 h-5 w-5 rounded-full bg-surface p-0.5 text-brand"
        strokeWidth={2.4}
        aria-hidden="true"
      />
      <span className="pointer-events-none absolute right-full mr-2 hidden whitespace-nowrap rounded-chip bg-ink px-3 py-1.5 text-xs font-bold text-surface shadow-card group-hover:block md:group-focus-visible:block">
        AI에게 물어보기
      </span>
    </Link>
  );
}
