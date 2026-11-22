"use client";

import { Eye, EyeOff, LockKeyhole, type LucideIcon } from "lucide-react";
import { useState, type InputHTMLAttributes } from "react";

export const fieldClass = "flex min-h-11 items-center gap-3 rounded-xl border border-line-light bg-bg px-3 text-ink focus-within:border-accent focus-within:ring-1 focus-within:ring-accent";
const inputClass = "min-w-0 flex-1 bg-transparent py-2 text-sm outline-none placeholder:text-muted";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon: LucideIcon;
}

export function AuthInput({ icon: Icon, ...props }: InputProps) {
  return (
    <div className={fieldClass}>
      <Icon size={18} className="shrink-0 text-accent" aria-hidden="true" />
      <input {...props} className={inputClass} />
    </div>
  );
}

export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={fieldClass}>
      <LockKeyhole size={18} className="shrink-0 text-accent" aria-hidden="true" />
      <input {...props} type={visible ? "text" : "password"} className={inputClass} />
      <button
        type="button"
        aria-label={visible ? "비밀번호 숨기기" : "비밀번호 표시"}
        aria-pressed={visible}
        onClick={() => setVisible((value) => !value)}
        className="grid h-9 w-8 shrink-0 place-items-center rounded-lg text-muted"
      >
        {visible ? <Eye size={18} aria-hidden="true" /> : <EyeOff size={18} aria-hidden="true" />}
      </button>
    </div>
  );
}

export const primaryButton = "flex min-h-12 w-full items-center justify-center rounded-2xl bg-brand px-4 py-2.5 text-base font-extrabold text-surface hover:bg-brand/90 disabled:opacity-60";
