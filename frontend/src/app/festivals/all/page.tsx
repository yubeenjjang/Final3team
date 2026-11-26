import { FestivalExploreView } from "@/features/festivals/explore/FestivalExploreView";
import {
  FESTIVAL_SECTION_CONFIG,
  isFestivalSectionKey,
} from "@/features/festivals/explore/sectionConfig";

export default async function AllFestivalsPage({
  searchParams,
}: {
  searchParams: Promise<{ section?: string | string[] }>;
}) {
  const rawSection = (await searchParams).section;
  const section = Array.isArray(rawSection) ? rawSection[0] : rawSection;
  const sectionKey = isFestivalSectionKey(section) ? section : "all";

  return (
    <FestivalExploreView
      mode="list"
      listTitle={FESTIVAL_SECTION_CONFIG[sectionKey].title}
    />
  );
}
