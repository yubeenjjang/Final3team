import { clearAuthSession, getRefreshToken, setAuthSession } from "@/lib/api/auth";
import { ApiError, apiPost } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SignupRequest = components["schemas"]["SignupRequest"];
type LoginRequest = components["schemas"]["LoginRequest"];
type RefreshRequest = components["schemas"]["RefreshRequest"];

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  user: { user_id: string; display_name: string };
}

const guestRequest = { skipAuth: true };

export function signup(data: SignupRequest) {
  return apiPost("/auth/signup", data, guestRequest);
}

export async function login(data: LoginRequest): Promise<void> {
  const response = await apiPost<TokenResponse>("/auth/login", data, guestRequest);
  setAuthSession({
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    user: {
      userId: response.user.user_id,
      displayName: response.user.display_name,
      email: data.email,
    },
  });
}

export async function logout(): Promise<void> {
  const token = getRefreshToken();
  try {
    if (!token) {
      return;
    }
    const body: RefreshRequest = { refresh_token: token };
    // The server rotates refresh tokens. A logout retry must send the rotated token in its body.
    try {
      await apiPost("/auth/logout", body, { skipAuthRefresh: true });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        throw error;
      }
      const currentToken = getRefreshToken() ?? token;
      const refreshed = await apiPost<TokenResponse>("/auth/refresh", { refresh_token: currentToken }, guestRequest);
      await apiPost("/auth/logout", { refresh_token: refreshed.refresh_token }, {
        headers: { Authorization: `Bearer ${refreshed.access_token}` },
        skipAuthRefresh: true,
      });
    }
  } finally {
    clearAuthSession();
  }
}

export function safeNextPath(next?: string): string {
  if (!next?.startsWith("/") || next.startsWith("//") || /[\\\s]/.test(next)) {
    return "/";
  }
  const url = new URL(next, "https://noldaga.invalid");
  if (url.origin !== "https://noldaga.invalid" || url.pathname.startsWith("//")) {
    return "/";
  }
  return url.pathname + url.search + url.hash;
}

export function authLink(path: string, params: Record<string, string | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) {
      query.set(key, value);
    }
  }
  return query.size ? `${path}?${query}` : path;
}
