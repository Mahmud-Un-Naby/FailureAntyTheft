"""Client and parser for the official Phyphox remote HTTP interface."""

import math
from dataclasses import dataclass
from urllib.parse import quote

import httpx


@dataclass(frozen=True, slots=True)
class BufferNames:
    time: str = "acc_time"
    x: str = "accX"
    y: str = "accY"
    z: str = "accZ"


@dataclass(frozen=True, slots=True)
class RawSample:
    device_time_s: float
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class PollResult:
    session: str
    measuring: bool
    samples: tuple[RawSample, ...]


class PhyphoxClient:
    def __init__(
        self,
        base_url: str,
        *,
        buffers: BufferNames | None = None,
        timeout_s: float = 2.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.buffers = buffers or BufferNames()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_s, follow_redirects=False)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def poll(self, cursor: float | None) -> PollResult:
        query = self._query(cursor)
        response = await self._client.get(f"{self.base_url}/get?{query}")
        if response.is_redirect:
            raise ValueError("Phyphox redirects are not allowed")
        response.raise_for_status()
        return self.parse_response(response.json(), self.buffers)

    async def control(self, command: str) -> None:
        if command not in {"start", "stop", "clear"}:
            raise ValueError("unsupported Phyphox control command")
        response = await self._client.get(f"{self.base_url}/control", params={"cmd": command})
        if response.is_redirect:
            raise ValueError("Phyphox redirects are not allowed")
        response.raise_for_status()
        if response.json().get("result") is not True:
            raise RuntimeError(f"Phyphox rejected {command!r}")

    def _query(self, cursor: float | None) -> str:
        names = self.buffers
        if cursor is None:
            return "&".join(
                quote(name, safe="") for name in (names.time, names.x, names.y, names.z)
            )
        threshold = format(cursor, ".17g")
        time = quote(names.time, safe="")
        parts = [f"{time}={quote(threshold, safe='')}"]
        for name in (names.x, names.y, names.z):
            value = quote(f"{threshold}|{names.time}", safe="")
            parts.append(f"{quote(name, safe='')}={value}")
        return "&".join(parts)

    @staticmethod
    def parse_response(data: object, names: BufferNames) -> PollResult:
        if not isinstance(data, dict):
            raise ValueError("Phyphox response must be an object")
        buffers = data.get("buffer")
        status = data.get("status")
        if not isinstance(buffers, dict) or not isinstance(status, dict):
            raise ValueError("Phyphox response requires buffer and status objects")

        values: list[list[object]] = []
        for name in (names.time, names.x, names.y, names.z):
            entry = buffers.get(name)
            if not isinstance(entry, dict) or not isinstance(entry.get("buffer"), list):
                raise ValueError(f"missing Phyphox buffer {name!r}")
            values.append(entry["buffer"])
        lengths = {len(value) for value in values}
        if len(lengths) != 1:
            raise ValueError("Phyphox buffers are not aligned")

        samples: list[RawSample] = []
        for row in zip(*values, strict=True):
            if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in row):
                continue
            numeric = tuple(float(item) for item in row)
            if not all(math.isfinite(item) for item in numeric) or numeric[0] < 0:
                continue
            samples.append(RawSample(*numeric))
        session = status.get("session")
        measuring = status.get("measuring")
        if not isinstance(session, str) or not session:
            raise ValueError("Phyphox status has no session")
        if not isinstance(measuring, bool):
            raise ValueError("Phyphox status has invalid measuring flag")
        return PollResult(session=session, measuring=measuring, samples=tuple(samples))


__all__ = ["BufferNames", "PhyphoxClient", "PollResult", "RawSample"]
