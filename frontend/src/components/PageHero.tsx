import Image from "next/image";
import type { ReactNode } from "react";

export function PageHero({ title, subtitle }: { title: ReactNode; subtitle: string }) {
  return (
    <section className="relative isolate min-h-[92px] overflow-hidden pt-2">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-0 top-0 -z-10 h-14 w-[28%] max-w-[104px]"
      >
        <Image
          src="/brand/festival-hero-compact.png"
          alt=""
          fill
          sizes="104px"
          className="object-contain object-right"
        />
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
