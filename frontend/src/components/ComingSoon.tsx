import { Clock } from "lucide-react";

export interface ComingSoonProps {
  title?: string;
  description?: string;
}

export function ComingSoon({
  title,
  description = "더 좋은 서비스로 곧 찾아올게요.",
}: ComingSoonProps) {
  return (
    <section className="flex min-h-[60vh] flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-chip bg-surface-soft text-brand">
        <Clock className="h-7 w-7" aria-hidden="true" />
      </div>
      {title ? (
        <h1 className="text-lg font-extrabold text-ink">{title}</h1>
      ) : null}
      <p className="mt-2 text-base font-bold text-ink">준비 중이에요</p>
      <p className="mt-1.5 max-w-xs text-sm text-muted">{description}</p>
    </section>
  );
}
