"use client";

import { CalendarDays, ChevronDown, Mail, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";
import { ApiError } from "@/lib/api/client";
import { authLink, signup } from "./api";
import { AuthInput, fieldClass, PasswordInput, primaryButton, useFormReady } from "./AuthFields";
import { MIN_BIRTH_YEAR, validateSignup } from "./validators";

function FieldTitle({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  const className = "mb-2 inline-flex items-center gap-1.5 text-sm font-extrabold after:text-brand after:content-['*']";
  return htmlFor
    ? <label htmlFor={htmlFor} className={className}>{children}</label>
    : <legend className={className}>{children}</legend>;
}

export function SignupForm({ next, maxBirthYear }: { next?: string; maxBirthYear: number }) {
  const router = useRouter();
  const formReady = useFormReady();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    const fields = new FormData(event.currentTarget);
    const gender = fields.get("gender");
    const data = {
      email: String(fields.get("email") ?? "").trim(),
      password: String(fields.get("password") ?? ""),
      display_name: String(fields.get("display_name") ?? "").trim(),
      birth_year: Number(fields.get("birth_year")),
      gender: String(gender ?? ""),
    };
    const invalid = validateSignup(data, String(fields.get("confirmation") ?? ""), maxBirthYear);
    if (invalid || (gender !== "female" && gender !== "male")) {
      setError(invalid ?? "성별을 선택해 주세요.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      await signup({ ...data, gender });
      router.replace(authLink("/auth/login", { email: data.email, next }));
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        if (cause.code === "EMAIL_ALREADY_EXISTS") {
          setError("이미 가입한 이메일이에요");
          return;
        }
        if (cause.code === "NICKNAME_TAKEN") {
          setError("이미 쓰는 닉네임이에요");
          return;
        }
      }
      setError("회원가입을 완료하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="space-y-4">
      <div>
        <FieldTitle htmlFor="signup-email">이메일</FieldTitle>
        <AuthInput icon={Mail} id="signup-email" name="email" type="email" autoComplete="email" placeholder="이메일 주소를 입력해 주세요" required />
      </div>
      <div>
        <FieldTitle htmlFor="signup-password">비밀번호</FieldTitle>
        <PasswordInput id="signup-password" name="password" autoComplete="new-password" placeholder="비밀번호를 입력해 주세요" aria-describedby="password-hint" required />
        <p id="password-hint" className="mt-1 text-[11px] text-muted">영문·숫자·특수문자를 조합해 8자 이상 입력해 주세요.</p>
      </div>
      <div>
        <FieldTitle htmlFor="signup-confirmation">비밀번호 확인</FieldTitle>
        <PasswordInput id="signup-confirmation" name="confirmation" autoComplete="new-password" placeholder="비밀번호를 다시 입력해 주세요" required />
      </div>
      <div>
        <FieldTitle htmlFor="signup-name">닉네임</FieldTitle>
        <AuthInput icon={UserRound} id="signup-name" name="display_name" autoComplete="nickname" placeholder="사용할 닉네임을 입력해 주세요 (2~12자)" required />
      </div>
      <fieldset>
        <FieldTitle>성별</FieldTitle>
        <div className="grid grid-cols-2 gap-2.5">
          {([{ value: "female", label: "여성" }, { value: "male", label: "남성" }] as const).map(({ value, label }) => (
            <label key={value} className="cursor-pointer">
              <input name="gender" type="radio" value={value} required className="peer sr-only" />
              <span className="flex min-h-12 items-center justify-center rounded-card-lg border border-line-strong bg-surface text-sm font-bold text-muted peer-checked:border-brand peer-checked:bg-surface-soft peer-checked:text-brand peer-focus-visible:ring-2 peer-focus-visible:ring-brand">
                {label}
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      <div>
        <FieldTitle htmlFor="signup-birth-year">출생연도</FieldTitle>
        <div className={fieldClass}>
          <CalendarDays size={18} className="shrink-0 text-brand" aria-hidden="true" />
          <div className="relative flex min-w-0 flex-1">
            <select id="signup-birth-year" name="birth_year" required defaultValue="" className="w-full appearance-none bg-transparent py-2 pr-7 text-sm outline-none invalid:text-muted">
              <option value="" disabled>출생연도를 선택해 주세요</option>
              {Array.from({ length: maxBirthYear - MIN_BIRTH_YEAR + 1 }, (_, index) => maxBirthYear - index).map((year) => (
                <option value={year} key={year}>{year}년</option>
              ))}
            </select>
            <ChevronDown size={16} className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
          </div>
        </div>
      </div>
      <div className="space-y-3 rounded-card-lg border border-line-light p-4 text-sm text-ink">
        <label className="flex items-center gap-3 border-b border-line-light pb-3 font-extrabold">
          <input type="checkbox" className="h-5 w-5 accent-brand" /> 약관 전체 동의
        </label>
        <label className="flex items-center gap-3">
          <input type="checkbox" className="h-5 w-5 accent-brand" /> <span><b className="text-brand">[필수]</b> 이용약관 동의</span>
        </label>
        <label className="flex items-center gap-3">
          <input type="checkbox" className="h-5 w-5 accent-brand" /> <span><b className="text-brand">[필수]</b> 개인정보 수집 및 이용 동의</span>
        </label>
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-brand">{error}</p>}
      <button type="submit" aria-label="회원가입" className={`${primaryButton} !mt-5`} disabled={!formReady || busy}>
        {busy ? "가입 중…" : "회원가입하기"}
      </button>
      <p className="text-center text-xs text-muted">가입 완료 후 좋아하는 축제 분야를 선택할 수 있어요.</p>
    </form>
  );
}
