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

describe("F10 auth and favorites flow", () => {
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

  it("signs up, logs in with the prefilled email, then keeps a festival saved on re-entry", async () => {
    let saved = false;
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
      if (path.endsWith("/festivals")) {
        return Response.json({ items: [festival] });
      }
      if (path.includes("/me/favorites")) {
        expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${tokens.access_token}`);
        if (init?.method === "PUT") {
          saved = true;
          return Response.json({ festival_id: festival.festival_id }, { status: 201 });
        }
        return Response.json({ items: saved ? [festival] : [], page: 1, page_size: 100, total: Number(saved) });
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
    await waitFor(() => expect(replace).toHaveBeenLastCalledWith("/"));
    expect(sessionStorage.getItem("noldaga.access_token")).toBe(tokens.access_token);
    expect(sessionStorage.getItem("noldaga.refresh_token")).toBe(tokens.refresh_token);

    cleanup();
    const home = render(<HomePage />);
    const unsaved = await screen.findByRole("button", { name: "테스트 축제 찜하기" });
    await waitFor(() => expect(unsaved).toBeEnabled());
    fireEvent.click(unsaved);
    expect(await screen.findByRole("button", { name: "테스트 축제 찜 해제" })).toHaveAttribute("aria-pressed", "true");

    home.unmount();
    render(<HomePage />);
    expect(await screen.findByRole("button", { name: "테스트 축제 찜 해제" })).toHaveAttribute("aria-pressed", "true");
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

    await expect(apiGet("/me/favorites")).resolves.toEqual({ items: [] });
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

    await expect(apiGet("/me/favorites")).rejects.toMatchObject({ status: 401 });
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
