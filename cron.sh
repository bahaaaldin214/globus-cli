#!/bin/bash
# set -euo pipefail

# Source the Conda activate script
source /opt/anaconda3-2024.10-1/etc/profile.d/conda.sh

# load the globus env
conda activate globus

# Move to project home dir
cd "$(dirname "$0")"

# grab any new code changes, otherwise skip
git pull --ff-only origin main

# install any new dependencies and make sure the package is available in env
pip install -e .

# run sync (NEU -> LSS dump) then BIDS transfer (dump -> inputs/act-int-ready)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "${SCRIPT_DIR}/globus_helper/sh/full_pipeline.sh"

