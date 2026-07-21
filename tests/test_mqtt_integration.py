import asyncio
import os

import pytest

from failureantytheft.messaging import MqttBus


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("FAILUREANTYTHEFT_MQTT_TEST") != "1", reason="requires a local MQTT broker"
)
async def test_mqtt_bus_round_trip() -> None:
    bus = MqttBus(port=int(os.getenv("FAILUREANTYTHEFT_MQTT_TEST_PORT", "1883")))
    await bus.start()
    stream = bus.subscribe("failureantytheft/devices/+/telemetry")
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.1)
    await bus.publish("failureantytheft/devices/phone-01/telemetry", b"sample")
    assert await asyncio.wait_for(pending, 2) == (
        "failureantytheft/devices/phone-01/telemetry",
        b"sample",
    )
    await stream.aclose()
    await bus.stop()
