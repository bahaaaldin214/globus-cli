#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/2] Starting Globus Sync..."
"${SCRIPT_DIR}/sync.sh"

echo "[2/2] Starting BIDS Transfer..."
"${SCRIPT_DIR}/transfer.sh"

echo "Pipeline complete."
