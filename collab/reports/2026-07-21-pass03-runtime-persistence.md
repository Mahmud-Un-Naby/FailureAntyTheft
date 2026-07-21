# Pass 03 — Runtime, in-process bus, and persistence

- Stage: 1 | Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: completed under Claude-limit fallback

## Understanding and scope

Wrap the pure detector with durable/published side effects while preserving
single-writer boundaries. Add a test/fallback bus and SQLite implementation.

## Changes

- Added MQTT-filter-compatible `InProcBus` fan-out.
- Added SQLite WAL schema/repository for devices, runtime state, and events.
- Added `DeviceRuntime` for state persistence, chart/state/alert publication,
  command idempotency, alert creation, and acknowledgement.
- Added repository, bus, and runtime integration tests.

## Validation

Final gate after fixing leaked SQLite cursors: 88 tests passed; Ruff, formatting,
and mypy passed. SQLite tests require running outside the restricted sandbox
because `aiosqlite` uses a worker thread.

## Cross-review and open items

Claude remained unavailable. Codex reviewed resource cleanup, topic/payload
identity, acknowledgement behavior, and restart intent. No user decision is
needed.

## Next pass

Implement the validated Phyphox HTTP client and collector safety boundary.
