"""Topic construction/parsing tests, including rejection of unsafe device ids."""

import pytest

from failurealert import topics


def test_build_expected_topics() -> None:
    assert topics.telemetry_topic("phone-01") == "failurealert/devices/phone-01/telemetry"
    assert topics.link_topic("phone-01") == "failurealert/devices/phone-01/link"
    assert topics.command_topic("phone-01") == "failurealert/devices/phone-01/command"
    assert topics.state_topic("phone-01") == "failurealert/devices/phone-01/state"
    assert topics.alert_topic("phone-01") == "failurealert/devices/phone-01/alert"
    assert topics.chart_topic("phone-01") == "failurealert/devices/phone-01/chart"


def test_system_status_constant() -> None:
    assert topics.SYSTEM_STATUS_TOPIC == "failurealert/system/status"


def test_wildcard_topic() -> None:
    assert topics.device_wildcard(topics.TELEMETRY) == "failurealert/devices/+/telemetry"


@pytest.mark.parametrize("kind", sorted(topics.DEVICE_TOPIC_KINDS))
def test_round_trip_parse(kind: str) -> None:
    topic = topics.device_topic("phone-01", kind)
    assert topics.parse_device_topic(topic) == ("phone-01", kind)


@pytest.mark.parametrize(
    "bad_id", ["", "phone 01", "phone/01", "phone+01", "-phone", "phone-01\n", "a" * 65]
)
def test_build_rejects_unsafe_device_id(bad_id: str) -> None:
    with pytest.raises(ValueError):
        topics.telemetry_topic(bad_id)


def test_build_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        topics.device_topic("phone-01", "bogus")


@pytest.mark.parametrize(
    "topic",
    [
        "failurealert/system/status",
        "failurealert/devices/phone-01",
        "failurealert/devices/phone-01/telemetry/extra",
        "failurealert/devices/phone 01/telemetry",
        "failurealert/devices/phone-01/bogus",
        "other/devices/phone-01/telemetry",
    ],
)
def test_parse_rejects_malformed_topics(topic: str) -> None:
    with pytest.raises(ValueError):
        topics.parse_device_topic(topic)
