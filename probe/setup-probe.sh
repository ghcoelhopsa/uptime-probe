#!/bin/bash

# Script to configure and run the Uptime Monitor probe in a Docker container
set -e

echo "Uptime Probe Docker Setup"
echo "============================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker before continuing."
    exit 1
fi

# Request API Key
read -p "Enter the probe API key: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "Error: API Key is required."
    exit 1
fi

# Request other parameters with default values
read -p "Enter the server URL (default: http://host.docker.internal:5001): " SERVER_URL
SERVER_URL=${SERVER_URL:-"http://host.docker.internal:5001"}

read -p "Enter the job update interval in seconds (default: 300): " FETCH_INTERVAL
FETCH_INTERVAL=${FETCH_INTERVAL:-300}

read -p "Enter the heartbeat interval in seconds (default: 60): " HEARTBEAT_INTERVAL
HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL:-60}

echo ""
echo "Building Docker image..."

# Build the Docker image
docker build -t uptime-probe .

echo ""
echo "Running container..."

# Run the container with the necessary environment variables and capabilities
docker run -d \
  --name uptime-probe \
  --restart unless-stopped \
  --cap-add=NET_RAW \
  -e API_KEY="$API_KEY" \
  -e SERVER_URL="$SERVER_URL" \
  -e FETCH_INTERVAL="$FETCH_INTERVAL" \
  -e HEARTBEAT_INTERVAL="$HEARTBEAT_INTERVAL" \
  uptime-probe

echo ""
echo "Uptime-probe container started successfully!"
echo "To view logs: docker logs uptime-probe"
echo "To stop: docker stop uptime-probe"
echo "To remove: docker rm uptime-probe"
