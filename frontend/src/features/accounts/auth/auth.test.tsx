import { renderToString } from "react-dom/server";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import LoginPage from "@/app/auth/login/page";
import SignupPage from "@/app/auth/signup/page";
import { getAccessToken, getAuthUser, getRefreshToken, resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { apiGet } from "@/lib/api/client";
import { logout, safeNextPath } from "./api";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

const fetchApi = vi.fn<typeof fetch>();
const fixture = {
  email: "tester@example.com",
  password: "kitten12",
  display_name: "테스터",
  birth_year: 1999,
  gender: "female",
};
const tokens = {
  access_token: "fixture-access",
  refresh_token: "fixture-refresh",
  user: { user_id: "fixture-user", display_name: fixture.display_name },
};
const festival = {
  festival_id: "fst_test01",
  name: "테스트 축제",
  region_code: "SEOUL",
  venue_name: "테스트 광장",
  start_date: "2026-11-01",
  end_date: "2026-11-30",
  thumbnail_url: null,
  event_status: "ongoing",
};

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label, { exact: true }), { target: { value } });
}

function fillSignup() {
  change("이메일", fixture.email);
  change("비밀번호", fixture.password);
  change("비밀번호 확인", fixture.password);
  change("닉네임", fixture.display_name);
  change("출생연도", String(fixture.birth_year));
  fireEvent.click(screen.getByRole("radio", { name: "여성" }));
}

function apiError(status: number, code: string) {
  return Response.json({ error: { code, message: "테스트 오류" } }, { status });
}

describe("F10 auth flow", () => {
  beforeEach(() => {
    resetAuthStateForTest();
    fetchApi.mockReset();
    replace.mockReset();
    vi.stubGlobal("fetch", fetchApi);
  });

  afterEach(() => {
    cleanup();
    resetAuthStateForTest();
    vi.unstubAllGlobals();
  });

  it("signs up, logs in with the prefilled email, and renders festivals with favorite controls", async () => {
    fetchApi.mockImplementation(async (input, init) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/auth/signup")) {
        expect(JSON.parse(String(init?.body))).toEqual(fixture);
        return Response.json({ user_id: tokens.user.user_id, display_name: fixture.display_name }, { status: 201 });
      }
      if (path.endsWith("/auth/login")) {
        expect(JSON.parse(String(init?.body))).toEqual({ email: fixture.email, password: fixture.password });
        return Response.json(tokens);
      }
      if (path.endsWith("/me/festival-preferences")) {
        return Response.json({ scenarios: [], onboarding_status: "pending", updated_at: null });
      }
      if (path.endsWith("/festivals")) {
        return Response.json({ items: [festival] });
      }
      if (path.endsWith("/me/favorites")) {
        return Response.json({ is_mock: true, items: [], total: 0, page: 1, page_size: 100 });
      }
      throw new Error(`테스트에 등록되지 않은 경로 ${path}`);
    });

    render(await SignupPage({ searchParams: Promise.resolve({ next: "/" }) }));
    fillSignup();
    fireEvent.click(screen.getByRole("button", { name: "회원가입" }));
    await waitFor(() => expect(replace).toHaveBeenCalledOnce());
    const signupRedirect = new URL(replace.mock.calls[0][0], "http://localhost");
    expect(signupRedirect.pathname).toBe("/auth/login");
    expect(signupRedirect.searchParams.get("email")).toBe(fixture.email);

    cleanup();
    render(await LoginPage({ searchParams: Promise.resolve(Object.fromEntries(signupRedirect.searchParams)) }));
    expect(screen.getByRole("textbox", { name: "이메일" })).toHaveValue(fixture.email);
    change("비밀번호", fixture.password);
    fireEvent.click(screen.getByRole("button", { name: "로그인" }));
    await waitFor(() => expect(replace).toHaveBeenLastCalledWith("/onboarding"));
    expect(sessionStorage.getItem("noldaga.access_token")).toBe(tokens.access_token);
    expect(sessionStorage.getItem("noldaga.refresh_token")).toBe(tokens.refresh_token);

    cleanup();
    render(<HomePage />);
    expect((await screen.findAllByText("테스트 축제")).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "찜하기" }).length).toBeGreaterThan(0);
  });

  it.each([
    ["EMAIL_ALREADY_EXISTS", "이미 가입한 이메일이에요"],
    ["NICKNAME_TAKEN", "이미 쓰는 닉네임이에요"],
  ])("shows the signup message for %s", async (code, message) => {
    fetchApi.mockResolvedValueOnce(apiError(409, code));
    render(await SignupPage({ searchParams: Promise.resolve({}) }));
    fillSignup();
    fireEvent.click(screen.getByRole("button", { name: "회원가입" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the 401 login message, then takes the user to the requested festival after success", async () => {
    fetchApi.mockResolvedValueOnce(apiError(401, "INVALID_CREDENTIALS"));
    fetchApi.mockResolvedValueOnce(Response.json(tokens));
    fetchApi.mockResolvedValueOnce(Response.json({
      scenarios: ["family_relaxed"],
      onboarding_status: "completed",
      updated_at: "2026-11-26T10:00:00+09:00",
    }));
    const next = "/festivals/fst_test01";
    render(await LoginPage({ searchParams: Promise.resolve({ next }) }));
    change("이메일", fixture.email);
    change("비밀번호", fixture.password);
    fireEvent.click(screen.getByRole("button", { name: "로그인" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("이메일 또는 비밀번호가 맞지 않아요");
    expect(replace).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "로그인" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith(next));
  });

  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "/a/..//evil.example"])(
    "falls back to home for an unsafe redirect %s",
    (next) => expect(safeNextPath(next)).toBe("/"),
  );

  it("F10 server renders POST forms with disabled submit buttons until hydration", async () => {
    const forms = [
      await LoginPage({ searchParams: Promise.resolve({}) }),
      await SignupPage({ searchParams: Promise.resolve({}) }),
    ];
    for (const form of forms) {
      const html = document.createElement("div");
      html.innerHTML = renderToString(form);
      expect(html.querySelector("form")).toHaveAttribute("method", "post");
      expect(html.querySelector("button[type=submit]")).toBeDisabled();
    }
  });

  it.each([200, 401])("F10 ignores a previous session refresh returning HTTP %i", async (status) => {
    setAuthSession({ accessToken: "previous-access", refreshToken: "previous-refresh" });
    const refresh = Promise.withResolvers<Response>();
    fetchApi
      .mockResolvedValueOnce(apiError(401, "UNAUTHORIZED"))
      .mockReturnValueOnce(refresh.promise);
    const previous = apiGet("/me/profile");
    const rejected = expect(previous).rejects.toMatchObject({ status: 401 });
    await waitFor(() => expect(fetchApi).toHaveBeenCalledTimes(2));
    const user = { userId: "current", displayName: "현재 사용자" };
    setAuthSession({ accessToken: "current-access", refreshToken: "current-refresh", user });
    refresh.resolve(Response.json(tokens, { status }));
    await rejected;
    expect(getAccessToken()).toBe("current-access");
    expect(getRefreshToken()).toBe("current-refresh");
    expect(getAuthUser()).toEqual(user);
    expect(fetchApi).toHaveBeenCalledTimes(2);
  });

  it("F10 shares refresh in flight and reuses the new token for a later 401", async () => {
    setAuthSession({ accessToken: "expired-access", refreshToken: "old-refresh" });
    const early = Promise.withResolvers<Response>();
    const concurrent = Promise.withResolvers<Response>();
    const late = Promise.withResolvers<Response>();
    const refresh = Promise.withResolvers<Response>();
    fetchApi
      .mockReturnValueOnce(early.promise)
      .mockReturnValueOnce(concurrent.promise)
      .mockReturnValueOnce(late.promise)
      .mockReturnValueOnce(refresh.promise)
      .mockImplementation(() => Promise.resolve(Response.json({ items: [] })));
    const requests = [apiGet("/one"), apiGet("/two"), apiGet("/three")];

    early.resolve(apiError(401, "UNAUTHORIZED"));
    await waitFor(() => expect(fetchApi).toHaveBeenCalledTimes(4));
    concurrent.resolve(apiError(401, "UNAUTHORIZED"));
    refresh.resolve(Response.json(tokens));
    await Promise.all(requests.slice(0, 2));
    late.resolve(apiError(401, "UNAUTHORIZED"));
    await requests[2];

    expect(fetchApi).toHaveBeenCalledTimes(7);
    expect(fetchApi.mock.calls.filter(([url]) => String(url).endsWith("/auth/refresh"))).toHaveLength(1);
    for (const [, init] of fetchApi.mock.calls.slice(4)) {
      expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${tokens.access_token}`);
    }
  });

  it("F10 clears the session immediately and shares pending rotation to revoke the right token", async () => {
    setAuthSession({ accessToken: "expired-access", refreshToken: "old-refresh" });
    const refresh = Promise.withResolvers<Response>();
    fetchApi
      .mockResolvedValueOnce(apiError(401, "UNAUTHORIZED"))
      .mockReturnValueOnce(refresh.promise)
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const rejected = expect(apiGet("/me/profile")).rejects.toMatchObject({ status: 401 });
    await waitFor(() => expect(fetchApi).toHaveBeenCalledTimes(2));
    const signingOut = logout();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    refresh.resolve(Response.json(tokens));
    await signingOut;
    await rejected;
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(fetchApi).toHaveBeenCalledTimes(3);
    expect(JSON.parse(String(fetchApi.mock.lastCall?.[1]?.body))).toEqual({ refresh_token: tokens.refresh_token });
  });

  it("rotates the session on 401 and retries the protected request once", async () => {
    setAuthSession({
      accessToken: "expired-access",
      refreshToken: "old-refresh",
      user: { userId: tokens.user.user_id, displayName: fixture.display_name },
    });
    fetchApi
      .mockResolvedValueOnce(apiError(401, "UNAUTHORIZED"))
      .mockResolvedValueOnce(Response.json(tokens))
      .mockResolvedValueOnce(Response.json({ items: [] }));

    await expect(apiGet("/me/profile")).resolves.toEqual({ items: [] });
    expect(fetchApi).toHaveBeenCalledTimes(3);
    expect(String(fetchApi.mock.calls[1][0])).toMatch(/\/auth\/refresh$/);
    expect(JSON.parse(String(fetchApi.mock.calls[1][1]?.body))).toEqual({ refresh_token: "old-refresh" });
    expect(new Headers(fetchApi.mock.calls[2][1]?.headers).get("Authorization")).toBe(`Bearer ${tokens.access_token}`);
    expect(getRefreshToken()).toBe(tokens.refresh_token);
  });

  it("clears the session when refresh fails", async () => {
    setAuthSession({ accessToken: "expired-access", refreshToken: "old-refresh", user: { userId: "test", displayName: "테스터" } });
    fetchApi
      .mockResolvedValueOnce(apiError(401, "UNAUTHORIZED"))
      .mockResolvedValueOnce(apiError(401, "REFRESH_INVALID"));

    await expect(apiGet("/me/profile")).rejects.toMatchObject({ status: 401 });
    expect(fetchApi).toHaveBeenCalledTimes(2);
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(getAuthUser()).toBeNull();
  });

  it("logs out through A35 from the account screen and clears the stored session", async () => {
    setAuthSession({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user: { userId: tokens.user.user_id, displayName: fixture.display_name },
    });
    fetchApi.mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(await LoginPage({ searchParams: Promise.resolve({}) }));
    fireEvent.click(screen.getByRole("button", { name: "로그아웃" }));

    expect(await screen.findByRole("button", { name: "로그인" })).toBeInTheDocument();
    expect(fetchApi).toHaveBeenCalledOnce();
    const [url, options] = fetchApi.mock.calls[0];
    expect(String(url)).toMatch(/\/auth\/logout$/);
    expect(JSON.parse(String(options?.body))).toEqual({ refresh_token: tokens.refresh_token });
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("logs out with the rotated refresh token if the original access token expired", async () => {
    setAuthSession({ accessToken: "expired-access", refreshToken: "old-refresh" });
    fetchApi
      .mockResolvedValueOnce(apiError(401, "UNAUTHORIZED"))
      .mockResolvedValueOnce(Response.json(tokens))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await logout();
    const [url, options] = fetchApi.mock.calls[2];
    expect(String(url)).toMatch(/\/auth\/logout$/);
    expect(new Headers(options?.headers).get("Authorization")).toBe(`Bearer ${tokens.access_token}`);
    expect(JSON.parse(String(options?.body))).toEqual({ refresh_token: tokens.refresh_token });
    expect(getRefreshToken()).toBeNull();
  });
});
