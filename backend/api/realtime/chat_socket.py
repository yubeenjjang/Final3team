"""WebSocket transport. Wakeups only signal changes, and PostgreSQL supplies history."""

import asyncio
import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Annotated, Protocol
from uuid import UUID

from anyio import CancelScope
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from api.auth.tokens import positive_setting
from api.errors import ApiError
from api.repositories import chat as repository
from api.schemas.chat import Send, Subscribe
from api.services import mock_chat
from api.services.chat import ChatIdentity, is_current
from shared.db.session import user_db_session

router = APIRouter()
TICKET_TTL = 30
RECHECK_SECONDS = 1
_EVENTS = TypeAdapter(Annotated[Subscribe | Send, Field(discriminator="type")])


class TicketStore(Protocol):
    def issue(self, identity: ChatIdentity) -> str: ...
    def consume(self, ticket: str) -> ChatIdentity | None: ...


class MemoryTickets:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock
        self.lock = Lock()
        self.entries: dict[str, tuple[float, ChatIdentity]] = {}

    @staticmethod
    def _key(ticket: str) -> str:
        return "ws:ticket:" + hashlib.sha256(ticket.encode()).hexdigest()

    def issue(self, identity: ChatIdentity) -> str:
        ticket = secrets.token_urlsafe(32)
        with self.lock:
            now = self.clock()
            self.entries = {key: value for key, value in self.entries.items() if value[0] > now}
            self.entries[self._key(ticket)] = (now + TICKET_TTL, identity)
        return ticket

    def consume(self, ticket: str) -> ChatIdentity | None:
        if len(ticket) != 43 or not ticket.isascii():
            return None
        with self.lock:
            entry = self.entries.pop(self._key(ticket), None)
            return entry[1] if entry and entry[0] > self.clock() else None


class ChatBus(Protocol):
    async def subscribe(self, topic: str, wake: asyncio.Event) -> None: ...
    async def unsubscribe(self, topic: str, wake: asyncio.Event) -> None: ...
    async def publish(self, topic: str) -> None: ...


class MemoryChatBus:
    def __init__(self) -> None:
        self.listeners: dict[str, set[asyncio.Event]] = {}

    async def subscribe(self, topic: str, wake: asyncio.Event) -> None:
        self.listeners.setdefault(topic, set()).add(wake)

    async def unsubscribe(self, topic: str, wake: asyncio.Event) -> None:
        listeners = self.listeners.get(topic)
        if listeners:
            listeners.discard(wake)
            if not listeners:
                del self.listeners[topic]

    async def publish(self, topic: str) -> None:
        for wake in self.listeners.get(topic, ()):
            wake.set()


class MessageLimits:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock
        self.lock = Lock()
        self.second = -1
        self.users: dict[UUID, int] = {}
        self.rooms: dict[str, int] = {}

    def charge(self, user_id: UUID, room_id: str) -> None:
        with self.lock:
            second = int(self.clock())
            if second != self.second:
                self.second = second
                self.users.clear()
                self.rooms.clear()
            user_count = self.users.get(user_id, 0)
            room_count = self.rooms.get(room_id, 0)
            if (user_count >= positive_setting("CHAT_RATE_USER", 5)
                    or room_count >= positive_setting("CHAT_RATE_ROOM", 20)):
                raise ApiError(429, "RATE_LIMITED", "잠시 뒤 메시지를 보내 주세요.")
            self.users[user_id] = user_count + 1
            self.rooms[room_id] = room_count + 1


tickets: TicketStore = MemoryTickets()
bus: ChatBus = MemoryChatBus()
limits = MessageLimits()


def room_topic(room_id: str) -> str:
    return f"chat:{room_id}"


def user_topic(user_id: UUID) -> str:
    return f"chat:notifications:{user_id}"


async def publish(topic: str) -> None:
    try:
        await bus.publish(topic)
    except Exception:
        # Wakeups are best effort. The next recheck reads the committed state.
        pass


@dataclass
class Subscription:
    cursor: int
    status: str = "active"


class ChatConnection:
    def __init__(self, socket: WebSocket, identity: ChatIdentity) -> None:
        self.socket = socket
        self.identity = identity
        self.user_id = identity.user_id
        self.wake = asyncio.Event()
        self.rooms: dict[str, Subscription] = {}
        self.notification_cursor = 0

    async def event(self, type_: str, **data) -> None:
        await self.socket.send_json(jsonable_encoder({"type": type_, **data}))

    async def error(self, code: str, client_id: str | None = None) -> None:
        data = {"client_message_id": client_id} if client_id is not None else {}
        await self.event("error", code=code, **data)

    async def room_page(self, room_id: str, cursor: int):
        if self.identity.claims is None:
            status, reason = mock_chat.mock_rooms.room_access(self.user_id, room_id)
            items, more = (mock_chat.mock_rooms.messages(self.user_id, room_id, cursor, None, 100)
                           if not reason else ([], False))
        else:
            async with user_db_session(self.user_id) as db:
                status, reason = await repository.room_access(db, self.user_id, room_id)
                items, more = (await repository.messages(db, room_id, cursor, None, 100)
                               if not reason else ([], False))
        return status, reason, items, more

    async def flush_room(self, room_id: str, *, initial: bool = False) -> None:
        sub = self.rooms[room_id]
        while True:
            status, reason, items, more = await self.room_page(room_id, sub.cursor)
            if reason and initial:
                await self.remove(room_id)
                await self.error("FORBIDDEN")
                return
            if status != sub.status:
                if status in ("read_only", "closed") and reason in (None, "blocked"):
                    await self.event("room_status", room_id=room_id, status=status)
                sub.status = status
            if reason:
                await self.remove(room_id)
                await self.event("unsubscribed", room_id=room_id, reason=reason)
                return
            for message in items:
                message.pop("sender_display_name")
                await self.event("message", room_id=room_id, **message)
                sub.cursor = message["seq"]
            if not more:
                return
            initial = False

    async def remove(self, room_id: str) -> None:
        self.rooms.pop(room_id, None)
        await bus.unsubscribe(room_topic(room_id), self.wake)

    async def send(self, request: Send) -> None:
        store = repository.ChatRooms if self.identity.claims else mock_chat.mock_rooms
        try:
            message_id, seq, created = await run_in_threadpool(
                store.send, self.user_id, request.room_id, request.client_message_id, request.body, limits.charge,
            )
        except ApiError as error:
            code = error.code if error.code in ("ROOM_READ_ONLY", "RATE_LIMITED") else "FORBIDDEN"
            await self.error(code, request.client_message_id)
            return
        except SQLAlchemyError:
            await self.error("STORE_FAILED", request.client_message_id)
            return
        try:
            await self.event("ack", client_message_id=request.client_message_id, message_id=message_id, seq=seq)
        finally:
            if created:
                await publish(room_topic(request.room_id))

    async def handle(self, frame: dict) -> None:
        if frame["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(frame["code"])
        payload = frame.get("text")
        try:
            if payload is None or len(payload) > 16000:
                await self.error("VALIDATION_ERROR")
                return
            request = _EVENTS.validate_json(payload)
        except (ValidationError, UnicodeError):
            await self.error("VALIDATION_ERROR")
            return
        if isinstance(request, Send):
            await self.send(request)
        else:
            await bus.subscribe(room_topic(request.room_id), self.wake)
            self.rooms[request.room_id] = Subscription(request.after_seq)
            try:
                await self.flush_room(request.room_id, initial=True)
            except ApiError:
                await self.remove(request.room_id)
                await self.error("FORBIDDEN")

    async def flush(self) -> None:
        for room_id in tuple(self.rooms):
            try:
                await self.flush_room(room_id)
            except ApiError:
                await self.remove(room_id)
                await self.event("unsubscribed", room_id=room_id, reason="removed")
        while True:
            if self.identity.claims is None:
                alerts = mock_chat.mock_rooms.recent_notifications(self.user_id, self.notification_cursor)
            else:
                async with user_db_session(self.user_id) as db:
                    alerts = await repository.recent_notifications(db, self.notification_cursor)
            for alert in alerts:
                await self.event("notification", notification=alert)
                self.notification_cursor = alert["notification_id"]
            if len(alerts) < 100:
                return

    async def active(self) -> bool:
        if await run_in_threadpool(is_current, self.identity):
            return True
        for room_id in self.rooms:
            await self.event("unsubscribed", room_id=room_id, reason="deleted")
        await self.socket.close(4403)
        return False

    async def run(self) -> None:
        if self.identity.claims is None:
            self.notification_cursor = mock_chat.mock_rooms.notification_head(self.user_id)
        else:
            async with user_db_session(self.user_id) as db:
                self.notification_cursor = await repository.notification_head(db)
        await self.socket.accept()
        await bus.subscribe(user_topic(self.user_id), self.wake)
        receive = asyncio.create_task(self.socket.receive())
        wakeup = asyncio.create_task(self.wake.wait())
        timer = asyncio.create_task(asyncio.sleep(RECHECK_SECONDS))
        try:
            while True:
                done, _ = await asyncio.wait((receive, wakeup, timer), return_when=asyncio.FIRST_COMPLETED)
                if receive in done and receive.result()["type"] == "websocket.disconnect":
                    return
                if not await self.active():
                    return
                if receive in done:
                    await self.handle(receive.result())
                    receive = asyncio.create_task(self.socket.receive())
                if wakeup in done or timer in done:
                    self.wake.clear()
                    await self.flush()
                    if wakeup in done:
                        wakeup = asyncio.create_task(self.wake.wait())
                    if timer in done:
                        timer = asyncio.create_task(asyncio.sleep(RECHECK_SECONDS))
        finally:
            for task in (receive, wakeup, timer):
                task.cancel()
            # A disconnect can also cancel the ASGI scope while subscriptions are being removed.
            with CancelScope(shield=True):
                await asyncio.gather(receive, wakeup, timer, return_exceptions=True)
                await bus.unsubscribe(user_topic(self.user_id), self.wake)
                for room_id in tuple(self.rooms):
                    await self.remove(room_id)


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    identity = tickets.consume(websocket.query_params.get("ticket", ""))
    try:
        current = identity is not None and await run_in_threadpool(is_current, identity)
    except SQLAlchemyError:
        current = False
    if not current:
        # Complete the handshake so browsers receive the application close code.
        await websocket.accept()
        await websocket.close(4401 if identity is None else 4403)
        return
    try:
        await ChatConnection(websocket, identity).run()
    except (WebSocketDisconnect, OSError):
        return
    except SQLAlchemyError:
        await websocket.close(1011)
