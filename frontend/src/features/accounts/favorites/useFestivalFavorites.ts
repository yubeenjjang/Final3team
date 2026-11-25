"use client";

import { useEffect, useRef, useState } from "react";
import { getAuthSessionVersion } from "@/lib/api/auth";
import { deleteFavorite, findFavorites, saveFavorite } from "@/features/festivals/detail/api";

export function useFestivalFavorites(festivalIds: readonly string[]) {
  const session = getAuthSessionVersion();
  const [lookup, setLookup] = useState<{
    ids: readonly string[];
    session: number;
    matches: Set<string>;
  } | null>(null);
  const savedIds = lookup?.ids === festivalIds && lookup.session === session ? lookup.matches : null;
  const [error, setError] = useState("");
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());
  const pending = useRef(new Set<string>());

  useEffect(() => {
    const controller = new AbortController();

    findFavorites(festivalIds, controller.signal).then((matches) => {
      if (!controller.signal.aborted && session === getAuthSessionVersion()) {
        setLookup({ ids: festivalIds, session, matches });
      }
    }).catch(() => {
      if (!controller.signal.aborted && session === getAuthSessionVersion()) {
        setError("찜 목록을 불러오지 못했어요.");
      }
    });
    return () => controller.abort();
  }, [festivalIds, session]);

  async function toggle(id: string) {
    if (!savedIds || session !== getAuthSessionVersion() || pending.current.has(id)) {
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
      if (session !== getAuthSessionVersion()) return;
      setLookup((current) => {
        if (current?.ids !== festivalIds || current.session !== session) return current;
        const matches = new Set(current.matches);
        if (saved) matches.delete(id);
        else matches.add(id);
        return { ...current, matches };
      });
    } catch {
      if (session === getAuthSessionVersion()) {
        setError("찜 상태를 바꾸지 못했어요. 다시 시도해 주세요.");
      }
    } finally {
      pending.current.delete(id);
      setBusyIds(new Set(pending.current));
    }
  }

  return { savedIds, busyIds, error, toggle };
}
