import { ExternalLink } from "lucide-react";
import type { KakaoMapPoint } from "./KakaoMap";

export function buildOpenStreetMapEmbedUrl(point: KakaoMapPoint): string {
  const longitudeSpan = 0.035;
  const latitudeSpan = 0.022;
  const params = new URLSearchParams({
    bbox: [
      point.lng - longitudeSpan,
      point.lat - latitudeSpan,
      point.lng + longitudeSpan,
      point.lat + latitudeSpan,
    ].join(","),
    layer: "mapnik",
    marker: `${point.lat},${point.lng}`,
  });
  return `https://www.openstreetmap.org/export/embed.html?${params.toString()}`;
}

export function buildOpenStreetMapLink(point: KakaoMapPoint): string {
  return `https://www.openstreetmap.org/?mlat=${point.lat}&mlon=${point.lng}#map=14/${point.lat}/${point.lng}`;
}

export function OpenStreetMap({
  center,
  title,
  markers = [],
  className = "h-80 w-full",
}: {
  center: KakaoMapPoint;
  title: string;
  markers?: Array<KakaoMapPoint & { title: string; label: string }>;
  className?: string;
}) {
  const longitudeSpan = 0.035;
  const latitudeSpan = 0.022;

  return (
    <div className="overflow-hidden rounded-card-lg border border-line-light bg-surface shadow-card">
      <div className="relative overflow-hidden">
        <iframe
          key={`${center.lat}-${center.lng}`}
          title={`${title} 지도`}
          src={buildOpenStreetMapEmbedUrl(center)}
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          className={`pointer-events-none block border-0 ${className}`}
        />
        {markers.map((marker) => {
          const left = 50 + ((marker.lng - center.lng) / longitudeSpan) * 50;
          const top = 50 - ((marker.lat - center.lat) / latitudeSpan) * 50;
          if (left < 2 || left > 98 || top < 2 || top > 98) return null;
          return (
            <span
              key={`${marker.title}-${marker.lat}-${marker.lng}`}
              title={marker.title}
              aria-label={marker.title}
              className="absolute grid h-7 w-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-chip border-2 border-surface bg-brand text-[11px] font-black text-surface shadow-md"
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              {marker.label}
            </span>
          );
        })}
      </div>
      <div className="flex items-center justify-between gap-2 px-3 py-2 text-[10px] text-muted">
        <span>© OpenStreetMap contributors</span>
        <a
          href={buildOpenStreetMapLink(center)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-bold text-ink hover:text-brand"
        >
          크게 보기 <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </a>
      </div>
    </div>
  );
}
