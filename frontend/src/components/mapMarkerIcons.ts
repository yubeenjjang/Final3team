export type MapMarkerIcon = "festival" | "subway" | "toilet";

const ICONS: Record<MapMarkerIcon, string> = {
  festival: `
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M3.5 20h17L12 5 3.5 20Z" />
      <path d="M12 5v15M7.5 20 12 13l4.5 7" />
      <path d="M12 5h5l-1.8 2L17 9h-5" />
    </svg>
  `,
  subway: `
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="5" y="3" width="14" height="16" rx="4" />
      <path d="M8 7h8v5H8zM8 16h.01M16 16h.01M8 21l2-2M16 21l-2-2" />
    </svg>
  `,
  toilet: `
    <svg class="map-marker-icon--filled" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="7" cy="4.5" r="1.8" />
      <path d="M5.7 7h2.6l2.2 7H8.8v6H7.4v-5.5h-.8V20H5.2v-6H3.5l2.2-7Z" />
      <circle cx="17" cy="4.5" r="1.8" />
      <path d="M15.2 7h3.6c.7 0 1.2.5 1.2 1.2V14h-1.5v6H17v-6h-1v6h-1.5v-6H14V8.2c0-.7.5-1.2 1.2-1.2Z" />
    </svg>
  `,
};

export function getMapMarkerIconMarkup(icon?: MapMarkerIcon): string | null {
  return icon ? ICONS[icon] : null;
}
