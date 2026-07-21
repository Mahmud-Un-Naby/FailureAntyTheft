"""Application coordinator: lifecycle, routing, runtimes, and collectors."""

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

from failurealert.collector import DeviceCollector
from failurealert.contracts import Command, DeviceConfig, LinkState, Telemetry
from failurealert.database import SQLiteRepo
from failurealert.messaging import InProcBus, MqttBus
from failurealert.ports import Bus
from failurealert.runtime import DeviceRuntime
from failurealert.topics import COMMAND, LINK, TELEMETRY, parse_device_topic


class FailureAlertService:
    def __init__(
        self,
        database_path: str | Path,
        *,
        transport: str = "mqtt",
        mqtt_host: str = "127.0.0.1",
        mqtt_port: int = 1883,
        enable_collectors: bool = True,
        bus: Bus | None = None,
    ) -> None:
        self.repo = SQLiteRepo(database_path)
        self.bus = bus or (MqttBus(mqtt_host, mqtt_port) if transport == "mqtt" else InProcBus())
        self.transport = transport
        self.enable_collectors = enable_collectors
        self.runtimes: dict[str, DeviceRuntime] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._collector_tasks: dict[str, asyncio.Task[None]] = {}
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        await self.repo.start()
        await self.repo.init_schema()
        await self.bus.start()
        self._tasks = [
            asyncio.create_task(self._route_inputs()),
            asyncio.create_task(self._tick_runtimes()),
        ]
        await asyncio.sleep(0)
        for config in await self.repo.list_devices():
            await self.add_device(config)

    async def stop(self) -> None:
        self._stop.set()
        for task in [*self._collector_tasks.values(), *self._tasks]:
            task.cancel()
        await asyncio.gather(*self._collector_tasks.values(), *self._tasks, return_exceptions=True)
        self._collector_tasks.clear()
        self._tasks.clear()
        await self.bus.stop()
        await self.repo.stop()

    async def add_device(self, config: DeviceConfig) -> DeviceRuntime:
        await self.repo.upsert_device(config)
        old_task = self._collector_tasks.pop(config.device_id, None)
        if old_task:
            old_task.cancel()
            await asyncio.gather(old_task, return_exceptions=True)
        runtime = DeviceRuntime(config, self.bus, self.repo)
        self.runtimes[config.device_id] = runtime
        await runtime.restore(time.monotonic())
        if self.enable_collectors and config.enabled:
            collector = DeviceCollector(config, self.bus)
            self._collector_tasks[config.device_id] = asyncio.create_task(collector.run(self._stop))
        return runtime

    async def _route_inputs(self) -> None:
        subscription = self.bus.subscribe("failurealert/devices/#")
        async for topic, payload in subscription:
            try:
                device_id, kind = parse_device_topic(topic)
            except ValueError:
                continue
            runtime = self.runtimes.get(device_id)
            if runtime is None:
                continue
            now_s = time.monotonic()
            try:
                if kind == TELEMETRY:
                    await runtime.handle_telemetry(Telemetry.model_validate_json(payload), now_s)
                elif kind == LINK:
                    await runtime.handle_link(LinkState.model_validate_json(payload), now_s)
                elif kind == COMMAND:
                    await runtime.handle_command(Command.model_validate_json(payload), now_s)
            except ValueError:
                # One malformed external message must not stop every device.
                continue

    async def _tick_runtimes(self) -> None:
        while not self._stop.is_set():
            now_s = time.monotonic()
            for runtime in tuple(self.runtimes.values()):
                await runtime.tick(now_s)
            await asyncio.sleep(0.1)

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)


__all__ = ["FailureAlertService"]
