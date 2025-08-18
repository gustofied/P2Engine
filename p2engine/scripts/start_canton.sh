#!/usr/bin/env bash
set -euo pipefail

# Colors
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

# Ensure log dir exists
mkdir -p logs/canton

# --- Resolve Canton path (prefer standalone, then legacy-in-SDK) ---
CANTON_PATH="${CANTON_PATH:-}"
if [[ -z "${CANTON_PATH}" ]]; then
  if [[ -n "${CANTON_BIN:-}" && -x "${CANTON_BIN}" ]]; then
    CANTON_PATH="$CANTON_BIN"
  elif [[ -n "${CANTON_HOME:-}" && -x "${CANTON_HOME}/bin/canton" ]]; then
    CANTON_PATH="$CANTON_HOME/bin/canton"
  elif [[ -n "${CANTON_JAR:-}" && -f "${CANTON_JAR}" ]]; then
    CANTON_PATH="$CANTON_JAR"
  else
    # Fallback: try to locate old SDK-bundled Canton
    for version_dir in "$HOME/.daml/sdk/"*/ ; do
      if [[ -x "${version_dir}daml-sdk/canton" ]]; then
        CANTON_PATH="${version_dir}daml-sdk/canton"; break
      elif [[ -f "${version_dir}canton/canton.jar" ]]; then
        CANTON_PATH="${version_dir}canton/canton.jar"; break
      fi
    done
  fi
fi

if [[ -z "${CANTON_PATH}" ]]; then
  echo "${RED}Canton not found.${NC}"
  echo "Set one of: CANTON_HOME (…/canton-2.10.x), CANTON_BIN, or CANTON_JAR."
  exit 1
fi

echo "${GREEN}Starting Canton using: ${CANTON_PATH}${NC}"

# Build the command (launcher vs jar)
if [[ "${CANTON_PATH}" == *.jar ]]; then
  CMD=(java -jar "${CANTON_PATH}" daemon --config config/canton.conf --bootstrap config/connect.canton)
else
  CMD=("${CANTON_PATH}" daemon --config config/canton.conf --bootstrap config/connect.canton)
fi

# Start Canton
nohup "${CMD[@]}" > logs/canton/canton.out 2>&1 &
CANTON_PID=$!
echo "Canton PID: ${CANTON_PID}"
echo "${YELLOW}Waiting for Canton to start...${NC}"
sleep 20

if kill -0 "${CANTON_PID}" 2>/dev/null; then
  echo "${GREEN}Canton process is running${NC}"
  echo "Waiting for Canton auto-connection..."
  sleep 15

  echo "Starting Daml JSON API..."
  daml json-api \
    --ledger-host localhost \
    --ledger-port 10011 \
    --http-port 7575 \
    --allow-insecure-tokens \
    > logs/canton/json-api.out 2>&1 &
  JSON_API_PID=$!
  echo "JSON API PID: ${JSON_API_PID}"

  sleep 10
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:7575/livez | grep -q "200"; then
    echo "${GREEN}JSON API is responding!${NC}"
    echo ""
    echo "${GREEN}Canton services are running:${NC}"
    echo "  Ledger API: localhost:10011"
    echo "  Admin API:  localhost:10012"
    echo "  JSON API:   localhost:7575"
    echo ""
    echo "To stop: kill ${CANTON_PID} ${JSON_API_PID}"
    echo "To view logs: tail -f logs/canton/canton.out"

    # Lightweight monitor to auto-restart JSON API
    monitor_json_api() {
      while true; do
        sleep 30
        if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:7575/livez | grep -q "200"; then
          echo "${YELLOW}JSON API appears to be down, restarting...${NC}"
          pkill -f "json-api" 2>/dev/null || true
          sleep 2
          daml json-api \
            --ledger-host localhost \
            --ledger-port 10011 \
            --http-port 7575 \
            --allow-insecure-tokens \
            > logs/canton/json-api.out 2>&1 &
          echo "JSON API restarted with PID: $!"
          sleep 10
        fi
      done
    }
    monitor_json_api &
    echo "JSON API monitor PID: $!"
  else
    echo "${RED}JSON API failed to start${NC}"
    echo "Check logs/canton/json-api.out"
    kill "${CANTON_PID}" 2>/dev/null || true
    exit 1
  fi
else
  echo "${RED}Canton failed to start. Check logs/canton/canton.out${NC}"
  exit 1
fi
