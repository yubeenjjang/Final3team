import { apiDelete, apiGet, apiPut } from "@/lib/api/client";
import { MOCK_FESTIVALS } from "@/features/festivals/explore/mockFestivals";

export interface FavoriteItem {
  festival_id: string;
  name: string;
  thumbnail_url?: string | null;
  saved_at: string;
}

interface FavoritesPage {
  items: FavoriteItem[];
  total: number;
  page: number;
  page_size: number;
}

const MOCK_FAVORITES_KEY = "noldaga.mock_favorites";

function usesMockFestivals() {
  return process.env.NEXT_PUBLIC_USE_MOCK_FESTIVALS === "1";
}

function readMockFavoriteIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const value = JSON.parse(
      window.localStorage.getItem(MOCK_FAVORITES_KEY) ?? "[]",
    );
    return Array.isArray(value)
      ? value.filter((id): id is string => typeof id === "string")
      : [];
  } catch {
    return [];
  }
}

function writeMockFavoriteIds(ids: string[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(MOCK_FAVORITES_KEY, JSON.stringify(ids));
}

export function listFavorites(signal?: AbortSignal) {
  if (usesMockFestivals()) {
    const ids = new Set(readMockFavoriteIds());
    const items = MOCK_FESTIVALS.filter((item) => ids.has(item.festival_id)).map(
      (item) => ({
        festival_id: item.festival_id,
        name: item.name,
        thumbnail_url: item.thumbnail_url,
        saved_at: new Date().toISOString(),
      }),
    );
    return Promise.resolve({
      items,
      total: items.length,
      page: 1,
      page_size: 100,
    });
  }

  return apiGet<FavoritesPage>("/me/favorites", {
    query: { page: 1, page_size: 100 },
    signal,
  });
}

export function saveFavorite(festivalId: string) {
  if (usesMockFestivals()) {
    writeMockFavoriteIds([...new Set([...readMockFavoriteIds(), festivalId])]);
    return Promise.resolve({ festival_id: festivalId });
  }
  return apiPut(`/me/favorites/${encodeURIComponent(festivalId)}`, {});
}

export function removeFavorite(festivalId: string) {
  if (usesMockFestivals()) {
    writeMockFavoriteIds(
      readMockFavoriteIds().filter((id) => id !== festivalId),
    );
    return Promise.resolve(undefined);
  }
  return apiDelete(`/me/favorites/${encodeURIComponent(festivalId)}`);
}
