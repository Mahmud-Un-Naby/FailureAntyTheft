# FailureAlert decision ledger

This file records decisions ratified by the user, Claude, and Codex. Detailed
design rationale lives in `ARCHITECTURE.md`; per-pass evidence and disagreements
live in `collab/reports/`.

## D-001 — Three-person collaboration

- Date: 2026-07-21
- Status: ratified

The user, Claude, and Codex work as one team. A named owner is the primary
editor, not an isolated module owner. Before every implementation pass, Claude
and Codex exchange current context and agree on scope, contracts, and acceptance
checks. After every pass, the non-editing agent reviews the actual changes and
both explicitly agree before advancing.

## D-002 — User-facing Claude reports

- Date: 2026-07-21
- Status: ratified

Claude creates one report per completed pass in `collab/reports/` using the
filename `YYYY-MM-DD-passNN-short-slug.md`. A report states Claude's
understanding, scope, changes, contract impact, real validation evidence,
cross-review findings, disagreements or decisions needed from the user, and the
next proposed pass. The final report produced in a working session also serves
as its session close-out.

## D-003 — Disagreement handling

- Date: 2026-07-21
- Status: ratified

Resolved disagreements are recorded in the pass report. An unresolved issue
that changes requirements, architecture, contracts, safety, or user-visible
behavior blocks the next pass and is escalated to the user. Minor implementation
choices may be resolved jointly without interrupting the user.

## D-004 — Architecture baseline

- Date: 2026-07-21
- Status: ratified

`ARCHITECTURE.md` is the current architecture baseline. Its principal decisions
are a single FastAPI/asyncio process, a pure detector wrapped by a per-device
runtime, SQLite configuration/runtime-state separation, MQTT as the final MVP's
default transport, explicit-only in-process fallback, asynchronous commands,
and collector/runtime single-writer boundaries.

## D-005 — Implementation authorization

- Date: 2026-07-21
- Status: ratified

The user authorized implementation and installation of required dependencies.
If Claude reaches a session or usage limit, Codex must tell the user promptly so
the user can continue the remaining work with Codex.

## D-006 — Executable contract v1

- Date: 2026-07-21
- Status: accepted by Codex under the user-authorized Claude-limit fallback;
  Claude retrospective review pending

Pass 01 freezes strict Pydantic v1 payloads, topic helpers, and signature-only
ports. Device time is experiment-relative seconds, server datetimes are
timezone-aware, every bus/WS payload carries `schema_version=1`, and device
commands contain a device ID in addition to their topic routing identity.

Claude authored the initial pass but reached its session limit before reviewing
the correction set. Codex completed the review and validation. The exact
handoff and validation evidence are recorded in
`collab/reports/2026-07-21-pass01-contracts.md`.

## D-007 — Pure detector behavior

- Date: 2026-07-21
- Status: accepted by Codex under the user-authorized Claude-limit fallback

The detector is pure and timer-injected. It calibrates after placement delay,
rejects insufficient or noisy baselines, filters magnitudes with an EMA, and
requires configured crossings inside a device-time window. Acknowledgement
disarms. Disconnect preserves durable armed intent and reconnect always starts
fresh calibration. Evidence is in
`collab/reports/2026-07-21-pass02-detector.md`.

## D-008 — Runtime and persistence boundary

- Date: 2026-07-21
- Status: accepted by Codex under Claude-limit fallback

`DeviceRuntime` owns detector side effects, SQLite stores configuration/runtime
state/events, and `InProcBus` provides MQTT-style fan-out for tests and explicit
fallback. Details are in the Pass 03 report.

## D-009 — Phyphox pull protocol

- Date: 2026-07-21
- Status: accepted by Codex under Claude-limit fallback

The collector uses Phyphox `/get` as a buffered pull API. Subsequent XYZ reads
use the experiment-time buffer as their threshold reference; phone buffer names
remain configurable and must be confirmed during the physical feasibility test.

## D-010 — Collector, service, and control surface

- Date: 2026-07-21
- Status: accepted by Codex under Claude-limit fallback

One resilient asynchronous collector runs per enabled device. The FastAPI
lifespan owns the repository, bus, collector, and runtime tasks. REST commands
travel through the same bus path used by MQTT, WebSocket publishes live state,
chart, and alert envelopes, and the dashboard supplies registration, individual
and global arm/disarm, alarm acknowledgement, history, CSV export, and audible
alerts. Details are in the Pass 05 report.

## D-011 — MQTT is the production-default transport

- Date: 2026-07-21
- Status: accepted by Codex under Claude-limit fallback

Mosquitto is the documented default. `MqttBus` supervises its connection,
resubscribes after reconnect, uses QoS 0 for replaceable telemetry/chart data,
QoS 1 for state/commands/alerts, and retains link/state messages. In-process
transport remains explicit-only for development and tests. A live broker
round-trip and an actual broker-restart test passed. Details are in Pass 06.

## D-012 — Software handoff versus physical acceptance

- Date: 2026-07-21
- Status: software accepted; physical acceptance pending user hardware

The implementation and automated/software integration gates are complete.
The project must not be described as satisfying its full Definition of Done
until two real phones have confirmed their Phyphox buffer names and passed the
private-LAN stationary, motion, disconnect/reconnect, and concurrent-device
checks. This is an external validation dependency, not an unresolved Claude/
Codex disagreement. Details are in Pass 07.
