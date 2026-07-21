"""Validated MQTT/bus topic construction and parsing.

All topic strings for FailureAntyTheft are built and parsed here so that device
identifiers are validated in exactly one place (reusing ``contracts.DEVICE_ID_RE``)
and topic layout never drifts between publishers and subscribers.

Layout::

    failureantytheft/devices/{device_id}/telemetry
    failureantytheft/devices/{device_id}/link
    failureantytheft/devices/{device_id}/command
    failureantytheft/devices/{device_id}/state
    failureantytheft/devices/{device_id}/alert
    failureantytheft/devices/{device_id}/chart
    failureantytheft/system/status
"""

from failureantytheft.contracts import DEVICE_ID_RE

TOPIC_ROOT = "failureantytheft"

# Per-device topic kinds (the final path segment).
TELEMETRY = "telemetry"
LINK = "link"
COMMAND = "command"
STATE = "state"
ALERT = "alert"
CHART = "chart"

DEVICE_TOPIC_KINDS: frozenset[str] = frozenset({TELEMETRY, LINK, COMMAND, STATE, ALERT, CHART})

SYSTEM_STATUS_TOPIC = f"{TOPIC_ROOT}/system/status"

_DEVICE_PREFIX = f"{TOPIC_ROOT}/devices/"
_MQTT_WILDCARD = "+"


def _require_safe_device_id(device_id: str) -> None:
    if DEVICE_ID_RE.fullmatch(device_id) is None:
        raise ValueError(f"unsafe device id: {device_id!r}")


def _require_known_kind(kind: str) -> None:
    if kind not in DEVICE_TOPIC_KINDS:
        raise ValueError(f"unknown device topic kind: {kind!r}")


def device_topic(device_id: str, kind: str) -> str:
    """Build a per-device topic for ``kind``, validating both inputs."""
    _require_safe_device_id(device_id)
    _require_known_kind(kind)
    return f"{_DEVICE_PREFIX}{device_id}/{kind}"


def telemetry_topic(device_id: str) -> str:
    return device_topic(device_id, TELEMETRY)


def link_topic(device_id: str) -> str:
    return device_topic(device_id, LINK)


def command_topic(device_id: str) -> str:
    return device_topic(device_id, COMMAND)


def state_topic(device_id: str) -> str:
    return device_topic(device_id, STATE)


def alert_topic(device_id: str) -> str:
    return device_topic(device_id, ALERT)


def chart_topic(device_id: str) -> str:
    return device_topic(device_id, CHART)


def device_wildcard(kind: str) -> str:
    """Build an MQTT subscription filter for ``kind`` across all devices."""
    _require_known_kind(kind)
    return f"{_DEVICE_PREFIX}{_MQTT_WILDCARD}/{kind}"


def parse_device_topic(topic: str) -> tuple[str, str]:
    """Parse a per-device topic into ``(device_id, kind)``.

    Raises ``ValueError`` for anything that is not a well-formed device topic with
    a safe device id and a known kind.
    """
    if not topic.startswith(_DEVICE_PREFIX):
        raise ValueError(f"not a device topic: {topic!r}")
    remainder = topic[len(_DEVICE_PREFIX) :]
    parts = remainder.split("/")
    if len(parts) != 2:
        raise ValueError(f"malformed device topic: {topic!r}")
    device_id, kind = parts
    _require_safe_device_id(device_id)
    _require_known_kind(kind)
    return device_id, kind


__all__ = [
    "TOPIC_ROOT",
    "TELEMETRY",
    "LINK",
    "COMMAND",
    "STATE",
    "ALERT",
    "CHART",
    "DEVICE_TOPIC_KINDS",
    "SYSTEM_STATUS_TOPIC",
    "device_topic",
    "telemetry_topic",
    "link_topic",
    "command_topic",
    "state_topic",
    "alert_topic",
    "chart_topic",
    "device_wildcard",
    "parse_device_topic",
]
