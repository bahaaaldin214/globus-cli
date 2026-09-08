#!/bin/bash
# Globus Sunday cron: sync NEU -> dump, then reshape -> act-int-ready.
# Prefer: `bahaa pipeline globus-both` (see tools/cron/jobs.txt). This script
# remains for manual/legacy use; pip/git failures must not block transfer.

source /opt/anaconda3-2024.10-1/etc/profile.d/conda.sh
conda activate globus

cd "$(dirname "$0")"

# Best-effort update only — network often flaky on vosslink.
git pull --ff-only origin main || echo "WARNING: git pull failed; continuing with local tree" >&2
pip install -e . || echo "WARNING: pip install failed; continuing with installed package" >&2

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "${SCRIPT_DIR}/globus_helper/sh/full_pipeline.sh"
