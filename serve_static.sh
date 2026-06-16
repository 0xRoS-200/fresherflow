#!/usr/bin/env bash
# Jobs-only: serve the site + cached feed (no PDF parsing). Use run.sh for full features.
set -e
cd "$(dirname "$0")"
PORT="${PORT:-8080}"
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti:"$PORT" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "Stopping process on port $PORT..."
    kill -9 $PIDS 2>/dev/null || true
    sleep 1
  fi
fi
echo "FresherFlow (static) at http://localhost:$PORT"
echo "Jobs load from data/jobs_live_cache.json — no server scripts required."
exec python3 -m http.server "$PORT"
