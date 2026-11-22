import { ReturnRouteView } from "@/features/routes/return/ReturnRouteView";

interface ReturnRoutePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ReturnRoutePage({ searchParams }: ReturnRoutePageProps) {
  const { festivalId, id, token } = await searchParams;
  const initialFestivalId = typeof festivalId === "string" ? festivalId : undefined;
  const route = typeof id === "string" && id && typeof token === "string" && token
    ? { id, token }
    : undefined;

  return (
    <ReturnRouteView
      key={JSON.stringify([initialFestivalId, route?.id, route?.token])}
      festivalId={initialFestivalId}
      directRoute={route}
    />
  );
}
