#!/bin/bash
# run-metrics-server.sh — Start the full monitoring stack on the Halo.
# Includes Prometheus, Grafana, node-exporter, glances, process-exporter,
# podman-exporter, and the Pushgateway for receiving remote device metrics.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Stopping existing monitoring stack..."
docker compose down

echo "Starting monitoring stack..."
docker compose up -d

echo "Waiting for containers to be ready..."
sleep 10

echo "Checking container status..."
docker compose ps

echo ""
echo "Monitoring stack is up."
echo "  Grafana:      http://localhost:3000"
echo "  Prometheus:   http://localhost:9090"
echo "  Pushgateway:  http://localhost:9091"
