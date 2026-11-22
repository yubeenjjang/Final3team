import "@testing-library/jest-dom/vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import {
  markMockDataDetected,
  resetMockDataDetected,
} from "@/lib/api/client";
import { AppShell } from "./AppShell";
import { ComingSoon } from "./ComingSoon";

let mockPathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

describe("F3 AppShell & F5 MockBadge", () => {
  beforeEach(() => {
    mockPathname = "/";
    resetAuthStateForTest();
    resetMockDataDetected();
  });

  afterEach(() => {
    cleanup();
  });

  it("F3 renders 5 bottom tabs and applies dark theme only on home", () => {
    mockPathname = "/";
    const { rerender } = render(
      <AppShell>
        <div>홈 본문</div>
      </AppShell>,
    );

    const shell = screen.getByTestId("app-shell");
    expect(shell).toHaveAttribute("data-theme", "dark");
    expect(shell.className).toContain("bg-dark-bg");

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
    expect(screen.getByTestId("app-shell").className).toContain("bg-bg");
    expect(screen.getByRole("link", { name: "동행" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("준비 중이에요")).toBeInTheDocument();
  });

  it("F3 shows login link when logged out and nickname initial when logged in", () => {
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
        user: { userId: "usr_1", displayName: "놀다가유저" },
      });
    });

    const accountLink = screen.getByRole("link", { name: /내 계정/ });
    expect(accountLink).toHaveTextContent("놀");
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
