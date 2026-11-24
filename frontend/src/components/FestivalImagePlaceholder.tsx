import Image from "next/image";

export interface FestivalImagePlaceholderProps {
  compact?: boolean;
  className?: string;
}

export function FestivalImagePlaceholder({
  compact = false,
  className = "",
}: FestivalImagePlaceholderProps) {
  return (
    <div
      className={`flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-surface-soft via-surface to-surface-muted text-center ${
        compact ? "gap-1.5 px-2.5 py-3" : "gap-2 px-4 py-6"
      } ${className}`}
    >
      <Image
        src="/logo-noldaga.png"
        alt=""
        width={compact ? 84 : 132}
        height={compact ? 28 : 44}
        unoptimized
        className={`${compact ? "h-5" : "h-8"} w-auto object-contain opacity-90 mix-blend-multiply`}
      />
      <span
        className={`${
          compact ? "text-[10px]" : "text-xs"
        } font-semibold text-muted`}
      >
        이미지 준비 중
      </span>
    </div>
  );
}
