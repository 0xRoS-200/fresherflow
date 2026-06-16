#!/usr/bin/env bash
# One command: start app + auto-fetch new jobs every 2 hours. Keep this terminal open.
set -e
cd "$(dirname "$0")"
if ! python3 -c "import pdfplumber" 2>/dev/null; then
  echo "Installing Python dependencies..."
  pip3 install -r requirements.txt || {
    echo "Could not install dependencies. Run: pip3 install -r requirements.txt"
    exit 1
  }
fi
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti:8080 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "Stopping previous server on port 8080..."
    kill -9 $PIDS 2>/dev/null || true
    sleep 1
  fi
fi
echo "Loading job feed (first fetch may take ~15s)..."
python3 scripts/refresh_jobs_cache.py || true
echo "Starting FresherFlow — jobs refresh automatically every 2 hours while this runs."
exec python3 scripts/serve.py
