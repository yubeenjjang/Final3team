export interface AuthUser {
  userId: string;
  displayName: string;
  email?: string;
}

export interface AuthSessionInput {
  accessToken: string;
  refreshToken: string;
  user?: AuthUser | null;
}

const ACCESS_TOKEN_KEY = "noldaga.access_token";
const REFRESH_TOKEN_KEY = "noldaga.refresh_token";
const AUTH_USER_KEY = "noldaga.auth_user";

let memoryAccessToken: string | null = null;
let memoryUser: AuthUser | null = null;
let hydrated = false;
let sessionVersion = 0;

const listeners = new Set<() => void>();

function notifyAuthListeners(): void {
  listeners.forEach((listener) => {
    listener();
  });
}

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function hydrateIfNeeded(): void {
  if (hydrated) {
    return;
  }
  const storage = getStorage();
  if (!storage) {
    return;
  }
  hydrated = true;

  const storedAccess = storage.getItem(ACCESS_TOKEN_KEY);
  if (storedAccess) {
    memoryAccessToken = storedAccess;
  }

  const storedUser = storage.getItem(AUTH_USER_KEY);
  if (storedUser) {
    try {
      const parsed = JSON.parse(storedUser) as Partial<AuthUser>;
      if (
        typeof parsed.userId === "string" &&
        typeof parsed.displayName === "string"
      ) {
        memoryUser = {
          userId: parsed.userId,
          displayName: parsed.displayName,
          email: typeof parsed.email === "string" ? parsed.email : undefined,
        };
      }
    } catch {
      storage.removeItem(AUTH_USER_KEY);
    }
  }
}

export function getAccessToken(): string | null {
  hydrateIfNeeded();
  return memoryAccessToken;
}

export function getRefreshToken(): string | null {
  const storage = getStorage();
  if (!storage) {
    return null;
  }
  return storage.getItem(REFRESH_TOKEN_KEY);
}

export function getAuthUser(): AuthUser | null {
  hydrateIfNeeded();
  return memoryUser;
}

export function getAuthUserServerSnapshot(): AuthUser | null {
  return null;
}

export function getAuthSessionVersion(): number {
  return sessionVersion;
}

export function setAuthSession(session: AuthSessionInput): void {
  sessionVersion += 1;
  hydrated = true;
  memoryAccessToken = session.accessToken;
  if (session.user !== undefined) {
    memoryUser = session.user;
  }

  const storage = getStorage();
  if (storage) {
    storage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
    storage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
    if (session.user) {
      storage.setItem(AUTH_USER_KEY, JSON.stringify(session.user));
    } else if (session.user === null) {
      storage.removeItem(AUTH_USER_KEY);
    }
  }

  notifyAuthListeners();
}

export function updateAccessTokens(tokens: {
  accessToken: string;
  refreshToken?: string;
}): void {
  hydrated = true;
  memoryAccessToken = tokens.accessToken;

  const storage = getStorage();
  if (storage) {
    storage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
    if (tokens.refreshToken) {
      storage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
    }
  }

  notifyAuthListeners();
}

export function clearAuthSession(): void {
  sessionVersion += 1;
  hydrated = true;
  memoryAccessToken = null;
  memoryUser = null;

  const storage = getStorage();
  if (storage) {
    storage.removeItem(ACCESS_TOKEN_KEY);
    storage.removeItem(REFRESH_TOKEN_KEY);
    storage.removeItem(AUTH_USER_KEY);
  }

  notifyAuthListeners();
}

export function subscribeAuth(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function resetAuthStateForTest(): void {
  sessionVersion += 1;
  memoryAccessToken = null;
  memoryUser = null;
  hydrated = false;
  const storage = getStorage();
  if (storage) {
    storage.removeItem(ACCESS_TOKEN_KEY);
    storage.removeItem(REFRESH_TOKEN_KEY);
    storage.removeItem(AUTH_USER_KEY);
  }
  notifyAuthListeners();
}
