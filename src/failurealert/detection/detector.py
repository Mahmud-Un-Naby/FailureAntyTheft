"""Deterministic per-device movement detector.

The detector has no I/O and never reads the wall or monotonic clock itself.
Callers supply monotonic ``now_s`` values and domain inputs to :meth:`step`.
This keeps calibration, filtering, and state transitions fully replayable.
"""

import math
import statistics
from collections import deque
from dataclasses import dataclass
from typing import TypeAlias

from failurealert.contracts import Command, CommandAction, DeviceId, DeviceStateEnum, Telemetry


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    threshold: float
    placement_delay_s: float = 5.0
    calibration_window_s: float = 2.0
    calibration_min_samples: int = 10
    calibration_max_stddev: float = 0.15
    ema_alpha: float = 0.35
    required_crossings: int = 3
    crossing_window_s: float = 0.5

    def __post_init__(self) -> None:
        positive = {
            "threshold": self.threshold,
            "calibration_window_s": self.calibration_window_s,
            "calibration_max_stddev": self.calibration_max_stddev,
            "ema_alpha": self.ema_alpha,
            "crossing_window_s": self.crossing_window_s,
        }
        for name, value in positive.items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.placement_delay_s) or self.placement_delay_s < 0:
            raise ValueError("placement_delay_s must be finite and non-negative")
        if self.ema_alpha > 1:
            raise ValueError("ema_alpha cannot exceed 1")
        if self.calibration_min_samples < 1:
            raise ValueError("calibration_min_samples must be at least 1")
        if self.required_crossings < 1:
            raise ValueError("required_crossings must be at least 1")


@dataclass(frozen=True, slots=True)
class SampleReceived:
    telemetry: Telemetry


@dataclass(frozen=True, slots=True)
class LinkChanged:
    online: bool


@dataclass(frozen=True, slots=True)
class Tick:
    """Advance timer-driven behavior without requiring a sensor sample."""


DetectorInput: TypeAlias = SampleReceived | LinkChanged | Tick | Command


@dataclass(frozen=True, slots=True)
class StateChanged:
    previous: DeviceStateEnum
    current: DeviceStateEnum
    desired_armed: bool


@dataclass(frozen=True, slots=True)
class ChartPoint:
    device_time_s: float
    magnitude: float
    motion_score: float


@dataclass(frozen=True, slots=True)
class AlertTriggered:
    device_time_s: float
    motion_score: float
    threshold: float


@dataclass(frozen=True, slots=True)
class CalibrationFailed:
    reason: str
    sample_count: int
    stddev: float | None


DetectorOutput: TypeAlias = StateChanged | ChartPoint | AlertTriggered | CalibrationFailed


class DeviceDetector:
    """Pure state machine for one configured device."""

    def __init__(self, device_id: DeviceId, config: DetectorConfig) -> None:
        self.device_id = device_id
        self.config = config
        self.state = DeviceStateEnum.offline
        self.online = False
        self.desired_armed = False
        self.motion_score = 0.0
        self.baseline: float | None = None

        self._calibration_collect_at: float | None = None
        self._calibration_finish_at: float | None = None
        self._calibration_values: list[float] = []
        self._filtered_magnitude: float | None = None
        self._crossings: deque[float] = deque()
        self._last_sequence: int | None = None
        self._last_device_time_s: float | None = None

    def step(self, event: DetectorInput, now_s: float) -> list[DetectorOutput]:
        if not math.isfinite(now_s) or now_s < 0:
            raise ValueError("now_s must be finite and non-negative")
        if isinstance(event, LinkChanged):
            return self._on_link(event.online, now_s)
        if isinstance(event, Command):
            return self._on_command(event, now_s)
        if isinstance(event, SampleReceived):
            return self._on_sample(event.telemetry, now_s)
        return self._on_tick(now_s)

    def _transition(self, state: DeviceStateEnum) -> StateChanged | None:
        if state is self.state:
            return None
        previous = self.state
        self.state = state
        return StateChanged(previous=previous, current=state, desired_armed=self.desired_armed)

    def _on_link(self, online: bool, now_s: float) -> list[DetectorOutput]:
        outputs: list[DetectorOutput] = []
        self.online = online
        if not online:
            self._reset_signal_state(reset_sequence=True)
            transition = self._transition(DeviceStateEnum.offline)
            if transition:
                outputs.append(transition)
            return outputs

        if self.state is DeviceStateEnum.offline:
            transition = self._transition(DeviceStateEnum.disarmed)
            if transition:
                outputs.append(transition)
            if self.desired_armed:
                outputs.extend(self._start_calibration(now_s))
        return outputs

    def _on_command(self, command: Command, now_s: float) -> list[DetectorOutput]:
        if command.device_id != self.device_id:
            raise ValueError("command device_id does not match detector")

        if command.action is CommandAction.arm:
            self.desired_armed = True
            if not self.online:
                return []
            return self._start_calibration(now_s)

        if command.action is CommandAction.disarm:
            self.desired_armed = False
            self._reset_signal_state(reset_sequence=False)
            target = DeviceStateEnum.disarmed if self.online else DeviceStateEnum.offline
            transition = self._transition(target)
            return [transition] if transition else []

        # Acknowledgement changes live state only for an active alarm. Historical
        # acknowledgement persistence is handled by DeviceRuntime.
        if self.state is not DeviceStateEnum.alarm:
            return []
        self.desired_armed = False
        self._reset_signal_state(reset_sequence=False)
        transition = self._transition(DeviceStateEnum.disarmed)
        return [transition] if transition else []

    def _start_calibration(self, now_s: float) -> list[DetectorOutput]:
        self._reset_signal_state(reset_sequence=False)
        self._calibration_collect_at = now_s + self.config.placement_delay_s
        self._calibration_finish_at = (
            self._calibration_collect_at + self.config.calibration_window_s
        )
        transition = self._transition(DeviceStateEnum.calibrating)
        return [transition] if transition else []

    def _on_tick(self, now_s: float) -> list[DetectorOutput]:
        if self.state is not DeviceStateEnum.calibrating:
            return []
        finish_at = self._calibration_finish_at
        if finish_at is None or now_s < finish_at:
            return []
        return self._finish_calibration()

    def _on_sample(self, telemetry: Telemetry, now_s: float) -> list[DetectorOutput]:
        if telemetry.device_id != self.device_id:
            raise ValueError("telemetry device_id does not match detector")
        if not self.online:
            return []
        if self._is_duplicate_or_stale(telemetry):
            return []

        self._last_sequence = telemetry.sequence
        self._last_device_time_s = telemetry.device_time_s
        magnitude = math.sqrt(
            telemetry.acceleration.x**2 + telemetry.acceleration.y**2 + telemetry.acceleration.z**2
        )

        if self.state is DeviceStateEnum.calibrating:
            collect_at = self._calibration_collect_at
            finish_at = self._calibration_finish_at
            if collect_at is not None and finish_at is not None:
                if collect_at <= now_s <= finish_at:
                    self._calibration_values.append(magnitude)
                if now_s >= finish_at:
                    return self._finish_calibration()
            return []

        if self.state not in {
            DeviceStateEnum.armed,
            DeviceStateEnum.suspicious,
            DeviceStateEnum.alarm,
        }:
            return []
        if self.baseline is None:
            raise RuntimeError("armed detector has no calibration baseline")

        alpha = self.config.ema_alpha
        if self._filtered_magnitude is None:
            self._filtered_magnitude = magnitude
        else:
            self._filtered_magnitude = alpha * magnitude + (1 - alpha) * self._filtered_magnitude
        self.motion_score = abs(self._filtered_magnitude - self.baseline)
        outputs: list[DetectorOutput] = [
            ChartPoint(
                device_time_s=telemetry.device_time_s,
                magnitude=magnitude,
                motion_score=self.motion_score,
            )
        ]

        if self.state is DeviceStateEnum.alarm:
            return outputs
        if self.motion_score > self.config.threshold:
            cutoff = telemetry.device_time_s - self.config.crossing_window_s
            self._crossings.append(telemetry.device_time_s)
            while self._crossings and self._crossings[0] < cutoff:
                self._crossings.popleft()
            transition = self._transition(DeviceStateEnum.suspicious)
            if transition:
                outputs.append(transition)
            if len(self._crossings) >= self.config.required_crossings:
                alarm_transition = self._transition(DeviceStateEnum.alarm)
                if alarm_transition:
                    outputs.append(alarm_transition)
                outputs.append(
                    AlertTriggered(
                        device_time_s=telemetry.device_time_s,
                        motion_score=self.motion_score,
                        threshold=self.config.threshold,
                    )
                )
        else:
            self._crossings.clear()
            transition = self._transition(DeviceStateEnum.armed)
            if transition:
                outputs.append(transition)
        return outputs

    def _finish_calibration(self) -> list[DetectorOutput]:
        values = self._calibration_values
        stddev = statistics.pstdev(values) if len(values) >= 2 else None
        failure: str | None = None
        if len(values) < self.config.calibration_min_samples:
            failure = "insufficient_samples"
        elif stddev is None or stddev > self.config.calibration_max_stddev:
            failure = "device_moving"

        if failure is not None:
            self.desired_armed = False
            transition = self._transition(DeviceStateEnum.disarmed)
            self._reset_signal_state(reset_sequence=False)
            outputs: list[DetectorOutput] = [
                CalibrationFailed(reason=failure, sample_count=len(values), stddev=stddev)
            ]
            if transition:
                outputs.insert(0, transition)
            return outputs

        self.baseline = statistics.median(values)
        self._filtered_magnitude = self.baseline
        self.motion_score = 0.0
        self._calibration_values = []
        self._calibration_collect_at = None
        self._calibration_finish_at = None
        transition = self._transition(DeviceStateEnum.armed)
        return [transition] if transition else []

    def _is_duplicate_or_stale(self, telemetry: Telemetry) -> bool:
        if self._last_sequence is not None and telemetry.sequence <= self._last_sequence:
            return True
        return (
            self._last_device_time_s is not None
            and telemetry.device_time_s <= self._last_device_time_s
        )

    def _reset_signal_state(self, *, reset_sequence: bool) -> None:
        self.motion_score = 0.0
        self.baseline = None
        self._calibration_collect_at = None
        self._calibration_finish_at = None
        self._calibration_values = []
        self._filtered_magnitude = None
        self._crossings.clear()
        if reset_sequence:
            self._last_sequence = None
            self._last_device_time_s = None


__all__ = [
    "AlertTriggered",
    "CalibrationFailed",
    "ChartPoint",
    "DetectorConfig",
    "DetectorInput",
    "DetectorOutput",
    "DeviceDetector",
    "LinkChanged",
    "SampleReceived",
    "StateChanged",
    "Tick",
]
