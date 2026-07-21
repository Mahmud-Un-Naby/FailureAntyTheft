import asyncio
from datetime import UTC, datetime

import pytest

from failureantytheft.collector.manager import DeviceCollector
from failureantytheft.collector.phyphox import PollResult, RawSample
from failureantytheft.contracts import DeviceConfig, LinkState, Telemetry
from failureantytheft.messaging import InProcBus
from failureantytheft.topics import link_topic, telemetry_topic

NOW = datetime(2026, 7, 21, tzinfo=UTC)


class FakeClient:
    async def poll(self, cursor: float | None) -> PollResult:
        return PollResult("session-1", True, (RawSample(1.0, 0.1, 0.2, 9.8),))

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_collector_normalizes_and_publishes() -> None:
    bus = InProcBus()
    await bus.start()
    config = DeviceConfig(
        device_id="phone-01",
        name="Bag",
        source_url="http://192.168.1.2:8080",
        sensitivity=1.5,
        created_at=NOW,
    )
    collector = DeviceCollector(
        config,
        bus,
        client_factory=lambda _: FakeClient(),
        validator=lambda url: _return(url),
        wall_clock=lambda: NOW,
    )
    telemetry_stream = bus.subscribe(telemetry_topic("phone-01"))
    link_stream = bus.subscribe(link_topic("phone-01"))
    telemetry_pending = asyncio.create_task(anext(telemetry_stream))
    link_pending = asyncio.create_task(anext(link_stream))
    await asyncio.sleep(0)
    assert await collector.poll_once() == 1
    message = Telemetry.model_validate_json((await telemetry_pending)[1])
    link = LinkState.model_validate_json((await link_pending)[1])
    assert message.sequence == 1 and message.acceleration.z == 9.8
    assert link.online is True
    await telemetry_stream.aclose()
    await link_stream.aclose()
    await bus.stop()


async def _return(value: str) -> str:
    return value
