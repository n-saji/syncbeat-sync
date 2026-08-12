# syncbeat-sync

Stateless worker: consumes playback events off `sync-queue.fifo`, recomputes
canonical room state, writes it to redis, publishes it for the mainframe to
broadcast over WebSocket.

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

