#!/bin/bash
# Deploy on the target host: pull the latest stack and wait until healthy.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Pulling latest images..."
docker compose pull || docker compose build

echo "==> Starting stack..."
docker compose up -d

echo "==> Waiting for /health..."
./scripts/health-check.sh "http://127.0.0.1:8000/health"

echo "==> Deploy complete."
docker compose ps
