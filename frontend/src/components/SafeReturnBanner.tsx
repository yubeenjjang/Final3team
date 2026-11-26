import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

export function SafeReturnBanner({
  festivalId,
  className = "",
}: {
  festivalId?: string;
  className?: string;
}) {
  const href = festivalId
    ? `/routes/return?festivalId=${encodeURIComponent(festivalId)}`
    : "/routes/return";

  return (
    <section
      className={`rounded-[20px] bg-banner-dark p-4 text-surface shadow-md ${className}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brand/20 ring-1 ring-brand/40">
            <ShieldCheck
              className="h-6 w-6 fill-brand text-surface"
              aria-hidden="true"
            />
          </div>
          <div className="min-w-0 space-y-0.5">
            <h2 className="text-sm font-black">AI 안심 귀가</h2>
            <p className="text-[11px] leading-snug text-surface/80">
              혼잡도와 동선을 고려한 안전한 귀갓길을 안내해요
            </p>
          </div>
        </div>

        <Link
          href={href}
          className="inline-flex shrink-0 items-center gap-1 rounded-chip bg-brand px-3.5 py-2 text-xs font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90"
        >
          귀가 경로 보기
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}
