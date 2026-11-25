"use client";

import { useEffect, useSyncExternalStore, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  clearAuthSession,
  getAccessToken,
  getAuthSessionVersion,
  subscribeAuth,
} from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

type AuthGuardState = "checking" | "signed_in" | "signed_out";

let suppressedRedirectVersion: number | null = null;

export function suppressNextAuthRedirect(): void {
  suppressedRedirectVersion = getAuthSessionVersion();
}

function getAuthGuardSnapshot(): AuthGuardState {
  if (typeof window === "undefined") {
    return "checking";
  }
  return getAccessToken() ? "signed_in" : "signed_out";
}

function getAuthGuardServerSnapshot(): AuthGuardState {
  return "checking";
}

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
  const authState = useSyncExternalStore(
    subscribeAuth,
    getAuthGuardSnapshot,
    getAuthGuardServerSnapshot,
  );
  const target = nextPath ?? pathname;

  useEffect(() => {
    if (authState !== "signed_out") {
      return;
    }
    if (suppressedRedirectVersion === getAuthSessionVersion()) {
      suppressedRedirectVersion = null;
      return;
    }
    router.replace(`/auth/login?next=${encodeURIComponent(target)}`);
  }, [authState, router, target]);

  if (authState === "checking") {
    return (
      <div
        role="status"
        className="flex min-h-[50vh] flex-col items-center justify-center gap-2 px-4 py-12 text-center"
      >
        <p className="text-sm font-semibold text-muted">로그인 상태를 확인하고 있어요…</p>
      </div>
    );
  }

  if (authState === "signed_out") {
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
