"use client";

import { useEffect } from "react";
import Link from "next/link";
import { UserRound, X } from "lucide-react";

export interface LoginPromptSheetProps {
  open: boolean;
  onClose: () => void;
  nextPath: string;
  title?: string;
  description?: string;
}

export function LoginPromptSheet({
  open,
  onClose,
  nextPath,
  title = "로그인이 필요해요",
  description = "회원 전용 기능을 이용하려면 로그인해 주세요.",
}: LoginPromptSheetProps) {
  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const loginHref = `/auth/login?next=${encodeURIComponent(nextPath)}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 backdrop-blur-[1px]"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-prompt-title"
        className="w-full max-w-[480px] rounded-t-[24px] bg-surface px-5 pb-7 pt-4 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-chip bg-line-light" aria-hidden="true" />
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-chip bg-surface-soft text-brand">
              <UserRound className="h-4 w-4 text-brand" aria-hidden="true" />
            </span>
            <h2 id="login-prompt-title" className="text-base font-black text-ink">
              {title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="flex h-8 w-8 items-center justify-center rounded-chip text-muted hover:bg-surface-muted hover:text-ink"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <p className="mt-2.5 text-sm leading-relaxed text-muted">{description}</p>
        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-chip border border-line-light bg-surface py-3 text-sm font-bold text-ink hover:bg-surface-muted"
          >
            다음에 할게요
          </button>
          <Link
            href={loginHref}
            onClick={onClose}
            className="flex flex-1 items-center justify-center rounded-chip bg-brand py-3 text-sm font-extrabold text-surface shadow-sm hover:opacity-90"
          >
            로그인하기
          </Link>
        </div>
      </div>
    </div>
  );
}
