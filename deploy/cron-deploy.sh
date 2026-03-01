#!/usr/bin/env bash
# cron-deploy.sh — Cron fallback for Potencjal deploy.
# Only deploys if there are new commits on origin/main.
# Add to crontab: */5 * * * * /opt/potencjal/deploy/cron-deploy.sh >> /var/log/potencjal-cron.log 2>&1
set -euo pipefail

REPO_DIR="/opt/potencjal"
BRANCH="main"
LOCK_FILE="/tmp/potencjal-deploy.lock"
DEPLOY_SCRIPT="$(dirname "$(readlink -f "$0")")/deploy.sh"

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "[$(date '+%H:%M:%S')] Deploy already running (PID $LOCK_PID), skipping"
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# Check for changes
cd "$REPO_DIR"
git fetch origin "$BRANCH" -q 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cron: new commits detected ($LOCAL → $REMOTE)"
exec bash "$DEPLOY_SCRIPT" "$BRANCH"
