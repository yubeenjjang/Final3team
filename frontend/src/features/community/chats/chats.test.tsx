import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { ChatListView, CLOSED_DIRECT_HINT } from "./ChatListView";
import { ChatRoomView } from "./ChatRoomView";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  usePathname: () => "/chats",
}));

class FakeWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly url: string;
  readyState = 0;
  sent: string[] = [];
  private listeners = new Map<string, Set<(event: unknown) => void>>();

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, cb: (event: unknown) => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(cb);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
  }

  emitOpen() {
    this.readyState = FakeWebSocket.OPEN;
    this.listeners.get("open")?.forEach((cb) => cb({}));
  }

  emitMessage(payload: unknown) {
    const data = JSON.stringify(payload);
    this.listeners.get("message")?.forEach((cb) => cb({ data }));
  }

  emitClose(code = 1006) {
    this.readyState = FakeWebSocket.CLOSED;
    this.listeners.get("close")?.forEach((cb) => cb({ code }));
  }
}

describe("Chat screens", () => {
  const originalFetch = globalThis.fetch;
  const originalWebSocket = globalThis.WebSocket;

  beforeEach(() => {
    pushMock.mockReset();
    replaceMock.mockReset();
    FakeWebSocket.instances = [];
    resetAuthStateForTest();
    globalThis.WebSocket = FakeWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
    globalThis.WebSocket = originalWebSocket;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders empty hint and error state in ChatListView", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr-1", displayName: "테스터" },
    });

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.searchParams.get("filter") === "past") {
        return Response.json(
          { error: { code: "HTTP_ERROR", message: "채팅방 오류" } },
          { status: 500 },
        );
      }
      return Response.json({
        items: [],
        empty_hint: "동행을 찾거나 친구를 추가해 보세요",
      });
    }) as unknown as typeof fetch;

    render(<ChatListView />);

    await waitFor(() => {
      expect(screen.getByText("동행을 찾거나 친구를 추가해 보세요")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "지난 대화" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("채팅방 오류");
    });
  });

  it("shows closed direct message hint on closed 1:1 room", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr-1", displayName: "테스터" },
    });

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/me/chat-rooms")) {
        return Response.json({
          items: [
            {
              room_id: "crm_CLOSED001",
              room_type: "direct",
              name: null,
              status: "closed",
              last_message_at: null,
              unread_count: 0,
              my_status: "joined",
            },
          ],
        });
      }
      if (url.pathname.endsWith("/messages")) {
        return Response.json(
          { error: { code: "FORBIDDEN", message: "접근 불가" } },
          { status: 403 },
        );
      }
      return Response.json({});
    }) as unknown as typeof fetch;

    render(<ChatRoomView roomId="crm_CLOSED001" />);

    await waitFor(() => {
      expect(screen.getByText(CLOSED_DIRECT_HINT)).toBeInTheDocument();
    });
    expect(screen.getByLabelText("메시지 입력")).toBeDisabled();
  });

  it("loads history, loads older messages, connects via ws-ticket, receives & sends messages, and restores after reconnect", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr-1", displayName: "테스터" },
    });

    let ticketCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/me/chat-rooms")) {
        return Response.json({
          items: [
            {
              room_id: "crm_ROOM0001",
              room_type: "friend_group",
              name: "불꽃축제 팀",
              status: "active",
              last_message_at: "2026-11-24T12:00:00+09:00",
              unread_count: 0,
              my_status: "joined",
            },
          ],
        });
      }
      if (url.pathname.endsWith("/messages")) {
        if (url.searchParams.get("before_seq") === "2") {
          return Response.json({
            items: [
              {
                message_id: 1,
                seq: 1,
                sender_id: "usr-2",
                sender_display_name: "민수",
                msg_type: "text",
                body: "이전 메시지",
                created_at: "2026-11-24T11:50:00+09:00",
              },
            ],
            has_more: false,
          });
        }
        if (url.searchParams.get("after_seq") === "3") {
          return Response.json({
            items: [
              {
                message_id: 4,
                seq: 4,
                sender_id: "usr-2",
                sender_display_name: "민수",
                msg_type: "text",
                body: "재연결 후 복원 메시지",
                created_at: "2026-11-24T12:05:00+09:00",
              },
            ],
            has_more: false,
          });
        }
        return Response.json({
          items: [
            {
              message_id: 2,
              seq: 2,
              sender_id: "usr-2",
              sender_display_name: "민수",
              msg_type: "text",
              body: "안녕하세요",
              created_at: "2026-11-24T12:00:00+09:00",
            },
          ],
          has_more: true,
        });
      }
      if (url.pathname.endsWith("/read")) {
        return new Response(null, { status: 204 });
      }
      if (url.pathname.endsWith("/ws-tickets")) {
        ticketCount += 1;
        return Response.json({ ticket: `ticket-${ticketCount}`, expires_in: 30 }, { status: 201 });
      }
      return Response.json({});
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<ChatRoomView roomId="crm_ROOM0001" />);

    await waitFor(() => {
      expect(screen.getByText("안녕하세요")).toBeInTheDocument();
    });

    // Load older messages
    fireEvent.click(screen.getByRole("button", { name: "이전 메시지 더 불러오기" }));
    await waitFor(() => {
      expect(screen.getByText("이전 메시지")).toBeInTheDocument();
    });

    // Wait for WS ticket + connection
    await waitFor(() => {
      expect(FakeWebSocket.instances).toHaveLength(1);
    });
    const firstSocket = FakeWebSocket.instances[0];
    expect(firstSocket.url).toContain("/ws/chat?ticket=ticket-1");

    act(() => {
      firstSocket.emitOpen();
    });
    expect(JSON.parse(firstSocket.sent[0])).toEqual({
      type: "subscribe",
      room_id: "crm_ROOM0001",
      after_seq: 2,
    });

    // Receive realtime WS message
    act(() => {
      firstSocket.emitMessage({
        type: "message",
        room_id: "crm_ROOM0001",
        message_id: 3,
        seq: 3,
        sender_id: "usr-2",
        msg_type: "text",
        body: "실시간 도착!",
        created_at: "2026-11-24T12:01:00+09:00",
      });
    });
    expect(screen.getByText("실시간 도착!")).toBeInTheDocument();

    // Send a message
    fireEvent.change(screen.getByLabelText("메시지 입력"), { target: { value: "반가워요" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 보내기" }));
    const sentPayload = JSON.parse(firstSocket.sent[1]);
    expect(sentPayload).toMatchObject({
      type: "send",
      room_id: "crm_ROOM0001",
      body: "반가워요",
    });

    // Disconnect and verify reconnect + after_seq restoration
    vi.useFakeTimers();
    act(() => {
      firstSocket.emitClose(1006);
    });
    expect(screen.getByText("다시 연결 중…")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1100);
    });
    vi.useRealTimers();

    await waitFor(() => {
      expect(FakeWebSocket.instances).toHaveLength(2);
    });
    const secondSocket = FakeWebSocket.instances[1];
    expect(secondSocket.url).toContain("ticket=ticket-2");

    act(() => {
      secondSocket.emitOpen();
    });
    expect(JSON.parse(secondSocket.sent[0])).toEqual({
      type: "subscribe",
      room_id: "crm_ROOM0001",
      after_seq: 3,
    });

    await waitFor(() => {
      expect(screen.getByText("재연결 후 복원 메시지")).toBeInTheDocument();
    });
  });
});
