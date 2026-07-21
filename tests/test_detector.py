"""Deterministic tests for movement detection and state transitions."""

from datetime import UTC, datetime

import pytest

from failureantytheft.contracts import (
    Acceleration,
    Command,
    CommandAction,
    DeviceStateEnum,
    Telemetry,
)
from failureantytheft.detection import (
    AlertTriggered,
    CalibrationFailed,
    DetectorConfig,
    DeviceDetector,
    LinkChanged,
    SampleReceived,
    StateChanged,
    Tick,
)

NOW = datetime(2026, 7, 21, tzinfo=UTC)


def sample(sequence: int, device_time_s: float, z: float = 9.81) -> SampleReceived:
    return SampleReceived(
        Telemetry(
            device_id="phone-01",
            device_time_s=device_time_s,
            received_at=NOW,
            sequence=sequence,
            acceleration=Acceleration(x=0.0, y=0.0, z=z),
        )
    )


def command(action: CommandAction, *, event_id: str | None = None) -> Command:
    return Command(
        device_id="phone-01",
        action=action,
        request_id=f"req-{action}",
        event_id=event_id,
    )


def detector(**overrides: object) -> DeviceDetector:
    defaults: dict[str, object] = {
        "threshold": 1.0,
        "placement_delay_s": 1.0,
        "calibration_window_s": 1.0,
        "calibration_min_samples": 3,
        "calibration_max_stddev": 0.1,
        "ema_alpha": 1.0,
        "required_crossings": 3,
        "crossing_window_s": 0.5,
    }
    defaults.update(overrides)
    return DeviceDetector("phone-01", DetectorConfig(**defaults))  # type: ignore[arg-type]


def arm_and_calibrate(target: DeviceDetector) -> None:
    target.step(LinkChanged(True), now_s=0.0)
    target.step(command(CommandAction.arm), now_s=0.0)
    target.step(sample(1, 1.0), now_s=1.0)
    target.step(sample(2, 1.1), now_s=1.1)
    target.step(sample(3, 1.2), now_s=1.2)
    target.step(Tick(), now_s=2.0)
    assert target.state is DeviceStateEnum.armed


def transitions(outputs: list[object]) -> list[DeviceStateEnum]:
    return [item.current for item in outputs if isinstance(item, StateChanged)]


def test_connect_arm_calibrate() -> None:
    target = detector()
    assert transitions(target.step(LinkChanged(True), 0.0)) == [DeviceStateEnum.disarmed]
    assert transitions(target.step(command(CommandAction.arm), 0.0)) == [
        DeviceStateEnum.calibrating
    ]
    target.step(sample(1, 1.0), 1.0)
    target.step(sample(2, 1.1), 1.1)
    target.step(sample(3, 1.2), 1.2)
    assert transitions(target.step(Tick(), 2.0)) == [DeviceStateEnum.armed]
    assert target.baseline == pytest.approx(9.81)


def test_placement_delay_samples_do_not_calibrate() -> None:
    target = detector()
    target.step(LinkChanged(True), 0.0)
    target.step(command(CommandAction.arm), 0.0)
    target.step(sample(1, 0.1), 0.1)
    target.step(sample(2, 0.2), 0.2)
    outputs = target.step(Tick(), 2.0)
    failure = next(item for item in outputs if isinstance(item, CalibrationFailed))
    assert failure.reason == "insufficient_samples"
    assert failure.sample_count == 0
    assert target.state is DeviceStateEnum.disarmed
    assert target.desired_armed is False


def test_noisy_calibration_fails() -> None:
    target = detector(calibration_max_stddev=0.05)
    target.step(LinkChanged(True), 0.0)
    target.step(command(CommandAction.arm), 0.0)
    target.step(sample(1, 1.0, 9.0), 1.0)
    target.step(sample(2, 1.1, 10.0), 1.1)
    target.step(sample(3, 1.2, 11.0), 1.2)
    outputs = target.step(Tick(), 2.0)
    failure = next(item for item in outputs if isinstance(item, CalibrationFailed))
    assert failure.reason == "device_moving"
    assert failure.stddev is not None and failure.stddev > 0.05


def test_three_crossings_inside_window_trigger_one_alarm() -> None:
    target = detector()
    arm_and_calibrate(target)
    first = target.step(sample(4, 2.1, 12.0), 2.1)
    second = target.step(sample(5, 2.3, 12.0), 2.3)
    third = target.step(sample(6, 2.5, 12.0), 2.5)
    assert transitions(first) == [DeviceStateEnum.suspicious]
    assert transitions(second) == []
    assert transitions(third) == [DeviceStateEnum.alarm]
    assert len([item for item in third if isinstance(item, AlertTriggered)]) == 1
    assert not any(
        isinstance(item, AlertTriggered) for item in target.step(sample(7, 2.6, 12.0), 2.6)
    )


def test_crossings_outside_window_do_not_trigger() -> None:
    target = detector()
    arm_and_calibrate(target)
    target.step(sample(4, 2.1, 12.0), 2.1)
    target.step(sample(5, 2.7, 12.0), 2.7)
    outputs = target.step(sample(6, 3.3, 12.0), 3.3)
    assert target.state is DeviceStateEnum.suspicious
    assert not any(isinstance(item, AlertTriggered) for item in outputs)


def test_motion_subsides_from_suspicious() -> None:
    target = detector()
    arm_and_calibrate(target)
    target.step(sample(4, 2.1, 12.0), 2.1)
    outputs = target.step(sample(5, 2.2, 9.81), 2.2)
    assert transitions(outputs) == [DeviceStateEnum.armed]


def test_acknowledge_alarm_disarms() -> None:
    target = detector()
    arm_and_calibrate(target)
    target.step(sample(4, 2.1, 12.0), 2.1)
    target.step(sample(5, 2.2, 12.0), 2.2)
    target.step(sample(6, 2.3, 12.0), 2.3)
    outputs = target.step(command(CommandAction.acknowledge, event_id="evt-1"), 2.4)
    assert transitions(outputs) == [DeviceStateEnum.disarmed]
    assert target.desired_armed is False


def test_disconnect_preserves_intent_and_recalibrates_on_reconnect() -> None:
    target = detector()
    arm_and_calibrate(target)
    assert transitions(target.step(LinkChanged(False), 3.0)) == [DeviceStateEnum.offline]
    assert target.desired_armed is True
    assert transitions(target.step(LinkChanged(True), 4.0)) == [
        DeviceStateEnum.disarmed,
        DeviceStateEnum.calibrating,
    ]


def test_arm_while_offline_waits_for_link() -> None:
    target = detector()
    assert target.step(command(CommandAction.arm), 0.0) == []
    assert target.desired_armed is True
    assert transitions(target.step(LinkChanged(True), 1.0)) == [
        DeviceStateEnum.disarmed,
        DeviceStateEnum.calibrating,
    ]


def test_duplicate_and_stale_samples_are_ignored() -> None:
    target = detector()
    arm_and_calibrate(target)
    target.step(sample(4, 2.1, 12.0), 2.1)
    assert target.step(sample(4, 2.1, 12.0), 2.2) == []
    assert target.step(sample(5, 2.0, 12.0), 2.3) == []


def test_wrong_device_rejected() -> None:
    target = detector()
    wrong = Command(device_id="phone-02", action=CommandAction.arm, request_id="req-1")
    with pytest.raises(ValueError, match="does not match"):
        target.step(wrong, 0.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"threshold": 0.0},
        {"ema_alpha": 1.1},
        {"required_crossings": 0},
        {"placement_delay_s": -1.0},
    ],
)
def test_invalid_detector_config_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        detector(**kwargs)
