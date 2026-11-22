import { ReturnRouteView } from "@/features/routes/return/ReturnRouteView";

interface ReturnRoutePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ReturnRoutePage({ searchParams }: ReturnRoutePageProps) {
  const { festivalId, id } = await searchParams;
  const initialFestivalId = typeof festivalId === "string" ? festivalId : undefined;
  const routeId = typeof id === "string" && id ? id : undefined;

  return (
    <ReturnRouteView
      key={JSON.stringify([initialFestivalId, routeId])}
      festivalId={initialFestivalId}
      routeId={routeId}
    />
  );
}
