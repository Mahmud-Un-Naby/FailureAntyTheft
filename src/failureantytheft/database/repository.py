"""Async SQLite implementation of the repository port."""

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import aiosqlite

from failureantytheft.contracts import (
    AlertSeverity,
    AlertState,
    AlertType,
    DeviceConfig,
    DeviceRuntimeRecord,
    DeviceStateEnum,
    EventRecord,
)


class SQLiteRepo:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._db: aiosqlite.Connection | None = None

    async def start(self) -> None:
        if self._db is not None:
            return
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        cursor = await self._db.execute("PRAGMA journal_mode=WAL")
        await cursor.close()
        cursor = await self._db.execute("PRAGMA foreign_keys=ON")
        await cursor.close()

    async def stop(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    def _connection(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("repository is not started")
        return self._db

    async def init_schema(self) -> None:
        db = self._connection()
        cursor = await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                sensitivity REAL NOT NULL CHECK (sensitivity > 0),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS device_state (
                device_id TEXT PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
                desired_armed INTEGER NOT NULL CHECK (desired_armed IN (0, 1)),
                last_state TEXT NOT NULL,
                last_seen_at TEXT,
                last_motion_score REAL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                motion_score REAL,
                threshold REAL,
                started_at TEXT NOT NULL,
                state TEXT NOT NULL,
                acknowledged_at TEXT,
                acknowledged_by TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_device_started
                ON events(device_id, started_at DESC);
            """
        )
        await cursor.close()
        await db.commit()

    async def get_device(self, device_id: str) -> DeviceConfig | None:
        cursor = await self._connection().execute(
            "SELECT * FROM devices WHERE id = ?", (device_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        return self._device(row) if row else None

    async def list_devices(self) -> Sequence[DeviceConfig]:
        cursor = await self._connection().execute("SELECT * FROM devices ORDER BY created_at, id")
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._device(row) for row in rows]

    async def upsert_device(self, config: DeviceConfig) -> None:
        db = self._connection()
        cursor = await db.execute(
            """INSERT INTO devices (id, name, source_url, enabled, sensitivity, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                 source_url=excluded.source_url, enabled=excluded.enabled,
                 sensitivity=excluded.sensitivity""",
            (
                config.device_id,
                config.name,
                config.source_url,
                config.enabled,
                config.sensitivity,
                config.created_at.isoformat(),
            ),
        )
        await cursor.close()
        await db.commit()

    async def get_runtime_record(self, device_id: str) -> DeviceRuntimeRecord | None:
        cursor = await self._connection().execute(
            "SELECT * FROM device_state WHERE device_id = ?", (device_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        return self._runtime(row) if row else None

    async def save_runtime_record(self, record: DeviceRuntimeRecord) -> None:
        db = self._connection()
        cursor = await db.execute(
            """INSERT INTO device_state
               (device_id, desired_armed, last_state, last_seen_at, last_motion_score, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(device_id) DO UPDATE SET
                 desired_armed=excluded.desired_armed, last_state=excluded.last_state,
                 last_seen_at=excluded.last_seen_at,
                 last_motion_score=excluded.last_motion_score, updated_at=excluded.updated_at""",
            (
                record.device_id,
                record.desired_armed,
                record.last_state.value,
                record.last_seen_at.isoformat() if record.last_seen_at else None,
                record.last_motion_score,
                record.updated_at.isoformat(),
            ),
        )
        await cursor.close()
        await db.commit()

    async def insert_event(self, event: EventRecord) -> None:
        db = self._connection()
        cursor = await db.execute(
            """INSERT OR IGNORE INTO events
               (id, device_id, event_type, severity, motion_score, threshold,
                started_at, state, acknowledged_at, acknowledged_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.device_id,
                event.type.value,
                event.severity.value,
                event.motion_score,
                event.threshold,
                event.started_at.isoformat(),
                event.state.value,
                event.acknowledged_at.isoformat() if event.acknowledged_at else None,
                event.acknowledged_by,
            ),
        )
        await cursor.close()
        await db.commit()

    async def get_event(self, event_id: str) -> EventRecord | None:
        cursor = await self._connection().execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = await cursor.fetchone()
        await cursor.close()
        return self._event(row) if row else None

    async def acknowledge_event(
        self, event_id: str, acknowledged_by: str | None, acknowledged_at: datetime
    ) -> None:
        db = self._connection()
        cursor = await db.execute(
            """UPDATE events SET state = ?, acknowledged_at = ?, acknowledged_by = ?
               WHERE id = ? AND state = ?""",
            (
                AlertState.acknowledged.value,
                acknowledged_at.isoformat(),
                acknowledged_by,
                event_id,
                AlertState.active.value,
            ),
        )
        await cursor.close()
        await db.commit()

    async def list_events(
        self, *, device_id: str | None = None, limit: int = 100
    ) -> Sequence[EventRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        db = self._connection()
        if device_id is None:
            cursor = await db.execute(
                "SELECT * FROM events ORDER BY started_at DESC, id DESC LIMIT ?", (limit,)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM events WHERE device_id = ?
                   ORDER BY started_at DESC, id DESC LIMIT ?""",
                (device_id, limit),
            )
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._event(row) for row in rows]

    @staticmethod
    def _device(row: aiosqlite.Row) -> DeviceConfig:
        return DeviceConfig(
            device_id=row["id"],
            name=row["name"],
            source_url=row["source_url"],
            enabled=bool(row["enabled"]),
            sensitivity=row["sensitivity"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _runtime(row: aiosqlite.Row) -> DeviceRuntimeRecord:
        return DeviceRuntimeRecord(
            device_id=row["device_id"],
            desired_armed=bool(row["desired_armed"]),
            last_state=DeviceStateEnum(row["last_state"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"])
            if row["last_seen_at"]
            else None,
            last_motion_score=row["last_motion_score"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _event(row: aiosqlite.Row) -> EventRecord:
        return EventRecord(
            event_id=row["id"],
            device_id=row["device_id"],
            type=AlertType(row["event_type"]),
            severity=AlertSeverity(row["severity"]),
            motion_score=row["motion_score"],
            threshold=row["threshold"],
            started_at=datetime.fromisoformat(row["started_at"]),
            state=AlertState(row["state"]),
            acknowledged_at=datetime.fromisoformat(row["acknowledged_at"])
            if row["acknowledged_at"]
            else None,
            acknowledged_by=row["acknowledged_by"],
        )


__all__ = ["SQLiteRepo"]
