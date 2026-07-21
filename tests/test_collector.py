import httpx
import pytest

from failureantytheft.collector import BufferNames, PhyphoxClient, validate_sensor_url


def response() -> dict[str, object]:
    return {
        "buffer": {
            "t": {"size": 100, "updateMode": "partial", "buffer": [1.0, 1.1]},
            "accX": {"size": 100, "updateMode": "partial", "buffer": [0.1, 0.2]},
            "accY": {"size": 100, "updateMode": "partial", "buffer": [0.0, 0.1]},
            "accZ": {"size": 100, "updateMode": "partial", "buffer": [9.8, 9.7]},
        },
        "status": {"session": "abc", "measuring": True},
    }


def test_parse_aligned_phyphox_response() -> None:
    result = PhyphoxClient.parse_response(response(), BufferNames())
    assert result.session == "abc"
    assert len(result.samples) == 2
    assert result.samples[-1].device_time_s == 1.1


def test_parse_rejects_unaligned_buffers() -> None:
    data = response()
    data["buffer"]["accX"]["buffer"] = [0.1]  # type: ignore[index]
    with pytest.raises(ValueError, match="not aligned"):
        PhyphoxClient.parse_response(data, BufferNames())


@pytest.mark.asyncio
async def test_poll_uses_reference_cursor() -> None:
    seen_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_url
        seen_url = str(request.url)
        return httpx.Response(200, json=response())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    phyphox = PhyphoxClient("http://192.168.1.2:8080", client=client)
    await phyphox.poll(1.0)
    assert "accX=1%7Ct" in seen_url
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://192.168.1.2:8080",
        "http://127.0.0.1:8080",
        "http://224.0.0.1:8080",
        "http://192.168.1.2:9999",
        "http://user:pass@192.168.1.2:8080",
        "http://192.168.1.2:8080/get",
    ],
)
async def test_sensor_url_rejects_unsafe_destinations(url: str) -> None:
    with pytest.raises(ValueError):
        await validate_sensor_url(url)


@pytest.mark.asyncio
async def test_sensor_url_accepts_private_address() -> None:
    assert await validate_sensor_url("http://192.168.1.2:8080/") == "http://192.168.1.2:8080"
