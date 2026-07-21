"""Frozen shared contracts for FailureAntyTheft (Pass 01).

These are the versioned, strict Pydantic v2 models exchanged over the bus and the
WebSocket gateway, plus the minimal persistence models referenced by the ``Repo``
protocol. Design rationale lives in ``ARCHITECTURE.md`` (see sections 4 and 6).

Conventions ratified for this pass:

* Every model is strict, forbids extra fields, and is immutable (``frozen``).
* Every bus/WebSocket payload carries ``schema_version`` (see ``CONTRACTS_VERSION``).
* ``device_time_s`` is an experiment-relative, finite, non-negative number of
  seconds reported by Phyphox, NOT a wall-clock timestamp. Server-generated times
  (``received_at``, ``updated_at``, ``started_at``, ...) are timezone-aware datetimes.
* Device identifiers are validated by a single shared pattern, reused by ``topics``.
"""

import math
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

CONTRACTS_VERSION: Final[Literal[1]] = 1

# --------------------------------------------------------------------------- #
# Shared constrained types and validators
# --------------------------------------------------------------------------- #

#: Single source of truth for safe device identifiers. Reused by ``topics``.
DEVICE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
DEVICE_ID_RE = re.compile(DEVICE_ID_PATTERN)


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("must be a finite number")
    return value


def _finite_non_negative(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("must be a finite number")
    if value < 0:
        raise ValueError("must be non-negative")
    return value


def _finite_positive(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("must be a finite number")
    if value <= 0:
        raise ValueError("must be positive")
    return value


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("datetime must be timezone-aware")
    return value


FiniteFloat = Annotated[float, AfterValidator(_finite)]
NonNegFiniteFloat = Annotated[float, AfterValidator(_finite_non_negative)]
PositiveFiniteFloat = Annotated[float, AfterValidator(_finite_positive)]
AwareDatetime = Annotated[datetime, AfterValidator(_aware)]
DeviceId = Annotated[str, StringConstraints(pattern=DEVICE_ID_PATTERN)]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #


class DeviceStateEnum(StrEnum):
    offline = "offline"
    disarmed = "disarmed"
    calibrating = "calibrating"
    armed = "armed"
    suspicious = "suspicious"
    alarm = "alarm"


class CommandAction(StrEnum):
    arm = "arm"
    disarm = "disarm"
    acknowledge = "acknowledge"


class AlertType(StrEnum):
    movement_detected = "movement_detected"
    connectivity_warning = "connectivity_warning"


class AlertSeverity(StrEnum):
    info = "info"
    warning = "warning"
    high = "high"


class AlertState(StrEnum):
    active = "active"
    acknowledged = "acknowledged"


class Transport(StrEnum):
    mqtt = "mqtt"
    inproc = "inproc"


# --------------------------------------------------------------------------- #
# Base models
# --------------------------------------------------------------------------- #


class _StrictModel(BaseModel):
    """Strict, immutable base: no coercion, no extra fields, frozen."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class _VersionedModel(_StrictModel):
    """A strict model that carries an explicit schema version."""

    schema_version: Literal[1] = CONTRACTS_VERSION


# --------------------------------------------------------------------------- #
# Bus payloads
# --------------------------------------------------------------------------- #


class Acceleration(_StrictModel):
    """A single accelerometer sample. Nested inside :class:`Telemetry`."""

    x: FiniteFloat
    y: FiniteFloat
    z: FiniteFloat
    unit: Literal["m/s2"] = "m/s2"


class Telemetry(_VersionedModel):
    """One normalized accelerometer sample (topic ``.../telemetry``).

    The collector splits each buffered Phyphox poll into individual samples, so a
    ``Telemetry`` message always carries exactly one reading.
    """

    device_id: DeviceId
    device_time_s: NonNegFiniteFloat
    received_at: AwareDatetime
    sequence: NonNegativeInt
    acceleration: Acceleration


class LinkState(_VersionedModel):
    """Collector-owned connectivity facts (topic ``.../link``)."""

    device_id: DeviceId
    online: bool
    last_seen: AwareDatetime | None = None
    consecutive_failures: NonNegativeInt = 0

    @model_validator(mode="after")
    def _check_online_last_seen(self) -> "LinkState":
        if self.online and self.last_seen is None:
            raise ValueError("last_seen is required when online is true")
        return self


class Command(_VersionedModel):
    """An operator command routed to a device runtime (topic ``.../command``).

    The device identity is repeated in the payload so consumers can reject a
    topic/payload mismatch. ``event_id`` is required only for ``acknowledge``
    and forbidden otherwise; ``acknowledged_by`` is optional and permitted only
    for ``acknowledge``.
    """

    device_id: DeviceId
    action: CommandAction
    request_id: NonEmptyStr
    event_id: NonEmptyStr | None = None
    acknowledged_by: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _check_acknowledge_fields(self) -> "Command":
        if self.action is CommandAction.acknowledge:
            if self.event_id is None:
                raise ValueError("event_id is required for the acknowledge action")
        else:
            if self.event_id is not None:
                raise ValueError("event_id is only valid for the acknowledge action")
            if self.acknowledged_by is not None:
                raise ValueError("acknowledged_by is only valid for the acknowledge action")
        return self


class DeviceState(_VersionedModel):
    """Runtime-owned unified operational view (topic ``.../state``)."""

    device_id: DeviceId
    online: bool
    state: DeviceStateEnum
    desired_armed: bool
    motion_score: NonNegFiniteFloat
    last_sample_time_s: NonNegFiniteFloat | None = None
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def _check_online_state(self) -> "DeviceState":
        if self.online == (self.state is DeviceStateEnum.offline):
            raise ValueError("online must be false exactly when state is offline")
        return self


class Alert(_VersionedModel):
    """Runtime-owned alert notification (topic ``.../alert``)."""

    event_id: NonEmptyStr
    device_id: DeviceId
    type: AlertType
    severity: AlertSeverity
    motion_score: NonNegFiniteFloat | None = None
    threshold: PositiveFiniteFloat | None = None
    started_at: AwareDatetime
    state: AlertState

    @model_validator(mode="after")
    def _check_type_metrics(self) -> "Alert":
        if self.type is AlertType.movement_detected:
            if self.motion_score is None or self.threshold is None:
                raise ValueError("movement alerts require motion_score and threshold")
        elif self.motion_score is not None or self.threshold is not None:
            raise ValueError("connectivity warnings cannot include movement metrics")
        return self


class ChartSample(_VersionedModel):
    """Chart-ready sample for subscribed dashboards (topic ``.../chart``)."""

    device_id: DeviceId
    device_time_s: NonNegFiniteFloat
    magnitude: NonNegFiniteFloat
    motion_score: NonNegFiniteFloat


class SystemStatus(_VersionedModel):
    """Server/broker health (topic ``failureantytheft/system/status``)."""

    ready: bool
    transport: Transport
    broker_connected: bool | None = None
    device_count: NonNegativeInt = 0
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def _check_transport_status(self) -> "SystemStatus":
        if self.transport is Transport.mqtt and self.broker_connected is None:
            raise ValueError("broker_connected is required for MQTT transport")
        if self.transport is Transport.inproc and self.broker_connected is not None:
            raise ValueError("broker_connected must be null for in-process transport")
        return self


# --------------------------------------------------------------------------- #
# Persistence models (referenced by the Repo protocol)
# --------------------------------------------------------------------------- #


class DeviceConfig(_StrictModel):
    """API/registration-owned device configuration.

    ``source_url`` is stored verbatim here; SSRF/allow-list validation is owned by
    the collector/API pass and is intentionally out of scope for these contracts.
    """

    device_id: DeviceId
    name: NonEmptyStr
    source_url: NonEmptyStr
    enabled: bool = True
    sensitivity: PositiveFiniteFloat
    created_at: AwareDatetime


class DeviceRuntimeRecord(_StrictModel):
    """Runtime-owned durable state. ``last_state`` is a display/audit snapshot and is
    never trusted to restore a device directly to ``armed`` on restart."""

    device_id: DeviceId
    desired_armed: bool
    last_state: DeviceStateEnum
    last_seen_at: AwareDatetime | None = None
    last_motion_score: NonNegFiniteFloat | None = None
    updated_at: AwareDatetime


class EventRecord(_StrictModel):
    """Persisted event history: movement alerts and connectivity warnings, plus
    acknowledgement metadata written by the runtime."""

    event_id: NonEmptyStr
    device_id: DeviceId
    type: AlertType
    severity: AlertSeverity
    motion_score: NonNegFiniteFloat | None = None
    threshold: PositiveFiniteFloat | None = None
    started_at: AwareDatetime
    state: AlertState
    acknowledged_at: AwareDatetime | None = None
    acknowledged_by: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _check_event_consistency(self) -> "EventRecord":
        if self.type is AlertType.movement_detected:
            if self.motion_score is None or self.threshold is None:
                raise ValueError("movement events require motion_score and threshold")
        elif self.motion_score is not None or self.threshold is not None:
            raise ValueError("connectivity events cannot include movement metrics")

        if self.state is AlertState.acknowledged:
            if self.acknowledged_at is None:
                raise ValueError("acknowledged events require acknowledged_at")
        elif self.acknowledged_at is not None or self.acknowledged_by is not None:
            raise ValueError("active events cannot include acknowledgement metadata")
        return self


# --------------------------------------------------------------------------- #
# WebSocket envelopes (top-level discriminated union)
# --------------------------------------------------------------------------- #


class _EnvelopeBase(_VersionedModel):
    server_time: AwareDatetime


class DeviceStateEnvelope(_EnvelopeBase):
    type: Literal["device_state"] = "device_state"
    payload: DeviceState


class AlertEnvelope(_EnvelopeBase):
    type: Literal["alert"] = "alert"
    payload: Alert


class ChartEnvelope(_EnvelopeBase):
    type: Literal["chart"] = "chart"
    payload: ChartSample


class SystemEnvelope(_EnvelopeBase):
    type: Literal["system_status"] = "system_status"
    payload: SystemStatus


#: The WebSocket message type: a discriminated union keyed by the envelope ``type``.
WsEnvelope = Annotated[
    DeviceStateEnvelope | AlertEnvelope | ChartEnvelope | SystemEnvelope,
    Field(discriminator="type"),
]

#: Validator/serializer for the ``WsEnvelope`` union (use for round-tripping).
WS_ENVELOPE_ADAPTER: TypeAdapter[
    DeviceStateEnvelope | AlertEnvelope | ChartEnvelope | SystemEnvelope
] = TypeAdapter(WsEnvelope)


__all__ = [
    "CONTRACTS_VERSION",
    "DEVICE_ID_PATTERN",
    "DEVICE_ID_RE",
    "DeviceId",
    "NonEmptyStr",
    "PositiveFiniteFloat",
    "DeviceStateEnum",
    "CommandAction",
    "AlertType",
    "AlertSeverity",
    "AlertState",
    "Transport",
    "Acceleration",
    "Telemetry",
    "LinkState",
    "Command",
    "DeviceState",
    "Alert",
    "ChartSample",
    "SystemStatus",
    "DeviceConfig",
    "DeviceRuntimeRecord",
    "EventRecord",
    "DeviceStateEnvelope",
    "AlertEnvelope",
    "ChartEnvelope",
    "SystemEnvelope",
    "WsEnvelope",
    "WS_ENVELOPE_ADAPTER",
]
