import { apiGet, apiPatch, apiPost } from "@/lib/api/client";

export type RoomType = "companion" | "direct" | "friend_group";
export type RoomStatus = "active" | "read_only" | "closed";
export type MemberStatus = "invited" | "joined" | "declined" | "left";
export type RoomFilter = "all" | "companion" | "friend" | "past";
export type RoomAction = "accept" | "decline" | "leave";

export interface ChatRoomItem {
  room_id: string;
  room_type: RoomType;
  name: string | null;
  peer_display_name?: string | null;
  festival_name?: string | null;
  meet_at?: string | null;
  status: RoomStatus;
  last_message_at: string | null;
  unread_count: number;
  my_status: "invited" | "joined";
}

export interface ChatRoomListResponse {
  items: ChatRoomItem[];
  empty_hint?: string;
}

export interface ChatRoomCreated {
  room_id: string;
}

export interface InvitedMember {
  user_id: string;
  status: "invited";
  invited_at: string;
}

export interface InvitationResponse {
  room_id: string;
  invited: InvitedMember[];
}

export interface RoomActionResponse {
  room_id: string;
  my_status: MemberStatus;
}

export interface RenameRoomResponse {
  room_id: string;
  name: string;
}

export interface ChatMessageItem {
  message_id: number;
  seq: number;
  sender_id: string | null;
  sender_display_name?: string | null;
  msg_type: "text" | "system";
  body: string;
  created_at: string;
}

export interface ChatMessagesResponse {
  items: ChatMessageItem[];
  has_more: boolean;
}

export interface WsTicketResponse {
  ticket: string;
  expires_in: number;
}

export function listChatRooms(
  filter: RoomFilter = "all",
  signal?: AbortSignal,
): Promise<ChatRoomListResponse> {
  return apiGet<ChatRoomListResponse>("/me/chat-rooms", {
    query: { filter },
    signal,
  });
}

export function createDirectRoom(friendId: string): Promise<ChatRoomCreated> {
  return apiPost<ChatRoomCreated>("/chat-rooms", {
    type: "direct",
    friend_id: friendId,
  });
}

export function createGroupRoom(
  name: string,
  inviteeIds: string[],
): Promise<ChatRoomCreated> {
  return apiPost<ChatRoomCreated>("/chat-rooms", {
    type: "friend_group",
    name,
    invitee_ids: inviteeIds,
  });
}

export function inviteToRoom(
  roomId: string,
  inviteeIds: string[],
): Promise<InvitationResponse> {
  return apiPost<InvitationResponse>(
    `/chat-rooms/${encodeURIComponent(roomId)}/invitations`,
    { invitee_ids: inviteeIds },
  );
}

export function actOnRoom(
  roomId: string,
  action: RoomAction,
): Promise<RoomActionResponse> {
  return apiPost<RoomActionResponse>(
    `/chat-rooms/${encodeURIComponent(roomId)}/${action}`,
  );
}

export function renameRoom(
  roomId: string,
  name: string,
): Promise<RenameRoomResponse> {
  return apiPatch<RenameRoomResponse>(
    `/chat-rooms/${encodeURIComponent(roomId)}`,
    { name },
  );
}

export function listRoomMessages(
  roomId: string,
  params: { after_seq?: number; before_seq?: number; limit?: number } = {},
  signal?: AbortSignal,
): Promise<ChatMessagesResponse> {
  return apiGet<ChatMessagesResponse>(
    `/chat-rooms/${encodeURIComponent(roomId)}/messages`,
    {
      query: {
        after_seq: params.after_seq,
        before_seq: params.before_seq,
        limit: params.limit ?? 50,
      },
      signal,
    },
  );
}

export function markRoomRead(roomId: string, seq: number): Promise<void> {
  return apiPost<void>(`/chat-rooms/${encodeURIComponent(roomId)}/read`, {
    seq,
  });
}

export function issueWsTicket(): Promise<WsTicketResponse> {
  return apiPost<WsTicketResponse>("/ws-tickets", {});
}
