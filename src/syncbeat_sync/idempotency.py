"""Cheap dedupe against SQS's at-least-once delivery.

SQS can redeliver a message that was already successfully processed (e.g. if
the visibility timeout expires right after we finished but before we deleted
it). We don't want to double-apply a PLAY/SEEK/SKIP.
"""

from syncbeat_sync.models import PlaybackEvent
from syncbeat_sync.redis_client import get_client
from syncbeat_sync.config import settings


def event_key(event: PlaybackEvent) -> str:
    return f"processed:{event.room_id}:{event.timestamp}"


def already_processed(event: PlaybackEvent) -> bool:
    """True if this (room_id, timestamp) pair was handled recently."""
    return get_client().exists(event_key(event)) == 1


def mark_processed(event: PlaybackEvent) -> None:
    """Remember this event for settings.idempotency_ttl_seconds."""
    get_client().set(event_key(event), "1", ex=settings.idempotency_ttl_seconds)