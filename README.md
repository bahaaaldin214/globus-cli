## Globus Sync Helper

This project keeps the Globus CLI invocation logic in `globus_helper/main.py` so we can call it from cron jobs or ad-hoc shell scripts without duplicating options.

### Requirements
- Python 3.9+
- Globus CLI installed and authenticated for the account running transfers

> REQUIRED SCOPES
> - manage_collection
> - set_gcs_attributes

### Install and Configure the Globus CLI

1. Install the Globus CLI (choose one):
...
2. Log in to your Globus account:
   ```bash
   globus login
   ```

### Background Authentication (Automation)
For background sync (Service Account):
1. Register app at [developers.globus.org](https://developers.globus.org).
2. Set `GLOBUS_CLIENT_ID` and `GLOBUS_CLIENT_SECRET` in `.env`.
3. Give Service Account Identity (`UUID@clients.auth.globus.org`) access to endpoints.
   ```bash
   pipx install globus-cli
   # or
   pip install --user globus-cli
   ```
2. Log in so the CLI can submit transfers on your behalf:
   ```bash
   globus login
   ```
3. (Optional) Verify credentials:
   ```bash
   globus session show
   ```

Official documentation provides platform-specific guidance and troubleshooting: https://docs.globus.org/cli/

## Installation

Install dependencies and register the console script either with uv or pip.

```bash
# uv (creates .venv by default)
uv pip install --editable .

# pip (activate your virtualenv first)
pip install --editable .
```

To install only runtime dependencies without editable mode, use `uv pip install -r requirements.txt` or `pip install -r requirements.txt`. Developers can add `-r requirements-dev.txt` for pytest.

## Configuration

Populate these environment variables before running Globus transfers:

### Configuration
Populate these environment variables before running the helper:
- `GLOBUS_SOURCE_ENDPOINT`
- `GLOBUS_DEST_ENDPOINT`
- `GLOBUS_SOURCE_PATH` (defaults to `/` if unset)
- `GLOBUS_DEST_PATH`
- `GLOBUS_LABEL` (defaults to `NEU to UI sync`)
- `GLOBUS_SYNC_LEVEL` (defaults to `mtime`)
- `GLOBUS_NOTIFY` (`on`, `off`, or `failed`; defaults to `on`)
- `GLOBUS_PRESERVE_MTIME` (`true`/`false`; defaults to `true`)
- `GLOBUS_DRY_RUN` (`true`/`false`; defaults to `false`)
- `GLOBUS_EXTRA_FLAGS` (optional string of additional CLI flags)
- `GLOBUS_CLI` (override the `globus` executable path)

### Quick Start
Run the Click-based CLI via the installed console script:

```bash
globus-helper sync
```

To confirm the generated command without executing it:

```bash
globus-helper sync --show-command
```

Override individual arguments via flags as needed:

```bash
globus-helper sync \
  --dest-path "/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/bmohammad-dump/Actigraph" \
  --dry-run
```

### Using From Bash
Wrap the helper in your script (e.g., `globus_helper/sh/sync.sh`) and delegate the actual transfer to Python:

```bash
#!/usr/bin/env bash
set -euo pipefail

export GLOBUS_SOURCE_ENDPOINT="686bbc3e-08f7-46cf-95f8-7539e6fee972"
export GLOBUS_DEST_ENDPOINT="39dd0982-d784-11e6-9cd4-22000a1e3b52"
export GLOBUS_DEST_PATH="/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/bmohammad-dump/Actigraph"

globus-helper sync
```

Replace the endpoint IDs and destination path as required, and add optional overrides (such as `--dry-run`) to the final command when testing. You can interchangeably call the module with Python if the console script is unavailable:

```bash
python -m globus_helper.main sync --show-command
```

## Actigraphy Transfer

`globus_helper/transfer/main.py` converts the raw actigraphy dump into the BIDS-like layout expected by downstream tooling.

### Configuration
- Set `BASE_PATH` to the `3-experiment` root that contains both `data/` and `inputs/`. The script will create the required BIDS folders as needed.
- Set `RAW_FOLDER` to the raw actigraphy folder under `BASE_PATH`; the default is `data/bmohammad-dump/Actigraph`.
- Set `DEST_FOLDER` to the canonical transfer destination under `BASE_PATH`; the default is `inputs/act-int-ready`.
- A live transfer report is written to `BASE_PATH/inputs/transfered-month-day-year.txt` unless `--report-path` is provided.

### Usage
Run the helper directly to copy files and echo each source/destination pair:

```bash
globus-helper transfer --apply --base-path /path/to/share
```

Add `--dry-run` to verify the mapping without writing files, or `--base-path` / `--raw-folder` / `--dest-folder` to override environment defaults:

```bash
BASE_PATH=/path/to/3-experiment RAW_FOLDER=data/bmohammad-dump/Actigraph DEST_FOLDER=inputs/act-int-ready python -m globus_helper.transfer.main --dry-run
```

The transfer helper currently selects `*RAW.csv` files. The transfer helper is idempotent: existing destination files are skipped, and new copies are written with fresh default permissions (no metadata is propagated from the source CSVs).

You can also import and call `copy_actigraphy_to_bids()` from another script to get the list of copied `(source, destination)` paths for logging or testing.
