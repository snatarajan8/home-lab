#!/bin/bash

echo "Stopping existing monitoring stack..."
docker compose down

echo "Removing old images..."
# We don't want to remove everything, just the ones we've modified or are problematic
# But for a clean start, we can remove the containers.

echo "Starting monitoring stack..."
docker compose up -d

echo "Waiting for containers to be ready..."
sleep 10

echo "Checking container status..."
docker compose ps

echo "Monitoring stack is up."
