"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import {
  Check,
  MessageCircle,
  Plus,
  RotateCcw,
  Users,
  X,
} from "lucide-react";
import { handleAuthError, RequireAuth } from "@/components/RequireAuth";
import { listFriends, type FriendItem } from "@/features/community/friends/api";
import { ApiError } from "@/lib/api/client";
import {
  actOnRoom,
  createDirectRoom,
  createGroupRoom,
  listChatRooms,
  type ChatRoomItem,
  type RoomFilter,
} from "./api";
import { getChatRoomTitle } from "./roomDisplay";

const FILTER_OPTIONS: { value: RoomFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "companion", label: "동행" },
  { value: "friend", label: "친구" },
  { value: "past", label: "지난 대화" },
];

export const CLOSED_DIRECT_HINT =
  "닫힌 대화예요. 새로 대화를 시작할 수 있어요";

function roomTypeLabel(type: ChatRoomItem["room_type"]): string {
  if (type === "companion") return "동행";
  if (type === "direct") return "친구";
  return "단체";
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function ChatListContent() {
  const router = useRouter();
  const [filter, setFilter] = useState<RoomFilter>("all");
  const [rooms, setRooms] = useState<ChatRoomItem[]>([]);
  const [emptyHint, setEmptyHint] = useState("동행을 찾거나 친구를 추가해 보세요");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [busyRoomId, setBusyRoomId] = useState<string | null>(null);

  // Create room modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createMode, setCreateMode] = useState<"direct" | "friend_group">("direct");
  const [friends, setFriends] = useState<FriendItem[]>([]);
  const [friendsLoading, setFriendsLoading] = useState(false);
  const [selectedFriendIds, setSelectedFriendIds] = useState<string[]>([]);
  const [groupName, setGroupName] = useState("");
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await listChatRooms(filter, controller.signal);
        if (controller.signal.aborted) return;
        setRooms(res.items);
        if (res.empty_hint) {
          setEmptyHint(res.empty_hint);
        }
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        setRooms([]);
        setError(
          cause instanceof ApiError
            ? cause.message
            : "채팅방 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [filter, reloadTick]);

  useEffect(() => {
    if (!createOpen) return;
    const controller = new AbortController();
    async function load() {
      setFriendsLoading(true);
      setCreateError(null);
      try {
        const res = await listFriends(1, controller.signal);
        if (!controller.signal.aborted) setFriends(res.items);
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        setCreateError(
          cause instanceof ApiError
            ? cause.message
            : "친구 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setFriendsLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [createOpen]);

  async function handleInvitation(roomId: string, action: "accept" | "decline") {
    if (busyRoomId) return;
    setBusyRoomId(roomId);
    setError(null);
    try {
      await actOnRoom(roomId, action);
      if (action === "accept") {
        router.push(`/chats/${encodeURIComponent(roomId)}`);
      } else {
        setReloadTick((v) => v + 1);
      }
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError ? cause.message : "초대 처리에 실패했어요.",
      );
    } finally {
      setBusyRoomId(null);
    }
  }

  function toggleFriend(userId: string) {
    if (createMode === "direct") {
      setSelectedFriendIds([userId]);
      return;
    }
    setSelectedFriendIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : prev.length < 19
          ? [...prev, userId]
          : prev,
    );
  }

  async function handleCreateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (createBusy) return;
    setCreateError(null);

    if (createMode === "direct") {
      if (selectedFriendIds.length !== 1) {
        setCreateError("1:1 대화를 시작할 친구를 한 명 선택해 주세요.");
        return;
      }
    } else {
      if (!groupName.trim()) {
        setCreateError("단체방 이름을 입력해 주세요.");
        return;
      }
      if (selectedFriendIds.length < 2) {
        setCreateError("단체방은 친구를 2명 이상 선택해 주세요.");
        return;
      }
    }

    setCreateBusy(true);
    try {
      const created =
        createMode === "direct"
          ? await createDirectRoom(selectedFriendIds[0])
          : await createGroupRoom(groupName.trim(), selectedFriendIds);
      setCreateOpen(false);
      setSelectedFriendIds([]);
      setGroupName("");
      router.push(`/chats/${encodeURIComponent(created.room_id)}`);
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setCreateError(
        cause instanceof ApiError
          ? cause.message
          : "채팅방을 만들지 못했어요.",
      );
    } finally {
      setCreateBusy(false);
    }
  }

  return (
    <div className="space-y-4 px-4 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          <h1 className="text-lg font-black text-ink">채팅</h1>
        </div>
        <div className="flex items-center gap-1.5">
          <Link
            href="/friends"
            className="rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand"
          >
            친구
          </Link>
          <button
            type="button"
            onClick={() => {
              setSelectedFriendIds([]);
              setGroupName("");
              setCreateError(null);
              setCreateOpen(true);
            }}
            className="inline-flex items-center gap-1 rounded-chip bg-brand px-3.5 py-1.5 text-xs font-extrabold text-surface shadow-sm hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            <span>새 채팅</span>
          </button>
        </div>
      </div>

      {/* 필터 */}
      <div
        role="group"
        aria-label="채팅방 분류"
        className="flex items-center gap-1.5 overflow-x-auto py-0.5"
      >
        {FILTER_OPTIONS.map((opt) => {
          const active = filter === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(opt.value)}
              className={
                active
                  ? "shrink-0 rounded-chip bg-brand px-3.5 py-1.5 text-xs font-bold text-surface"
                  : "shrink-0 rounded-chip border border-line-light bg-surface px-3.5 py-1.5 text-xs font-semibold text-muted hover:text-ink"
              }
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div role="status" aria-label="채팅방 불러오는 중" className="space-y-2.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-card bg-surface-muted" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-12 text-center">
          <p role="alert" className="text-sm font-semibold text-ink">
            {error}
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
      ) : rooms.length === 0 ? (
        <div className="space-y-3 rounded-card border border-line-light bg-surface px-4 py-12 text-center">
          <MessageCircle className="mx-auto h-8 w-8 text-brand/60" aria-hidden="true" />
          <p className="text-sm font-bold text-ink">{emptyHint}</p>
          <div className="flex justify-center gap-2">
            <Link
              href="/companions"
              className="rounded-chip bg-brand px-4 py-2 text-xs font-extrabold text-surface"
            >
              동행 찾기
            </Link>
            <Link
              href="/friends"
              className="rounded-chip border border-line-light bg-surface px-4 py-2 text-xs font-bold text-ink"
            >
              친구 추가
            </Link>
          </div>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {rooms.map((room) => {
            const isClosedDirect =
              room.room_type === "direct" && room.status === "closed";
            return (
              <li
                key={room.room_id}
                className="rounded-card border border-line-light bg-surface p-4 shadow-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="rounded-chip bg-surface-soft px-2 py-0.5 text-[10px] font-extrabold text-brand">
                        {roomTypeLabel(room.room_type)}
                      </span>
                      {room.status === "read_only" ? (
                        <span className="rounded-chip bg-surface-muted px-2 py-0.5 text-[10px] font-bold text-muted">
                          읽기 전용
                        </span>
                      ) : room.status === "closed" ? (
                        <span className="rounded-chip bg-surface-muted px-2 py-0.5 text-[10px] font-bold text-muted">
                          닫힘
                        </span>
                      ) : null}
                      {room.my_status === "invited" ? (
                        <span className="rounded-chip bg-brand/15 px-2 py-0.5 text-[10px] font-extrabold text-brand">
                          초대됨
                        </span>
                      ) : null}
                    </div>
                    <p className="truncate text-sm font-extrabold text-ink">
                      {getChatRoomTitle(room)}
                    </p>
                    {isClosedDirect ? (
                      <p className="text-xs font-medium text-muted">
                        {CLOSED_DIRECT_HINT}
                      </p>
                    ) : room.last_message_at ? (
                      <p className="text-[11px] text-muted">
                        최근 메시지 · {formatTime(room.last_message_at)}
                      </p>
                    ) : (
                      <p className="text-[11px] text-muted">아직 메시지가 없어요</p>
                    )}
                  </div>

                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    {room.unread_count > 0 && room.my_status === "joined" ? (
                      <span
                        aria-label={`안 읽은 메시지 ${room.unread_count}개`}
                        className="rounded-chip bg-brand px-2 py-0.5 text-[11px] font-extrabold text-surface"
                      >
                        {room.unread_count}
                      </span>
                    ) : null}
                    {room.my_status === "joined" ? (
                      <Link
                        href={`/chats/${encodeURIComponent(room.room_id)}`}
                        className="rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-bold text-ink hover:border-brand/40 hover:text-brand"
                      >
                        열기
                      </Link>
                    ) : null}
                  </div>
                </div>

                {room.my_status === "invited" ? (
                  <div className="mt-3 flex justify-end gap-2">
                    <button
                      type="button"
                      disabled={busyRoomId === room.room_id}
                      onClick={() => void handleInvitation(room.room_id, "decline")}
                      className="inline-flex items-center gap-1 rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>거절</span>
                    </button>
                    <button
                      type="button"
                      disabled={busyRoomId === room.room_id}
                      onClick={() => void handleInvitation(room.room_id, "accept")}
                      className="inline-flex items-center gap-1 rounded-chip bg-brand px-3.5 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>수락</span>
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {/* 새 채팅방 만들기 모달 */}
      {createOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 backdrop-blur-[1px]"
          onClick={() => setCreateOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="new-chat-title"
            className="max-h-[85dvh] w-full max-w-[480px] overflow-y-auto rounded-t-[24px] bg-surface px-5 pb-7 pt-4 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 id="new-chat-title" className="text-base font-black text-ink">
                새 채팅 시작하기
              </h2>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                aria-label="닫기"
                className="flex h-8 w-8 items-center justify-center rounded-chip text-muted hover:bg-surface-muted"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <div className="mb-3 grid grid-cols-2 rounded-chip border border-line-light p-1">
              <button
                type="button"
                onClick={() => {
                  setCreateMode("direct");
                  setSelectedFriendIds((prev) => prev.slice(0, 1));
                }}
                className={`rounded-chip py-2 text-xs font-extrabold ${
                  createMode === "direct" ? "bg-brand text-surface" : "text-muted"
                }`}
              >
                1:1 대화
              </button>
              <button
                type="button"
                onClick={() => setCreateMode("friend_group")}
                className={`rounded-chip py-2 text-xs font-extrabold ${
                  createMode === "friend_group" ? "bg-brand text-surface" : "text-muted"
                }`}
              >
                단체방 (2명 이상)
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-3">
              {createMode === "friend_group" ? (
                <div>
                  <label
                    htmlFor="group-room-name"
                    className="mb-1 block text-xs font-bold text-ink"
                  >
                    단체방 이름 (1~40자)
                  </label>
                  <input
                    id="group-room-name"
                    type="text"
                    required
                    maxLength={40}
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    placeholder="예: 여의도 불꽃축제 팀"
                    className="h-10 w-full rounded-input border border-line-light px-3.5 text-sm focus:border-brand focus:outline-none"
                  />
                </div>
              ) : null}

              <div>
                <p className="mb-1.5 text-xs font-bold text-ink">
                  초대할 친구 선택 ({selectedFriendIds.length}명)
                </p>
                {friendsLoading ? (
                  <div className="h-20 animate-pulse rounded-card bg-surface-muted" />
                ) : friends.length === 0 ? (
                  <div className="rounded-card border border-line-light bg-surface-muted/50 px-3 py-5 text-center text-xs text-muted">
                    <Users className="mx-auto mb-1 h-5 w-5 text-muted" aria-hidden="true" />
                    <p>먼저 친구를 추가해 주세요.</p>
                  </div>
                ) : (
                  <ul className="max-h-48 space-y-1.5 overflow-y-auto rounded-card border border-line-light p-2">
                    {friends.map((friend) => {
                      const checked = selectedFriendIds.includes(friend.user_id);
                      return (
                        <li key={friend.user_id}>
                          <label className="flex cursor-pointer items-center justify-between rounded-xl px-2.5 py-2 hover:bg-surface-soft/50">
                            <span className="text-sm font-semibold text-ink">
                              {friend.display_name ?? "알 수 없음"}
                            </span>
                            <input
                              type={createMode === "direct" ? "radio" : "checkbox"}
                              name="chat-friend"
                              checked={checked}
                              onChange={() => toggleFriend(friend.user_id)}
                              className="h-4 w-4 accent-brand"
                            />
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              {createError ? (
                <p role="alert" className="text-xs font-semibold text-brand">
                  {createError}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={createBusy || friends.length === 0}
                className="w-full rounded-chip bg-brand py-3 text-sm font-extrabold text-surface shadow-sm disabled:opacity-60"
              >
                {createBusy ? "생성 중…" : "채팅방 만들기"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ChatListView() {
  return (
    <RequireAuth nextPath="/chats">
      <ChatListContent />
    </RequireAuth>
  );
}
