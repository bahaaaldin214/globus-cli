#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/../..:${PYTHONPATH:-}"
export BASE_PATH="${BASE_PATH:-/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment}"
export RAW_FOLDER="${RAW_FOLDER:-data/bmohammad-dump/Actigraph}"
export DEST_FOLDER="${DEST_FOLDER:-inputs/act-int-ready}"

python -m globus_helper.transfer.main "$@"
