import type { ReactNode } from "react";

export function TabPageHero({
  title,
  subtitle,
  aside,
}: {
  title: ReactNode;
  subtitle: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section className="relative isolate flex min-h-14 items-start justify-between gap-2 overflow-hidden">
      <div className="relative z-10 min-w-0 pt-0.5">
        <h1 className="text-2xl font-black leading-tight tracking-tight text-ink">
          {title}
        </h1>
        <p className="mt-1 whitespace-nowrap text-xs font-medium text-muted">
          {subtitle}
        </p>
      </div>
      {aside ? <div className="relative z-10 shrink-0">{aside}</div> : null}
    </section>
  );
}
