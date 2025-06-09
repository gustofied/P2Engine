set -euo pipefail
CANTON_JAR=""
CANTON_BIN=""
# Color codes
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'
# Check all installed SDK versions
for version_dir in "$HOME/.daml/sdk/"*/; do
    if [ -f "${version_dir}canton/canton.jar" ]; then
        CANTON_JAR="${version_dir}canton/canton.jar"
        break
    elif [ -f "${version_dir}daml-sdk/canton" ]; then
        CANTON_BIN="${version_dir}daml-sdk/canton"
        break
    fi
done
if [ -n "${CANTON_JAR}" ]; then
    echo "${GREEN}Starting Canton using JAR: ${CANTON_JAR}${NC}"
    java -jar "${CANTON_JAR}" daemon \
        --config config/canton.conf \
        --bootstrap config/connect.canton \
        > logs/canton/canton.out 2>&1 &
    CANTON_PID=$!
elif [ -n "${CANTON_BIN}" ]; then
    echo "${GREEN}Starting Canton using executable: ${CANTON_BIN}${NC}"
    "${CANTON_BIN}" daemon \
        --config config/canton.conf \
        > logs/canton/canton.out 2>&1 &
    CANTON_PID=$!
else
    echo "${RED}Canton not found in Daml SDK!${NC}"
    exit 1
fi
echo "Canton PID: ${CANTON_PID}"
echo "${YELLOW}Waiting for Canton to start...${NC}"
sleep 20
if kill -0 ${CANTON_PID} 2>/dev/null; then
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
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:7575/livez 2>/dev/null | grep -q "200"; then
        echo "${GREEN}JSON API is responding!${NC}"
        echo ""
        echo "${GREEN}Canton services are running:${NC}"
        echo "  Ledger API: localhost:10011"
        echo "  Admin API: localhost:10012"
        echo "  JSON API: localhost:7575"
        echo ""
        echo "To stop: kill ${CANTON_PID} ${JSON_API_PID}"
        echo "To view logs: tail -f logs/canton/canton.out"
        
        # Start monitor function
        monitor_json_api() {
            while true; do
                sleep 30
                if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:7575/livez 2>/dev/null | grep -q "200"; then
                    echo "${YELLOW}JSON API appears to be down, restarting...${NC}"
                    pkill -f "json-api" 2>/dev/null || true
                    sleep 2
                    daml json-api \
                        --ledger-host localhost \
                        --ledger-port 10011 \
                        --http-port 7575 \
                        --allow-insecure-tokens \
                        > logs/canton/json-api.out 2>&1 &
                    JSON_API_PID=$!
                    echo "JSON API restarted with PID: ${JSON_API_PID}"
                    sleep 10
                fi
            done
        }

        # Start the monitor in background
        monitor_json_api &
        MONITOR_PID=$!
        echo "JSON API monitor PID: ${MONITOR_PID}"
        echo "To stop monitor: kill ${MONITOR_PID}"
    else
        echo "${RED}JSON API failed to start${NC}"
        echo "Check logs/canton/json-api.out for details"
        kill ${CANTON_PID} 2>/dev/null || true
        exit 1
    fi
else
    echo "${RED}Canton failed to start. Check logs/canton/canton.out${NC}"
    exit 1
fi