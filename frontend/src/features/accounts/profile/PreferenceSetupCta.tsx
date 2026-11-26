import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

export function PreferenceSetupCta() {
  return (
    <section className="rounded-card-lg border-2 border-brand/45 bg-surface-soft/70 p-4 shadow-sm md:flex md:items-center md:justify-between md:gap-6 md:px-6">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-surface text-brand shadow-sm">
          <Sparkles className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-extrabold text-ink">나만을 위한 축제를 만나보세요</h2>
          <p className="mt-1 text-xs text-muted">취향을 선택하면 나에게 맞는 축제를 추천해드려요.</p>
        </div>
      </div>
      <Link
        href="/onboarding"
        className="mt-4 flex min-h-11 w-full items-center justify-center gap-1 rounded-chip bg-brand px-5 text-sm font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90 md:mt-0 md:w-auto md:shrink-0"
      >
        나만의 축제 취향 선택하러 가기
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </section>
  );
}
