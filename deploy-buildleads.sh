#!/bin/bash
set -e

echo "=== BuildLeads Deploy ==="

# Clean up any previous attempt
rm -rf /opt/_deploy_tmp

# Clone repo
echo "1/5 Downloading code..."
git clone -b claude/claude-md-mmafm87dgyn3q029-ZBhkB https://github.com/Dsdgold/Potencjal.git /opt/_deploy_tmp

# Copy buildleads dir
echo "2/5 Copying files..."
mkdir -p /opt/buildleads
cp -r /opt/_deploy_tmp/buildleads/* /opt/buildleads/
rm -rf /opt/_deploy_tmp

# Stop old backend
echo "3/5 Stopping old services..."
pkill -f "uvicorn app.main" 2>/dev/null || true
cd /opt/potencjal/backend 2>/dev/null && docker compose down 2>/dev/null || true

# Start new stack
echo "4/5 Building and starting containers..."
cd /opt/buildleads
docker compose up --build -d

# Wait and verify
echo "5/5 Waiting for services..."
sleep 20
docker compose ps
echo ""
curl -s http://localhost/health || echo "API still starting..."
echo ""
echo "=== Deploy complete ==="
echo "Visit: http://46.225.131.52"
