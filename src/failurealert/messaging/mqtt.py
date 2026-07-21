"""MQTT-backed bus with reconnect and resubscription."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress

import aiomqtt

from failurealert.messaging.inproc import _matches


class MqttBus:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1883,
        *,
        reconnect_interval_s: float = 1.0,
        connect_timeout_s: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.reconnect_interval_s = reconnect_interval_s
        self.connect_timeout_s = connect_timeout_s
        self._client: aiomqtt.Client | None = None
        self._supervisor: asyncio.Task[None] | None = None
        self._connected = asyncio.Event()
        self._stopping = False
        self._subscribers: dict[int, tuple[str, asyncio.Queue[tuple[str, bytes] | None]]] = {}
        self._next_id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._supervisor is not None:
            return
        self._stopping = False
        self._supervisor = asyncio.create_task(self._supervise())
        try:
            await asyncio.wait_for(self._connected.wait(), self.connect_timeout_s)
        except TimeoutError:
            await self.stop()
            raise ConnectionError(
                f"cannot connect to MQTT broker {self.host}:{self.port}"
            ) from None

    async def stop(self) -> None:
        self._stopping = True
        self._connected.clear()
        task, self._supervisor = self._supervisor, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        async with self._lock:
            subscribers = list(self._subscribers.values())
            self._subscribers.clear()
        for _, queue in subscribers:
            await queue.put(None)
        self._client = None

    async def publish(self, topic: str, payload: bytes) -> None:
        suffix = topic.rsplit("/", 1)[-1]
        qos = 0 if suffix in {"telemetry", "chart"} else 1
        retain = suffix in {"link", "state", "status"}
        for _ in range(2):
            await self._connected.wait()
            client = self._client
            if client is None:
                continue
            try:
                await client.publish(topic, payload=payload, qos=qos, retain=retain)
                return
            except aiomqtt.MqttError:
                self._connected.clear()
        raise ConnectionError("MQTT publish failed after reconnect")

    async def subscribe(self, topic_filter: str) -> AsyncIterator[tuple[str, bytes]]:
        queue: asyncio.Queue[tuple[str, bytes] | None] = asyncio.Queue(256)
        async with self._lock:
            subscriber_id = self._next_id
            self._next_id += 1
            self._subscribers[subscriber_id] = (topic_filter, queue)
        await self._connected.wait()
        client = self._client
        if client is not None:
            with suppress(aiomqtt.MqttError):
                await client.subscribe(topic_filter, qos=1)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            async with self._lock:
                self._subscribers.pop(subscriber_id, None)

    async def _supervise(self) -> None:
        while not self._stopping:
            try:
                async with aiomqtt.Client(hostname=self.host, port=self.port) as client:
                    self._client = client
                    async with self._lock:
                        filters = {topic_filter for topic_filter, _ in self._subscribers.values()}
                    for topic_filter in filters:
                        await client.subscribe(topic_filter, qos=1)
                    self._connected.set()
                    async for message in client.messages:
                        await self._dispatch(str(message.topic), bytes(message.payload))
            except aiomqtt.MqttError:
                self._connected.clear()
                self._client = None
                if not self._stopping:
                    await asyncio.sleep(self.reconnect_interval_s)
            except asyncio.CancelledError:
                raise
            finally:
                self._connected.clear()
                self._client = None

    async def _dispatch(self, topic: str, payload: bytes) -> None:
        async with self._lock:
            queues = [
                queue
                for topic_filter, queue in self._subscribers.values()
                if _matches(topic_filter, topic)
            ]
        for queue in queues:
            with suppress(asyncio.QueueFull):
                queue.put_nowait((topic, payload))


__all__ = ["MqttBus"]
