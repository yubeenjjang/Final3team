import { listFavorites, removeFavorite, saveFavorite } from "./api";

let ids = new Set<string>();
let loadedUserId: string | null = null;
let pendingLoad: Promise<void> | null = null;
let version = 0;
const listeners = new Set<() => void>();

function emit() {
  version += 1;
  for (const listener of listeners) listener();
}

export function subscribeFavorites(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getFavoritesVersion() {
  return version;
}

export function isFestivalFavorite(festivalId: string) {
  return ids.has(festivalId);
}

export function ensureFavoritesLoaded(userId: string) {
  if (loadedUserId === userId || pendingLoad) return;
  pendingLoad = listFavorites()
    .then((page) => {
      ids = new Set(page.items.map((item) => item.festival_id));
      loadedUserId = userId;
      emit();
    })
    .catch(() => undefined)
    .finally(() => {
      pendingLoad = null;
    });
}

export async function setFestivalFavorite(festivalId: string, favorite: boolean) {
  const previous = ids.has(festivalId);
  if (favorite) ids.add(festivalId);
  else ids.delete(festivalId);
  emit();
  try {
    if (favorite) await saveFavorite(festivalId);
    else await removeFavorite(festivalId);
  } catch (error) {
    if (previous) ids.add(festivalId);
    else ids.delete(festivalId);
    emit();
    throw error;
  }
}
