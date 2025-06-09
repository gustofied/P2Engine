#!/bin/bash
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

echo "${GREEN}Setting up Canton for p2engine...${NC}"

# Create necessary directories
mkdir -p canton
mkdir -p logs/canton

# Check if daml is installed
if ! command -v daml &> /dev/null; then
    echo "${RED}Daml SDK is not installed!${NC}"
    echo "Please install Daml SDK first: https://docs.daml.com/getting-started/installation.html"
    exit 1
fi

# Get the installed Daml SDK versions
DAML_VERSION=$(daml version 2>/dev/null | grep -E '^\s+[0-9]+\.[0-9]+\.[0-9]+' | tail -1 | xargs)
DAML_SDK_PATH="$HOME/.daml/sdk/${DAML_VERSION}"

echo "Found Daml SDK version: ${DAML_VERSION} at ${DAML_SDK_PATH}"

# Check if Canton exists in the SDK
if [ -f "${DAML_SDK_PATH}/canton/canton.jar" ]; then
    echo "${GREEN}✓ Canton found in Daml SDK${NC}"
    CANTON_JAR="${DAML_SDK_PATH}/canton/canton.jar"
elif [ -f "${DAML_SDK_PATH}/daml-sdk/canton" ]; then
    echo "${GREEN}✓ Canton executable found in Daml SDK${NC}"
    CANTON_BIN="${DAML_SDK_PATH}/daml-sdk/canton"
else
    echo "${YELLOW}Canton not found in Daml SDK ${DAML_VERSION}${NC}"
    echo "Checking other installed versions..."
    
    # Check all installed SDK versions
    for version_dir in "$HOME/.daml/sdk/"*/; do
        version=$(basename "$version_dir")
        if [ -f "${version_dir}canton/canton.jar" ]; then
            echo "${GREEN}✓ Found Canton in SDK version ${version}${NC}"
            CANTON_JAR="${version_dir}canton/canton.jar"
            break
        fi
    done
    
    if [ -z "${CANTON_JAR:-}" ] && [ -z "${CANTON_BIN:-}" ]; then
        echo "${RED}Canton not found in any installed Daml SDK version${NC}"
        echo ""
        echo "Options:"
        echo "1. Install a Daml SDK version that includes Canton"
        echo "2. Use Docker: docker run --rm -it digitalasset/canton-community:2.8.0"
        exit 1
    fi
fi

# Create the start_canton.sh script
cat > scripts/start_canton.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# Find Canton in the Daml SDK
CANTON_JAR=""
CANTON_BIN=""

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
    echo "Starting Canton using JAR: ${CANTON_JAR}"
    java -jar "${CANTON_JAR}" daemon \
        --config config/canton.conf \
        > logs/canton/canton.out 2>&1 &
    CANTON_PID=$!
elif [ -n "${CANTON_BIN}" ]; then
    echo "Starting Canton using executable: ${CANTON_BIN}"
    "${CANTON_BIN}" daemon \
        --config config/canton.conf \
        > logs/canton/canton.out 2>&1 &
    CANTON_PID=$!
else
    echo "Canton not found in Daml SDK!"
    exit 1
fi

echo "Canton PID: ${CANTON_PID}"
echo "Waiting for Canton to start..."
sleep 10

if kill -0 ${CANTON_PID} 2>/dev/null; then
    echo "Canton appears to be running!"
    
    # Also start the JSON API
    echo "Starting Daml JSON API..."
    daml json-api \
        --ledger-host localhost \
        --ledger-port 10011 \
        --http-port 7575 \
        --allow-insecure-tokens \
        > logs/canton/json-api.out 2>&1 &
    JSON_API_PID=$!
    
    echo "JSON API PID: ${JSON_API_PID}"
    sleep 5
    
    if kill -0 ${JSON_API_PID} 2>/dev/null; then
        echo "JSON API started successfully!"
        echo ""
        echo "Canton is running with:"
        echo "  Ledger API: localhost:10011"
        echo "  Admin API: localhost:10012"
        echo "  JSON API: localhost:7575"
        echo ""
        echo "To stop: kill ${CANTON_PID} ${JSON_API_PID}"
    else
        echo "JSON API failed to start. Check logs/canton/json-api.out"
        kill ${CANTON_PID}
        exit 1
    fi
else
    echo "Canton failed to start. Check logs/canton/canton.out"
    exit 1
fi
EOF

chmod +x scripts/start_canton.sh

# Create the Docker alternative script
cat > scripts/start_canton_docker.sh << 'EOF'
#!/bin/bash
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
echo "1. ${GREEN}Using your local Daml SDK installation:${NC}"
echo "   ./scripts/start_canton.sh"
echo ""
echo "2. ${GREEN}Using Docker (if you prefer containerized setup):${NC}"
echo "   ./scripts/start_canton_docker.sh"
echo ""
echo "The main run script will automatically use the local Daml SDK version."