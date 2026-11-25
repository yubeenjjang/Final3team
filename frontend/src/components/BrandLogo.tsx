import Image from "next/image";

export interface BrandLogoProps {
  className?: string;
  priority?: boolean;
}

export function BrandLogo({ className = "", priority = false }: BrandLogoProps) {
  return (
    <Image
      src="/brand/noldaga-logo.png"
      alt="NOLDAGA"
      width={1101}
      height={366}
      priority={priority}
      unoptimized
      className={`object-contain ${className || "h-8 w-auto"}`}
    />
  );
}
