"""Top-level orchestration — wires sqs_consumer + idempotency + state + redis_client together.

This is deliberately left as pseudocode-with-structure rather than a working
loop: fill in the pieces in sqs_consumer.py / redis_client.py / state.py /
idempotency.py first (each has its own TODOs), then this function should
mostly just fall into place.
"""

import logging

from syncbeat_sync import idempotency, redis_client, sqs_consumer, state
from syncbeat_sync.models import PlaybackEvent

logger = logging.getLogger("syncbeat_sync")


def handle_message(raw_body: str) -> None:
    event = PlaybackEvent.model_validate_json(raw_body)

    if idempotency.already_processed(event):
        logger.info("skipping duplicate event room=%s ts=%s", event.room_id, event.timestamp)
        return

    previous = redis_client.read_state(event.room_id)
    if previous is None:
        logger.warning("no live state for room=%s, dropping event", event.room_id)
        return

    new_state = state.apply_event(previous, event)

    redis_client.write_state(new_state)
    redis_client.publish_state(new_state)
    idempotency.mark_processed(event)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("syncbeat-sync starting, long-polling for playback events")

    for message in sqs_consumer.poll():
        try:
            handle_message(message["Body"])
            sqs_consumer.delete(message["ReceiptHandle"])
        except Exception:
            # Deliberately don't delete on failure — let SQS redeliver after the
            # visibility timeout. After maxReceiveCount attempts it routes to the
            # DLQ automatically (configured on the queue, not here).
            logger.exception("failed to process message, leaving for redrive")
