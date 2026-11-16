#!/bin/bash
# Usage: ./scripts/health-check.sh [url] [retries]
set -uo pipefail

URL="${1:-http://127.0.0.1:8000/health}"
RETRIES="${2:-15}"
DELAY=2

for i in $(seq 1 "$RETRIES"); do
  if curl -fsS "$URL" > /dev/null 2>&1; then
    echo "Healthy: $URL (attempt $i)"
    curl -fsS "$URL"
    echo
    exit 0
  fi
  echo "Attempt $i/$RETRIES: not healthy yet, retrying in ${DELAY}s..."
  sleep "$DELAY"
done

echo "ERROR: $URL did not become healthy after $RETRIES attempts" >&2
exit 1
