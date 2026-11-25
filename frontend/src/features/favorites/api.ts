import { apiDelete, apiGet, apiPut } from "@/lib/api/client";

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

export function listFavorites(signal?: AbortSignal) {
  return apiGet<FavoritesPage>("/me/favorites", {
    query: { page: 1, page_size: 100 },
    signal,
  });
}

export function saveFavorite(festivalId: string) {
  return apiPut(`/me/favorites/${encodeURIComponent(festivalId)}`, {});
}

export function removeFavorite(festivalId: string) {
  return apiDelete(`/me/favorites/${encodeURIComponent(festivalId)}`);
}
