import "@testing-library/jest-dom/vitest";
import { StrictMode } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { FavoriteListSection } from "./FavoriteListSection";

describe("FavoriteListSection", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    resetAuthStateForTest();
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "user-1", displayName: "테스터" },
    });
  });

  afterEach(() => {
    cleanup();
    resetAuthStateForTest();
    globalThis.fetch = originalFetch;
  });

  it("shows saved festivals in StrictMode instead of treating the cancelled first request as a failure", async () => {
    globalThis.fetch = vi.fn(async () =>
      Response.json({
        total: 1,
        page: 1,
        page_size: 100,
        items: [{ festival_id: "fst_1", name: "찜한 등불축제", thumbnail_url: null, saved_at: "2026-11-26T10:00:00+09:00" }],
      }),
    ) as unknown as typeof fetch;

    render(
      <StrictMode>
        <FavoriteListSection />
      </StrictMode>,
    );

    expect(await screen.findByText("찜한 등불축제")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /다시 불러오기/ })).not.toBeInTheDocument();
  });

  it("still offers a retry when the request really fails", async () => {
    globalThis.fetch = vi.fn(async () => new Response("boom", { status: 500 })) as unknown as typeof fetch;

    render(<FavoriteListSection />);

    expect(await screen.findByRole("button", { name: /다시 불러오기/ })).toBeInTheDocument();
  });
});
