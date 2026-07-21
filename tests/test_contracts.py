"""Contract tests: serialization round-trips and rejection of malformed values."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from failurealert.contracts import (
    CONTRACTS_VERSION,
    WS_ENVELOPE_ADAPTER,
    Acceleration,
    Alert,
    AlertEnvelope,
    AlertSeverity,
    AlertState,
    AlertType,
    ChartSample,
    Command,
    CommandAction,
    DeviceConfig,
    DeviceRuntimeRecord,
    DeviceState,
    DeviceStateEnum,
    DeviceStateEnvelope,
    EventRecord,
    LinkState,
    SystemStatus,
    Telemetry,
    Transport,
)

NOW = datetime(2026, 7, 21, 10, 30, 14, tzinfo=UTC)


def _telemetry() -> Telemetry:
    return Telemetry(
        device_id="phone-01",
        device_time_s=12.5,
        received_at=NOW,
        sequence=1521,
        acceleration=Acceleration(x=0.12, y=-0.08, z=9.79),
    )


def _alert() -> Alert:
    return Alert(
        event_id="evt-1",
        device_id="phone-01",
        type=AlertType.movement_detected,
        severity=AlertSeverity.high,
        motion_score=3.64,
        threshold=1.5,
        started_at=NOW,
        state=AlertState.active,
    )


def _device_state() -> DeviceState:
    return DeviceState(
        device_id="phone-01",
        online=True,
        state=DeviceStateEnum.armed,
        desired_armed=True,
        motion_score=0.18,
        last_sample_time_s=12.5,
        updated_at=NOW,
    )


def test_contracts_version_is_one() -> None:
    assert CONTRACTS_VERSION == 1
    assert _telemetry().schema_version == 1


@pytest.mark.parametrize(
    "model",
    [
        _telemetry(),
        _alert(),
        _device_state(),
        LinkState(device_id="phone-01", online=True, last_seen=NOW, consecutive_failures=0),
        Command(device_id="phone-01", action=CommandAction.arm, request_id="req-1"),
        Command(
            device_id="phone-01",
            action=CommandAction.acknowledge,
            request_id="req-2",
            event_id="evt-1",
        ),
        ChartSample(device_id="phone-01", device_time_s=12.5, magnitude=9.81, motion_score=0.2),
        SystemStatus(
            ready=True,
            transport=Transport.mqtt,
            broker_connected=True,
            device_count=2,
            updated_at=NOW,
        ),
        DeviceConfig(
            device_id="phone-01",
            name="Bag phone",
            source_url="http://192.168.1.20:8080",
            sensitivity=1.5,
            created_at=NOW,
        ),
        DeviceRuntimeRecord(
            device_id="phone-01",
            desired_armed=True,
            last_state=DeviceStateEnum.armed,
            updated_at=NOW,
        ),
        EventRecord(
            event_id="evt-1",
            device_id="phone-01",
            type=AlertType.movement_detected,
            severity=AlertSeverity.high,
            motion_score=3.64,
            threshold=1.5,
            started_at=NOW,
            state=AlertState.active,
        ),
    ],
)
def test_json_round_trip(model: object) -> None:
    dumped = model.model_dump_json()  # type: ignore[attr-defined]
    restored = type(model).model_validate_json(dumped)  # type: ignore[attr-defined]
    assert restored == model


def test_models_are_frozen() -> None:
    telemetry = _telemetry()
    with pytest.raises(ValidationError):
        telemetry.device_id = "other"  # type: ignore[misc]


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Acceleration(x=0.0, y=0.0, z=9.8, extra=1)  # type: ignore[call-arg]


def test_naive_datetime_rejected() -> None:
    naive = datetime(2026, 7, 21, 10, 30, 14)  # noqa: DTZ001 - intentional
    with pytest.raises(ValidationError):
        DeviceState(
            device_id="phone-01",
            online=True,
            state=DeviceStateEnum.armed,
            desired_armed=True,
            motion_score=0.1,
            updated_at=naive,
        )


def test_non_utc_aware_datetime_accepted() -> None:
    dhaka = timezone(timedelta(hours=6))
    telemetry = _telemetry().model_copy(update={"received_at": NOW.astimezone(dhaka)})
    assert telemetry.received_at.utcoffset() == timedelta(hours=6)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_acceleration_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        Acceleration(x=bad, y=0.0, z=9.8)


def test_negative_device_time_rejected() -> None:
    with pytest.raises(ValidationError):
        ChartSample(device_id="phone-01", device_time_s=-0.1, magnitude=1.0, motion_score=0.0)


@pytest.mark.parametrize("bad_id", ["", "phone 01", "phone/01", "phone+01", "-phone", "a" * 65])
def test_invalid_device_id_rejected(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        LinkState(device_id=bad_id, online=True)


def test_max_length_device_id_accepted() -> None:
    ok = "a" * 64
    assert LinkState(device_id=ok, online=True, last_seen=NOW).device_id == ok


def test_acknowledge_requires_event_id() -> None:
    with pytest.raises(ValidationError):
        Command(device_id="phone-01", action=CommandAction.acknowledge, request_id="req-1")


def test_event_id_forbidden_for_non_acknowledge() -> None:
    with pytest.raises(ValidationError):
        Command(
            device_id="phone-01",
            action=CommandAction.arm,
            request_id="req-1",
            event_id="evt-1",
        )


def test_acknowledged_by_forbidden_for_non_acknowledge() -> None:
    with pytest.raises(ValidationError):
        Command(
            device_id="phone-01",
            action=CommandAction.disarm,
            request_id="req-1",
            acknowledged_by="operator",
        )


def test_acknowledge_allows_acknowledged_by() -> None:
    command = Command(
        device_id="phone-01",
        action=CommandAction.acknowledge,
        request_id="req-1",
        event_id="evt-1",
        acknowledged_by="operator",
    )
    assert command.acknowledged_by == "operator"


def test_whitespace_only_string_rejected() -> None:
    with pytest.raises(ValidationError):
        Command(device_id="phone-01", action=CommandAction.arm, request_id="   ")


def test_online_link_requires_last_seen() -> None:
    with pytest.raises(ValidationError):
        LinkState(device_id="phone-01", online=True)


@pytest.mark.parametrize(
    ("online", "state"),
    [(True, DeviceStateEnum.offline), (False, DeviceStateEnum.armed)],
)
def test_device_online_state_must_be_consistent(online: bool, state: DeviceStateEnum) -> None:
    with pytest.raises(ValidationError):
        DeviceState(
            device_id="phone-01",
            online=online,
            state=state,
            desired_armed=False,
            motion_score=0.0,
            updated_at=NOW,
        )


def test_movement_alert_requires_metrics() -> None:
    with pytest.raises(ValidationError):
        Alert(
            event_id="evt-1",
            device_id="phone-01",
            type=AlertType.movement_detected,
            severity=AlertSeverity.high,
            started_at=NOW,
            state=AlertState.active,
        )


def test_connectivity_alert_forbids_movement_metrics() -> None:
    with pytest.raises(ValidationError):
        Alert(
            event_id="evt-1",
            device_id="phone-01",
            type=AlertType.connectivity_warning,
            severity=AlertSeverity.warning,
            motion_score=1.0,
            started_at=NOW,
            state=AlertState.active,
        )


def test_zero_sensitivity_rejected() -> None:
    with pytest.raises(ValidationError):
        DeviceConfig(
            device_id="phone-01",
            name="Bag phone",
            source_url="http://192.168.1.20:8080",
            sensitivity=0.0,
            created_at=NOW,
        )


def test_mqtt_status_requires_broker_state() -> None:
    with pytest.raises(ValidationError):
        SystemStatus(ready=False, transport=Transport.mqtt, updated_at=NOW)


def test_inproc_status_forbids_broker_state() -> None:
    with pytest.raises(ValidationError):
        SystemStatus(
            ready=True,
            transport=Transport.inproc,
            broker_connected=True,
            updated_at=NOW,
        )


def test_acknowledged_event_requires_acknowledged_at() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            event_id="evt-1",
            device_id="phone-01",
            type=AlertType.connectivity_warning,
            severity=AlertSeverity.warning,
            started_at=NOW,
            state=AlertState.acknowledged,
        )


def test_active_event_forbids_acknowledgement_metadata() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            event_id="evt-1",
            device_id="phone-01",
            type=AlertType.connectivity_warning,
            severity=AlertSeverity.warning,
            started_at=NOW,
            state=AlertState.active,
            acknowledged_at=NOW,
        )


def test_ws_envelope_discriminated_round_trip() -> None:
    envelope = AlertEnvelope(server_time=NOW, payload=_alert())
    restored = WS_ENVELOPE_ADAPTER.validate_json(envelope.model_dump_json())
    assert isinstance(restored, AlertEnvelope)
    assert restored == envelope


def test_ws_envelope_selects_correct_variant() -> None:
    envelope = DeviceStateEnvelope(server_time=NOW, payload=_device_state())
    restored = WS_ENVELOPE_ADAPTER.validate_json(envelope.model_dump_json())
    assert isinstance(restored, DeviceStateEnvelope)


def test_ws_envelope_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        WS_ENVELOPE_ADAPTER.validate_python({"type": "mystery", "server_time": NOW, "payload": {}})
