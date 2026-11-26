import type { ChatRoomItem } from "./api";

function formatMeetDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "numeric",
    day: "numeric",
  }).format(date);
}

export function getChatRoomTitle(room: ChatRoomItem | null): string {
  if (!room) return "채팅방";

  const customName = room.name?.trim();
  if (room.room_type === "direct") {
    return room.peer_display_name?.trim() || customName || "친구 채팅";
  }

  if (room.room_type === "companion") {
    const festivalName = room.festival_name?.trim();
    const meetDate = formatMeetDate(room.meet_at);
    if (festivalName && meetDate) return `${festivalName} · ${meetDate} 동행`;
    if (festivalName) return `${festivalName} 동행`;
    return customName || "동행 채팅";
  }

  return customName || "단체 채팅방";
}
