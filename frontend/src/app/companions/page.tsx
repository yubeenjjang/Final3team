import { CompanionsView } from "@/features/community/companions/CompanionsView";

export default async function CompanionsPage({
  searchParams,
}: {
  searchParams: Promise<{ festivalId?: string; tab?: string }>;
}) {
  const params = await searchParams;
  return (
    <CompanionsView
      initialFestivalId={params.festivalId}
      initialTab={params.tab === "mine" ? "mine" : "browse"}
    />
  );
}
