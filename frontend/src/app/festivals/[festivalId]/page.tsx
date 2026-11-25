import { FestivalDetailView } from "@/features/festivals/detail/FestivalDetailView";

export interface FestivalDetailPageProps {
  params: Promise<{ festivalId: string }>;
}

export default async function FestivalDetailPage({
  params,
}: FestivalDetailPageProps) {
  const { festivalId } = await params;
  return <FestivalDetailView festivalId={festivalId} />;
}
