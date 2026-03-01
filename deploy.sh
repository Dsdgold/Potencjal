#!/bin/bash
# Auto-deploy script for Potencjal
# Add to cron: */2 * * * * /opt/potencjal/deploy.sh >> /tmp/potencjal-deploy.log 2>&1

set -euo pipefail

REPO="https://github.com/Dsdgold/Potencjal.git"
TMP="/tmp/potencjal-update"
BACKEND="/opt/potencjal/backend"
FRONTEND="/var/www/html"
MARKER="/tmp/.potencjal-last-deploy"

cd /tmp
rm -rf "$TMP"
git clone --depth 1 -q "$REPO" "$TMP" 2>/dev/null || { echo "$(date) - git clone failed"; exit 1; }

# Check if anything changed since last deploy
NEW_HASH=$(find "$TMP/backend/app" "$TMP/mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html" -type f -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1)
OLD_HASH=""
[ -f "$MARKER" ] && OLD_HASH=$(cat "$MARKER")

if [ "$NEW_HASH" = "$OLD_HASH" ]; then
    rm -rf "$TMP"
    exit 0
fi

echo "$(date) - Changes detected, deploying..."

# Copy backend (preserve .env and .venv)
rsync -a --exclude '.env' --exclude '__pycache__' --exclude '.venv' --exclude '*.pyc' "$TMP/backend/" "$BACKEND/"

# Copy frontend
cp "$TMP/mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html" "$FRONTEND/"

# Install any new dependencies
cd "$BACKEND"
if [ -d .venv ]; then
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
fi

# Run migrations
.venv/bin/alembic upgrade head 2>/dev/null || true

# Restart backend
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/potencjal.log 2>&1 &

# Save hash
echo "$NEW_HASH" > "$MARKER"
echo "$(date) - Deploy OK (PID $!)"

rm -rf "$TMP"
