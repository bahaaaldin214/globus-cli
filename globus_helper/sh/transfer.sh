#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/../..:${PYTHONPATH:-}"
export BASE_PATH="${BASE_PATH:-/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data}"
export RAW_FOLDER="${RAW_FOLDER:-bmohammad-dump/Actigraph}"

python -m globus_helper.transfer.main "$@"
