"use client";

import { Heart } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { getAuthUser, getAuthUserServerSnapshot, subscribeAuth } from "@/lib/api/auth";
import {
  ensureFavoritesLoaded,
  getFavoritesVersion,
  isFestivalFavorite,
  setFestivalFavorite,
  subscribeFavorites,
} from "./favoriteStore";

export function FavoriteButton({ festivalId, className = "" }: { festivalId: string; className?: string }) {
  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUserServerSnapshot);
  useSyncExternalStore(subscribeFavorites, getFavoritesVersion, () => 0);
  const favorite = isFestivalFavorite(festivalId);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) ensureFavoritesLoaded(user.userId);
  }, [user]);

  async function toggle() {
    if (!user) {
      window.open(`/auth/login?next=${encodeURIComponent(window.location.pathname)}`, "_self");
      return;
    }
    if (busy) return;
    setBusy(true);
    try {
      await setFestivalFavorite(festivalId, !favorite);
    } catch {
      // The shared store restores the previous value on request failure.
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      aria-label={favorite ? "찜 해제" : "찜하기"}
      aria-pressed={favorite}
      disabled={busy}
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        void toggle();
      }}
      className={`grid h-11 w-11 place-items-center rounded-chip border border-surface/80 bg-ink/45 text-surface shadow-md backdrop-blur-sm transition-transform active:scale-95 disabled:opacity-60 ${className}`}
    >
      <Heart className={`h-5 w-5 ${favorite ? "fill-brand text-brand" : "text-surface"}`} aria-hidden="true" />
    </button>
  );
}
