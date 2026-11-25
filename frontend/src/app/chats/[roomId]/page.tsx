import { ChatRoomView } from "@/features/community/chats/ChatRoomView";

export default async function ChatRoomPage({
  params,
}: {
  params: Promise<{ roomId: string }>;
}) {
  const { roomId } = await params;
  return <ChatRoomView roomId={decodeURIComponent(roomId)} />;
}
