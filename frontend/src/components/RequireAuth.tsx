"use client";

import { useEffect, useSyncExternalStore, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearAuthSession, getAccessToken, subscribeAuth } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

function getSignedInSnapshot(): boolean {
  return Boolean(getAccessToken());
}

function getSignedInServerSnapshot(): boolean {
  return false;
}

export function useIsSignedIn(): boolean {
  return useSyncExternalStore(
    subscribeAuth,
    getSignedInSnapshot,
    getSignedInServerSnapshot,
  );
}

export function handleAuthError(error: unknown): boolean {
  if (error instanceof ApiError && error.status === 401) {
    clearAuthSession();
    return true;
  }
  return false;
}

export interface RequireAuthProps {
  children: ReactNode;
  nextPath?: string;
}

export function RequireAuth({ children, nextPath }: RequireAuthProps) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const signedIn = useIsSignedIn();
  const target = nextPath ?? pathname;

  useEffect(() => {
    if (!signedIn) {
      router.replace(`/auth/login?next=${encodeURIComponent(target)}`);
    }
  }, [router, signedIn, target]);

  if (!signedIn) {
    return (
      <div
        role="status"
        className="flex min-h-[50vh] flex-col items-center justify-center gap-2 px-4 py-12 text-center"
      >
        <p className="text-sm font-bold text-ink">로그인이 필요한 화면이에요</p>
        <p className="text-xs text-muted">로그인 화면으로 이동하고 있어요…</p>
      </div>
    );
  }

  return <>{children}</>;
}
