"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import {
  Check,
  MessageCircle,
  RotateCcw,
  Search,
  ShieldBan,
  UserMinus,
  UserPlus,
  X,
} from "lucide-react";
import { handleAuthError, RequireAuth } from "@/components/RequireAuth";
import { createDirectRoom } from "@/features/community/chats/api";
import { ApiError } from "@/lib/api/client";
import {
  actOnFriendRequest,
  blockUser,
  createFriendRequest,
  deleteFriend,
  listFriendRequests,
  listFriends,
  searchUsersByNickname,
  type FriendItem,
  type FriendRequestItem,
  type FriendSearchItem,
} from "./api";
import { rememberBlockedUser } from "./blockCache";

type FriendsTab = "friends" | "received" | "sent";

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

function FriendsContent() {
  const router = useRouter();
  const [tab, setTab] = useState<FriendsTab>("friends");

  // Search state
  const [nickname, setNickname] = useState("");
  const [searchResults, setSearchResults] = useState<FriendSearchItem[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Friends list
  const [friends, setFriends] = useState<FriendItem[]>([]);
  const [page, setPage] = useState(1);
  const [hasMoreFriends, setHasMoreFriends] = useState(false);
  const [friendsLoading, setFriendsLoading] = useState(true);
  const [friendsError, setFriendsError] = useState<string | null>(null);

  // Requests
  const [received, setReceived] = useState<FriendRequestItem[]>([]);
  const [sent, setSent] = useState<FriendRequestItem[]>([]);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [requestsError, setRequestsError] = useState<string | null>(null);

  const [reloadTick, setReloadTick] = useState(0);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setFriendsLoading(true);
      setFriendsError(null);
      try {
        const res = await listFriends(1, controller.signal);
        if (controller.signal.aborted) return;
        setFriends(res.items);
        setPage(1);
        setHasMoreFriends(res.items.length >= 20);
      } catch (error) {
        if (controller.signal.aborted) return;
        if (handleAuthError(error)) return;
        setFriendsError(
          error instanceof ApiError
            ? error.message
            : "친구 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setFriendsLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [reloadTick]);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setRequestsLoading(true);
      setRequestsError(null);
      try {
        const [recvRes, sentRes] = await Promise.all([
          listFriendRequests("received", controller.signal),
          listFriendRequests("sent", controller.signal),
        ]);
        if (controller.signal.aborted) return;
        setReceived(recvRes.items);
        setSent(sentRes.items);
      } catch (error) {
        if (controller.signal.aborted) return;
        if (handleAuthError(error)) return;
        setRequestsError(
          error instanceof ApiError
            ? error.message
            : "친구 신청 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setRequestsLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [reloadTick]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = nickname.trim();
    if (query.length < 2 || query.length > 12) {
      setSearchError("닉네임은 2~12자로 정확히 입력해 주세요.");
      return;
    }
    setSearching(true);
    setSearchError(null);
    setNotice(null);
    try {
      const res = await searchUsersByNickname(query);
      setSearchResults(res.items);
    } catch (error) {
      if (handleAuthError(error)) return;
      setSearchResults(null);
      setSearchError(
        error instanceof ApiError
          ? error.message
          : "사용자 검색에 실패했어요.",
      );
    } finally {
      setSearching(false);
    }
  }

  async function handleSendRequest(userId: string) {
    if (busyKey) return;
    setBusyKey(`req:${userId}`);
    setActionError(null);
    setNotice(null);
    try {
      const res = await createFriendRequest(userId);
      setNotice(
        res.status === "accepted"
          ? "서로 신청해서 바로 친구가 되었어요!"
          : "친구 신청을 보냈어요.",
      );
      setSearchResults((prev) =>
        prev
          ? prev.map((item) =>
              item.user_id === userId
                ? {
                    ...item,
                    friendship_status:
                      res.status === "accepted" ? "friends" : "pending_sent",
                  }
                : item,
            )
          : prev,
      );
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) return;
      setActionError(
        error instanceof ApiError ? error.message : "친구 신청에 실패했어요.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRequestAction(
    requestId: string,
    action: "accept" | "reject" | "cancel",
  ) {
    if (busyKey) return;
    setBusyKey(`act:${requestId}`);
    setActionError(null);
    setNotice(null);
    try {
      await actOnFriendRequest(requestId, action);
      setNotice(
        action === "accept"
          ? "친구 신청을 수락했어요."
          : action === "reject"
            ? "친구 신청을 거절했어요."
            : "친구 신청을 취소했어요.",
      );
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) return;
      setActionError(
        error instanceof ApiError ? error.message : "요청 처리에 실패했어요.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDeleteFriend(userId: string) {
    if (busyKey) return;
    setBusyKey(`del:${userId}`);
    setActionError(null);
    setNotice(null);
    try {
      await deleteFriend(userId);
      setNotice("친구를 삭제했어요.");
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) return;
      setActionError(
        error instanceof ApiError ? error.message : "친구 삭제에 실패했어요.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleBlock(userId: string, displayName: string | null) {
    if (busyKey) return;
    setBusyKey(`blk:${userId}`);
    setActionError(null);
    setNotice(null);
    try {
      await blockUser(userId);
      rememberBlockedUser(userId, displayName);
      setNotice("사용자를 차단했어요. 마이페이지에서 차단을 해제할 수 있어요.");
      setSearchResults((prev) =>
        prev ? prev.filter((item) => item.user_id !== userId) : prev,
      );
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) return;
      setActionError(
        error instanceof ApiError ? error.message : "차단에 실패했어요.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleStartDirectChat(friendId: string) {
    if (busyKey) return;
    setBusyKey(`chat:${friendId}`);
    setActionError(null);
    try {
      const created = await createDirectRoom(friendId);
      router.push(`/chats/${encodeURIComponent(created.room_id)}`);
    } catch (error) {
      if (handleAuthError(error)) return;
      setActionError(
        error instanceof ApiError
          ? error.message
          : "1:1 채팅방을 열지 못했어요.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleLoadMoreFriends() {
    if (busyKey) return;
    const nextPage = page + 1;
    setBusyKey("more");
    try {
      const res = await listFriends(nextPage);
      setFriends((prev) => [...prev, ...res.items]);
      setPage(nextPage);
      setHasMoreFriends(res.items.length >= 20);
    } catch (error) {
      if (handleAuthError(error)) return;
      setFriendsError(
        error instanceof ApiError
          ? error.message
          : "추가 친구를 불러오지 못했어요.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  const pendingReceivedCount = received.filter((r) => r.status === "pending").length;

  return (
    <div className="space-y-4 px-4 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          <h1 className="text-lg font-black text-ink">친구</h1>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/chats"
            className="rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand"
          >
            채팅방
          </Link>
          <Link
            href="/me"
            className="rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-muted hover:text-ink"
          >
            차단 관리
          </Link>
        </div>
      </div>

      {/* 닉네임 검색 */}
      <section className="space-y-2.5 rounded-card border border-line-light bg-surface p-4 shadow-sm">
        <h2 className="text-sm font-extrabold text-ink">닉네임으로 친구 찾기</h2>
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
              aria-hidden="true"
            />
            <input
              type="search"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="정확한 닉네임 (2~12자)"
              aria-label="닉네임 검색"
              minLength={2}
              maxLength={12}
              className="h-10 w-full rounded-input border border-line-light bg-surface pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="h-10 shrink-0 rounded-input bg-brand px-4 text-xs font-extrabold text-surface disabled:opacity-60"
          >
            {searching ? "검색 중…" : "검색"}
          </button>
        </form>

        {searchError ? (
          <p role="alert" className="text-xs font-semibold text-brand">
            {searchError}
          </p>
        ) : null}

        {searchResults !== null ? (
          searchResults.length === 0 ? (
            <p className="rounded-xl bg-surface-muted/60 px-3 py-3 text-center text-xs text-muted">
              일치하는 사용자가 없어요. 닉네임을 정확히 입력했는지 확인해 주세요.
            </p>
          ) : (
            <ul className="space-y-2">
              {searchResults.map((user) => (
                <li
                  key={user.user_id}
                  className="flex items-center justify-between gap-2 rounded-xl bg-surface-soft/50 px-3.5 py-2.5"
                >
                  <span className="truncate text-sm font-extrabold text-ink">
                    {user.display_name}
                  </span>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {user.friendship_status === "none" ? (
                      <button
                        type="button"
                        disabled={busyKey === `req:${user.user_id}`}
                        onClick={() => void handleSendRequest(user.user_id)}
                        className="inline-flex items-center gap-1 rounded-chip bg-brand px-3 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                      >
                        <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>친구 신청</span>
                      </button>
                    ) : user.friendship_status === "pending_sent" ? (
                      <span className="rounded-chip bg-surface px-2.5 py-1 text-[11px] font-bold text-muted">
                        신청 보냄
                      </span>
                    ) : user.friendship_status === "pending_received" ? (
                      <button
                        type="button"
                        disabled={busyKey === `req:${user.user_id}`}
                        onClick={() => void handleSendRequest(user.user_id)}
                        className="rounded-chip bg-brand px-3 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                      >
                        수락하기
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={busyKey === `chat:${user.user_id}`}
                        onClick={() => void handleStartDirectChat(user.user_id)}
                        className="inline-flex items-center gap-1 rounded-chip bg-brand px-3 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                      >
                        <MessageCircle className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>1:1 채팅</span>
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={busyKey === `blk:${user.user_id}`}
                      onClick={() => void handleBlock(user.user_id, user.display_name)}
                      aria-label={`${user.display_name} 차단`}
                      className="rounded-chip border border-line-light bg-surface p-1.5 text-muted hover:text-brand"
                    >
                      <ShieldBan className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )
        ) : null}
      </section>

      {notice ? (
        <p role="status" className="rounded-card bg-surface-soft px-3.5 py-2.5 text-xs font-semibold text-ink">
          {notice}
        </p>
      ) : null}
      {actionError ? (
        <p role="alert" className="rounded-card border border-brand/30 bg-surface-soft/50 px-3.5 py-2.5 text-xs font-semibold text-brand">
          {actionError}
        </p>
      ) : null}

      {/* 탭 */}
      <div
        role="tablist"
        aria-label="친구 탭"
        className="grid grid-cols-3 rounded-chip border border-line-light bg-surface p-1 shadow-sm"
      >
        <button
          type="button"
          role="tab"
          aria-selected={tab === "friends"}
          onClick={() => setTab("friends")}
          className={`rounded-chip py-2 text-xs font-extrabold ${
            tab === "friends" ? "bg-brand text-surface" : "text-muted hover:text-ink"
          }`}
        >
          친구 목록 ({friends.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "received"}
          onClick={() => setTab("received")}
          className={`rounded-chip py-2 text-xs font-extrabold ${
            tab === "received" ? "bg-brand text-surface" : "text-muted hover:text-ink"
          }`}
        >
          받은 신청 {pendingReceivedCount > 0 ? `(${pendingReceivedCount})` : ""}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "sent"}
          onClick={() => setTab("sent")}
          className={`rounded-chip py-2 text-xs font-extrabold ${
            tab === "sent" ? "bg-brand text-surface" : "text-muted hover:text-ink"
          }`}
        >
          보낸 신청
        </button>
      </div>

      {/* 친구 목록 */}
      {tab === "friends" ? (
        friendsLoading ? (
          <div role="status" className="space-y-2">
            {[0, 1].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-card bg-surface-muted" />
            ))}
          </div>
        ) : friendsError ? (
          <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
            <p role="alert" className="text-sm font-semibold text-ink">
              {friendsError}
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
        ) : friends.length === 0 ? (
          <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center">
            <p className="text-sm font-bold text-ink">아직 친구가 없어요</p>
            <p className="mt-1 text-xs text-muted">
              위에서 닉네임으로 친구를 검색해 신청해 보세요.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            <ul className="space-y-2">
              {friends.map((friend) => (
                <li
                  key={friend.user_id}
                  className="flex items-center justify-between gap-2 rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-extrabold text-ink">
                      {friend.display_name ?? "알 수 없음"}
                    </p>
                    <p className="text-[11px] text-muted">
                      친구 시작 · {formatShortDate(friend.since)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <button
                      type="button"
                      disabled={busyKey === `chat:${friend.user_id}`}
                      onClick={() => void handleStartDirectChat(friend.user_id)}
                      className="inline-flex items-center gap-1 rounded-chip bg-brand px-3 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                    >
                      <MessageCircle className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>채팅</span>
                    </button>
                    <button
                      type="button"
                      disabled={busyKey === `del:${friend.user_id}`}
                      onClick={() => void handleDeleteFriend(friend.user_id)}
                      aria-label={`${friend.display_name ?? "친구"} 삭제`}
                      className="inline-flex items-center gap-1 rounded-chip border border-line-light px-2.5 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                    >
                      <UserMinus className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>삭제</span>
                    </button>
                    <button
                      type="button"
                      disabled={busyKey === `blk:${friend.user_id}`}
                      onClick={() => void handleBlock(friend.user_id, friend.display_name)}
                      aria-label={`${friend.display_name ?? "친구"} 차단`}
                      className="rounded-chip border border-line-light p-1.5 text-muted hover:text-brand disabled:opacity-60"
                    >
                      <ShieldBan className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            {hasMoreFriends ? (
              <button
                type="button"
                disabled={busyKey === "more"}
                onClick={() => void handleLoadMoreFriends()}
                className="w-full rounded-card border border-line-light bg-surface py-2.5 text-xs font-bold text-ink hover:bg-surface-soft"
              >
                {busyKey === "more" ? "불러오는 중…" : "더 보기"}
              </button>
            ) : null}
          </div>
        )
      ) : requestsLoading ? (
        <div role="status" className="h-24 animate-pulse rounded-card bg-surface-muted" />
      ) : requestsError ? (
        <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <p role="alert" className="text-sm font-semibold text-ink">
            {requestsError}
          </p>
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            다시 시도
          </button>
        </div>
      ) : tab === "received" ? (
        received.length === 0 ? (
          <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center text-sm text-muted">
            받은 친구 신청이 없어요.
          </div>
        ) : (
          <ul className="space-y-2">
            {received.map((req) => (
              <li
                key={req.request_id}
                className="flex items-center justify-between gap-2 rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-extrabold text-ink">
                    {req.display_name ?? "알 수 없음"}
                  </p>
                  <p className="text-[11px] text-muted">
                    {formatShortDate(req.created_at)} ·{" "}
                    {req.status === "pending"
                      ? "대기 중"
                      : req.status === "accepted"
                        ? "수락됨"
                        : req.status === "rejected"
                          ? "거절됨"
                          : "취소됨"}
                  </p>
                </div>
                {req.status === "pending" ? (
                  <div className="flex shrink-0 items-center gap-1.5">
                    <button
                      type="button"
                      disabled={busyKey === `act:${req.request_id}`}
                      onClick={() => void handleRequestAction(req.request_id, "reject")}
                      className="inline-flex items-center gap-1 rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>거절</span>
                    </button>
                    <button
                      type="button"
                      disabled={busyKey === `act:${req.request_id}`}
                      onClick={() => void handleRequestAction(req.request_id, "accept")}
                      className="inline-flex items-center gap-1 rounded-chip bg-brand px-3 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>수락</span>
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )
      ) : sent.length === 0 ? (
        <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center text-sm text-muted">
          보낸 친구 신청이 없어요.
        </div>
      ) : (
        <ul className="space-y-2">
          {sent.map((req) => (
            <li
              key={req.request_id}
              className="flex items-center justify-between gap-2 rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-extrabold text-ink">
                  {req.display_name ?? "알 수 없음"}
                </p>
                <p className="text-[11px] text-muted">
                  {formatShortDate(req.created_at)} ·{" "}
                  {req.status === "pending"
                    ? "응답 대기 중"
                    : req.status === "accepted"
                      ? "수락됨"
                      : req.status === "rejected"
                        ? "거절됨"
                        : "취소됨"}
                </p>
              </div>
              {req.status === "pending" ? (
                <button
                  type="button"
                  disabled={busyKey === `act:${req.request_id}`}
                  onClick={() => void handleRequestAction(req.request_id, "cancel")}
                  className="shrink-0 rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                >
                  신청 취소
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function FriendsView() {
  return (
    <RequireAuth nextPath="/friends">
      <FriendsContent />
    </RequireAuth>
  );
}
