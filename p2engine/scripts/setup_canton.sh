#!/usr/bin/env bash
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

echo "${GREEN}Setting up Canton for p2engine...${NC}"

# Create necessary directories
mkdir -p canton
mkdir -p logs/canton
mkdir -p scripts

# Try to locate Daml (optional – we can proceed without it if standalone Canton is used)
if ! command -v daml &> /dev/null; then
    echo "${YELLOW}Warning: Daml SDK CLI not found in PATH.${NC}"
    echo "You can still run Canton if you point to a standalone install (CANTON_HOME/CANTON_BIN/CANTON_JAR),"
    echo "but JSON API requires the Daml CLI."
fi

# --- Discover Canton (prefer standalone; fallback to SDK legacy) ---
CANTON_JAR=""
CANTON_BIN=""

# Env overrides
if [[ -n "${CANTON_BIN:-}" && -x "${CANTON_BIN}" ]]; then
  CANTON_BIN="${CANTON_BIN}"
elif [[ -n "${CANTON_HOME:-}" && -x "${CANTON_HOME}/bin/canton" ]]; then
  CANTON_BIN="${CANTON_HOME}/bin/canton"
elif [[ -n "${CANTON_JAR:-}" && -f "${CANTON_JAR}" ]]; then
  CANTON_JAR="${CANTON_JAR}"
else
  # Common standalone locations
  for d in "$HOME/tools"/canton-* "$HOME/opt"/canton-* /opt/canton-* ; do
    if [[ -x "$d/bin/canton" ]]; then CANTON_BIN="$d/bin/canton"; break; fi
    shopt -s nullglob
    for jar in "$d"/lib/canton-*.jar "$d"/canton-*.jar; do
      [[ -f "$jar" ]] && CANTON_JAR="$jar" && break
    done
    shopt -u nullglob
    [[ -n "${CANTON_BIN:-}" || -n "${CANTON_JAR:-}" ]] && break
  done

  # Fallback: legacy inside SDK
  if [[ -z "${CANTON_BIN:-}" && -z "${CANTON_JAR:-}" ]] && command -v daml &>/dev/null; then
    DAML_VERSION=$(daml version 2>/dev/null | grep -E '^\s+[0-9]+\.[0-9]+\.[0-9]+' | tail -1 | xargs || true)
    DAML_SDK_PATH="$HOME/.daml/sdk/${DAML_VERSION:-}"
    if [[ -n "${DAML_VERSION:-}" ]]; then
      echo "Found Daml SDK version: ${DAML_VERSION} at ${DAML_SDK_PATH}"
    fi
    if [[ -x "${DAML_SDK_PATH}/daml-sdk/canton" ]]; then
      echo "${GREEN}✓ Canton executable found in Daml SDK${NC}"
      CANTON_BIN="${DAML_SDK_PATH}/daml-sdk/canton"
    elif [[ -f "${DAML_SDK_PATH}/canton/canton.jar" ]]; then
      echo "${GREEN}✓ Canton JAR found in Daml SDK${NC}"
      CANTON_JAR="${DAML_SDK_PATH}/canton/canton.jar"
    else
      echo "${YELLOW}Canton not found in the current SDK; checking all SDKs...${NC}"
      for version_dir in "$HOME/.daml/sdk/"*/; do
        if [[ -x "${version_dir}daml-sdk/canton" ]]; then
          echo "${GREEN}✓ Found Canton executable in SDK ${version_dir}${NC}"
          CANTON_BIN="${version_dir}daml-sdk/canton"; break
        elif [[ -f "${version_dir}canton/canton.jar" ]]; then
          echo "${GREEN}✓ Found Canton JAR in SDK ${version_dir}${NC}"
          CANTON_JAR="${version_dir}canton/canton.jar"; break
        fi
      done
    fi
  fi
fi

if [[ -z "${CANTON_BIN:-}" && -z "${CANTON_JAR:-}" ]]; then
    echo "${RED}Canton not found in standalone locations or Daml SDK.${NC}"
    echo ""
    echo "Options:"
    echo "1) Install standalone Canton and set CANTON_HOME (recommended for 2.10.x)."
    echo "2) Use Docker: ${YELLOW}./scripts/start_canton_docker.sh${NC}"
    echo "3) Install a Daml SDK version that includes Canton (older releases)."
    exit 1
fi

# Create the start_canton.sh script (robust; prefers standalone)
cat > scripts/start_canton.sh << 'EOF'
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
EOF

chmod +x scripts/start_canton.sh

# Create the Docker alternative script (unchanged behavior)
cat > scripts/start_canton_docker.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

CANTON_VERSION="${CANTON_VERSION:-2.8.0}"

echo "Starting Canton using Docker..."

# Stop and remove any existing container
docker stop canton-p2engine 2>/dev/null || true
docker rm canton-p2engine 2>/dev/null || true

# Start Canton container
docker run -d \
    --name canton-p2engine \
    -p 10011:10011 \
    -p 10012:10012 \
    -p 10018:10018 \
    -v "$(pwd)/config/canton.conf:/canton/config/canton.conf:ro" \
    digitalasset/canton-community:${CANTON_VERSION} \
    daemon --config /canton/config/canton.conf

echo "Waiting for Canton to start..."
sleep 10

if docker ps | grep canton-p2engine > /dev/null; then
    echo "Canton is running in Docker!"
    
    # Start JSON API in another container
    docker run -d \
        --name canton-json-api \
        --network container:canton-p2engine \
        -p 7575:7575 \
        digitalasset/daml-sdk:${CANTON_VERSION} \
        json-api \
        --ledger-host localhost \
        --ledger-port 10011 \
        --http-port 7575 \
        --allow-insecure-tokens
    
    echo "JSON API starting..."
    sleep 5
    
    echo ""
    echo "Canton is running with:"
    echo "  Ledger API: localhost:10011"
    echo "  Admin API: localhost:10012"
    echo "  JSON API: localhost:7575"
    echo ""
    echo "To view logs: docker logs -f canton-p2engine"
    echo "To stop: docker stop canton-p2engine canton-json-api"
else
    echo "Failed to start Canton in Docker"
    exit 1
fi
EOF

chmod +x scripts/start_canton_docker.sh

echo "${GREEN}Setup complete!${NC}"
echo ""
echo "${YELLOW}Canton can be run in two ways:${NC}"
echo ""
echo "1. ${GREEN}Using your local/standalone install or SDK fallback:${NC}"
echo "   ./scripts/start_canton.sh"
echo ""
echo "2. ${GREEN}Using Docker (containerized setup):${NC}"
echo "   ./scripts/start_canton_docker.sh"
echo ""
echo "The main run script will automatically discover a standalone Canton first."
