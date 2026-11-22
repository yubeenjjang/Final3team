"use client";

import Link from "next/link";
import { Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { getAuthUser, getAuthUserServerSnapshot, subscribeAuth } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { authLink, login, logout, safeNextPath } from "./api";
import { AuthInput, PasswordInput, primaryButton } from "./AuthFields";

export function LoginForm({ email, next }: { email?: string; next?: string }) {
  const router = useRouter();
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
      router.replace(safeNextPath(next));
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
      <h1 className="mb-5 text-center text-[clamp(17px,5.4vw,25px)] font-black leading-tight tracking-tight">
        로그인하고<br />나만의 <span className="text-brand">축제</span>를 시작하세요!
      </h1>
      <form onSubmit={submit} className="space-y-2.5">
        <AuthInput
          icon={Mail}
          name="email"
          type="email"
          autoComplete="email"
          defaultValue={email}
          placeholder="이메일 아이디를 입력하세요"
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
        {error && <p role="alert" className="text-sm font-semibold text-brand">{error}</p>}
        <button type="submit" disabled={busy} className={`${primaryButton} !mt-4 !rounded-chip`}>
          {busy ? "로그인 중…" : "로그인"}
        </button>
      </form>
      <div className="my-3.5 flex items-center gap-2 text-xs font-medium text-muted before:h-px before:flex-1 before:bg-line-light after:h-px after:flex-1 after:bg-line-light">
        계정이 없으신가요?
      </div>
      <Link
        href={authLink("/auth/signup", { next })}
        className="flex min-h-10 items-center justify-center rounded-chip border border-brand text-sm font-extrabold text-brand"
      >
        회원가입
      </Link>
    </>
  );
}
