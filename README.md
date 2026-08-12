# syncbeat-sync

Stateless worker: consumes playback events off `sync-queue.fifo`, recomputes
canonical room state, writes it to redis, publishes it for the mainframe to
broadcast over WebSocket. See `../syncbeat-service-breakdown.md` section 2 for
the full design, and `../syncbeat-mainframe/README.md` for the overall
architecture diagram this fits into.

This is a **skeleton** — every module has function signatures and docstrings
but the actual logic is `raise NotImplementedError` / `# TODO`. Fill in, in
this order (each layer only needs the one below it to work):

1. `redis_client.py` — read/write/publish against the same keys the mainframe
   writes (`room:{id}:state`, `room:{id}:members`). Run mainframe locally
   first and inspect those keys with `redis-cli` so you know the exact shape.
2. `idempotency.py` — trivial once redis_client works (it's just SET/EXISTS
   with a TTL).
3. `state.py` — the actual state-transition logic per event type. Pure
   functions, no I/O, easiest to unit test (see `tests/test_state.py`).
4. `sqs_consumer.py` — long-poll loop. Needs `sync-queue.fifo` to exist in
   LocalStack first (see `../syncbeat-mainframe/localstack/init.sh` for how
   the mainframe's queues/topics get created — add this one alongside them).
5. `service.py` already wires 1-4 together — shouldn't need changes.

## Running

```bash
cd syncbeat-sync
uv sync
cp .env.example .env   # then fill in SYNC_QUEUE_URL once the queue exists
uv run syncbeat-sync
```

## Tests

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
```
