import { FerrisWheel, Tent } from "lucide-react";
import type { ReactNode } from "react";

export function PageHero({ title, subtitle }: { title: ReactNode; subtitle: string }) {
  return (
    <section className="relative isolate min-h-[92px] overflow-hidden pt-2">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-0 top-2 -z-10 h-12 w-[24%]"
      >
        <div className="absolute bottom-0 right-0 h-10 w-24 rounded-full bg-surface-soft blur-xl" />
        <FerrisWheel className="absolute bottom-0 right-0 h-11 w-11 text-ink/75" strokeWidth={1.25} />
        <Tent className="absolute bottom-0 right-9 h-9 w-11 fill-brand/25 text-brand" strokeWidth={1.5} />
      </div>
      <h1 className="text-[clamp(29px,8vw,34px)] font-black leading-tight tracking-tight text-ink">
        {title}
      </h1>
      <p className="relative z-10 mt-2 max-w-[276px] whitespace-nowrap text-[12px] font-semibold tracking-[-0.02em] text-ink/80">
        {subtitle}
      </p>
    </section>
  );
}
