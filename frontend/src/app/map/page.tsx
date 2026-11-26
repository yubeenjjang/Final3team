import { FestivalMapView } from "@/features/festivals/map/FestivalMapView";
import { parseMapSelection } from "@/features/festivals/map/selection";

export default async function MapPage({
  searchParams,
}: {
  searchParams: Promise<{ festival?: string; group?: string; category?: string }>;
}) {
  const params = await searchParams;
  const selection = parseMapSelection({
    festival: typeof params.festival === "string" ? params.festival : undefined,
    group: typeof params.group === "string" ? params.group : undefined,
    category: typeof params.category === "string" ? params.category : undefined,
  });
  return (
    <FestivalMapView
      initialFestivalId={selection.festivalId}
      initialGroup={selection.group}
      initialCategory={selection.category}
    />
  );
}
