"""Resilient polling loop that publishes normalized Phyphox readings."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Protocol

import httpx

from failurealert.collector.phyphox import PhyphoxClient, PollResult
from failurealert.collector.security import validate_sensor_url
from failurealert.contracts import Acceleration, DeviceConfig, LinkState, Telemetry
from failurealert.ports import Bus
from failurealert.topics import link_topic, telemetry_topic


class PollClient(Protocol):
    async def poll(self, cursor: float | None) -> PollResult: ...
    async def close(self) -> None: ...


class DeviceCollector:
    def __init__(
        self,
        config: DeviceConfig,
        bus: Bus,
        *,
        poll_interval_s: float = 0.1,
        failure_threshold: int = 3,
        client_factory: Callable[[str], PollClient] = PhyphoxClient,
        validator: Callable[[str], Awaitable[str]] | None = None,
        wall_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.bus = bus
        self.poll_interval_s = poll_interval_s
        self.failure_threshold = failure_threshold
        self._client_factory = client_factory
        self._validator = validator or validate_sensor_url
        self._wall_clock = wall_clock or (lambda: datetime.now(UTC))
        self._client: PollClient | None = None
        self._cursor: float | None = None
        self._session: str | None = None
        self._sequence = 0
        self._failures = 0
        self._online = False

    async def run(self, stop: asyncio.Event) -> None:
        try:
            while not stop.is_set():
                try:
                    await self.poll_once()
                except (OSError, ValueError, RuntimeError, httpx.HTTPError):
                    await self._record_failure()
                    await self._reset_client()
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=self.poll_interval_s)
        finally:
            await self._reset_client()

    async def poll_once(self) -> int:
        if self._client is None:
            # Validation happens for every new HTTP connection/client.
            base_url = await self._validator(self.config.source_url)
            self._client = self._client_factory(base_url)
        result = await self._client.poll(self._cursor)
        now = self._now()
        if result.session != self._session:
            self._session = result.session
            self._cursor = None
            self._sequence = 0
        published = 0
        for sample in result.samples:
            if self._cursor is not None and sample.device_time_s <= self._cursor:
                continue
            self._sequence += 1
            message = Telemetry(
                device_id=self.config.device_id,
                device_time_s=sample.device_time_s,
                received_at=now,
                sequence=self._sequence,
                acceleration=Acceleration(x=sample.x, y=sample.y, z=sample.z),
            )
            await self.bus.publish(
                telemetry_topic(self.config.device_id), message.model_dump_json().encode()
            )
            self._cursor = sample.device_time_s
            published += 1
        self._failures = 0
        if not self._online:
            self._online = True
            await self._publish_link(True, now)
        return published

    async def _record_failure(self) -> None:
        self._failures += 1
        if self._online and self._failures >= self.failure_threshold:
            self._online = False
            await self._publish_link(False, self._now())

    async def _publish_link(self, online: bool, now: datetime) -> None:
        message = LinkState(
            device_id=self.config.device_id,
            online=online,
            last_seen=now if online else None,
            consecutive_failures=self._failures,
        )
        await self.bus.publish(
            link_topic(self.config.device_id), message.model_dump_json().encode()
        )

    async def _reset_client(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _now(self) -> datetime:
        value = self._wall_clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("wall_clock must be timezone-aware")
        return value


__all__ = ["DeviceCollector", "PollClient"]
