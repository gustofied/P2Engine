#!/bin/bash
set -euo pipefail

# ANSI Color codes
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
RUN_DIR="logs/run_${TIMESTAMP}"
mkdir -p "${RUN_DIR}"/{workers,pids,artifacts}

# Set environment variables
export LOG_DIR="${RUN_DIR}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export WORKER_LOG_LEVEL="${WORKER_LOG_LEVEL:-INFO}"
export LITELLM_LOG_LEVEL="${LITELLM_LOG_LEVEL:-error}"
export LEDGER_DEV_MODE="true"

# Logging function
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${RUN_DIR}/main.log" ; }

# Worker PIDs
declare -a WORKER_PIDS=()
ENGINE_PID=""

###############################################################################
# Canton/Daml helper
###############################################################################
find_canton() {
    if ! command -v daml &> /dev/null; then
        echo ""
        return
    fi
    
    # Get current Daml version
    DAML_VERSION=$(daml version 2>/dev/null | grep -E '^\s+[0-9]+\.[0-9]+\.[0-9]+' | tail -1 | xargs)
    
    # Check for Canton in the current SDK first
    if [ -f "$HOME/.daml/sdk/${DAML_VERSION}/canton/canton.jar" ]; then
        echo "$HOME/.daml/sdk/${DAML_VERSION}/canton/canton.jar"
        return
    fi
    
    # Check other SDK versions
    for version_dir in "$HOME/.daml/sdk/"*/; do
        if [ -f "${version_dir}canton/canton.jar" ]; then
            echo "${version_dir}canton/canton.jar"
            return
        fi
    done
    
    echo ""
}

###############################################################################
# Build Daml and extract package ID
###############################################################################
build_daml_and_extract_package_id() {
    log "${YELLOW}Building Daml project...${NC}"
    
    # Build the Daml project
    if ! daml build -o .daml/dist/p2engine-ledger-0.1.0.dar; then
        log "${RED}Failed to build Daml project${NC}"
        return 1
    fi
    
    log "${GREEN}Daml build successful${NC}"
    
    # Extract package ID using daml damlc inspect-dar
    log "Extracting package ID..."
    
    # First, let's see what the output looks like
    INSPECT_OUTPUT=$(daml damlc inspect-dar .daml/dist/p2engine-ledger-0.1.0.dar 2>&1)
    
    # Try different patterns to extract package ID
    PACKAGE_ID=$(echo "$INSPECT_OUTPUT" | grep -i "main package" | sed -E 's/.*: *//' | tr -d ' ')
    
    if [ -z "$PACKAGE_ID" ]; then
        PACKAGE_ID=$(echo "$INSPECT_OUTPUT" | grep -E '^[a-f0-9]{64}$' | head -1)
    fi
    
    if [ -z "$PACKAGE_ID" ]; then
        PACKAGE_ID=$(echo "$INSPECT_OUTPUT" | grep "p2engine-ledger" | grep -oE '[a-f0-9]{64}' | head -1)
    fi
    
    if [ -z "$PACKAGE_ID" ]; then
        # Try JSON format
        if daml damlc inspect-dar --json .daml/dist/p2engine-ledger-0.1.0.dar >/dev/null 2>&1; then
            PACKAGE_ID=$(daml damlc inspect-dar --json .daml/dist/p2engine-ledger-0.1.0.dar 2>/dev/null | jq -r '.main_package_id // empty')
        fi
    fi
    
    if [ -z "$PACKAGE_ID" ]; then
        log "${RED}Failed to extract package ID${NC}"
        return 1
    fi
    
    log "${GREEN}Package ID: $PACKAGE_ID${NC}"
    export DAML_PACKAGE_ID="$PACKAGE_ID"
    
    # Update .env file if it exists
    if [ -f ".env" ]; then
        grep -v "^DAML_PACKAGE_ID=" .env > .env.tmp || true
        mv .env.tmp .env
        echo "DAML_PACKAGE_ID=$PACKAGE_ID" >> .env
        log "Updated .env with DAML_PACKAGE_ID"
    fi
    
    return 0
}

###############################################################################
# Kill all existing processes
###############################################################################
kill_all_processes() {
    log "${YELLOW}Cleaning up existing processes...${NC}"
    
    # Kill Celery workers
    if ORPHANS=$(pgrep -f 'celery.*runtime.tasks.celery_app' 2>/dev/null) && [ -n "${ORPHANS}" ] ; then
        log "Killing stray Celery workers: ${ORPHANS}"
        pkill -TERM -f 'celery.*runtime.tasks.celery_app' || true
        sleep 2
        pkill -9 -f 'celery.*runtime.tasks.celery_app' 2>/dev/null || true
    fi
    
    # Kill Canton daemon
    if pgrep -f "canton.*daemon" > /dev/null 2>&1; then
        log "Killing Canton daemon..."
        pkill -TERM -f "canton.*daemon" || true
        sleep 2
        pkill -9 -f "canton.*daemon" 2>/dev/null || true
    fi
    
    # Kill Canton JAR processes
    if pgrep -f "canton.jar" > /dev/null 2>&1; then
        log "Killing Canton JAR processes..."
        pkill -TERM -f "canton.jar" || true
        sleep 2
        pkill -9 -f "canton.jar" 2>/dev/null || true
    fi
    
    # Kill JSON API
    if pgrep -f "json-api" > /dev/null 2>&1; then
        log "Killing JSON API..."
        pkill -TERM -f "json-api" || true
        sleep 2
        pkill -9 -f "json-api" 2>/dev/null || true
    fi
    
    # Kill p2engine processes
    if pgrep -f "runtime/engine.py" > /dev/null 2>&1; then
        log "Killing p2engine processes..."
        pkill -TERM -f "runtime/engine.py" || true
        sleep 2
        pkill -9 -f "runtime/engine.py" 2>/dev/null || true
    fi
    
    log "${GREEN}Process cleanup complete${NC}"
}

###############################################################################
# Start Redis
###############################################################################
ensure_redis () {
    local timeout=10
    log "Starting Redis..."
    
    if command -v brew &> /dev/null; then
        brew services start redis
    else
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes
        else
            log "${RED}Redis is not installed. Please install Redis first.${NC}"
            exit 1
        fi
    fi
    
    # Wait for Redis to be ready
    log "Waiting for Redis to be ready..."
    local elapsed=0
    until redis-cli ping >/dev/null 2>&1 ; do
        sleep 0.5
        ((elapsed+=1))
        if [ "${elapsed}" -ge $((timeout*2)) ] ; then
            log "${RED}Redis did not respond within ${timeout}s – aborting.${NC}"
            exit 1
        fi
    done
    
    log "${GREEN}Redis is up.${NC}"
    
    # Clear Redis database
    log "Clearing Redis database..."
    redis-cli FLUSHDB
}

###############################################################################
# Start Canton
###############################################################################
start_canton() {
    local CANTON_JAR="$1"
    
    log "${YELLOW}Starting Canton...${NC}"
    
    # Start Canton daemon with bootstrap
    java -jar "${CANTON_JAR}" daemon \
        --config config/canton.conf \
        --bootstrap config/connect.canton \
        > "${RUN_DIR}/canton.log" 2>&1 &
    
    CANTON_PID=$!
    log "Canton PID: ${CANTON_PID}"
    
    # Wait for Canton to initialize
    log "Waiting for Canton to initialize..."
    sleep 25
    
    # Check if Canton is running
    if ! kill -0 ${CANTON_PID} 2>/dev/null; then
        log "${RED}Canton failed to start${NC}"
        if [ -f "${RUN_DIR}/canton.log" ]; then
            log "Canton log tail:"
            tail -20 "${RUN_DIR}/canton.log"
        fi
        return 1
    fi
    
    log "${GREEN}Canton process is running${NC}"
    
    # Give Canton more time to establish domain connections
    log "Waiting for Canton domain connections..."
    sleep 20
    
    return 0
}

###############################################################################
# Start JSON API
###############################################################################
start_json_api() {
    log "${YELLOW}Starting JSON API...${NC}"
    
    daml json-api \
        --ledger-host localhost \
        --ledger-port 10011 \
        --http-port 7575 \
        --allow-insecure-tokens \
        > "${RUN_DIR}/json-api.log" 2>&1 &
    
    JSON_API_PID=$!
    log "JSON API PID: ${JSON_API_PID}"
    
    # Wait for JSON API to start
    sleep 10
    
    # Check if JSON API is responding
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:7575/livez 2>/dev/null | grep -q "200"; then
        log "${GREEN}JSON API started successfully!${NC}"
        return 0
    else
        log "${RED}JSON API failed to start${NC}"
        kill ${JSON_API_PID} 2>/dev/null || true
        return 1
    fi
}

###############################################################################
# Cleanup function
###############################################################################
cleanup () {
    log "${YELLOW}Shutting down services...${NC}"
    
    # Stop all worker processes
    for pid in "${ENGINE_PID}" "${WORKER_PIDS[@]:-}" ; do
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null ; then
            kill -TERM "${pid}" 2>/dev/null || true
        fi
    done
    
    sleep 2
    
    # Kill all processes
    kill_all_processes
    
    # Stop Redis
    if command -v brew &> /dev/null; then
        brew services stop redis || true
    else
        redis-cli shutdown || true
    fi
    
    log "${GREEN}Cleanup complete.${NC}"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

###############################################################################
# Main execution
###############################################################################

# Change to project directory
cd "$(dirname "$0")/.."
log "Working directory: $(pwd)"

# Load environment variables from .env if it exists
DOTENV_PATH="${DOTENV_PATH:-.env}"
if [ -f "${DOTENV_PATH}" ] ; then
    set -a ; . "${DOTENV_PATH}" ; set +a
    log "Loaded environment variables from ${DOTENV_PATH}"
fi

# Make repository root importable
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

# Kill all existing processes first
kill_all_processes

# Start Redis
ensure_redis

# Check configuration
CONFIG_PATH="${P2ENGINE_CONFIG_PATH:-config/config.json}"
if [ ! -f "${CONFIG_PATH}" ] ; then
    log "${RED}Configuration file not found: ${CONFIG_PATH}${NC}"
    exit 1
fi

# Validate config.json
if ! jq -e '.llm' "${CONFIG_PATH}" >/dev/null ; then
    log "${RED}Invalid config.json – .llm section missing${NC}"
    exit 1
fi

# Check OpenAI API key
if [ -z "${OPENAI_API_KEY:-}" ]; then
    log "${RED}OPENAI_API_KEY environment variable is not set!${NC}"
    log "Please set it in your .env file or export it in your shell."
    exit 1
fi

# Canton/Ledger setup
if [ "${LEDGER_ENABLED:-true}" = "true" ]; then
    log "Checking Canton/Ledger setup..."
    
    CANTON_JAR=$(find_canton)
    if [ -z "${CANTON_JAR}" ]; then
        log "${YELLOW}Canton not found in Daml SDK.${NC}"
        log "${YELLOW}Continuing without ledger support.${NC}"
        export LEDGER_ENABLED="false"
    else
        log "${GREEN}Found Canton at: ${CANTON_JAR}${NC}"
        
        # Build Daml and extract package ID
        if ! build_daml_and_extract_package_id; then
            log "${RED}Failed to build Daml project - continuing without ledger${NC}"
            export LEDGER_ENABLED="false"
        else
            # Start Canton
            if start_canton "${CANTON_JAR}"; then
                # Start JSON API
                if start_json_api; then
                    log "${GREEN}Canton and JSON API are ready!${NC}"
                    
                    # Extra stabilization time
                    log "Waiting for services to stabilize..."
                    sleep 10
                else
                    log "${RED}Failed to start JSON API - continuing without ledger${NC}"
                    export LEDGER_ENABLED="false"
                fi
            else
                log "${RED}Failed to start Canton - continuing without ledger${NC}"
                export LEDGER_ENABLED="false"
            fi
        fi
    fi
else
    log "Ledger support is disabled (LEDGER_ENABLED=false)"
fi

# Initialize the application
log "Initializing the application..."
if ! poetry run python scripts/initialize_app.py; then
    log "${RED}Application initialization failed!${NC}"
    exit 1
fi

# Start Celery workers
log "Starting Celery workers..."

# Helper to convert log level to lowercase
lc() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' ; }

# Start rollouts worker
poetry run celery -A runtime.tasks.celery_app worker \
        --loglevel="$(lc "${WORKER_LOG_LEVEL}")" -Q rollouts -n rollouts@%h -c 2 \
        --pidfile "${RUN_DIR}/pids/rollouts.pid" \
        > "${RUN_DIR}/workers/rollouts.log" 2>&1 &
WORKER_PIDS+=($!)

# Start ticks worker
poetry run celery -A runtime.tasks.celery_app worker \
        --loglevel="$(lc "${WORKER_LOG_LEVEL}")" -Q ticks -n ticks@%h -c 16 \
        --pidfile "${RUN_DIR}/pids/ticks.pid" \
        > "${RUN_DIR}/workers/ticks.log" 2>&1 &
WORKER_PIDS+=($!)

# Start tools worker
poetry run celery -A runtime.tasks.celery_app worker \
        --loglevel="$(lc "${WORKER_LOG_LEVEL}")" -Q tools -n tools@%h -c 16 \
        --pidfile "${RUN_DIR}/pids/tools.pid" \
        > "${RUN_DIR}/workers/tools.log" 2>&1 &
WORKER_PIDS+=($!)

# Start evals worker with beat
poetry run celery -A runtime.tasks.celery_app worker \
        --loglevel="$(lc "${WORKER_LOG_LEVEL}")" -Q evals -n evals@%h -c 8 --beat \
        --pidfile "${RUN_DIR}/pids/evals.pid" \
        > "${RUN_DIR}/workers/evals.log" 2>&1 &
WORKER_PIDS+=($!)

# Wait for workers to start
sleep 3

# Start Engine (background)
log "Starting Engine (background)..."
poetry run python runtime/engine.py >> "${RUN_DIR}/main.log" 2>&1 &
ENGINE_PID=$!
WORKER_PIDS+=("${ENGINE_PID}")

# Wait for engine to start
sleep 3

# Check if engine is running
if ! kill -0 "${ENGINE_PID}" 2>/dev/null; then
    log "${RED}Engine failed to start! Check ${RUN_DIR}/main.log for errors.${NC}"
    exit 1
fi

log "${GREEN}Engine is up${NC}"

# Initialize wallets if ledger is enabled
if [ "${LEDGER_ENABLED:-true}" = "true" ] && [ -n "${DAML_PACKAGE_ID:-}" ]; then
    log "Waiting for ledger services to be ready..."
    sleep 15
    
    # Run Canton health check
    if ./scripts/canton-health-check.sh > /dev/null 2>&1; then
        log "${GREEN}Canton health check passed${NC}"
    else
        log "${YELLOW}Canton health check failed - some features may not work${NC}"
    fi
    
    # Initialize agent wallets
    log "Initializing agent wallets..."
    
    # Run wallet initialization with timeout
    (
        poetry run p2engine ledger init --balance 100.0
    ) &
    INIT_PID=$!
    
    # Wait up to 30 seconds for initialization
    SECONDS=0
    while kill -0 $INIT_PID 2>/dev/null && [ $SECONDS -lt 30 ]; do
        sleep 1
    done
    
    if kill -0 $INIT_PID 2>/dev/null; then
        # Still running after 30 seconds - kill it
        kill -TERM $INIT_PID 2>/dev/null || true
        wait $INIT_PID 2>/dev/null
        log "${YELLOW}Wallet initialization timed out - continuing anyway${NC}"
    else
        # Process finished - check exit status
        wait $INIT_PID
        if [ $? -eq 0 ]; then
            log "${GREEN}Agent wallets initialized successfully!${NC}"
        else
            log "${YELLOW}Wallet initialization had some issues (non-fatal)${NC}"
        fi
    fi
fi

# System is ready
log "${GREEN}System is ready!${NC}"

# Launch CLI or run command
log "Launching CLI. Press Ctrl-C to quit."
if [ "$#" -eq 0 ] ; then
    poetry run p2engine shell
else
    poetry run python -m cli "$@"
fi

log "CLI exited – shutting down..."