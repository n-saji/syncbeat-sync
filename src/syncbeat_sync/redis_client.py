"""Redis access — reads/writes the same keys syncbeat-mainframe's RedisService uses.

Key layout (must match com.syncbeat.mainframe...service.RedisService):
  room:{room_id}:state    hash  -> roomName, roomType, hostId, trackId, positionMs, isPlaying, updatedAt
  room:{room_id}:members  set   -> member user ids
"""

from functools import lru_cache

import redis
from redis.typing import EncodableT, FieldT

from syncbeat_sync.config import settings
from syncbeat_sync.models import RoomMembers, RoomState

ROOM_TTL_SECONDS = 6 * 60 * 60
"""Matches mainframe's RedisService.ROOM_TTL (Duration.ofHours(6))."""


@lru_cache
def get_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username,
        password=settings.redis_password,
        ssl=settings.redis_ssl,
        decode_responses=True,
    )


def state_key(room_id: str) -> str:
    return f"room:{room_id}:state"


def members_key(room_id: str) -> str:
    return f"room:{room_id}:members"


def _decode(value: bytes | str) -> str:
    """redis-py types hgetall/smembers as bytes | str regardless of decode_responses;
    decode_responses=True on our client guarantees str at runtime."""
    return value.decode() if isinstance(value, bytes) else value


def read_members(room_id: str) -> RoomMembers:
    """Read the current canonical members for a room, or [] if it has no live session."""
    raw_members = get_client().smembers(members_key(room_id))
    return RoomMembers(room_id=room_id, members=[_decode(m) for m in raw_members])


def read_state(room_id: str) -> RoomState | None:
    """Read the current canonical state for a room, or None if it has no live session."""
    hash_data = get_client().hgetall(state_key(room_id))
    if not hash_data:
        return None
    raw_track_id = hash_data.get("trackId")
    return RoomState(
        room_id=room_id,
        room_name=_decode(hash_data["roomName"]),
        room_type=_decode(hash_data["roomType"]),
        host_id=_decode(hash_data["hostId"]),
        track_id=_decode(raw_track_id) if raw_track_id else None,
        position_ms=int(hash_data["positionMs"]),
        is_playing=_decode(hash_data["isPlaying"]) == "true",
        updated_at=_decode(hash_data["updatedAt"]),
    )


def write_state(state: RoomState) -> None:
    """Persist the recomputed canonical state and keep the TTL alive."""
    key = state_key(state.room_id)
    fields: dict[FieldT, EncodableT] = {
        "roomName": state.room_name,
        "roomType": state.room_type,
        "hostId": state.host_id,
        "trackId": state.track_id or "",
        "positionMs": str(state.position_ms),
        "isPlaying": "true" if state.is_playing else "false",
        "updatedAt": state.updated_at,
    }
    client = get_client()
    client.hset(name=key, mapping=fields)
    client.expire(key, ROOM_TTL_SECONDS)


def publish_state(state: RoomState) -> None:
    """Broadcast the updated state so the mainframe's Pub/Sub listener can fan it out to clients."""
    get_client().publish(f"room:{state.room_id}", state.model_dump_json())
