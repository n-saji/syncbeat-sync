"""Starter test — once state.apply_event branches are implemented, test each
event type here without needing a live redis/SQS (pure function, no I/O)."""

from syncbeat_sync.models import EventType, PlaybackEvent, RoomState


def make_state(**overrides) -> RoomState:
    defaults = {
        "room_id": "room-1",
        "room_name": "Test Room",
        "room_type": "public",
        "host_id": "user-1",
        "track_id": None,
        "position_ms": 0,
        "is_playing": False,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    return RoomState(**{**defaults, **overrides})


def test_seek_sets_position():
    from syncbeat_sync.state import apply_event

    previous = make_state(is_playing=True, position_ms=1000)
    event = PlaybackEvent(room_id="room-1", event_type=EventType.SEEK, timestamp=1, position_ms=5000)

    result = apply_event(previous, event)

    assert result.position_ms == 5000


def test_play_without_track_id_resumes_existing_track():
    from syncbeat_sync.state import apply_event

    previous = make_state(track_id="track-1", is_playing=False, position_ms=42000)
    event = PlaybackEvent(room_id="room-1", event_type=EventType.PLAY, timestamp=1)

    result = apply_event(previous, event)

    assert result.is_playing is True
    assert result.track_id == "track-1"
    assert result.position_ms == 42000


def test_pause_records_reported_position():
    from syncbeat_sync.state import apply_event

    previous = make_state(track_id="track-1", is_playing=True, position_ms=1000)
    event = PlaybackEvent(
        room_id="room-1", event_type=EventType.PAUSE, timestamp=1, position_ms=30000
    )

    result = apply_event(previous, event)

    assert result.is_playing is False
    assert result.position_ms == 30000


def test_resume_after_pause_continues_from_reported_position():
    from syncbeat_sync.state import apply_event

    paused = make_state(track_id="track-1", is_playing=False, position_ms=30000)
    event = PlaybackEvent(
        room_id="room-1", event_type=EventType.PLAY, timestamp=1, position_ms=30000
    )

    result = apply_event(paused, event)

    assert result.is_playing is True
    assert result.position_ms == 30000


def test_play_with_track_id_loads_track_and_resets_position():
    from syncbeat_sync.state import apply_event

    previous = make_state(track_id="track-1", is_playing=False, position_ms=42000)
    event = PlaybackEvent(room_id="room-1", event_type=EventType.PLAY, timestamp=1, track_id="track-2")

    result = apply_event(previous, event)

    assert result.is_playing is True
    assert result.track_id == "track-2"
    assert result.position_ms == 0
