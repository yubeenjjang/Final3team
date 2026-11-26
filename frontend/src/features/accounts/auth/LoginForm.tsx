"use client";

import Link from "next/link";
import { Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { getAuthUser, getAuthUserServerSnapshot, subscribeAuth } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { getFestivalPreferences } from "@/features/accounts/profile/api";
import { authLink, login, logout, safeNextPath } from "./api";
import { AuthInput, PasswordInput, primaryButton, useFormReady } from "./AuthFields";

export function LoginForm({
  email,
  next,
  notice,
}: {
  email?: string;
  next?: string;
  notice?: string;
}) {
  const router = useRouter();
  const formReady = useFormReady();
  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUserServerSnapshot);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      await login({
        email: String(data.get("email")).trim(),
        password: String(data.get("password")),
      });
      let destination = safeNextPath(next);
      try {
        const preferences = await getFestivalPreferences();
        if (preferences.onboarding_status === "pending") {
          destination = "/onboarding";
        }
      } catch {
        // 로그인은 성공했으므로 취향 상태 확인 실패만으로 진입을 막지 않습니다.
      }
      router.replace(destination);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 401
          ? "이메일 또는 비밀번호가 맞지 않아요"
          : "로그인하지 못했어요. 다시 시도해 주세요.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    setError("");
    try {
      await logout();
    } catch {
      setError("서버에서 로그아웃을 확인하지 못했어요.");
    } finally {
      setBusy(false);
    }
  }

  if (user) {
    return (
      <section className="space-y-4 text-center">
        <h1 className="text-xl font-black">{user.displayName}님</h1>
        {user.email && <p className="break-words text-sm text-muted">{user.email}</p>}
        <Link href={safeNextPath(next)} className={primaryButton}>
          {next && safeNextPath(next) !== "/" ? "이전 화면으로" : "홈으로"}
        </Link>
        <button
          type="button"
          onClick={() => void signOut()}
          disabled={busy}
          className="w-full rounded-chip border border-brand px-4 py-2 text-sm font-extrabold text-brand disabled:opacity-60"
        >
          {busy ? "처리 중…" : "로그아웃"}
        </button>
      </section>
    );
  }

  return (
    <>
      <form method="post" onSubmit={submit} className="space-y-4">
        {notice && !error ? (
          <p role="status" className="text-sm font-semibold text-ink">{notice}</p>
        ) : null}
        <AuthInput
          icon={Mail}
          name="email"
          type="email"
          autoComplete="email"
          defaultValue={email}
          placeholder="이메일을 입력해주세요"
          aria-label="이메일"
          required
        />
        <PasswordInput
          name="password"
          autoComplete="current-password"
          placeholder="비밀번호를 입력하세요"
          aria-label="비밀번호"
          required
        />
        <div className="flex items-center justify-between text-sm text-ink">
          <label className="flex items-center gap-2">
            <input type="checkbox" className="h-5 w-5 rounded-control border-line-strong accent-brand" />
            로그인 상태 유지
          </label>
          <span className="font-semibold">비밀번호 찾기 ›</span>
        </div>
        {error && <p role="alert" className="text-sm font-semibold text-brand">{error}</p>}
        <button type="submit" disabled={!formReady || busy} className={`${primaryButton} !mt-6`}>
          {busy ? "로그인 중…" : "로그인"}
        </button>
      </form>
      <p className="mt-7 text-center text-base font-medium text-ink">
        아직 회원이 아니신가요?{" "}
        <Link href={authLink("/auth/signup", { next })} className="font-extrabold text-brand underline underline-offset-4">회원가입</Link>
      </p>
    </>
  );
}
