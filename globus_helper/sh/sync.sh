#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/../..:${PYTHONPATH:-}"
export GLOBUS_SOURCE_ENDPOINT="${GLOBUS_SOURCE_ENDPOINT:-f183d8f3-a966-49cd-b175-817a0a88cc3c}"
export GLOBUS_DEST_ENDPOINT="${GLOBUS_DEST_ENDPOINT:-39dd0982-d784-11e6-9cd4-22000a1e3b52}"
export GLOBUS_DEST_PATH="${GLOBUS_DEST_PATH:-/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/bmohammad-dump/Actigraph}"
# As of 2026-09-08 Globus web still shows data under /Actigraphy Data/
export GLOBUS_SOURCE_PATH="${GLOBUS_SOURCE_PATH:-/Actigraphy Data/}"

python -m globus_helper.main sync --source-path "${GLOBUS_SOURCE_PATH}" "$@"

