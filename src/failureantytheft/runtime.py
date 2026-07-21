"""Side-effecting runtime wrapper around the pure device detector."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import uuid4

from failureantytheft.contracts import (
    Alert,
    AlertSeverity,
    AlertState,
    AlertType,
    ChartSample,
    Command,
    CommandAction,
    DeviceConfig,
    DeviceRuntimeRecord,
    DeviceState,
    EventRecord,
    LinkState,
    Telemetry,
)
from failureantytheft.detection import (
    AlertTriggered,
    ChartPoint,
    DetectorConfig,
    DetectorOutput,
    DeviceDetector,
    LinkChanged,
    SampleReceived,
    StateChanged,
    Tick,
)
from failureantytheft.ports import Bus, Repo
from failureantytheft.topics import alert_topic, chart_topic, state_topic


class DeviceRuntime:
    """Own persistence/publication for one device while the detector owns logic."""

    def __init__(
        self,
        config: DeviceConfig,
        bus: Bus,
        repo: Repo,
        *,
        detector_config: DetectorConfig | None = None,
        wall_clock: Callable[[], datetime] | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.config = config
        self.bus = bus
        self.repo = repo
        self.detector = DeviceDetector(
            config.device_id,
            detector_config or DetectorConfig(threshold=config.sensitivity),
        )
        self._wall_clock = wall_clock or (lambda: datetime.now(UTC))
        self._event_id_factory = event_id_factory or (lambda: f"evt-{uuid4()}")
        self._last_seen_at: datetime | None = None
        self._last_sample_time_s: float | None = None
        self._active_event_id: str | None = None
        self._processed_requests: set[str] = set()
        self._last_heartbeat_s = float("-inf")

    async def restore(self, now_s: float) -> None:
        record = await self.repo.get_runtime_record(self.config.device_id)
        if record and record.desired_armed:
            command = Command(
                device_id=self.config.device_id,
                action=CommandAction.arm,
                request_id="internal-restore",
            )
            await self._apply(command, now_s)
        await self._persist_and_publish_state()

    async def handle_link(self, link: LinkState, now_s: float) -> None:
        if link.device_id != self.config.device_id:
            raise ValueError("link device_id does not match runtime")
        if link.last_seen is not None:
            self._last_seen_at = link.last_seen
        was_armed = self.detector.desired_armed
        outputs = self.detector.step(LinkChanged(link.online), now_s)
        await self._handle_outputs(outputs)
        if not link.online and was_armed:
            await self._create_connectivity_warning()

    async def handle_telemetry(self, telemetry: Telemetry, now_s: float) -> None:
        self._last_seen_at = telemetry.received_at
        self._last_sample_time_s = telemetry.device_time_s
        await self._handle_outputs(self.detector.step(SampleReceived(telemetry), now_s))

    async def handle_command(self, command: Command, now_s: float) -> None:
        if command.device_id != self.config.device_id:
            raise ValueError("command device_id does not match runtime")
        if command.request_id in self._processed_requests:
            return
        self._processed_requests.add(command.request_id)

        if command.action is CommandAction.acknowledge:
            assert command.event_id is not None
            await self.repo.acknowledge_event(
                command.event_id, command.acknowledged_by, self._now()
            )
            event = await self.repo.get_event(command.event_id)
            if event is not None:
                await self._publish_alert_record(event)
            if command.event_id != self._active_event_id:
                return
            self._active_event_id = None
        await self._apply(command, now_s)

    async def tick(self, now_s: float) -> None:
        await self._handle_outputs(self.detector.step(Tick(), now_s))
        if now_s - self._last_heartbeat_s >= 1.0:
            await self._persist_and_publish_state()
            self._last_heartbeat_s = now_s

    async def _apply(self, command: Command, now_s: float) -> None:
        previous_state = self.detector.state
        previous_desired_armed = self.detector.desired_armed
        outputs = self.detector.step(command, now_s)
        await self._handle_outputs(outputs)
        changed_without_transition = (
            self.detector.state is not previous_state
            or self.detector.desired_armed != previous_desired_armed
        ) and not any(isinstance(output, StateChanged) for output in outputs)
        if changed_without_transition:
            await self._persist_and_publish_state()

    async def _handle_outputs(self, outputs: Sequence[DetectorOutput]) -> None:
        state_changed = False
        for output in outputs:
            if isinstance(output, StateChanged):
                state_changed = True
            elif isinstance(output, ChartPoint):
                chart = ChartSample(
                    device_id=self.config.device_id,
                    device_time_s=output.device_time_s,
                    magnitude=output.magnitude,
                    motion_score=output.motion_score,
                )
                await self.bus.publish(
                    chart_topic(self.config.device_id), chart.model_dump_json().encode()
                )
            elif isinstance(output, AlertTriggered):
                await self._create_movement_alert(output)
        if state_changed:
            await self._persist_and_publish_state()

    async def _persist_and_publish_state(self) -> None:
        now = self._now()
        await self.repo.save_runtime_record(
            DeviceRuntimeRecord(
                device_id=self.config.device_id,
                desired_armed=self.detector.desired_armed,
                last_state=self.detector.state,
                last_seen_at=self._last_seen_at,
                last_motion_score=self.detector.motion_score,
                updated_at=now,
            )
        )
        await self._publish_state(now)

    async def _publish_state(self, now: datetime | None = None) -> None:
        state = DeviceState(
            device_id=self.config.device_id,
            online=self.detector.online,
            state=self.detector.state,
            desired_armed=self.detector.desired_armed,
            motion_score=self.detector.motion_score,
            last_sample_time_s=self._last_sample_time_s,
            updated_at=now or self._now(),
        )
        await self.bus.publish(state_topic(self.config.device_id), state.model_dump_json().encode())

    async def _create_movement_alert(self, output: AlertTriggered) -> None:
        now = self._now()
        event_id = self._event_id_factory()
        self._active_event_id = event_id
        event = EventRecord(
            event_id=event_id,
            device_id=self.config.device_id,
            type=AlertType.movement_detected,
            severity=AlertSeverity.high,
            motion_score=output.motion_score,
            threshold=output.threshold,
            started_at=now,
            state=AlertState.active,
        )
        await self.repo.insert_event(event)
        await self._publish_alert_record(event)

    async def _create_connectivity_warning(self) -> None:
        event = EventRecord(
            event_id=self._event_id_factory(),
            device_id=self.config.device_id,
            type=AlertType.connectivity_warning,
            severity=AlertSeverity.warning,
            started_at=self._now(),
            state=AlertState.active,
        )
        await self.repo.insert_event(event)
        await self._publish_alert_record(event)

    async def _publish_alert_record(self, event: EventRecord) -> None:
        alert = Alert(
            event_id=event.event_id,
            device_id=event.device_id,
            type=event.type,
            severity=event.severity,
            motion_score=event.motion_score,
            threshold=event.threshold,
            started_at=event.started_at,
            state=event.state,
        )
        await self.bus.publish(alert_topic(self.config.device_id), alert.model_dump_json().encode())

    def _now(self) -> datetime:
        value = self._wall_clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("wall_clock must return a timezone-aware datetime")
        return value


__all__ = ["DeviceRuntime"]
