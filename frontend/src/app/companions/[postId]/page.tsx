import { CompanionDetailView } from "@/features/community/companions/CompanionDetailView";

export default async function CompanionDetailPage({
  params,
}: {
  params: Promise<{ postId: string }>;
}) {
  const { postId } = await params;
  return <CompanionDetailView postId={decodeURIComponent(postId)} />;
}
