import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { FriendsView } from "./FriendsView";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  usePathname: () => "/friends",
}));

describe("Friends screen", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    pushMock.mockReset();
    replaceMock.mockReset();
    resetAuthStateForTest();
  });

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("redirects unauthenticated user to login", async () => {
    render(<FriendsView />);
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/auth/login?next=%2Ffriends");
    });
  });

  it("renders empty state, searches by nickname, sends request, and accepts received request", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "11111111-1111-1111-1111-111111111111", displayName: "테스터" },
    });

    let accepted = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/me/friends")) {
        return Response.json({
          items: accepted
            ? [
                {
                  user_id: "22222222-2222-2222-2222-222222222222",
                  display_name: "민수",
                  since: "2026-11-24T12:00:00+09:00",
                },
              ]
            : [],
        });
      }
      if (url.pathname.endsWith("/me/friend-requests")) {
        if (url.searchParams.get("box") === "received") {
          return Response.json({
            items: accepted
              ? []
              : [
                  {
                    request_id: "frq_01JD8Q3K2M",
                    user_id: "22222222-2222-2222-2222-222222222222",
                    display_name: "민수",
                    status: "pending",
                    created_at: "2026-11-24T11:00:00+09:00",
                  },
                ],
          });
        }
        return Response.json({ items: [] });
      }
      if (url.pathname.endsWith("/users/search")) {
        return Response.json({
          items: [
            {
              user_id: "33333333-3333-3333-3333-333333333333",
              display_name: "지영",
              friendship_status: "none",
            },
          ],
        });
      }
      if (url.pathname.endsWith("/friend-requests") && init?.method === "POST") {
        return Response.json({ request_id: "frq_01NEWREQ00", status: "pending" }, { status: 201 });
      }
      if (url.pathname.endsWith("/friend-requests/frq_01JD8Q3K2M/accept")) {
        accepted = true;
        return Response.json({ request_id: "frq_01JD8Q3K2M", status: "accepted" });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<FriendsView />);

    await waitFor(() => {
      expect(screen.getByText("아직 친구가 없어요")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("닉네임 검색"), { target: { value: "지영" } });
    fireEvent.click(screen.getByRole("button", { name: "검색" }));

    await waitFor(() => {
      expect(screen.getByText("지영")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "친구 신청" }));
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("친구 신청을 보냈어요.");
    });

    fireEvent.click(screen.getByRole("tab", { name: /받은 신청/ }));
    await waitFor(() => {
      expect(screen.getByText("민수")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "수락" }));
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("친구 신청을 수락했어요.");
    });
  });

  it("shows error state with retry when friend list fails", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "11111111-1111-1111-1111-111111111111", displayName: "테스터" },
    });

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/me/friends")) {
        return Response.json(
          { error: { code: "HTTP_ERROR", message: "친구 목록 오류" } },
          { status: 500 },
        );
      }
      return Response.json({ items: [] });
    }) as unknown as typeof fetch;

    render(<FriendsView />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("친구 목록 오류");
    });
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });
});
