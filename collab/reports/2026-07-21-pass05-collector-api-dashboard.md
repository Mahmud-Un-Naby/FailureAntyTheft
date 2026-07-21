# Pass 05 — Collector, API, and dashboard

- Stage: 2–3 | Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: complete under the user-authorized Claude-limit fallback

## Understanding and scope

Complete one integrated vertical path rather than isolated modules: a registered
Phyphox phone is polled, normalized telemetry enters the shared bus, the runtime
detects and persists state/events, and every browser sees live results and can
send commands.

## Changes

- Added a resilient collector task per enabled device, cursor/session handling,
  online/offline publication, failure thresholds, and automatic retry.
- Added lifecycle coordination for SQLite, bus routing, runtimes, collectors,
  periodic ticks, device creation, and safe collector replacement after edits.
- Added registration/edit, health, arm/disarm, event acknowledgement/history,
  and CSV REST endpoints.
- Added the WebSocket state/alert/chart gateway and static dashboard.
- Added sensor cards, registration, per-device and global controls, live chart,
  alarm banner/sound, event table, acknowledgement, and CSV download.
- Added private-network URL validation at registration and connection time.

## Validation

API, WebSocket, collector, security, persistence, runtime, and dashboard-serving
paths are covered by automated tests. A real-socket Uvicorn smoke check returned
HTTP 200 for both `/api/health` and `/`.

## Cross-review and open items

Claude had reached his session limit and the user explicitly directed Codex to
continue alone. No Claude/Codex disagreement is pending. Physical Phyphox buffer
names remain deliberately unclaimed until checked on the actual phones.

## Next pass

Make MQTT the verified default, exercise reconnect behavior, then run all final
quality and packaging gates.
