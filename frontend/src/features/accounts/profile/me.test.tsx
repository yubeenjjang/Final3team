import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAuthUser, resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { MeView } from "./MeView";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  usePathname: () => "/me",
}));

describe("My Page screen", () => {
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
    render(<MeView />);
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/auth/login?next=%2Fme");
    });
  });

  it("renders profile, updates nickname, manages favorites, preferences, notifications, and withdrawal", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "11111111-1111-1111-1111-111111111111", displayName: "테스터" },
    });

    let displayName = "테스터";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/me/profile")) {
        if (init?.method === "PATCH") {
          const body = JSON.parse(String(init.body)) as { display_name: string };
          displayName = body.display_name;
        }
        return Response.json({
          user_id: "11111111-1111-1111-1111-111111111111",
          display_name: displayName,
          birth_year: 1998,
          gender: "female",
          onboarding_status: "pending",
        });
      }
      if (url.pathname.endsWith("/me/favorites")) {
        return Response.json({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        });
      }
      if (url.pathname.endsWith("/me/festival-preferences")) {
        if (init?.method === "PUT") {
          const body = JSON.parse(String(init.body)) as { scenarios: string[]; skip: boolean };
          return Response.json({
            scenarios: body.scenarios,
            onboarding_status: body.skip ? "skipped" : "completed",
            updated_at: "2026-11-24T12:00:00+09:00",
          });
        }
        return Response.json({
          scenarios: [],
          onboarding_status: "pending",
          updated_at: null,
        });
      }
      if (url.pathname.endsWith("/me/notifications")) {
        return Response.json({
          items: [
            {
              notification_id: 10,
              type: "companion_approved",
              ref_type: "companion_post",
              ref_id: "cpo_01JD8Q3K2M",
              created_at: "2026-11-24T12:00:00+09:00",
              read_at: null,
            },
          ],
          unread_count: 1,
        });
      }
      if (url.pathname.endsWith("/me/notifications/read")) {
        return new Response(null, { status: 204 });
      }
      if (url.pathname.endsWith("/me") && init?.method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      return Response.json({});
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<MeView />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "테스터" })).toBeInTheDocument();
    });
    expect(screen.getByText("저장한 관심 축제가 없어요")).toBeInTheDocument();

    // Edit nickname
    fireEvent.click(screen.getByRole("button", { name: "닉네임 수정" }));
    fireEvent.change(screen.getByLabelText("새 닉네임"), { target: { value: "놀다가왕" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "놀다가왕" })).toBeInTheDocument();
    });
    expect(getAuthUser()?.displayName).toBe("놀다가왕");

    // Preferences tab
    fireEvent.click(screen.getByRole("tab", { name: /취향/ }));
    await waitFor(() => {
      expect(screen.getByText("가족과 즐기는 한가로운 축제")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /가족과 즐기는 한가로운 축제/ }));
    fireEvent.click(screen.getByRole("button", { name: "취향 저장" }));
    await waitFor(() => {
      expect(screen.getByText("축제 취향을 저장했어요!")).toBeInTheDocument();
    });

    // Notifications tab
    fireEvent.click(screen.getByRole("tab", { name: /알림/ }));
    await waitFor(() => {
      expect(screen.getByText("동행 신청이 승인됐어요")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "모두 읽음" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "모두 읽음" })).toBeDisabled();
    });

    // Withdrawal confirmation step
    fireEvent.click(screen.getByRole("button", { name: "탈퇴하기" }));
    const confirmBtn = screen.getByRole("button", { name: "회원 탈퇴 확인" });
    expect(confirmBtn).toBeDisabled();
    fireEvent.change(screen.getByLabelText("탈퇴 확인 비밀번호"), {
      target: { value: "secret123" },
    });
    fireEvent.click(screen.getByRole("checkbox"));
    expect(confirmBtn).toBeEnabled();
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/");
    });
  });

  it("renders error state when profile loading fails", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "11111111-1111-1111-1111-111111111111", displayName: "테스터" },
    });

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/me/profile")) {
        return Response.json(
          { error: { code: "HTTP_ERROR", message: "프로필 조회 실패" } },
          { status: 500 },
        );
      }
      return Response.json({ items: [], total: 0, page: 1, page_size: 20 });
    }) as unknown as typeof fetch;

    render(<MeView />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("프로필 조회 실패");
    });
  });
});
