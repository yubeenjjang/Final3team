import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import {
  markMockDataDetected,
  resetMockDataDetected,
} from "@/lib/api/client";
import { AppShell } from "./AppShell";
import { ComingSoon } from "./ComingSoon";

let mockPathname = "/";
const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ replace: vi.fn(), push: pushMock }),
}));

describe("F3 AppShell & F5 MockBadge", () => {
  beforeEach(() => {
    mockPathname = "/";
    resetAuthStateForTest();
    resetMockDataDetected();
    pushMock.mockReset();
  });

  it("moves to the home page when the header logo is clicked", () => {
    mockPathname = "/festivals/fst_000001";
    render(
      <AppShell>
        <div>축제 상세</div>
      </AppShell>,
    );

    fireEvent.click(screen.getByRole("link", { name: "놀다가 홈" }));
    expect(pushMock).toHaveBeenCalledWith("/");
  });

  afterEach(() => {
    cleanup();
  });

  it("F3 renders 5 bottom tabs and applies light theme across routes", () => {
    mockPathname = "/";
    const { rerender } = render(
      <AppShell>
        <div>홈 본문</div>
      </AppShell>,
    );

    const shell = screen.getByTestId("app-shell");
    expect(shell).toHaveAttribute("data-theme", "light");
    expect(shell.className).toContain("bg-canvas");
    expect(screen.getByAltText("NOLDAGA")).toBeInTheDocument();

    const tabs = [
      { label: "홈", href: "/" },
      { label: "축제", href: "/festivals" },
      { label: "동행", href: "/companions" },
      { label: "귀가", href: "/routes/return" },
      { label: "지도", href: "/map" },
    ];

    for (const tab of tabs) {
      const link = screen.getByRole("link", { name: tab.label });
      expect(link).toHaveAttribute("href", tab.href);
    }

    const activeHomeTab = screen.getByRole("link", { name: "홈" });
    expect(activeHomeTab).toHaveAttribute("aria-current", "page");
    expect(activeHomeTab.className).toContain("bg-brand");

    mockPathname = "/companions";
    rerender(
      <AppShell>
        <ComingSoon title="동행 찾기" />
      </AppShell>,
    );

    expect(screen.getByTestId("app-shell")).toHaveAttribute(
      "data-theme",
      "light",
    );
    expect(screen.getByTestId("app-shell").className).toContain("bg-canvas");
    expect(screen.getByRole("link", { name: "동행" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("준비 중이에요")).toBeInTheDocument();
  });

  it.each(["놀", "👩🏽‍💻", "𠮷"])("F3 shows login when logged out and preserves %s as the nickname initial", (initial) => {
    render(
      <AppShell>
        <div>본문</div>
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: "로그인" })).toHaveAttribute(
      "href",
      "/auth/login",
    );

    act(() => {
      setAuthSession({
        accessToken: "token-a",
        refreshToken: "token-r",
        user: { userId: "usr_1", displayName: `${initial}다가유저` },
      });
    });

    const accountLink = screen.getByRole("link", { name: /마이페이지/ });
    expect(accountLink.textContent).toBe(initial);
    expect(accountLink).toHaveAttribute("href", "/me");
  });

  it("F5 displays mock badge once mock response is observed", () => {
    render(
      <AppShell>
        <div>본문</div>
      </AppShell>,
    );

    expect(screen.queryByText("모의 데이터")).not.toBeInTheDocument();

    act(() => {
      markMockDataDetected();
    });

    expect(screen.getByText("모의 데이터")).toBeInTheDocument();
  });
});
