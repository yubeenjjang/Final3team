"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { deleteFavorite, saveFavorite, type FavoritesPage } from "@/features/festivals/detail/api";

export function useFestivalFavorites(festivalIds: readonly string[]) {
  const [savedIds, setSavedIds] = useState<Set<string> | null>(null);
  const [error, setError] = useState("");
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());
  const pending = useRef(new Set<string>());

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      const matches = new Set<string>();
      for (let page = 1; ; page += 1) {
        const result = await apiGet<FavoritesPage>("/me/favorites", {
          query: { page, page_size: 100 },
          signal: controller.signal,
        });
        for (const item of result.items) {
          if (festivalIds.includes(item.festival_id)) {
            matches.add(item.festival_id);
          }
        }
        if (matches.size === festivalIds.length || result.items.length === 0 ||
          result.page * result.page_size >= result.total) {
          break;
        }
      }
      if (!controller.signal.aborted) {
        setSavedIds(matches);
      }
    }

    void load().catch(() => {
      if (!controller.signal.aborted) {
        setError("찜 목록을 불러오지 못했어요.");
      }
    });
    return () => controller.abort();
  }, [festivalIds]);

  async function toggle(id: string) {
    if (!savedIds || pending.current.has(id)) {
      return;
    }
    pending.current.add(id);
    setBusyIds(new Set(pending.current));
    setError("");
    const saved = savedIds.has(id);

    try {
      if (saved) {
        await deleteFavorite(id);
      } else {
        await saveFavorite(id);
      }
      setSavedIds((current) => {
        const updated = new Set(current);
        if (saved) {
          updated.delete(id);
        } else {
          updated.add(id);
        }
        return updated;
      });
    } catch {
      setError("찜 상태를 바꾸지 못했어요. 다시 시도해 주세요.");
    } finally {
      pending.current.delete(id);
      setBusyIds(new Set(pending.current));
    }
  }

  return { savedIds, busyIds, error, toggle };
}
