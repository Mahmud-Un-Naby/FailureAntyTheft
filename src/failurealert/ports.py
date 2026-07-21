"""Protocol (port) definitions for the message bus and the repository.

These are signature-level contracts only: no implementations, no side effects. The
``InProcBus``/``MqttBus`` (messaging pass) and the SQLite repository (persistence
pass) will satisfy these protocols. Concrete database schema is out of scope here.

The bus deals in already-serialized ``bytes`` payloads on string topics, keeping it
faithful to MQTT so that the in-process and MQTT implementations are interchangeable;
serialization of the :mod:`failurealert.contracts` models is the caller's concern.
"""

from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from failurealert.contracts import DeviceConfig, DeviceRuntimeRecord, EventRecord


@runtime_checkable
class Bus(Protocol):
    """Publish/subscribe transport abstraction (in-process or MQTT)."""

    async def start(self) -> None:
        """Connect/prepare the transport."""
        ...

    async def stop(self) -> None:
        """Disconnect and release resources."""
        ...

    async def publish(self, topic: str, payload: bytes) -> None:
        """Publish ``payload`` to ``topic``."""
        ...

    def subscribe(self, topic_filter: str) -> AsyncIterator[tuple[str, bytes]]:
        """Yield ``(topic, payload)`` pairs matching ``topic_filter``."""
        ...


@runtime_checkable
class Repo(Protocol):
    """Durable storage for device configuration, runtime state, and events."""

    async def init_schema(self) -> None:
        """Create or migrate the schema so the repository is ready for use."""
        ...

    # -- device configuration (API/registration-owned) -- #
    async def get_device(self, device_id: str) -> DeviceConfig | None: ...
    async def list_devices(self) -> Sequence[DeviceConfig]: ...
    async def upsert_device(self, config: DeviceConfig) -> None: ...

    # -- runtime state (runtime-owned) -- #
    async def get_runtime_record(self, device_id: str) -> DeviceRuntimeRecord | None: ...
    async def save_runtime_record(self, record: DeviceRuntimeRecord) -> None: ...

    # -- events (runtime-owned) -- #
    async def insert_event(self, event: EventRecord) -> None: ...
    async def get_event(self, event_id: str) -> EventRecord | None: ...
    async def acknowledge_event(
        self,
        event_id: str,
        acknowledged_by: str | None,
        acknowledged_at: datetime,
    ) -> None: ...
    async def list_events(
        self,
        *,
        device_id: str | None = None,
        limit: int = 100,
    ) -> Sequence[EventRecord]: ...


__all__ = ["Bus", "Repo"]
