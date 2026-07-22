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

## Run

```bash
./run.sh
```

The launcher performs first-time setup, creates `.env`, installs dependencies,
starts the Docker MQTT broker when needed, and launches the server. On later
runs, use the same command. Open `http://localhost:8000`; API documentation is
at `http://localhost:8000/docs`.

To run without Docker or an MQTT broker:

```bash
./run.sh --inproc
```

For manual setup, use:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
docker compose up -d mosquitto
set -a
source .env
set +a
.venv/bin/failureantytheft
```

The application never silently falls back from MQTT; use `--inproc` explicitly
when that is the desired mode.

## Connect a phone

1. Open an accelerometer experiment in Phyphox.
2. Enable **Allow remote access**.
3. Keep the experiment running and the app in the foreground.
4. Register the displayed private URL with the **Add sensor** form on the
   dashboard (or through `POST /api/devices`). Android commonly uses port 8080;
   iPhone may use port 80.
5. If the experiment uses different buffer names, adjust `BufferNames` in the
   collector configuration before the physical demo. The current defaults are
   `acc_time`, `accX`, `accY`, and `accZ`, matching Phyphox's built-in
   **Acceleration with g** experiment. Confirm custom experiments against the
   phone's `/config` endpoint.

Example registration:

```bash
curl -X POST http://localhost:8000/api/devices \
  -H 'content-type: application/json' \
  -d '{"device_id":"phone-01","name":"Bag phone","source_url":"http://192.168.1.20:8080","sensitivity":1.5}'
```

## Operator workflow

1. Confirm the phone appears online.
2. Arm it. This also prepares browser audio; leave the phone still during
   placement/calibration. The header's **Sound on/off** control can test or mute
   the siren at any time.
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

## Presentation

The complete editable deck is at
`presentation/FailureAntyTheft-Presentation.pptx`, with a light-theme copy at
`presentation/FailureAntyTheft-Presentation-Light.pptx`. Its folder also
contains the content outline, embedded-notes source, presentation-day demo
checklist, official branding sources, assets, and a reproducible PptxGenJS build
script.

To rebuild it:

```bash
cd presentation
npm install
npm run build:all
```

## Physical acceptance check

The automated suite includes deterministic stationary and movement recordings,
but a final classroom setup still needs two real phones. Before the demo, confirm
each phone's buffer names through its Phyphox `/config` endpoint, then run the
two-phone checklist in `PROJECT_PLAN.md` section 21. This is the only validation
that cannot be completed without the intended phones and Wi-Fi network.
