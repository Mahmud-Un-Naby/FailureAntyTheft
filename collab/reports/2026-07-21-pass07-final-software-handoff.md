# Pass 07 — Final software handoff

- Stage: final verification | Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: software ready; physical two-phone acceptance pending

## What Claude understood and completed

Claude and Codex agreed on the architecture, pass-by-pass workflow, contract
boundary, detector behavior, runtime/persistence split, MQTT-first deployment,
and user-facing reporting format. Claude authored the early architecture and
contract work, then reached his session limit. The user explicitly instructed
Codex to finish independently. Earlier reports preserve the exact handoff.

## What Codex completed

Codex reviewed and finished the executable contracts, pure detector, runtime,
SQLite repository, in-process and MQTT buses, Phyphox parsing/client/collector,
private-network validation, FastAPI REST/WebSocket service, complete dashboard,
Mosquitto deployment, replay fixtures, documentation, and regression tests.

## Final evidence

- Full suite: **104 passed, 1 skipped** in 2.94 seconds. The skip is the
  environment-gated live MQTT test, which was run separately and passed.
- Coverage: **84%** overall; detector 94%, contracts/repository 98%, runtime 90%,
  API 87%. MQTT's default coverage number excludes its separately executed live
  broker test.
- Live MQTT round-trip: **1 passed** against Mosquitto 2.
- Live broker restart: reconnect and resubscription passed.
- Ruff lint/format: passed. Strict mypy: passed. Python compilation and browser
  JavaScript syntax: passed. Git whitespace check: passed.
- Real-socket Uvicorn smoke: health 200, dashboard 200.
- Compose validation: passed.
- Wheel build: passed; the wheel contains Python modules and all dashboard
  HTML/CSS/JavaScript assets.

One upstream `StarletteDeprecationWarning` reports that FastAPI's current test
client still imports the deprecated httpx compatibility surface. It does not
affect runtime behavior or test results.

## Agreement, confusion, and limitations

There is no unresolved Claude/Codex disagreement. The software is ready to run.
The whole project, under `PROJECT_PLAN.md`'s Definition of Done, still needs two
real phones on the intended private network to confirm `/config` buffer names
and complete stationary, movement, offline/recovery, simultaneous-device, and
15-minute stability checks. Synthetic fixtures are clearly labelled as such and
are not represented as physical evidence.

## User's next acceptance session

Follow the README to start Mosquitto and FailureAlert, register both displayed
Phyphox URLs in the dashboard, confirm their buffers, then execute section 21 of
`PROJECT_PLAN.md`. Record the results in a new report so the project can be
truthfully marked fully ready.
