#!/usr/bin/env bash
# Rebuild locally, test, then push site/ to Hermes. Same scp policy as htp-crm (no git on the VPS).
set -euo pipefail
cd "$(dirname "$0")"
PYTHONIOENCODING=utf-8 python build.py
PYTHONIOENCODING=utf-8 python test_build.py
ssh hermes "mkdir -p /opt/htp-card"
scp -r -q site deploy/Caddyfile deploy/docker-compose.yml hermes:/opt/htp-card/
ssh hermes "cd /opt/htp-card && docker compose up -d && docker exec card-site caddy reload --config /etc/caddy/Caddyfile"
echo "deployed -> https://card.hungthanhphat.vn"
