import asyncio

import pytest

from failurealert.messaging import InProcBus


@pytest.mark.asyncio
async def test_bus_fans_out_and_matches_wildcard() -> None:
    bus = InProcBus()
    await bus.start()
    subscription = bus.subscribe("failurealert/devices/+/telemetry")
    pending = asyncio.create_task(anext(subscription))
    await asyncio.sleep(0)
    await bus.publish("failurealert/devices/phone-01/telemetry", b"sample")
    assert await asyncio.wait_for(pending, 1) == (
        "failurealert/devices/phone-01/telemetry",
        b"sample",
    )
    await subscription.aclose()
    await bus.stop()


@pytest.mark.asyncio
async def test_publish_requires_started_bus() -> None:
    with pytest.raises(RuntimeError, match="not started"):
        await InProcBus().publish("topic", b"data")
