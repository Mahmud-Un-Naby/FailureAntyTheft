"""Replay recorded-shape JSONL data through the pure detector."""

import json
from datetime import UTC, datetime
from pathlib import Path

from failureantytheft.contracts import Acceleration, Command, CommandAction, Telemetry
from failureantytheft.detection import (
    AlertTriggered,
    DetectorConfig,
    DeviceDetector,
    LinkChanged,
    SampleReceived,
    Tick,
)

FIXTURES = Path(__file__).with_name("fixtures")
NOW = datetime(2026, 7, 21, tzinfo=UTC)


def load_samples(name: str, first_sequence: int) -> list[SampleReceived]:
    result: list[SampleReceived] = []
    for offset, line in enumerate((FIXTURES / name).read_text().splitlines()):
        raw = json.loads(line)
        result.append(
            SampleReceived(
                Telemetry(
                    device_id="phone-01",
                    device_time_s=raw["device_time_s"],
                    received_at=NOW,
                    sequence=first_sequence + offset,
                    acceleration=Acceleration(x=raw["x"], y=raw["y"], z=raw["z"]),
                )
            )
        )
    return result


def test_stationary_then_movement_replay_triggers_once() -> None:
    detector = DeviceDetector(
        "phone-01",
        DetectorConfig(
            threshold=1.0,
            placement_delay_s=0.0,
            calibration_window_s=0.5,
            calibration_min_samples=5,
            calibration_max_stddev=0.1,
            ema_alpha=1.0,
            required_crossings=3,
            crossing_window_s=0.5,
        ),
    )
    detector.step(LinkChanged(True), 0.0)
    detector.step(
        Command(device_id="phone-01", action=CommandAction.arm, request_id="replay-arm"),
        0.0,
    )
    for sample in load_samples("stationary.jsonl", 1):
        detector.step(sample, sample.telemetry.device_time_s)
    detector.step(Tick(), 0.5)

    alerts = []
    for sample in load_samples("movement.jsonl", 7):
        alerts.extend(detector.step(sample, sample.telemetry.device_time_s))

    assert len([output for output in alerts if isinstance(output, AlertTriggered)]) == 1
