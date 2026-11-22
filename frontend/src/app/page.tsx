import Link from "next/link";
import { ArrowRight, Compass, ShieldCheck } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-5 px-4 py-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-3xl font-extrabold leading-tight tracking-tight text-surface">
          오늘, 어디서 <span className="text-neon">놀까?</span>
        </h1>
        <p className="text-sm text-dark-muted">
          전국의 축제부터 안전한 귀갓길까지, 놀다가와 함께하세요.
        </p>
      </section>

      <section className="rounded-card bg-neon p-5 text-ink">
        <div className="mb-2 inline-flex items-center gap-1.5 rounded-chip bg-dark-bg px-3 py-1 text-xs font-bold text-neon">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
          핵심 서비스
        </div>
        <h2 className="text-xl font-extrabold">AI 안심 귀가</h2>
        <p className="mt-1 text-sm font-medium text-ink/80">
          축제 종료 후, 혼잡도와 동선을 고려한 안전한 귀갓길을 안내해 드려요.
        </p>
        <Link
          href="/routes/return"
          className="mt-4 inline-flex items-center gap-2 rounded-chip bg-dark-bg px-4 py-2.5 text-sm font-bold text-surface transition-opacity hover:opacity-90"
        >
          귀가 경로 조회하기
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </section>

      <section className="rounded-card border border-line-dark bg-dark-surface p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-chip bg-accent/20 text-accent">
              <Compass className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-bold text-surface">전국 축제 둘러보기</h2>
              <p className="text-xs text-dark-muted">
                지역과 일정별로 축제를 찾아보세요.
              </p>
            </div>
          </div>
          <Link
            href="/festivals"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-chip bg-brand text-surface transition-opacity hover:opacity-90"
            aria-label="전국 축제 둘러보기"
          >
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </section>
    </div>
  );
}
