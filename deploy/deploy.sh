#!/usr/bin/env bash
# deploy.sh — Main deploy script for Potencjal
# Called by webhook listener and cron job.
# Run on the server, not locally.
set -euo pipefail

REPO_DIR="/opt/potencjal"
FRONTEND_DIR="/var/www/html"
BRANCH="${1:-main}"
LOG="/var/log/potencjal-deploy.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== Deploy started (branch: $BRANCH) ==="

# ── 1. Pull latest code ──────────────────────────────────────────────
cd "$REPO_DIR"
git fetch origin "$BRANCH" 2>&1 | tee -a "$LOG"

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Already up-to-date ($LOCAL). Nothing to deploy."
    exit 0
fi

git reset --hard "origin/$BRANCH" 2>&1 | tee -a "$LOG"
log "Updated: $LOCAL → $REMOTE"

# ── 2. Deploy frontend ───────────────────────────────────────────────
cp -f "$REPO_DIR/mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html" \
      "$FRONTEND_DIR/" 2>&1 | tee -a "$LOG"
log "Frontend deployed to $FRONTEND_DIR"

# ── 3. Backend dependencies ──────────────────────────────────────────
cd "$REPO_DIR/backend"

if [ ! -d .venv ]; then
    python3 -m venv .venv
    log "Created virtualenv"
fi

# Reinstall only when requirements change
REQS_HASH=$(md5sum requirements.txt | cut -d' ' -f1)
PREV_HASH_FILE=".venv/.reqs_hash"
PREV_HASH=""
[ -f "$PREV_HASH_FILE" ] && PREV_HASH=$(cat "$PREV_HASH_FILE")

if [ "$REQS_HASH" != "$PREV_HASH" ]; then
    .venv/bin/pip install -q -r requirements.txt 2>&1 | tee -a "$LOG"
    echo "$REQS_HASH" > "$PREV_HASH_FILE"
    log "Dependencies updated"
else
    log "Dependencies unchanged, skipping pip install"
fi

# ── 4. Database ───────────────────────────────────────────────────────
docker compose up -d 2>&1 | tee -a "$LOG"
cp -n .env.example .env 2>/dev/null || true
.venv/bin/alembic upgrade head 2>&1 | tee -a "$LOG"
log "Database migrated"

# ── 5. Restart backend ───────────────────────────────────────────────
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    >> /tmp/potencjal.log 2>&1 &
log "Backend restarted (PID: $!)"

# ── 6. Health check ──────────────────────────────────────────────────
sleep 3
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    log "Health check OK"
else
    log "WARNING: Health check failed — backend may still be starting"
fi

log "=== Deploy finished ==="
