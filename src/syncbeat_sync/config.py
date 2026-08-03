"""Environment-driven settings.

Mirrors the env var names already used by syncbeat-mainframe's
application.properties / docker-compose so both services can share one
LocalStack + Redis setup in dev.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Redis (same instance the mainframe writes room state to)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_username: str | None = None
    redis_password: str | None = None
    redis_ssl: bool = False

    # AWS / LocalStack (SQS)
    aws_region: str = "us-east-1"
    aws_access_key: str = "test"
    aws_secret_key: str = "test"
    aws_endpoint: str | None = "http://localhost:4566"

    sync_queue_url: str = ""
    """URL of sync-queue.fifo — set once the queue exists (see syncbeat-service-breakdown.md)."""

    # Consumer tuning
    sqs_wait_time_seconds: int = 20
    """Long-poll duration. 20s is the SQS max and avoids empty-receive churn."""
    sqs_max_messages: int = 10

    idempotency_ttl_seconds: int = 60
    """How long a processed (room_id, timestamp) pair is remembered to dedupe SQS at-least-once delivery."""


settings = Settings()
