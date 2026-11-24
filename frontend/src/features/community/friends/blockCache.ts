import { getAuthUser } from "@/lib/api/auth";

export interface BlockedUserRecord {
  user_id: string;
  display_name: string | null;
  blocked_at: string;
}

function storageKey(): string | null {
  const userId = getAuthUser()?.userId;
  if (!userId) return null;
  return `noldaga.blocks.${userId}`;
}

export function getRememberedBlocks(): BlockedUserRecord[] {
  if (typeof window === "undefined") return [];
  const key = storageKey();
  if (!key) return [];
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as BlockedUserRecord[]) : [];
  } catch {
    return [];
  }
}

export function rememberBlockedUser(
  userId: string,
  displayName: string | null,
): BlockedUserRecord[] {
  const current = getRememberedBlocks().filter((item) => item.user_id !== userId);
  const next: BlockedUserRecord[] = [
    { user_id: userId, display_name: displayName, blocked_at: new Date().toISOString() },
    ...current,
  ];
  saveRememberedBlocks(next);
  return next;
}

export function forgetBlockedUser(userId: string): BlockedUserRecord[] {
  const next = getRememberedBlocks().filter((item) => item.user_id !== userId);
  saveRememberedBlocks(next);
  return next;
}

function saveRememberedBlocks(items: BlockedUserRecord[]): void {
  if (typeof window === "undefined") return;
  const key = storageKey();
  if (!key) return;
  try {
    window.sessionStorage.setItem(key, JSON.stringify(items));
  } catch {
    // Ignore storage quota errors
  }
}
