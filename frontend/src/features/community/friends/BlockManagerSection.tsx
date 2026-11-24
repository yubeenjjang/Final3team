"use client";

import { useState, type FormEvent } from "react";
import { ShieldBan, ShieldCheck } from "lucide-react";
import { handleAuthError } from "@/components/RequireAuth";
import { ApiError } from "@/lib/api/client";
import { blockUser, unblockUser } from "./api";
import {
  forgetBlockedUser,
  getRememberedBlocks,
  rememberBlockedUser,
  type BlockedUserRecord,
} from "./blockCache";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function BlockManagerSection() {
  const [records, setRecords] = useState<BlockedUserRecord[]>(() =>
    getRememberedBlocks(),
  );
  const [targetUserId, setTargetUserId] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleUnblock(userId: string) {
    if (busyId) return;
    setBusyId(userId);
    setError(null);
    setNotice(null);
    try {
      await unblockUser(userId);
      setRecords(forgetBlockedUser(userId));
      setNotice("차단을 해제했어요. 친구 관계나 닫힌 1:1 방은 복원되지 않아요.");
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError
          ? cause.message
          : "차단을 해제하지 못했어요.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleManualAction(
    event: FormEvent<HTMLFormElement>,
    mode: "block" | "unblock",
  ) {
    event.preventDefault();
    const id = targetUserId.trim();
    if (!UUID_REGEX.test(id)) {
      setError("올바른 사용자 ID(UUID) 형식을 입력해 주세요.");
      return;
    }
    if (busyId) return;
    setBusyId(id);
    setError(null);
    setNotice(null);
    try {
      if (mode === "block") {
        await blockUser(id);
        setRecords(rememberBlockedUser(id, null));
        setNotice("사용자를 차단했어요.");
      } else {
        await unblockUser(id);
        setRecords(forgetBlockedUser(id));
        setNotice("차단을 해제했어요.");
      }
      setTargetUserId("");
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError
          ? cause.message
          : mode === "block"
            ? "차단에 실패했어요."
            : "차단 해제에 실패했어요.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section
      aria-labelledby="block-manager-title"
      className="space-y-3 rounded-card border border-line-light bg-surface p-4 shadow-sm"
    >
      <div className="flex items-center gap-2">
        <ShieldBan className="h-4 w-4 text-brand" aria-hidden="true" />
        <h2 id="block-manager-title" className="text-base font-extrabold text-ink">
          차단 관리
        </h2>
      </div>
      <p className="text-xs leading-relaxed text-muted">
        차단하면 친구 관계와 대기 중인 신청이 취소되고 1:1 채팅방이 닫혀요. 차단을
        풀어도 닫힌 1:1 방은 다시 열리지 않아요.
      </p>

      {notice ? (
        <p role="status" className="rounded-xl bg-surface-soft px-3 py-2 text-xs font-semibold text-ink">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-xs font-semibold text-brand">
          {error}
        </p>
      ) : null}

      {records.length === 0 ? (
        <p className="rounded-xl bg-surface-muted/60 px-3 py-4 text-center text-xs text-muted">
          이 세션에서 차단한 사용자가 없어요.
        </p>
      ) : (
        <ul className="space-y-2">
          {records.map((item) => (
            <li
              key={item.user_id}
              className="flex items-center justify-between gap-2 rounded-xl border border-line-light px-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-ink">
                  {item.display_name ?? "알 수 없음"}
                </p>
                <p className="truncate text-[11px] text-muted">{item.user_id}</p>
              </div>
              <button
                type="button"
                disabled={busyId === item.user_id}
                onClick={() => void handleUnblock(item.user_id)}
                className="inline-flex shrink-0 items-center gap-1 rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
                <span>{busyId === item.user_id ? "처리 중…" : "차단 해제"}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <form
        onSubmit={(event) => void handleManualAction(event, "unblock")}
        className="space-y-2 border-t border-line-light pt-3"
      >
        <label
          htmlFor="block-user-uuid"
          className="block text-xs font-bold text-ink"
        >
          사용자 ID로 직접 차단 · 해제
        </label>
        <input
          id="block-user-uuid"
          type="text"
          value={targetUserId}
          onChange={(e) => setTargetUserId(e.target.value)}
          placeholder="사용자 UUID 입력"
          className="h-10 w-full rounded-input border border-line-light px-3.5 text-xs text-ink placeholder:text-muted focus:border-brand focus:outline-none"
        />
        <div className="flex gap-2">
          <button
            type="button"
            disabled={busyId !== null}
            onClick={(event) => {
              const form = event.currentTarget.form;
              if (form) {
                void handleManualAction(
                  { preventDefault: () => {} } as FormEvent<HTMLFormElement>,
                  "block",
                );
              }
            }}
            className="flex-1 rounded-chip border border-brand/40 bg-surface-soft py-2 text-xs font-bold text-brand disabled:opacity-60"
          >
            차단하기
          </button>
          <button
            type="submit"
            disabled={busyId !== null}
            className="flex-1 rounded-chip border border-line-light bg-surface py-2 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
          >
            차단 해제
          </button>
        </div>
      </form>
    </section>
  );
}
