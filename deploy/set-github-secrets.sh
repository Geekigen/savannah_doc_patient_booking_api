#!/usr/bin/env bash
# One-time: put SSH deploy secrets into the public GitHub repo (never commit them).
# Requires: gh auth login
set -euo pipefail

REPO="${REPO:-Geekigen/savannah_doc_patient_booking_api}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY="${ROOT}/deploy/github-deploy-key"

if [[ ! -f "$KEY" ]]; then
    echo "Missing ${KEY}" >&2
    exit 1
fi

if ! command -v gh >/dev/null; then
    echo "Install GitHub CLI (gh), then: gh auth login" >&2
    exit 1
fi

gh secret set SSH_HOST -b '13.140.169.79' -R "$REPO"
gh secret set SSH_USER -b 'deploy' -R "$REPO"
gh secret set SSH_PATH -b '/var/www/savannah' -R "$REPO"
gh secret set SSH_PRIVATE_KEY < "$KEY" -R "$REPO"
gh secret list -R "$REPO"
echo "Done. Push to deploy (or workflow_dispatch) to trigger savannah."
