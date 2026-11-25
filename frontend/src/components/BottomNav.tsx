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

export function BottomNav() {
  const pathname = usePathname() ?? "/";

  return (
    <nav
      aria-label="주요 메뉴"
      className="app-bottom-nav fixed bottom-0 left-1/2 z-30 -translate-x-1/2 rounded-t-nav border border-b-0 border-line-light bg-surface/95 backdrop-blur-md"
    >
      <ul className="grid h-full grid-cols-5 items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;

          return (
            <li key={item.href} className="flex justify-center">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-16 w-full flex-col items-center justify-center gap-1 rounded-nav px-1 text-[13px] font-semibold transition-colors ${
                  active
                    ? "bg-brand/15 font-bold text-brand"
                    : "text-ink/70 hover:text-brand"
                }`}
              >
                <Icon className="h-6 w-6" aria-hidden={true} />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
