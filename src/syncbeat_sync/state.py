"""Turns a PlaybackEvent + the previous RoomState into the new canonical RoomState.

This is the actual "sync" in sync-service — see syncbeat-service-breakdown.md
section 2 ("Detailed consumer logic" + "The sync-pulse specifically") for the
behaviour each branch needs. Kept as one function per event type so each can
be implemented (and tested) independently.
"""


from datetime import UTC, datetime

from syncbeat_sync.models import EventType, PlaybackEvent, RoomState
from syncbeat_sync.redis_client import read_members


def _now_iso() -> str:
    """Server-side instant, formatted to match mainframe's Instant.now().toString()."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def apply_event(previous: RoomState, event: PlaybackEvent) -> RoomState:
    match event.event_type:
        case EventType.PLAY | EventType.PAUSE:
            return _apply_play_pause(previous, event)
        case EventType.SEEK:
            return _apply_seek(previous, event)
        case EventType.SKIP:
            return _apply_skip(previous, event)
        case EventType.SYNC_PULSE:
            return _apply_sync_pulse(previous, event)
        case EventType.HOST_CHANGED:
            return _apply_host_changed(previous, event)


def _apply_play_pause(previous: RoomState, event: PlaybackEvent) -> RoomState:
    return previous.model_copy(update={
        "is_playing": event.event_type == EventType.PLAY,
        "updated_at": _now_iso(),
    })


def _apply_seek(previous: RoomState, event: PlaybackEvent) -> RoomState:
    return previous.model_copy(update={
        "position_ms": event.position_ms if event.position_ms is not None else previous.position_ms,
        "updated_at": _now_iso(),
    })


def _apply_skip(previous: RoomState, event: PlaybackEvent) -> RoomState:
    return previous.model_copy(update={
        "track_id": event.track_id or previous.track_id,
        "position_ms": 0,
        "updated_at": _now_iso(),
    })


def _apply_sync_pulse(previous: RoomState, event: PlaybackEvent) -> RoomState:
    """Drift correction — the reason this service exists.

    Don't trust event.position_ms. If previous.is_playing, recompute:
        position_ms = previous.position_ms + (now - previous.updated_at)
    and write that back as the corrected canonical position. If not playing,
    position is unchanged — just refresh updated_at.
    """
    now = datetime.now(UTC)
    if not previous.is_playing:
        return previous.model_copy(update={"updated_at": now.isoformat().replace("+00:00", "Z")})

    elapsed_ms = int((now - _parse_iso(previous.updated_at)).total_seconds() * 1000)
    return previous.model_copy(update={
        "position_ms": previous.position_ms + elapsed_ms,
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    })


def _apply_host_changed(previous: RoomState, event: PlaybackEvent) -> RoomState:
    # mainframe's RoomService.leaveRoom already does host re-election synchronously
    # today; once the WebSocket + SNS path exists this event type may become
    # redundant with that, or the mainframe path gets removed in favour of this one.
    new_host_id = event.user_id
    if not new_host_id:
        members = read_members(previous.room_id)
        if members.members:
            new_host_id = str(next(iter(members.members)))
    return previous.model_copy(update={
        "host_id": new_host_id or previous.host_id,
        "updated_at": _now_iso(),
    })
