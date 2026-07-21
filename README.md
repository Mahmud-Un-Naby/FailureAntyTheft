# FailureAntyTheft

FailureAntyTheft uses phones running Phyphox as Wi-Fi motion sensors. A local Python
server calibrates each phone, detects sustained movement, stores alerts in
SQLite, and updates a browser dashboard over WebSocket.

This is a classroom prototype for a trusted private LAN, not a certified
security system.

## Requirements

- Python 3.11 or newer
- Docker (recommended) or a local Mosquitto 2.x broker
- Phyphox on one or more phones
- All devices connected to the same private Wi-Fi/hotspot

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

Start the broker:

```bash
docker compose up -d mosquitto
```

Load the environment and start the application:

```bash
set -a
source .env
set +a
.venv/bin/failureantytheft
```

Open `http://localhost:8000`. API documentation is at
`http://localhost:8000/docs`.

For development without a broker, explicitly set
`FAILUREANTYTHEFT_TRANSPORT=inproc`. The application never silently falls back from
MQTT.

## Connect a phone

1. Open an accelerometer experiment in Phyphox.
2. Enable **Allow remote access**.
3. Keep the experiment running and the app in the foreground.
4. Register the displayed private URL with the **Add sensor** form on the
   dashboard (or through `POST /api/devices`). Android commonly uses port 8080;
   iPhone may use port 80.
5. If the experiment uses different buffer names, adjust `BufferNames` in the
   collector configuration before the physical demo. The current defaults are
   `t`, `accX`, `accY`, and `accZ` and must be confirmed against `/config` on the
   actual phones.

Example registration:

```bash
curl -X POST http://localhost:8000/api/devices \
  -H 'content-type: application/json' \
  -d '{"device_id":"phone-01","name":"Bag phone","source_url":"http://192.168.1.20:8080","sensitivity":1.5}'
```

## Operator workflow

1. Confirm the phone appears online.
2. Arm it. Leave it still during placement/calibration.
3. Move the protected object. The dashboard shows and sounds an alarm.
4. Acknowledge the event; this disarms the device. Re-arm manually when safe.

## Quality checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
```

Architecture, decisions, and per-pass reports are in `ARCHITECTURE.md` and
`collab/`.

## Physical acceptance check

The automated suite includes deterministic stationary and movement recordings,
but a final classroom setup still needs two real phones. Before the demo, confirm
each phone's buffer names through its Phyphox `/config` endpoint, then run the
two-phone checklist in `PROJECT_PLAN.md` section 21. This is the only validation
that cannot be completed without the intended phones and Wi-Fi network.
