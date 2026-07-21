# Pass 06 — MQTT integration and hardening

- Stage: 4–5 | Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: complete under the user-authorized Claude-limit fallback

## Understanding and scope

The final MVP must use real MQTT by default, fail visibly if its broker is not
available at startup, and recover from a temporary broker interruption without
changing the contracts used by tests or the explicit in-process transport.

## Changes

- Added a supervised `aiomqtt` transport with reconnect, resubscription, local
  wildcard fan-out, bounded subscriber queues, message-class QoS, and retained
  link/state publication.
- Added Mosquitto 2 configuration and Docker Compose startup.
- Isolated malformed external messages so one bad payload cannot stop routing
  for every device.
- Persisted and published initial runtime state and one-second heartbeats.
- Fixed device-edit collector replacement and offline arm/disarm intent
  persistence.
- Added deterministic stationary/movement JSONL replay fixtures and tests.

## Validation

- Live Mosquitto publish/subscribe: passed.
- Broker restart while the client remained alive: `INITIAL_OK`, broker restart,
  then `RECONNECT_OK`; reconnect and resubscription passed.
- Docker Compose configuration: valid.
- The temporary test container was stopped and auto-removed afterward.

## Cross-review and open items

Claude remained unavailable. No design disagreement is pending. The broker is
configured for anonymous access only because the MVP is explicitly restricted
to a trusted private LAN; public exposure remains prohibited.

## Next pass

Run complete tests, coverage, static analysis, server and wheel smoke checks,
then produce the honest readiness handoff.
