import "@testing-library/jest-dom/vitest";
import { renderToString } from "react-dom/server";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAuthSession, resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { RequireAuth } from "./RequireAuth";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  usePathname: () => "/me",
}));

describe("RequireAuth", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    resetAuthStateForTest();
  });

  afterEach(() => {
    cleanup();
    resetAuthStateForTest();
  });

  it("renders a neutral loading status during SSR instead of a redirect message", () => {
    const html = renderToString(
      <RequireAuth nextPath="/me">
        <div>보호된 화면</div>
      </RequireAuth>,
    );
    expect(html).toContain("로그인 상태를 확인하고 있어요");
    expect(html).not.toContain("로그인이 필요한 화면이에요");
    expect(html).not.toContain("보호된 화면");
  });

  it("keeps a logged-in user on the protected page across refresh/hydration without redirecting", async () => {
    const html = renderToString(
      <RequireAuth nextPath="/me">
        <div>보호된 화면</div>
      </RequireAuth>,
    );

    // Simulate a fresh page reload where sessionStorage already holds the token
    // before auth.ts has hydrated memory state.
    sessionStorage.setItem("noldaga.access_token", "stored-token");
    sessionStorage.setItem("noldaga.refresh_token", "stored-refresh");

    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.appendChild(container);

    try {
      render(
        <RequireAuth nextPath="/me">
          <div>보호된 화면</div>
        </RequireAuth>,
        { container, hydrate: true },
      );

      await waitFor(() => {
        expect(screen.getByText("보호된 화면")).toBeInTheDocument();
      });
      expect(replaceMock).not.toHaveBeenCalled();
    } finally {
      container.remove();
    }
  });

  it("redirects after hydration when no stored session exists", async () => {
    const html = renderToString(
      <RequireAuth nextPath="/friends">
        <div>친구 화면</div>
      </RequireAuth>,
    );

    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.appendChild(container);

    try {
      render(
        <RequireAuth nextPath="/friends">
          <div>친구 화면</div>
        </RequireAuth>,
        { container, hydrate: true },
      );

      await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/auth/login?next=%2Ffriends");
      });
      expect(screen.queryByText("친구 화면")).not.toBeInTheDocument();
    } finally {
      container.remove();
    }
  });

  it("redirects when an active session is cleared", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr-1", displayName: "테스터" },
    });

    render(
      <RequireAuth nextPath="/chats/crm_1">
        <div>채팅 화면</div>
      </RequireAuth>,
    );

    expect(screen.getByText("채팅 화면")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();

    act(() => {
      clearAuthSession();
    });

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/auth/login?next=%2Fchats%2Fcrm_1");
    });
  });
});
