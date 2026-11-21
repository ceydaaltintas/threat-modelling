"""In-process event bus for live progress (SSE).

One broker per application instance. Each analysis run has a topic; every
connected client gets its own queue so a slow browser cannot block the
pipeline. The most recent events are kept per run so a client that connects
late (or reloads the page) immediately sees the current state instead of an
empty screen.

Jobs are plain asyncio tasks inside FastAPI - no Redis, no Celery.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

MAX_REPLAY_EVENTS = 400
QUEUE_MAX_SIZE = 500


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=MAX_REPLAY_EVENTS)
        )
        self._lock = asyncio.Lock()

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        payload = {"run_id": run_id, "ts": _now_iso(), **event}
        async with self._lock:
            self._history[run_id].append(payload)
            targets = list(self._subscribers.get(run_id, ()))
        for queue in targets:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # A client that cannot keep up loses intermediate events;
                # the pipeline must never be blocked by the UI.
                pass

    async def subscribe(
        self, run_id: str
    ) -> tuple[asyncio.Queue[dict[str, Any]], list[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
        async with self._lock:
            self._subscribers[run_id].add(queue)
            backlog = list(self._history.get(run_id, ()))
        return queue, backlog

    async def unsubscribe(
        self, run_id: str, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        async with self._lock:
            self._subscribers.get(run_id, set()).discard(queue)

    async def history(self, run_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._history.get(run_id, ()))

    async def clear(self, run_id: str) -> None:
        async with self._lock:
            self._history.pop(run_id, None)


broker = EventBroker()
