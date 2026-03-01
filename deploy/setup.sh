#!/usr/bin/env bash
# setup.sh — One-command setup for Potencjal deploy system on the server.
#
# Usage (run on server as root):
#   curl -sL https://raw.githubusercontent.com/Dsdgold/Potencjal/main/deploy/setup.sh | bash
#   — or —
#   bash /opt/potencjal/deploy/setup.sh
set -euo pipefail

REPO_DIR="/opt/potencjal"
REPO_URL="https://github.com/Dsdgold/Potencjal.git"
DEPLOY_DIR="$REPO_DIR/deploy"

echo "============================================"
echo "  Potencjal — Deploy System Setup"
echo "============================================"
echo ""

# ── 1. Clone repo if needed ──────────────────────────────────────────
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "[1/5] Cloning repository..."
    git clone "$REPO_URL" "$REPO_DIR"
else
    echo "[1/5] Repository exists, pulling latest..."
    cd "$REPO_DIR" && git pull origin main
fi

# ── 2. Make scripts executable ────────────────────────────────────────
echo "[2/5] Setting permissions..."
chmod +x "$DEPLOY_DIR/deploy.sh"
chmod +x "$DEPLOY_DIR/cron-deploy.sh"
chmod +x "$DEPLOY_DIR/webhook.py"

# ── 3. Configure webhook secret ──────────────────────────────────────
ENV_FILE="$DEPLOY_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    GENERATED_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "$ENV_FILE" <<EOF
# Webhook configuration
WEBHOOK_SECRET=$GENERATED_SECRET
WEBHOOK_PORT=9000
EOF
    echo "[3/5] Webhook .env created with auto-generated secret."
    echo ""
    echo "  >>> WEBHOOK_SECRET=$GENERATED_SECRET"
    echo "  >>> Copy this secret to GitHub (Settings → Webhooks → Secret)"
    echo ""
else
    echo "[3/5] Webhook .env already exists, keeping current config."
fi

# ── 4. Install systemd service ───────────────────────────────────────
echo "[4/5] Installing webhook systemd service..."
cp "$DEPLOY_DIR/webhook.service" /etc/systemd/system/potencjal-webhook.service
systemctl daemon-reload
systemctl enable potencjal-webhook.service
systemctl restart potencjal-webhook.service
echo "  Webhook listener active on port 9000"

# ── 5. Install cron fallback ─────────────────────────────────────────
echo "[5/5] Installing cron fallback (every 5 minutes)..."
CRON_LINE="*/5 * * * * $DEPLOY_DIR/cron-deploy.sh >> /var/log/potencjal-cron.log 2>&1"
# Remove old entry if exists, then add new one
(crontab -l 2>/dev/null | grep -v "cron-deploy.sh" || true; echo "$CRON_LINE") | crontab -
echo "  Cron job installed"

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "  Webhook:  http://$(hostname -I | awk '{print $1}'):9000/webhook"
echo "  Health:   http://$(hostname -I | awk '{print $1}'):9000/health"
echo "  Cron:     Every 5 minutes (fallback)"
echo "  Logs:     journalctl -u potencjal-webhook -f"
echo "            tail -f /var/log/potencjal-deploy.log"
echo ""
echo "  Next step:"
echo "  Go to GitHub → Settings → Webhooks → Add webhook"
echo "    Payload URL:  http://YOUR_SERVER_IP:9000/webhook"
echo "    Content type: application/json"
echo "    Secret:       (from $ENV_FILE)"
echo "    Events:       Just the push event"
echo ""
