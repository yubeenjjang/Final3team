"use client";

import { useSyncExternalStore } from "react";
import {
  getMockDataServerSnapshot,
  isMockDataDetected,
  subscribeMockData,
} from "@/lib/api/client";

export function MockBadge() {
  const isMock = useSyncExternalStore(
    subscribeMockData,
    isMockDataDetected,
    getMockDataServerSnapshot,
  );

  if (!isMock) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed bottom-20 right-4 z-40 rounded-chip border border-line-light bg-ink/85 px-2.5 py-1 text-[11px] font-semibold text-surface shadow-sm backdrop-blur"
    >
      모의 데이터
    </div>
  );
}
