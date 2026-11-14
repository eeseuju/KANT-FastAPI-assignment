#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/board-be
git pull --ff-only
export PATH="$HOME/.local/bin:$PATH"
uv sync --frozen --no-dev
.venv/bin/alembic upgrade head
sudo systemctl restart board-be
sleep 2
curl -fsS http://127.0.0.1:8000/health
echo
