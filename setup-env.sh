#!/bin/bash
# Setup .env file for BuildLeads production

cat > /opt/buildleads/.env << 'ENVFILE'
CEIDG_API_KEY=eyJraWQiOiJjZWlkZyIsImFsZyI6IkhTNTEyIn0.eyJnaXZlbl9uYW1lIjoicGlvdHIiLCJwZXNlbCI6IjkxMDcyMjAwMzk3IiwiaWF0IjoxNzcyNjA0MTE1LCJmYW1pbHlfbmFtZSI6ImR5YmEiLCJjbGllbnRfaWQiOiJVU0VSLTkxMDcyMjAwMzk3LVBJT1RSLURZQkEifQ.YD1KLYhkHyiUmRFgyDFa3R9I_bOjP3Jy1LkitP6dul-24u92dNJCoRob4IXGZTR9jW3xF5CBHlKmP_PqXuFEuQ
GUS_API_KEY=
JWT_SECRET=buildleads-prod-jwt-secret-change-me-to-random-64-chars
POSTGRES_PASSWORD=secret
ADMIN_EMAIL=admin@potencjal.pl
ADMIN_PASSWORD=admin123
ENVFILE

echo "Created /opt/buildleads/.env"

# Restart containers to pick up new env
cd /opt/buildleads
docker compose down
docker compose up -d

sleep 10
docker compose ps
curl -s http://localhost/health
echo ""
echo "Done! CEIDG key is now configured."
