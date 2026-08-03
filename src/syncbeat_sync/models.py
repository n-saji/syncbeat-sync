"""Wire format for events published by the mainframe's WebSocket layer onto SNS/SQS.

Keep this in sync with whatever shape the mainframe actually publishes once
that side is built (see "Backend API Service" > WebSocket layer in
syncbeat-service-breakdown.md). This is a first guess at the schema based on
the design doc — expect to adjust field names once the publisher exists.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class EventType(StrEnum):
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    SEEK = "SEEK"
    SKIP = "SKIP"
    SYNC_PULSE = "SYNC_PULSE"
    HOST_CHANGED = "HOST_CHANGED"


class PlaybackEvent(BaseModel):
    room_id: str
    event_type: EventType
    timestamp: int
    """Client-side event timestamp (ms epoch) — combine with room_id for the idempotency key."""

    # Present depending on event_type — TODO: tighten this once the real
    # publisher schema is known (could be a discriminated union per event type
    # instead of one bag of optional fields).
    position_ms: int | None = None
    track_id: str | None = None
    user_id: str | None = None

    extra: dict[str, Any] = {}


class RoomState(BaseModel):
    """Canonical room state as stored in redis `room:{room_id}:state`."""

    room_id: str
    room_name: str
    room_type: str
    host_id: str
    track_id: str | None = None
    position_ms: int = 0
    is_playing: bool = False
    updated_at: str
    """ISO-8601 instant string, matches how the mainframe writes it."""

class RoomMembers(BaseModel):
    """Canonical room members as stored in redis `room:{room_id}:members`."""

    room_id: str
    members: list[bytes | str] = []
