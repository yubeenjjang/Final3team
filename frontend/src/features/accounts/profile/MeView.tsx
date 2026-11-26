"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import {
  KeyRound,
  LogOut,
  MessageCircle,
  Pencil,
  RotateCcw,
  ShieldBan,
  Sparkles,
  Trash2,
  UsersRound,
} from "lucide-react";
import {
  handleAuthError,
  RequireAuth,
  suppressNextAuthRedirect,
} from "@/components/RequireAuth";
import { validatePasswordChange } from "@/features/accounts/auth/validators";
import { BlockManagerSection } from "@/features/community/friends/BlockManagerSection";
import { clearAuthSession, updateAuthUser } from "@/lib/api/auth";
import { ApiError, logoutAuthSession } from "@/lib/api/client";
import {
  changePassword,
  deleteAccount,
  getProfile,
  updateProfile,
  type Profile,
} from "./api";
import { PreferencesSection } from "./PreferencesView";
import { FavoriteListSection } from "@/features/favorites/FavoriteListSection";

type MeSectionTab = "preferences" | "blocks";

function MeContent() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [activeTab, setActiveTab] = useState<MeSectionTab>("preferences");

  // Profile edit
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);

  // Password change
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Logout & withdrawal
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [withdrawPassword, setWithdrawPassword] = useState("");
  const [withdrawChecked, setWithdrawChecked] = useState(false);
  const [withdrawBusy, setWithdrawBusy] = useState(false);
  const [withdrawError, setWithdrawError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getProfile(controller.signal);
        if (controller.signal.aborted) return;
        setProfile(res);
        setNameInput(res.display_name ?? "");
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        setError(
          cause instanceof ApiError
            ? cause.message
            : "프로필을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [reloadTick]);

  async function handleSaveNickname(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = nameInput.trim();
    if (trimmed.length < 2 || trimmed.length > 12) {
      setProfileError("닉네임은 2~12자로 입력해 주세요.");
      return;
    }
    setSavingName(true);
    setProfileError(null);
    setProfileNotice(null);
    try {
      const updated = await updateProfile(trimmed);
      setProfile(updated);
      if (updated.display_name) {
        updateAuthUser({ displayName: updated.display_name });
      }
      setEditingName(false);
      setProfileNotice("닉네임을 변경했어요.");
    } catch (cause) {
      if (handleAuthError(cause)) return;
      if (cause instanceof ApiError && cause.code === "NICKNAME_TAKEN") {
        setProfileError("이미 사용 중인 닉네임이에요.");
      } else {
        setProfileError(
          cause instanceof ApiError
            ? cause.message
            : "닉네임을 변경하지 못했어요.",
        );
      }
    } finally {
      setSavingName(false);
    }
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (passwordBusy) return;
    const validationError = validatePasswordChange(
      currentPassword,
      newPassword,
      confirmPassword,
    );
    if (validationError) {
      setPasswordError(validationError);
      return;
    }
    setPasswordBusy(true);
    setPasswordError(null);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      clearAuthSession();
      suppressNextAuthRedirect();
      router.replace("/auth/login?reason=password_changed");
    } catch (cause) {
      if (handleAuthError(cause)) return;
      if (
        cause instanceof ApiError &&
        cause.status === 403 &&
        cause.code === "PASSWORD_MISMATCH"
      ) {
        setPasswordError("현재 비밀번호가 맞지 않아요");
      } else if (cause instanceof ApiError && cause.status === 422) {
        setPasswordError(cause.message);
      } else {
        setPasswordError(
          cause instanceof ApiError
            ? cause.message
            : "비밀번호를 변경하지 못했어요. 다시 시도해 주세요.",
        );
      }
    } finally {
      setPasswordBusy(false);
    }
  }

  async function handleLogout() {
    if (logoutBusy) return;
    setLogoutBusy(true);
    try {
      const logoutPromise = logoutAuthSession();
      suppressNextAuthRedirect();
      await logoutPromise;
    } catch {
      // Session is already cleared locally
    } finally {
      setLogoutBusy(false);
      router.replace("/");
    }
  }

  async function handleWithdraw(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (withdrawBusy || !withdrawChecked || !withdrawPassword) return;
    setWithdrawBusy(true);
    setWithdrawError(null);
    try {
      await deleteAccount(withdrawPassword);
      clearAuthSession();
      suppressNextAuthRedirect();
      router.replace("/");
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setWithdrawError(
        cause instanceof ApiError
          ? cause.message
          : "회원 탈퇴에 실패했어요. 비밀번호를 확인해 주세요.",
      );
    } finally {
      setWithdrawBusy(false);
    }
  }

  return (
    <div className="space-y-7 px-5 py-6">
      <div>
        <div>
          <h1 className="text-[32px] font-black text-ink">마이페이지</h1>
          <p className="mt-2 text-base text-muted">나의 축제 활동을 한눈에 확인해요!</p>
        </div>
      </div>

      {/* 프로필 카드 */}
      {loading ? (
        <div role="status" className="h-28 animate-pulse rounded-card bg-surface-muted" />
      ) : error || !profile ? (
        <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-8 text-center">
          <p role="alert" className="text-sm font-semibold text-ink">
            {error ?? "프로필 정보를 불러오지 못했어요."}
          </p>
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
        </div>
      ) : (
        <section className="space-y-3 rounded-panel border border-brand/15 bg-surface-soft p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-chip border-2 border-brand/30 bg-surface text-xl font-black text-brand shadow-sm">
                {(profile.display_name ?? "나").slice(0, 1)}
              </div>
              <div>
                <h2 className="text-base font-black text-ink">
                  {profile.display_name ?? "닉네임 미설정"}
                </h2>
                <p className="text-xs text-muted">
                  {profile.birth_year ? `${profile.birth_year}년생` : "출생연도 미입력"} ·{" "}
                  {profile.gender === "male"
                    ? "남성"
                    : profile.gender === "female"
                      ? "여성"
                      : "성별 미입력"}
                </p>
                <span className="mt-1 inline-block rounded-chip bg-surface-soft px-2 py-0.5 text-[10px] font-extrabold text-brand">
                  취향{" "}
                  {profile.onboarding_status === "completed"
                    ? "설정 완료"
                    : profile.onboarding_status === "skipped"
                      ? "건너뜀"
                      : "미설정"}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                setEditingName((v) => !v);
                setNameInput(profile.display_name ?? "");
                setProfileError(null);
                setProfileNotice(null);
              }}
              className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand"
            >
              <Pencil className="h-3 w-3 shrink-0" aria-hidden="true" />
              <span>{editingName ? "취소" : "닉네임 수정"}</span>
            </button>
          </div>

          {profileNotice ? (
            <p role="status" className="text-xs font-semibold text-brand">
              {profileNotice}
            </p>
          ) : null}

          {editingName ? (
            <form onSubmit={handleSaveNickname} className="space-y-2 border-t border-line-light pt-3">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  required
                  minLength={2}
                  maxLength={12}
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  aria-label="새 닉네임"
                  placeholder="2~12자 닉네임"
                  className="h-10 flex-1 rounded-input border border-line-light px-3.5 text-sm focus:border-brand focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={savingName}
                  className="h-10 shrink-0 rounded-input bg-brand px-4 text-xs font-extrabold text-surface disabled:opacity-60"
                >
                  {savingName ? "저장 중…" : "저장"}
                </button>
              </div>
              {profileError ? (
                <p role="alert" className="text-xs font-semibold text-brand">
                  {profileError}
                </p>
              ) : null}
            </form>
          ) : null}
        </section>
      )}

      {/* 커뮤니티 빠른 이동 */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          href="/chats"
          className="flex min-h-16 items-center justify-center gap-2 rounded-card-lg border border-line-light bg-surface px-3 text-sm font-bold text-ink shadow-sm hover:border-brand/40 hover:text-brand"
        >
          <MessageCircle className="h-5 w-5 text-brand" aria-hidden="true" />
          <span>채팅방</span>
        </Link>
        <Link
          href="/friends"
          className="flex min-h-16 items-center justify-center gap-2 rounded-card-lg border border-line-light bg-surface px-3 text-sm font-bold text-ink shadow-sm hover:border-brand/40 hover:text-brand"
        >
          <UsersRound className="h-5 w-5 text-brand" aria-hidden="true" />
          <span>내 친구</span>
        </Link>
      </div>

      {/* 마이페이지 탭 */}
      <div
        role="tablist"
        aria-label="마이페이지 섹션"
        className="grid grid-cols-2 gap-1 rounded-chip border border-line-light bg-surface p-1 shadow-sm"
      >
        {(
          [
            { id: "preferences", label: "취향", icon: Sparkles },
            { id: "blocks", label: "차단", icon: ShieldBan },
          ] as const
        ).map((item) => {
          const Icon = item.icon;
          const active = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center justify-center gap-1 rounded-chip py-2 text-[11px] font-extrabold transition-colors ${
                active ? "bg-brand text-surface" : "text-muted hover:text-ink"
              }`}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* 선택된 섹션 */}
      {activeTab === "preferences" ? (
        <PreferencesSection
          embedded
          onSaved={(nextStatus) =>
            setProfile((prev) =>
              prev ? { ...prev, onboarding_status: nextStatus } : prev,
            )
          }
        />
      ) : (
        <BlockManagerSection />
      )}

      <FavoriteListSection />

      <div className="space-y-3">
        {/* 비밀번호 변경 */}
        <section className="space-y-3 rounded-card border border-line-light bg-surface p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-sm font-extrabold text-ink">비밀번호 변경</h2>
            <p className="text-[11px] text-muted">
              영문과 숫자를 포함한 8~64자로 새 비밀번호를 설정할 수 있어요.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setPasswordOpen((v) => !v);
              setPasswordError(null);
            }}
            className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand"
          >
            <KeyRound className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>{passwordOpen ? "닫기" : "변경하기"}</span>
          </button>
        </div>

        {passwordOpen ? (
          <form
            onSubmit={handleChangePassword}
            noValidate
            className="space-y-3 border-t border-line-light pt-3"
          >
            <div className="space-y-2">
              <input
                type="password"
                required
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="현재 비밀번호 입력"
                aria-label="현재 비밀번호"
                className="h-10 w-full rounded-input border border-line-light bg-surface px-3.5 text-sm focus:border-brand focus:outline-none"
              />
              <input
                type="password"
                required
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="새 비밀번호 입력 (영문·숫자 포함 8~64자)"
                aria-label="새 비밀번호"
                className="h-10 w-full rounded-input border border-line-light bg-surface px-3.5 text-sm focus:border-brand focus:outline-none"
              />
              <input
                type="password"
                required
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="새 비밀번호 다시 입력"
                aria-label="새 비밀번호 확인"
                className="h-10 w-full rounded-input border border-line-light bg-surface px-3.5 text-sm focus:border-brand focus:outline-none"
              />
            </div>
            {passwordError ? (
              <p role="alert" className="text-xs font-semibold text-brand">
                {passwordError}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={passwordBusy}
              className="w-full rounded-chip bg-brand py-2.5 text-xs font-extrabold text-surface disabled:opacity-50"
            >
              {passwordBusy ? "변경 중…" : "비밀번호 변경 저장"}
            </button>
          </form>
        ) : null}
        </section>

        {/* 로그아웃 */}
        <section className="flex items-center justify-between gap-3 rounded-card border border-line-light bg-surface p-4 shadow-sm">
        <div className="min-w-0">
          <h2 className="text-sm font-extrabold text-ink">로그아웃</h2>
          <p className="text-[11px] text-muted">현재 계정에서 로그아웃합니다.</p>
        </div>
        <button
          type="button"
          disabled={logoutBusy}
          onClick={() => void handleLogout()}
          aria-label="로그아웃"
          className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand disabled:opacity-60"
        >
          <LogOut className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{logoutBusy ? "로그아웃 중…" : "로그아웃"}</span>
        </button>
        </section>

        {/* 회원 탈퇴 */}
        <section className="space-y-3 rounded-card border border-line-light bg-surface-muted/40 p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-sm font-extrabold text-ink">회원 탈퇴</h2>
            <p className="text-[11px] text-muted">
              탈퇴 시 취향과 친구 관계가 모두 삭제돼요.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setWithdrawOpen((v) => !v);
              setWithdrawError(null);
            }}
            className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-chip border border-brand/40 bg-surface px-3 py-1.5 text-xs font-bold text-brand hover:bg-surface-soft"
          >
            <Trash2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>{withdrawOpen ? "닫기" : "탈퇴하기"}</span>
          </button>
        </div>

        {withdrawOpen ? (
          <form onSubmit={handleWithdraw} className="space-y-3 border-t border-line-light pt-3">
            <p className="text-xs leading-relaxed text-ink">
              탈퇴하면 되돌릴 수 없어요. 본인 확인을 위해 비밀번호를 다시 입력해 주세요.
            </p>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={withdrawPassword}
              onChange={(e) => setWithdrawPassword(e.target.value)}
              placeholder="현재 비밀번호 입력"
              aria-label="탈퇴 확인 비밀번호"
              className="h-10 w-full rounded-input border border-line-light bg-surface px-3.5 text-sm focus:border-brand focus:outline-none"
            />
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-ink">
              <input
                type="checkbox"
                checked={withdrawChecked}
                onChange={(e) => setWithdrawChecked(e.target.checked)}
                className="h-4 w-4 accent-brand"
              />
              <span>모든 개인 데이터 삭제 및 탈퇴에 동의합니다</span>
            </label>
            {withdrawError ? (
              <p role="alert" className="text-xs font-semibold text-brand">
                {withdrawError}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={withdrawBusy || !withdrawChecked || !withdrawPassword}
              className="w-full rounded-chip bg-brand py-2.5 text-xs font-extrabold text-surface disabled:opacity-50"
            >
              {withdrawBusy ? "탈퇴 처리 중…" : "회원 탈퇴 확인"}
            </button>
          </form>
        ) : null}
        </section>
      </div>
    </div>
  );
}

export function MeView() {
  return (
    <RequireAuth nextPath="/me">
      <MeContent />
    </RequireAuth>
  );
}
