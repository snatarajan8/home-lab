#!/bin/bash
set -e

# Navigate to the directory containing the docker-compose file
cd "$(dirname "$0")"

echo "Stopping existing monitoring containers..."
docker compose down

echo "Starting monitoring stack..."
docker compose up -d

echo "Waiting for containers to initialize (15s)..."
sleep 15

echo "Monitoring stack has been restarted."
echo "Please check Grafana at http://localhost:3000 to verify the new dashboards."
