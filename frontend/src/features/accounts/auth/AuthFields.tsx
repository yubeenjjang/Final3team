"use client";

import { Eye, EyeOff, LockKeyhole, type LucideIcon } from "lucide-react";
import { useState, useSyncExternalStore, type InputHTMLAttributes } from "react";

export const fieldClass =
  "flex min-h-14 items-center gap-3 rounded-card-lg border border-line-strong bg-surface px-4 text-ink transition-colors focus-within:border-brand focus-within:ring-1 focus-within:ring-brand";
const inputClass = "min-w-0 flex-1 bg-transparent py-3 text-[15px] outline-none placeholder:text-muted/65";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon: LucideIcon;
}

export function AuthInput({ icon: Icon, ...props }: InputProps) {
  return (
    <div className={fieldClass}>
      <Icon size={21} className="shrink-0 text-muted" aria-hidden="true" />
      <input {...props} className={inputClass} />
    </div>
  );
}

export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={fieldClass}>
      <LockKeyhole size={21} className="shrink-0 text-muted" aria-hidden="true" />
      <input {...props} type={visible ? "text" : "password"} className={inputClass} />
      <button
        type="button"
        aria-label={visible ? "비밀번호 숨기기" : "비밀번호 표시"}
        aria-pressed={visible}
        onClick={() => setVisible((value) => !value)}
        className="grid h-9 w-8 shrink-0 place-items-center rounded-lg text-muted hover:text-ink"
      >
        {visible ? <Eye size={18} aria-hidden="true" /> : <EyeOff size={18} aria-hidden="true" />}
      </button>
    </div>
  );
}

export const primaryButton =
  "flex min-h-14 w-full items-center justify-center rounded-card-lg bg-brand px-4 py-3 text-lg font-extrabold text-surface shadow-card transition-opacity hover:opacity-90 disabled:opacity-60";

const subscribeHydration = () => () => {};

export function useFormReady(): boolean {
  return useSyncExternalStore(subscribeHydration, () => true, () => false);
}
