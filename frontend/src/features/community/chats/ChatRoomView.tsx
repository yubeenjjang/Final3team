"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react";
import {
  ArrowLeft,
  ChevronUp,
  LogOut,
  Pencil,
  RotateCcw,
  Send,
  UserPlus,
  X,
} from "lucide-react";
import { handleAuthError, RequireAuth } from "@/components/RequireAuth";
import { listFriends, type FriendItem } from "@/features/community/friends/api";
import {
  getAuthUser,
  getAuthUserServerSnapshot,
  subscribeAuth,
} from "@/lib/api/auth";
import { ApiError, getWsUrl } from "@/lib/api/client";
import {
  actOnRoom,
  inviteToRoom,
  issueWsTicket,
  listChatRooms,
  listRoomMessages,
  markRoomRead,
  renameRoom,
  type ChatMessageItem,
  type ChatRoomItem,
  type RoomStatus,
} from "./api";
import { CLOSED_DIRECT_HINT } from "./ChatListView";

type ConnectionState = "connecting" | "connected" | "reconnecting" | "closed";

interface WsServerEvent {
  type: "ack" | "message" | "error" | "room_status" | "notification" | "unsubscribed";
  room_id?: string;
  client_message_id?: string;
  message_id?: number;
  seq?: number;
  sender_id?: string | null;
  sender_display_name?: string | null;
  msg_type?: "text" | "system";
  body?: string;
  created_at?: string;
  code?: string;
  status?: RoomStatus;
  reason?: "left" | "removed" | "blocked" | "deleted";
}

function createClientMessageId(): string {
  if (typeof globalThis.crypto !== "undefined" && globalThis.crypto.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function mergeMessages(
  existing: ChatMessageItem[],
  incoming: ChatMessageItem[],
  nameMap: Map<string, string>,
): ChatMessageItem[] {
  const bySeq = new Map<number, ChatMessageItem>();
  for (const item of existing) {
    if (item.sender_id && item.sender_display_name) {
      nameMap.set(item.sender_id, item.sender_display_name);
    }
    bySeq.set(item.seq, item);
  }
  for (const item of incoming) {
    if (item.sender_id && item.sender_display_name) {
      nameMap.set(item.sender_id, item.sender_display_name);
    }
    const prev = bySeq.get(item.seq);
    const resolvedName =
      item.sender_display_name ??
      prev?.sender_display_name ??
      (item.sender_id ? nameMap.get(item.sender_id) ?? null : null);
    bySeq.set(item.seq, { ...item, sender_display_name: resolvedName });
  }
  return Array.from(bySeq.values())
    .map((item) =>
      !item.sender_display_name && item.sender_id && nameMap.has(item.sender_id)
        ? { ...item, sender_display_name: nameMap.get(item.sender_id) ?? null }
        : item,
    )
    .sort((a, b) => a.seq - b.seq);
}

function wsErrorText(code?: string): string {
  switch (code) {
    case "ROOM_READ_ONLY":
      return "메시지를 보낼 수 없는 채팅방이에요.";
    case "RATE_LIMITED":
      return "잠시 뒤 메시지를 보내 주세요.";
    case "FORBIDDEN":
      return "이 채팅방에 접근할 수 없어요.";
    case "STORE_FAILED":
      return "메시지를 저장하지 못했어요. 다시 시도해 주세요.";
    case "VALIDATION_ERROR":
      return "메시지 형식을 확인해 주세요.";
    default:
      return "메시지 전송 중 오류가 발생했어요.";
  }
}

function formatMsgTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

export interface ChatRoomViewProps {
  roomId: string;
}

function ChatRoomContent({ roomId }: ChatRoomViewProps) {
  const router = useRouter();
  const me = useSyncExternalStore(
    subscribeAuth,
    getAuthUser,
    getAuthUserServerSnapshot,
  );

  const [room, setRoom] = useState<ChatRoomItem | null>(null);
  const [roomStatus, setRoomStatus] = useState<RoomStatus>("active");
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [connState, setConnState] = useState<ConnectionState>("connecting");
  const [unsubscribedReason, setUnsubscribedReason] = useState<string | null>(null);
  const [wsError, setWsError] = useState<string | null>(null);
  const [inputBody, setInputBody] = useState("");
  const [sending, setSending] = useState(false);

  // Group management states
  const [inviteOpen, setInviteOpen] = useState(false);
  const [friends, setFriends] = useState<FriendItem[]>([]);
  const [selectedInvitees, setSelectedInvitees] = useState<string[]>([]);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameInput, setRenameInput] = useState("");
  const [manageNotice, setManageNotice] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const lastSeqRef = useRef(0);
  const senderNamesRef = useRef<Map<string, string>>(new Map());
  const resolvingSendersRef = useRef<Set<string>>(new Set());
  const unresolvableSendersRef = useRef<Set<string>>(new Set());
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const stopReconnectRef = useRef(false);

  useEffect(() => {
    if (me?.userId && me.displayName) {
      senderNamesRef.current.set(me.userId, me.displayName);
    }
  }, [me]);

  // Initial load: room metadata + recent message history
  useEffect(() => {
    const controller = new AbortController();
    stopReconnectRef.current = false;
    resolvingSendersRef.current.clear();
    unresolvableSendersRef.current.clear();

    async function loadInitial() {
      setLoading(true);
      setError(null);
      setWsError(null);
      setUnsubscribedReason(null);
      let matchedRoom: ChatRoomItem | null = null;
      try {
        const roomsRes = await listChatRooms("all", controller.signal);
        matchedRoom = roomsRes.items.find((item) => item.room_id === roomId) ?? null;
        if (!controller.signal.aborted && matchedRoom) {
          setRoom(matchedRoom);
          setRoomStatus(matchedRoom.status);
          setRenameInput(matchedRoom.name ?? "");
        }
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
      }

      try {
        const historyRes = await listRoomMessages(
          roomId,
          { limit: 50 },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        const merged = mergeMessages([], historyRes.items, senderNamesRef.current);
        setMessages(merged);
        setHasMore(historyRes.has_more);
        const latestSeq = merged[merged.length - 1]?.seq ?? 0;
        lastSeqRef.current = latestSeq;
        if (latestSeq > 0) {
          void markRoomRead(roomId, latestSeq).catch(() => {});
        }
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        // Closed-by-block direct rooms return 403 on history; show the closed direct banner instead of a generic error.
        if (
          matchedRoom &&
          matchedRoom.room_type === "direct" &&
          matchedRoom.status === "closed"
        ) {
          setMessages([]);
          setHasMore(false);
          setConnState("closed");
          stopReconnectRef.current = true;
        } else {
          setError(
            cause instanceof ApiError
              ? cause.message
              : "채팅방 메시지를 불러오지 못했어요.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadInitial();
    return () => controller.abort();
  }, [roomId, reloadTick]);

  const syncMissedAfterSeq = useCallback(async () => {
    try {
      const res = await listRoomMessages(roomId, {
        after_seq: lastSeqRef.current,
        limit: 100,
      });
      if (!mountedRef.current || res.items.length === 0) return;
      setMessages((prev) => {
        const merged = mergeMessages(prev, res.items, senderNamesRef.current);
        const maxSeq = merged[merged.length - 1]?.seq ?? lastSeqRef.current;
        if (maxSeq > lastSeqRef.current) {
          lastSeqRef.current = maxSeq;
          void markRoomRead(roomId, maxSeq).catch(() => {});
        }
        return merged;
      });
    } catch {
      // Best-effort catch-up alongside WS subscribe after_seq
    }
  }, [roomId]);

  const resolveSenderNameFromHistory = useCallback(
    async (seq: number, senderId: string) => {
      if (
        senderNamesRef.current.has(senderId) ||
        resolvingSendersRef.current.has(senderId) ||
        unresolvableSendersRef.current.has(senderId)
      ) {
        return;
      }
      resolvingSendersRef.current.add(senderId);
      try {
        const res = await listRoomMessages(roomId, {
          after_seq: Math.max(0, seq - 1),
          limit: 20,
        });
        if (!mountedRef.current) return;
        const matched = res.items.find((item) => item.sender_id === senderId);
        if (matched && !matched.sender_display_name) {
          unresolvableSendersRef.current.add(senderId);
        }
        if (res.items.length > 0) {
          setMessages((prev) =>
            mergeMessages(prev, res.items, senderNamesRef.current),
          );
        }
      } catch {
        // Best-effort sender name lookup; keep fallback label if unavailable.
      } finally {
        resolvingSendersRef.current.delete(senderId);
      }
    },
    [roomId],
  );

  // WebSocket lifecycle: issue ticket -> connect -> subscribe -> reconnect + restore after last_seq
  useEffect(() => {
    if (loading || error || stopReconnectRef.current) {
      return;
    }
    if (room && room.room_type === "direct" && room.status === "closed") {
      return;
    }

    mountedRef.current = true;

    async function connect(isReconnect: boolean) {
      if (!mountedRef.current || stopReconnectRef.current) return;
      setConnState(isReconnect ? "reconnecting" : "connecting");

      try {
        const { ticket } = await issueWsTicket();
        if (!mountedRef.current || stopReconnectRef.current) return;

        const wsUrl = getWsUrl("/ws/chat", { ticket });
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.addEventListener("open", () => {
          if (!mountedRef.current || wsRef.current !== socket) return;
          const wasReconnect = reconnectAttemptRef.current > 0 || isReconnect;
          reconnectAttemptRef.current = 0;
          setConnState("connected");
          setWsError(null);
          socket.send(
            JSON.stringify({
              type: "subscribe",
              room_id: roomId,
              after_seq: lastSeqRef.current,
            }),
          );
          if (wasReconnect) {
            void syncMissedAfterSeq();
          }
        });

        socket.addEventListener("message", (event) => {
          if (!mountedRef.current || wsRef.current !== socket) return;
          let parsed: WsServerEvent;
          try {
            parsed = JSON.parse(String(event.data)) as WsServerEvent;
          } catch {
            return;
          }

          if (
            parsed.type === "message" &&
            parsed.room_id === roomId &&
            typeof parsed.seq === "number" &&
            typeof parsed.message_id === "number" &&
            typeof parsed.body === "string"
          ) {
            const incoming: ChatMessageItem = {
              message_id: parsed.message_id,
              seq: parsed.seq,
              sender_id: parsed.sender_id ?? null,
              sender_display_name: parsed.sender_display_name ?? null,
              msg_type: parsed.msg_type ?? "text",
              body: parsed.body,
              created_at: parsed.created_at ?? new Date().toISOString(),
            };
            setMessages((prev) =>
              mergeMessages(prev, [incoming], senderNamesRef.current),
            );
            if (
              incoming.msg_type !== "system" &&
              incoming.sender_id &&
              !incoming.sender_display_name &&
              !senderNamesRef.current.has(incoming.sender_id)
            ) {
              void resolveSenderNameFromHistory(incoming.seq, incoming.sender_id);
            }
            if (parsed.seq > lastSeqRef.current) {
              lastSeqRef.current = parsed.seq;
              void markRoomRead(roomId, parsed.seq).catch(() => {});
            }
            return;
          }

          if (parsed.type === "ack") {
            setSending(false);
            if (typeof parsed.seq === "number" && parsed.seq > lastSeqRef.current) {
              lastSeqRef.current = parsed.seq;
            }
            return;
          }

          if (
            parsed.type === "room_status" &&
            parsed.room_id === roomId &&
            parsed.status
          ) {
            setRoomStatus(parsed.status);
            setRoom((prev) => (prev ? { ...prev, status: parsed.status! } : prev));
            return;
          }

          if (parsed.type === "unsubscribed" && parsed.room_id === roomId) {
            stopReconnectRef.current = true;
            setUnsubscribedReason(parsed.reason ?? "removed");
            setConnState("closed");
            if (parsed.reason === "blocked") {
              setRoomStatus("closed");
            }
            return;
          }

          if (parsed.type === "error") {
            setSending(false);
            setWsError(wsErrorText(parsed.code));
          }
        });

        socket.addEventListener("close", (closeEvent) => {
          if (!mountedRef.current || wsRef.current !== socket) return;
          wsRef.current = null;
          if (stopReconnectRef.current || closeEvent.code === 4403) {
            setConnState("closed");
            return;
          }
          setConnState("reconnecting");
          const delay = Math.min(
            1000 * 2 ** reconnectAttemptRef.current,
            8000,
          );
          reconnectAttemptRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            void connect(true);
          }, delay);
        });
      } catch (cause) {
        if (!mountedRef.current || stopReconnectRef.current) return;
        if (handleAuthError(cause)) return;
        setConnState("reconnecting");
        const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 8000);
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          void connect(true);
        }, delay);
      }
    }

    void connect(false);

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [loading, error, roomId, room, syncMissedAfterSeq, resolveSenderNameFromHistory]);

  async function handleLoadOlder() {
    if (loadingMore || !hasMore || messages.length === 0) return;
    const oldestSeq = messages[0].seq;
    setLoadingMore(true);
    setWsError(null);
    try {
      const res = await listRoomMessages(roomId, {
        before_seq: oldestSeq,
        limit: 50,
      });
      setMessages((prev) =>
        mergeMessages(prev, res.items, senderNamesRef.current),
      );
      setHasMore(res.has_more);
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setWsError(
        cause instanceof ApiError
          ? cause.message
          : "이전 메시지를 불러오지 못했어요.",
      );
    } finally {
      setLoadingMore(false);
    }
  }

  function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = inputBody.trim();
    if (!trimmed) return;
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setWsError("실시간 연결을 복구하는 중이에요. 잠시 후 다시 보내 주세요.");
      return;
    }
    setSending(true);
    setWsError(null);
    socket.send(
      JSON.stringify({
        type: "send",
        room_id: roomId,
        client_message_id: createClientMessageId(),
        body: trimmed,
      }),
    );
    setInputBody("");
  }

  async function openInviteModal() {
    setInviteOpen(true);
    setSelectedInvitees([]);
    setManageNotice(null);
    try {
      const res = await listFriends(1);
      setFriends(res.items);
      for (const friend of res.items) {
        if (friend.display_name) {
          senderNamesRef.current.set(friend.user_id, friend.display_name);
        }
      }
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setWsError(
        cause instanceof ApiError
          ? cause.message
          : "친구 목록을 불러오지 못했어요.",
      );
    }
  }

  async function handleInviteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inviteBusy || selectedInvitees.length === 0) return;
    setInviteBusy(true);
    setWsError(null);
    try {
      const res = await inviteToRoom(roomId, selectedInvitees);
      setInviteOpen(false);
      setManageNotice(`${res.invited.length}명을 초대했어요.`);
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setWsError(
        cause instanceof ApiError ? cause.message : "초대에 실패했어요.",
      );
    } finally {
      setInviteBusy(false);
    }
  }

  async function handleRenameSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextName = renameInput.trim();
    if (!nextName) return;
    try {
      const updated = await renameRoom(roomId, nextName);
      setRoom((prev) => (prev ? { ...prev, name: updated.name } : prev));
      setRenameOpen(false);
      setManageNotice("채팅방 이름을 변경했어요.");
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setWsError(
        cause instanceof ApiError
          ? cause.message
          : "채팅방 이름을 변경하지 못했어요.",
      );
    }
  }

  async function handleLeaveRoom() {
    if (leaving) return;
    setLeaving(true);
    try {
      stopReconnectRef.current = true;
      await actOnRoom(roomId, "leave");
      router.replace("/chats");
    } catch (cause) {
      stopReconnectRef.current = false;
      if (handleAuthError(cause)) return;
      setWsError(
        cause instanceof ApiError ? cause.message : "채팅방을 나가지 못했어요.",
      );
    } finally {
      setLeaving(false);
    }
  }

  const isClosedDirect =
    (room?.room_type === "direct" && roomStatus === "closed") ||
    (room?.room_type === "direct" && unsubscribedReason === "blocked");
  const isInputDisabled =
    roomStatus !== "active" ||
    Boolean(unsubscribedReason) ||
    connState === "closed";

  if (loading) {
    return (
      <div role="status" className="space-y-3 px-4 py-4">
        <div className="h-8 w-40 animate-pulse rounded-card bg-surface-muted" />
        <div className="h-64 animate-pulse rounded-card bg-surface-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[55vh] flex-col items-center justify-center gap-3 px-4 py-12 text-center">
        <p role="alert" className="text-sm font-semibold text-ink">
          {error}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
          <Link
            href="/chats"
            className="rounded-chip border border-line-light px-4 py-2 text-xs font-bold text-ink"
          >
            채팅 목록
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100dvh-144px)] flex-col px-4 py-3">
      {/* 상단 바 */}
      <div className="flex items-center justify-between gap-2 border-b border-line-light pb-3">
        <div className="flex min-w-0 items-center gap-2">
          <Link
            href="/chats"
            aria-label="채팅 목록으로"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-chip text-ink hover:bg-surface-soft hover:text-brand"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </Link>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-black text-ink">
              {room?.name ||
                (room?.room_type === "direct"
                  ? "1:1 대화"
                  : room?.room_type === "companion"
                    ? "동행 채팅방"
                    : "채팅방")}
            </h1>
            <p className="text-[11px] text-muted">
              {connState === "connected"
                ? "실시간 연결됨"
                : connState === "reconnecting"
                  ? "다시 연결 중…"
                  : connState === "closed"
                    ? "연결 종료"
                    : "연결 중…"}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {room?.room_type === "friend_group" && roomStatus === "active" ? (
            <>
              <button
                type="button"
                onClick={() => void openInviteModal()}
                aria-label="친구 초대"
                className="flex h-8 w-8 items-center justify-center rounded-chip border border-line-light text-ink hover:border-brand/40 hover:text-brand"
              >
                <UserPlus className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => setRenameOpen((v) => !v)}
                aria-label="방 이름 변경"
                className="flex h-8 w-8 items-center justify-center rounded-chip border border-line-light text-ink hover:border-brand/40 hover:text-brand"
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
              </button>
            </>
          ) : null}
          {room && room.room_type !== "companion" ? (
            <button
              type="button"
              disabled={leaving}
              onClick={() => void handleLeaveRoom()}
              aria-label="채팅방 나가기"
              className="flex h-8 w-8 items-center justify-center rounded-chip border border-line-light text-muted hover:text-brand disabled:opacity-60"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : null}
        </div>
      </div>

      {/* 단체방 이름 변경 인라인 폼 */}
      {renameOpen ? (
        <form
          onSubmit={handleRenameSubmit}
          className="mt-2 flex items-center gap-2 rounded-card bg-surface-soft/60 p-2.5"
        >
          <input
            type="text"
            maxLength={40}
            required
            value={renameInput}
            onChange={(e) => setRenameInput(e.target.value)}
            aria-label="새 채팅방 이름"
            className="h-9 flex-1 rounded-input border border-line-light bg-surface px-3 text-xs focus:border-brand focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-chip bg-brand px-3 py-1.5 text-xs font-extrabold text-surface"
          >
            저장
          </button>
        </form>
      ) : null}

      {manageNotice ? (
        <p role="status" className="mt-2 rounded-xl bg-surface-soft px-3 py-2 text-xs font-semibold text-ink">
          {manageNotice}
        </p>
      ) : null}
      {wsError ? (
        <p role="alert" className="mt-2 rounded-xl border border-brand/30 bg-surface-soft/50 px-3 py-2 text-xs font-semibold text-brand">
          {wsError}
        </p>
      ) : null}

      {/* 닫힌 1:1 방 / 읽기 전용 배너 */}
      {isClosedDirect ? (
        <div className="mt-3 flex items-center justify-between gap-2 rounded-card border border-line-light bg-surface-soft px-4 py-3">
          <p className="text-xs font-bold text-ink">{CLOSED_DIRECT_HINT}</p>
          <Link
            href="/chats"
            className="shrink-0 rounded-chip bg-brand px-3 py-1.5 text-[11px] font-extrabold text-surface"
          >
            새 대화
          </Link>
        </div>
      ) : roomStatus === "read_only" ? (
        <p className="mt-3 rounded-card bg-surface-muted px-4 py-2.5 text-center text-xs font-semibold text-muted">
          종료된 대화예요. 이전 메시지만 확인할 수 있어요.
        </p>
      ) : roomStatus === "closed" || unsubscribedReason ? (
        <p className="mt-3 rounded-card bg-surface-muted px-4 py-2.5 text-center text-xs font-semibold text-muted">
          닫힌 채팅방이에요.
        </p>
      ) : null}

      {/* 메시지 영역 */}
      <div className="flex-1 space-y-2.5 py-3">
        {hasMore ? (
          <div className="text-center">
            <button
              type="button"
              disabled={loadingMore}
              onClick={() => void handleLoadOlder()}
              className="inline-flex items-center gap-1 rounded-chip border border-line-light bg-surface px-3.5 py-1.5 text-xs font-bold text-ink hover:bg-surface-soft disabled:opacity-60"
            >
              <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{loadingMore ? "불러오는 중…" : "이전 메시지 더 불러오기"}</span>
            </button>
          </div>
        ) : null}

        {messages.length === 0 ? (
          <div className="rounded-card border border-line-light bg-surface-muted/40 px-4 py-10 text-center text-xs text-muted">
            아직 대화가 없어요. 첫 메시지를 보내 보세요!
          </div>
        ) : (
          <ul className="space-y-2">
            {messages.map((msg) => {
              if (msg.msg_type === "system") {
                return (
                  <li key={`${msg.message_id}-${msg.seq}`} className="text-center">
                    <span className="inline-block rounded-chip bg-surface-muted px-3 py-1 text-[11px] font-semibold text-muted">
                      {msg.body}
                    </span>
                  </li>
                );
              }

              const isMine = Boolean(me?.userId && msg.sender_id === me.userId);
              return (
                <li
                  key={`${msg.message_id}-${msg.seq}`}
                  className={`flex flex-col ${isMine ? "items-end" : "items-start"}`}
                >
                  {!isMine ? (
                    <span className="mb-0.5 px-1 text-[11px] font-bold text-muted">
                      {msg.sender_display_name ?? "참여자"}
                    </span>
                  ) : null}
                  <div className="flex max-w-[82%] items-end gap-1.5">
                    {isMine ? (
                      <span className="shrink-0 text-[10px] text-muted">
                        {formatMsgTime(msg.created_at)}
                      </span>
                    ) : null}
                    <p
                      className={`whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-sm leading-snug ${
                        isMine
                          ? "bg-brand text-surface"
                          : "border border-line-light bg-surface-muted/70 text-ink"
                      }`}
                    >
                      {msg.body}
                    </p>
                    {!isMine ? (
                      <span className="shrink-0 text-[10px] text-muted">
                        {formatMsgTime(msg.created_at)}
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* 입력 폼 */}
      <form
        onSubmit={handleSend}
        className="sticky bottom-[76px] flex items-center gap-2 border-t border-line-light bg-surface pt-3"
      >
        <input
          type="text"
          value={inputBody}
          maxLength={1000}
          disabled={isInputDisabled}
          onChange={(e) => setInputBody(e.target.value)}
          placeholder={
            isInputDisabled
              ? "메시지를 보낼 수 없어요"
              : "메시지를 입력하세요"
          }
          aria-label="메시지 입력"
          className="h-11 flex-1 rounded-input border border-line-light bg-surface px-4 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none disabled:bg-surface-muted"
        />
        <button
          type="submit"
          disabled={isInputDisabled || sending || !inputBody.trim()}
          aria-label="메시지 보내기"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-chip bg-brand text-surface shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <Send className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>

      {/* 단체방 초대 모달 */}
      {inviteOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 backdrop-blur-[1px]"
          onClick={() => setInviteOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="invite-modal-title"
            className="max-h-[80dvh] w-full max-w-[480px] overflow-y-auto rounded-t-[24px] bg-surface px-5 pb-7 pt-4 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 id="invite-modal-title" className="text-base font-black text-ink">
                단체방에 친구 초대
              </h2>
              <button
                type="button"
                onClick={() => setInviteOpen(false)}
                aria-label="닫기"
                className="flex h-8 w-8 items-center justify-center rounded-chip text-muted hover:bg-surface-muted"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <form onSubmit={handleInviteSubmit} className="space-y-3">
              {friends.length === 0 ? (
                <p className="py-6 text-center text-xs text-muted">
                  초대할 수 있는 친구가 없어요.
                </p>
              ) : (
                <ul className="max-h-52 space-y-1.5 overflow-y-auto rounded-card border border-line-light p-2">
                  {friends.map((f) => {
                    const checked = selectedInvitees.includes(f.user_id);
                    return (
                      <li key={f.user_id}>
                        <label className="flex cursor-pointer items-center justify-between rounded-xl px-2.5 py-2 hover:bg-surface-soft/50">
                          <span className="text-sm font-semibold text-ink">
                            {f.display_name ?? "알 수 없음"}
                          </span>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() =>
                              setSelectedInvitees((prev) =>
                                prev.includes(f.user_id)
                                  ? prev.filter((id) => id !== f.user_id)
                                  : [...prev, f.user_id],
                              )
                            }
                            className="h-4 w-4 accent-brand"
                          />
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}
              <button
                type="submit"
                disabled={inviteBusy || selectedInvitees.length === 0}
                className="w-full rounded-chip bg-brand py-3 text-sm font-extrabold text-surface disabled:opacity-60"
              >
                {inviteBusy ? "초대 중…" : "초대하기"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ChatRoomView({ roomId }: ChatRoomViewProps) {
  return (
    <RequireAuth nextPath={`/chats/${roomId}`}>
      <ChatRoomContent roomId={roomId} />
    </RequireAuth>
  );
}
