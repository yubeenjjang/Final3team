"use client";

import Image from "next/image";
import Link from "next/link";
import { Heart, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { listFavorites, type FavoriteItem } from "./api";

export function FavoriteListSection() {
  const [items, setItems] = useState<FavoriteItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    listFavorites(controller.signal)
      .then((result) => setItems(result.items))
      .catch(() => setFailed(true));
    return () => controller.abort();
  }, [attempt]);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 text-xl font-black"><Heart className="h-5 w-5 fill-brand text-brand" aria-hidden="true" />찜한 축제</h2><Link href="/festivals" className="text-sm font-bold text-brand">전체보기 ›</Link></div>
      {failed ? <button type="button" onClick={() => { setFailed(false); setAttempt((value) => value + 1); }} className="flex w-full items-center justify-center gap-2 rounded-card-lg border border-line-light py-5 text-sm font-bold"><RotateCcw className="h-4 w-4" /> 다시 불러오기</button>
      : !items ? <div className="h-24 animate-pulse rounded-card-lg bg-surface-muted" />
      : items.length === 0 ? <div className="rounded-card-lg bg-surface-soft px-4 py-6 text-center text-sm text-muted">아직 찜한 축제가 없어요.</div>
      : <div className="flex gap-3 overflow-x-auto pb-1">{items.map((item) => <Link key={item.festival_id} href={`/festivals/${item.festival_id}`} className="w-28 shrink-0"><div className="relative aspect-[1/1.414] overflow-hidden rounded-card-lg bg-surface-soft">{item.thumbnail_url ? <Image src={item.thumbnail_url} alt="" fill unoptimized className="object-cover" /> : null}</div><p className="mt-1.5 line-clamp-2 text-xs font-extrabold">{item.name}</p></Link>)}</div>}
    </section>
  );
}
