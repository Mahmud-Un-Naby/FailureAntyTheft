"""FastAPI REST, WebSocket, and static-dashboard application."""

import asyncio
import csv
import io
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from failureantytheft.collector import validate_sensor_url
from failureantytheft.contracts import Command, CommandAction, DeviceConfig
from failureantytheft.service import FailureAntyTheftService
from failureantytheft.topics import command_topic, parse_device_topic

STATIC_DIR = Path(__file__).with_name("static")


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    source_url: Annotated[str, Field(min_length=1, max_length=2048)]
    sensitivity: Annotated[float, Field(gt=0, le=100)] = 1.5
    enabled: bool = True


class DevicePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    source_url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    sensitivity: Annotated[float, Field(gt=0, le=100)] | None = None
    enabled: bool | None = None


def create_app(
    *,
    database_path: str | Path | None = None,
    transport: Literal["mqtt", "inproc"] | None = None,
    enable_collectors: bool = True,
) -> FastAPI:
    database: str | Path = (
        database_path
        if database_path is not None
        else os.environ.get("FAILUREANTYTHEFT_DB", "data/failureantytheft.sqlite3")
    )
    raw_transport = transport or os.getenv("FAILUREANTYTHEFT_TRANSPORT", "mqtt")
    if raw_transport not in {"mqtt", "inproc"}:
        raise ValueError("FAILUREANTYTHEFT_TRANSPORT must be mqtt or inproc")
    selected_transport = cast(Literal["mqtt", "inproc"], raw_transport)
    service = FailureAntyTheftService(
        database,
        transport=selected_transport,
        mqtt_host=os.getenv("FAILUREANTYTHEFT_MQTT_HOST", "127.0.0.1"),
        mqtt_port=int(os.getenv("FAILUREANTYTHEFT_MQTT_PORT", "1883")),
        enable_collectors=enable_collectors,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        await service.start()
        yield
        await service.stop()

    app = FastAPI(title="FailureAntyTheft", version="0.1.0", lifespan=lifespan)
    app.state.failureantytheft = service

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "ready": True,
            "transport": selected_transport,
            "device_count": len(service.runtimes),
            "time": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/devices")
    async def devices() -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for config in await service.repo.list_devices():
            state = await service.repo.get_runtime_record(config.device_id)
            item = config.model_dump(mode="json")
            item["runtime"] = state.model_dump(mode="json") if state else None
            result.append(item)
        return result

    @app.post("/api/devices", status_code=201)
    async def register(body: DeviceCreate) -> dict[str, object]:
        try:
            normalized_url = await validate_sensor_url(body.source_url)
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        config = DeviceConfig(
            device_id=body.device_id,
            name=body.name,
            source_url=normalized_url,
            enabled=body.enabled,
            sensitivity=body.sensitivity,
            created_at=datetime.now(UTC),
        )
        await service.add_device(config)
        return config.model_dump(mode="json")

    @app.patch("/api/devices/{device_id}")
    async def update_device(device_id: str, body: DevicePatch) -> dict[str, object]:
        current = await service.repo.get_device(device_id)
        if current is None:
            raise HTTPException(status_code=404, detail="unknown device")
        source_url = current.source_url
        if body.source_url is not None:
            try:
                source_url = await validate_sensor_url(body.source_url)
            except (OSError, ValueError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        config = DeviceConfig(
            device_id=current.device_id,
            name=body.name if body.name is not None else current.name,
            source_url=source_url,
            enabled=body.enabled if body.enabled is not None else current.enabled,
            sensitivity=(body.sensitivity if body.sensitivity is not None else current.sensitivity),
            created_at=current.created_at,
        )
        await service.add_device(config)
        return config.model_dump(mode="json")

    async def publish_command(
        device_id: str, action: CommandAction, event_id: str | None = None
    ) -> dict[str, str]:
        if device_id not in service.runtimes:
            raise HTTPException(status_code=404, detail="unknown device")
        request_id = f"req-{uuid4()}"
        command = Command(
            device_id=device_id, action=action, request_id=request_id, event_id=event_id
        )
        await service.bus.publish(command_topic(device_id), command.model_dump_json().encode())
        return {"status": "accepted", "request_id": request_id}

    @app.post("/api/devices/{device_id}/arm", status_code=202)
    async def arm(device_id: str) -> dict[str, str]:
        return await publish_command(device_id, CommandAction.arm)

    @app.post("/api/devices/{device_id}/disarm", status_code=202)
    async def disarm(device_id: str) -> dict[str, str]:
        return await publish_command(device_id, CommandAction.disarm)

    @app.get("/api/events")
    async def events(
        device_id: str | None = None, limit: int = Query(100, ge=1, le=1000)
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in await service.repo.list_events(device_id=device_id, limit=limit)
        ]

    @app.post("/api/events/{event_id}/acknowledge", status_code=202)
    async def acknowledge(event_id: str) -> dict[str, str]:
        event = await service.repo.get_event(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="unknown event")
        return await publish_command(event.device_id, CommandAction.acknowledge, event_id)

    @app.get("/api/events/export.csv")
    async def export_events() -> Response:
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(
            ["id", "device_id", "type", "severity", "state", "started_at", "acknowledged_at"]
        )
        for event in await service.repo.list_events(limit=1000):
            writer.writerow(
                [
                    event.event_id,
                    event.device_id,
                    event.type,
                    event.severity,
                    event.state,
                    event.started_at.isoformat(),
                    event.acknowledged_at.isoformat() if event.acknowledged_at else "",
                ]
            )
        return Response(
            stream.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=failureantytheft-events.csv"},
        )

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        selected: set[str] = set()
        subscription = service.bus.subscribe("failureantytheft/devices/#")

        async def receive() -> None:
            while True:
                message = await websocket.receive_json()
                if message.get("action") == "subscribe_chart" and isinstance(
                    message.get("device_id"), str
                ):
                    selected.clear()
                    selected.add(message["device_id"])

        async def send() -> None:
            async for topic, payload in subscription:
                try:
                    device_id, kind = parse_device_topic(topic)
                except ValueError:
                    continue
                if kind == "chart" and device_id not in selected:
                    continue
                if kind not in {"state", "alert", "chart"}:
                    continue
                await websocket.send_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "type": kind,
                            "server_time": datetime.now(UTC).isoformat(),
                            "payload": json.loads(payload),
                        }
                    )
                )

        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(receive())
                group.create_task(send())
        except* WebSocketDisconnect:
            pass

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


__all__ = ["create_app"]
