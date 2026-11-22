"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Home, MapPin, Route, Users } from "lucide-react";
import type { ComponentType } from "react";

interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  match: (pathname: string) => boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "홈",
    icon: Home,
    match: (pathname) => pathname === "/",
  },
  {
    href: "/festivals",
    label: "축제",
    icon: CalendarDays,
    match: (pathname) =>
      pathname === "/festivals" || pathname.startsWith("/festivals/"),
  },
  {
    href: "/companions",
    label: "동행",
    icon: Users,
    match: (pathname) =>
      pathname === "/companions" || pathname.startsWith("/companions/"),
  },
  {
    href: "/routes/return",
    label: "귀가",
    icon: Route,
    match: (pathname) =>
      pathname === "/routes/return" || pathname.startsWith("/routes/return/"),
  },
  {
    href: "/map",
    label: "지도",
    icon: MapPin,
    match: (pathname) => pathname === "/map" || pathname.startsWith("/map/"),
  },
];

export interface BottomNavProps {
  isDark?: boolean;
}

export function BottomNav({ isDark = false }: BottomNavProps) {
  const pathname = usePathname() ?? "/";

  return (
    <nav
      aria-label="주요 메뉴"
      className={
        isDark
          ? "fixed bottom-0 left-1/2 z-30 h-[72px] w-full max-w-[480px] -translate-x-1/2 border-t border-line-dark bg-dark-surface/95 px-2 backdrop-blur"
          : "fixed bottom-0 left-1/2 z-30 h-[72px] w-full max-w-[480px] -translate-x-1/2 border-t border-line-light bg-surface/95 px-2 backdrop-blur"
      }
    >
      <ul className="grid h-full grid-cols-5 items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;

          const activeClasses = isDark
            ? "bg-brand text-surface"
            : "bg-brand text-surface";
          const inactiveClasses = isDark
            ? "text-dark-muted hover:text-surface"
            : "text-muted hover:text-ink";

          return (
            <li key={item.href} className="flex justify-center">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex h-14 w-full max-w-[76px] flex-col items-center justify-center gap-1 rounded-card text-xs font-semibold transition-colors ${
                  active ? activeClasses : inactiveClasses
                }`}
              >
                <Icon className="h-5 w-5" aria-hidden={true} />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
