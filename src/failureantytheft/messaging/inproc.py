"""In-process publish/subscribe bus for tests and explicit fallback mode."""

import asyncio
from collections.abc import AsyncIterator


def _matches(topic_filter: str, topic: str) -> bool:
    filter_parts = topic_filter.split("/")
    topic_parts = topic.split("/")
    for index, part in enumerate(filter_parts):
        if part == "#":
            return index == len(filter_parts) - 1
        if index >= len(topic_parts):
            return False
        if part != "+" and part != topic_parts[index]:
            return False
    return len(filter_parts) == len(topic_parts)


class InProcBus:
    """Fan-out bus with MQTT-compatible ``+`` and terminal ``#`` filters."""

    def __init__(self, *, queue_size: int = 256) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        self._queue_size = queue_size
        self._subscribers: dict[int, tuple[str, asyncio.Queue[tuple[str, bytes] | None]]] = {}
        self._next_id = 0
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False
        async with self._lock:
            subscribers = list(self._subscribers.values())
            self._subscribers.clear()
        for _, queue in subscribers:
            await queue.put(None)

    async def publish(self, topic: str, payload: bytes) -> None:
        if not self._started:
            raise RuntimeError("bus is not started")
        async with self._lock:
            queues = [
                queue
                for topic_filter, queue in self._subscribers.values()
                if _matches(topic_filter, topic)
            ]
        for queue in queues:
            await queue.put((topic, payload))

    async def subscribe(self, topic_filter: str) -> AsyncIterator[tuple[str, bytes]]:
        if not self._started:
            raise RuntimeError("bus is not started")
        queue: asyncio.Queue[tuple[str, bytes] | None] = asyncio.Queue(self._queue_size)
        async with self._lock:
            subscriber_id = self._next_id
            self._next_id += 1
            self._subscribers[subscriber_id] = (topic_filter, queue)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            async with self._lock:
                self._subscribers.pop(subscriber_id, None)


__all__ = ["InProcBus"]
