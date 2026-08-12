"""Long-polling SQS consumer for sync-queue.fifo.

boto3 client points at LocalStack in dev (see config.settings.aws_endpoint) and
real SQS in prod (unset AWS_ENDPOINT).
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

import boto3

from syncbeat_sync.config import settings


@lru_cache
def get_client():
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key or None,
        aws_secret_access_key=settings.aws_secret_key or None,
        endpoint_url=settings.aws_endpoint or None,
    )


def poll() -> Iterator[dict[str, Any]]:
    """Yields raw SQS messages, one long-poll batch at a time. Caller deletes each
    message after it's been fully processed (redis write + publish succeeded) —
    see service.run(). Leaving a message undeleted lets it become visible again
    after the queue's visibility timeout, which is the retry mechanism.
    """
    while True:
        resp = get_client().receive_message(
            QueueUrl=settings.sync_queue_url,
            MaxNumberOfMessages=settings.sqs_max_messages,
            WaitTimeSeconds=settings.sqs_wait_time_seconds,
        )
        for msg in resp.get("Messages", []):
            yield msg



def delete(receipt_handle: str) -> None:
    get_client().delete_message(QueueUrl=settings.sync_queue_url, ReceiptHandle=receipt_handle)
