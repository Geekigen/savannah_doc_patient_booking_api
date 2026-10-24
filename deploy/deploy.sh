#!/usr/bin/env bash
# Post-deploy tasks on the VPS (git pull, no rsync). Runs as deploy.
set -euo pipefail

APP_PATH="${APP_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
BRANCH="${DEPLOY_BRANCH:-deploy}"

cd "$APP_PATH"

echo "==> Deploying savannah in ${APP_PATH} (branch ${BRANCH})"

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found at ${APP_PATH}/.env" >&2
    echo "Bootstrap the VPS first (setup-vps.sh writes .env once)." >&2
    exit 1
fi

if [[ ! -d .git ]]; then
    echo "ERROR: ${APP_PATH} is not a git checkout" >&2
    exit 1
fi

echo "==> Updating code from origin/${BRANCH}"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only "origin" "$BRANCH"

if [[ ! -d .venv ]]; then
    echo "==> Creating virtualenv"
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p staticfiles media

echo "==> Running migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Restarting savannah"
if systemctl cat savannah.service &>/dev/null; then
    sudo systemctl restart savannah
    sudo systemctl is-active --quiet savannah
else
    echo "WARNING: savannah.service not found." >&2
fi

sudo systemctl reload nginx 2>/dev/null || true

echo "==> Savannah deploy finished successfully"
