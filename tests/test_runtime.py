import asyncio
from datetime import UTC, datetime

import pytest

from failureantytheft.contracts import (
    Acceleration,
    Alert,
    AlertState,
    Command,
    CommandAction,
    DeviceConfig,
    LinkState,
    Telemetry,
)
from failureantytheft.database import SQLiteRepo
from failureantytheft.detection import DetectorConfig
from failureantytheft.messaging import InProcBus
from failureantytheft.runtime import DeviceRuntime
from failureantytheft.topics import alert_topic

NOW = datetime(2026, 7, 21, tzinfo=UTC)


def telemetry(sequence: int, time_s: float, z: float) -> Telemetry:
    return Telemetry(
        device_id="phone-01",
        device_time_s=time_s,
        received_at=NOW,
        sequence=sequence,
        acceleration=Acceleration(x=0.0, y=0.0, z=z),
    )


@pytest.mark.asyncio
async def test_offline_arm_intent_is_persisted(tmp_path: object) -> None:
    repo = SQLiteRepo(tmp_path / "offline-arm.sqlite")  # type: ignore[operator]
    await repo.start()
    await repo.init_schema()
    bus = InProcBus()
    await bus.start()
    config = DeviceConfig(
        device_id="phone-01",
        name="Bag",
        source_url="http://192.168.1.2:8080",
        sensitivity=1.5,
        created_at=NOW,
    )
    await repo.upsert_device(config)
    runtime = DeviceRuntime(config, bus, repo, wall_clock=lambda: NOW)
    await runtime.restore(0.0)

    await runtime.handle_command(
        Command(device_id="phone-01", action=CommandAction.arm, request_id="offline-arm"),
        0.1,
    )

    record = await repo.get_runtime_record("phone-01")
    assert record is not None
    assert record.desired_armed is True
    assert record.last_state.value == "offline"
    await bus.stop()
    await repo.stop()


@pytest.mark.asyncio
async def test_runtime_persists_alert_and_acknowledges(tmp_path: object) -> None:
    repo = SQLiteRepo(tmp_path / "runtime.sqlite")  # type: ignore[operator]
    await repo.start()
    await repo.init_schema()
    bus = InProcBus()
    await bus.start()
    config = DeviceConfig(
        device_id="phone-01",
        name="Bag",
        source_url="http://192.168.1.2:8080",
        sensitivity=1.0,
        created_at=NOW,
    )
    await repo.upsert_device(config)
    runtime = DeviceRuntime(
        config,
        bus,
        repo,
        detector_config=DetectorConfig(
            threshold=1.0,
            placement_delay_s=0.0,
            calibration_window_s=1.0,
            calibration_min_samples=3,
            calibration_max_stddev=0.1,
            ema_alpha=1.0,
            required_crossings=3,
        ),
        wall_clock=lambda: NOW,
        event_id_factory=lambda: "evt-1",
    )
    alert_stream = bus.subscribe(alert_topic("phone-01"))
    pending = asyncio.create_task(anext(alert_stream))
    await asyncio.sleep(0)
    await runtime.handle_link(LinkState(device_id="phone-01", online=True, last_seen=NOW), 0.0)
    await runtime.handle_command(
        Command(device_id="phone-01", action=CommandAction.arm, request_id="arm-1"), 0.0
    )
    for sequence, time_s in enumerate((0.1, 0.2, 0.3), 1):
        await runtime.handle_telemetry(telemetry(sequence, time_s, 9.81), time_s)
    await runtime.tick(1.0)
    for sequence, time_s in enumerate((1.1, 1.2, 1.3), 4):
        await runtime.handle_telemetry(telemetry(sequence, time_s, 12.0), time_s)
    _, payload = await pending
    alert = Alert.model_validate_json(payload)
    assert alert.event_id == "evt-1"
    assert (await repo.get_event("evt-1")) is not None

    await runtime.handle_command(
        Command(
            device_id="phone-01",
            action=CommandAction.acknowledge,
            request_id="ack-1",
            event_id="evt-1",
        ),
        1.4,
    )
    event = await repo.get_event("evt-1")
    assert event is not None and event.state is AlertState.acknowledged
    record = await repo.get_runtime_record("phone-01")
    assert record is not None and record.desired_armed is False
    await alert_stream.aclose()
    await bus.stop()
    await repo.stop()
