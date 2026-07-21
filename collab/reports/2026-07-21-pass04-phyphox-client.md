# Pass 04 — Phyphox client and network safety

- Stage: 1 | Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: client/parser complete; collection manager and physical fixtures pending

## Understanding and scope

Implement against the official Phyphox REST shape rather than assumed streaming
behavior. Keep phone-specific buffer names configurable.

## Changes

- Added `/get` cursor queries using the time buffer as reference.
- Added aligned-buffer/session parsing and invalid-value filtering.
- Added start/stop/clear control calls with redirects disabled.
- Added private/link-local URL, scheme, credential, path, and port validation.
- Added HTTP/parser/security tests and the `httpx` dependency.

## Validation

Final project gate: 98 tests passed in 0.61s; Ruff, format check, and mypy all
passed.

## Cross-review and open items

Claude remained unavailable. Physical phone buffer names and `/config` output
are not available yet, so no real-phone fixture is claimed. The collection loop,
offline retry publication, and fixture recorder remain for the next pass.

## Next pass

Complete the collector manager and then build the FastAPI/WebSocket control
surface and dashboard.
