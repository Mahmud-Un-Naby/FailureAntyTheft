#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYPROJECT_MARKER="$VENV_DIR/.failureantytheft-pyproject.toml"
FORCE_INPROC=false

usage() {
    cat <<'EOF'
Usage: ./run.sh [--inproc]

Starts FailureAntyTheft and performs first-time setup automatically.

Options:
  --inproc  Run without Docker or an MQTT broker
  -h, --help  Show this help message
EOF
}

for argument in "$@"; do
    case "$argument" in
        --inproc)
            FORCE_INPROC=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $argument" >&2
            usage >&2
            exit 2
            ;;
    esac
done

cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3.11 or newer is required." >&2
    exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    echo "Error: Python 3.11 or newer is required." >&2
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Creating the Python environment..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    echo "Error: .venv uses an older Python version. Recreate it with Python 3.11+." >&2
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/failureantytheft" ]] \
    || [[ ! -f "$PYPROJECT_MARKER" ]] \
    || ! cmp -s pyproject.toml "$PYPROJECT_MARKER"; then
    echo "Installing project dependencies..."
    "$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -e ".[dev]"
    cp pyproject.toml "$PYPROJECT_MARKER"
fi

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example."
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ "$FORCE_INPROC" == true ]]; then
    export FAILUREANTYTHEFT_TRANSPORT=inproc
fi

TRANSPORT="${FAILUREANTYTHEFT_TRANSPORT:-mqtt}"
MQTT_HOST="${FAILUREANTYTHEFT_MQTT_HOST:-127.0.0.1}"
MQTT_PORT="${FAILUREANTYTHEFT_MQTT_PORT:-1883}"

broker_is_reachable() {
    "$VENV_DIR/bin/python" - "$MQTT_HOST" "$MQTT_PORT" <<'PY'
import socket
import sys

try:
    with socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=0.5):
        pass
except (OSError, ValueError):
    raise SystemExit(1)
PY
}

if [[ "$TRANSPORT" == mqtt ]] && ! broker_is_reachable; then
    if [[ "$MQTT_HOST" =~ ^(127\.0\.0\.1|localhost|::1)$ ]] \
        && [[ "$MQTT_PORT" == 1883 ]] \
        && command -v docker >/dev/null 2>&1 \
        && docker compose version >/dev/null 2>&1; then
        echo "Starting the MQTT broker..."
        docker compose up -d mosquitto
    else
        cat >&2 <<EOF
Error: the MQTT broker at $MQTT_HOST:$MQTT_PORT is unavailable.
Start the configured broker, install Docker, or run: ./run.sh --inproc
EOF
        exit 1
    fi
fi

echo "Starting FailureAntyTheft at http://localhost:8000"
exec "$VENV_DIR/bin/failureantytheft"
