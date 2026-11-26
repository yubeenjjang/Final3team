import { describe, expect, it } from "vitest";
import type { ChatRoomItem } from "./api";
import { getChatRoomTitle } from "./roomDisplay";

function room(overrides: Partial<ChatRoomItem>): ChatRoomItem {
  return {
    room_id: "crm_TEST0001",
    room_type: "direct",
    name: null,
    status: "active",
    last_message_at: null,
    unread_count: 0,
    my_status: "joined",
    ...overrides,
  };
}

describe("getChatRoomTitle", () => {
  it("uses the other user's nickname for a direct room", () => {
    expect(
      getChatRoomTitle(room({ peer_display_name: "민수" })),
    ).toBe("민수");
  });

  it("uses the festival and meeting date for a companion room", () => {
    expect(
      getChatRoomTitle(
        room({
          room_type: "companion",
          festival_name: "서울 빛 축제",
          meet_at: "2026-12-05T10:00:00+09:00",
        }),
      ),
    ).toBe("서울 빛 축제 · 12. 5. 동행");
  });

  it("keeps a custom group room name", () => {
    expect(
      getChatRoomTitle(room({ room_type: "friend_group", name: "불꽃축제 팀" })),
    ).toBe("불꽃축제 팀");
  });
});
