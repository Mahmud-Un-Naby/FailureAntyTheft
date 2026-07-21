from datetime import UTC, datetime, timedelta

import pytest

from failureantytheft.contracts import (
    AlertSeverity,
    AlertState,
    AlertType,
    DeviceConfig,
    DeviceRuntimeRecord,
    DeviceStateEnum,
    EventRecord,
)
from failureantytheft.database import SQLiteRepo

NOW = datetime(2026, 7, 21, tzinfo=UTC)


@pytest.mark.asyncio
async def test_repository_round_trip_and_acknowledgement(tmp_path: object) -> None:
    path = tmp_path / "test.sqlite"  # type: ignore[operator]
    repo = SQLiteRepo(path)
    await repo.start()
    await repo.init_schema()
    device = DeviceConfig(
        device_id="phone-01",
        name="Bag",
        source_url="http://192.168.1.2:8080",
        sensitivity=1.5,
        created_at=NOW,
    )
    await repo.upsert_device(device)
    assert await repo.get_device("phone-01") == device

    runtime = DeviceRuntimeRecord(
        device_id="phone-01",
        desired_armed=True,
        last_state=DeviceStateEnum.armed,
        last_seen_at=NOW,
        last_motion_score=0.2,
        updated_at=NOW,
    )
    await repo.save_runtime_record(runtime)
    assert await repo.get_runtime_record("phone-01") == runtime

    event = EventRecord(
        event_id="evt-1",
        device_id="phone-01",
        type=AlertType.movement_detected,
        severity=AlertSeverity.high,
        motion_score=2.0,
        threshold=1.5,
        started_at=NOW,
        state=AlertState.active,
    )
    await repo.insert_event(event)
    ack_time = NOW + timedelta(seconds=1)
    await repo.acknowledge_event("evt-1", "operator", ack_time)
    stored = await repo.get_event("evt-1")
    assert stored is not None
    assert stored.state is AlertState.acknowledged
    assert stored.acknowledged_at == ack_time
    assert list(await repo.list_events(device_id="phone-01")) == [stored]
    await repo.stop()


@pytest.mark.asyncio
async def test_repository_requires_start(tmp_path: object) -> None:
    repo = SQLiteRepo(tmp_path / "test.sqlite")  # type: ignore[operator]
    with pytest.raises(RuntimeError, match="not started"):
        await repo.init_schema()
