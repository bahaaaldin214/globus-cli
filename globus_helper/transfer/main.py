"""Transfer actigraphy CSVs into a BIDS-like layout.

File structure of the ne-dump on LSS (two layouts are supported)::

    # legacy layout (no dump folders)
    BASE_PATH/ne-dump/Actigraphy/<subject_id>_actigraphy/v<#>/<subject_id> (<date of recording>)RAW.csv

    # current layout with dumps A1–A4
    BASE_PATH/ne-dump/Actigraphy/A#/ <subject_id>_actigraphy/v<#>/<subject_id> (<date of recording>)RAW.csv

In the legacy layout, the version directory (`v0`, `v3`, `v5`) determines the
session number. In the dump-aware layout, the dump directory (`A1`–`A4`)
determines the session number while version directories are ignored for session
assignment.

The desired output is in a BIDS-inspired structure::

    BASE_PATH/inputs/act-int-ready/sub-<subject_id>/accel/ses-<session_id>/sub-<subject_id>_ses-<session_id>_accel.csv

This module provides a helper that copies each actigraphy CSV into the target
layout using glob pattern matching. `BASE_PATH` is expected to be supplied via
environment variable when no explicit path is provided.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from ..logging_config import setup_logging
except ImportError:  # pragma: no cover - allows running as a script
    from logging_config import setup_logging  # type: ignore

setup_logging()
logger = logging.getLogger(__name__)

VERSION_TO_SESSION = {"V0": "1", "V3": "2", "V5": "3"}
DUMP_TO_SESSION = {"A1": "1", "A2": "2", "A3": "3", "A4": "4"}
ENV_RAW_FOLDER = "RAW_FOLDER"
ENV_DEST_FOLDER = "DEST_FOLDER"
DEFAULT_RAW_FOLDER = "data/bmohammad-dump/Actigraph"
DEFAULT_DEST_FOLDER = "inputs/act-int-ready"
PROGRESS_WIDTH = 30


def _render_progress(
    current: int,
    total: int,
    *,
    copied: int = 0,
    skipped: int = 0,
    label: str = "Transfer",
) -> None:
    if total <= 0:
        return

    filled = int(PROGRESS_WIDTH * current / total)
    bar = "#" * filled + "-" * (PROGRESS_WIDTH - filled)
    percent = int(100 * current / total)
    sys.stdout.write(
        f"\r{label} [{bar}] {current}/{total} ({percent}%) "
        f"copied={copied} skipped={skipped}"
    )
    sys.stdout.flush()


def _finish_progress() -> None:
    sys.stdout.write("\n")
    sys.stdout.flush()


def _needs_copy(source: Path, destination: Path) -> bool:
    if not destination.exists():
        return True

    source_stat = source.stat()
    destination_stat = destination.stat()
    if source_stat.st_size != destination_stat.st_size:
        return True

    return source_stat.st_mtime > destination_stat.st_mtime


def _count_source_files(source_root: Path) -> tuple[int, int]:
    raw_count = sum(1 for _ in source_root.rglob("*RAW.csv"))
    sixty_sec_count = sum(1 for _ in source_root.rglob("*60sec.csv"))
    return raw_count, sixty_sec_count


def _default_report_path(base_path: Path) -> Path:
    stamp = datetime.now().strftime("%m-%d-%Y")
    return base_path / "inputs" / f"transfered-{stamp}.txt"


def _write_report(
    report_path: Path,
    *,
    source_root: Path,
    destination_root: Path,
    dry_run: bool,
    expected_copies: int,
    raw_count: int,
    sixty_sec_count: int,
    processed: int,
    copied: int,
    skipped: int,
    last_action: str = "not started",
) -> None:
    percent = int(100 * processed / expected_copies) if expected_copies else 100
    lines = [
        f"Report file: {report_path.name}",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Dry run: {dry_run}",
        f"Source root: {source_root}",
        f"Destination root: {destination_root}",
        f"Expected copies: {expected_copies}",
        f"Processed: {processed}/{expected_copies} ({percent}%)",
        f"Files copied: {copied}",
        f"Files skipped: {skipped}",
        f"RAW csv files found: {raw_count}",
        f"60sec csv files found: {sixty_sec_count}",
        f"Last action: {last_action}",
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_actigraphy_to_bids(
    base_path: Optional[Path] = None,
    *,
    dry_run: bool = False,
    raw_folder: Optional[str] = None,
    dest_folder: Optional[str] = None,
    report_path: Optional[Path] = None,
) -> List[Tuple[Path, Path]]:
    """Copy the actigraphy CSVs into a BIDS-compliant directory structure.

    Parameters
    ----------
    base_path:
        Optional base directory. If omitted, the value of the `BASE_PATH`
        environment variable is used.
    dry_run:
        When True, simulate the copy without creating directories or writing
        files. The returned list still contains the source and intended
        destination paths.
    raw_folder:
        Sub-path relative to base_path containing raw actigraphy files.
        Defaults to `RAW_FOLDER` when set, otherwise "data/bmohammad-dump/Actigraph".
    dest_folder:
        Sub-path relative to base_path where canonical files are written.
        Defaults to `DEST_FOLDER` when set, otherwise "inputs/act-int-ready".
    report_path:
        Optional path for a live-updated transfer report.

    Returns
    -------
    list[tuple[pathlib.Path, pathlib.Path]]
        A list of `(source, destination)` pairs for the files that were copied.

    Raises
    ------
    EnvironmentError
        If `BASE_PATH` is not provided via argument or environment.
    FileNotFoundError
        If the expected source directory does not exist.
    """

    if base_path is None:
        raw_base = os.environ.get("BASE_PATH")
        if not raw_base:
            logger.error("BASE_PATH environment variable is not set")
            raise EnvironmentError(
                "BASE_PATH environment variable must be set or base_path provided."
            )
        base_path = Path(raw_base)

    base_path = Path(base_path).expanduser().resolve()
    raw_folder = raw_folder or os.environ.get(ENV_RAW_FOLDER, DEFAULT_RAW_FOLDER)
    dest_folder = dest_folder or os.environ.get(ENV_DEST_FOLDER, DEFAULT_DEST_FOLDER)
    logger.debug("Resolved base path: %s (dry_run=%s)", base_path, dry_run)

    source_root = base_path / raw_folder
    destination_root = base_path / dest_folder
    report_path = Path(report_path).expanduser() if report_path else _default_report_path(base_path)

    logger.debug("Scanning source root: %s", source_root)

    if not source_root.is_dir():
        logger.error("Actigraphy source directory not found at %s", source_root)
        raise FileNotFoundError(f"Actigraphy source directory not found: {source_root}")

    planned: List[Tuple[Path, Path]] = []
    skipped_existing = 0
    raw_count, sixty_sec_count = _count_source_files(source_root)

    dump_dirs = [
        dump_dir
        for dump_dir in sorted(source_root.iterdir())
        if dump_dir.is_dir() and dump_dir.name in DUMP_TO_SESSION
    ]

    def _plan_csv(
        *, subject_id: str, session_id: str, csv_file: Path
    ) -> None:
        destination_dir = destination_root / f"sub-{subject_id}" / "accel" / f"ses-{session_id}"
        destination_file = destination_dir / f"sub-{subject_id}_ses-{session_id}_accel.csv"

        logger.debug("Planned copy %s -> %s", csv_file, destination_file)
        planned.append((csv_file, destination_file))

    def _iter_session_csvs(session_root: Path) -> List[Path]:
        csv_files = [csv_file for csv_file in sorted(session_root.glob("*RAW.csv")) if csv_file.is_file()]
        for version_dir in sorted(session_root.iterdir()):
            if not version_dir.is_dir() or version_dir.name.upper() not in VERSION_TO_SESSION:
                continue
            csv_files.extend(
                csv_file
                for csv_file in sorted(version_dir.glob("*RAW.csv"))
                if csv_file.is_file()
            )
        return csv_files

    if dump_dirs:
        logger.debug("Detected dump-aware layout with %d dump directory(ies)", len(dump_dirs))
        for dump_dir in dump_dirs:
            session_id = DUMP_TO_SESSION[dump_dir.name]
            for subject_dir in sorted(dump_dir.glob("*_Actigraphy")):
                if not subject_dir.is_dir():
                    continue

                subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
                if not subject_id:
                    logger.debug(
                        "Skipping subject directory %s due to missing subject_id", subject_dir
                    )
                    continue

                logger.debug(
                    "Processing subject %s in %s (session=%s)", subject_id, subject_dir, session_id
                )

                for csv_file in _iter_session_csvs(subject_dir):
                    _plan_csv(subject_id=subject_id, session_id=session_id, csv_file=csv_file)
    else:
        logger.debug("Detected legacy layout (no dump directories present)")
        for subject_dir in sorted(source_root.glob("*_Actigraphy")):
            if not subject_dir.is_dir():
                continue

            subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
            if not subject_id:
                logger.debug("Skipping subject directory %s due to missing subject_id", subject_dir)
                continue

            logger.debug("Processing subject %s in %s", subject_id, subject_dir)

            for session_dir in sorted(subject_dir.iterdir()):
                if not session_dir.is_dir():
                    continue

                session_id = DUMP_TO_SESSION.get(session_dir.name)
                if session_id is not None:
                    for csv_file in _iter_session_csvs(session_dir):
                        _plan_csv(
                            subject_id=subject_id,
                            session_id=session_id,
                            csv_file=csv_file,
                        )
                    continue

                session_id = VERSION_TO_SESSION.get(session_dir.name)
                if session_id is None:
                    logger.debug(
                        "Skipping version directory %s; no session mapping available",
                        session_dir,
                    )
                    continue

                for csv_file in sorted(session_dir.glob("*RAW.csv")):
                    if csv_file.is_file():
                        _plan_csv(
                            subject_id=subject_id, session_id=session_id, csv_file=csv_file
                        )

    if dry_run:
        copied = planned
        _write_report(
            report_path,
            source_root=source_root,
            destination_root=destination_root,
            dry_run=dry_run,
            expected_copies=len(planned),
            raw_count=raw_count,
            sixty_sec_count=sixty_sec_count,
            processed=len(planned),
            copied=0,
            skipped=0,
            last_action="dry run complete",
        )
    else:
        copied = []
        for index, (source, destination) in enumerate(planned, start=1):
            if _needs_copy(source, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary_destination = destination.with_suffix(
                    f"{destination.suffix}.tmp"
                )
                shutil.copyfile(source, temporary_destination)
                temporary_destination.replace(destination)
                copied.append((source, destination))
                last_action = "copied"
            else:
                skipped_existing += 1
                last_action = "skipped existing"

            _render_progress(
                index,
                len(planned),
                copied=len(copied),
                skipped=skipped_existing,
            )
            _write_report(
                report_path,
                source_root=source_root,
                destination_root=destination_root,
                dry_run=dry_run,
                expected_copies=len(planned),
                raw_count=raw_count,
                sixty_sec_count=sixty_sec_count,
                processed=index,
                copied=len(copied),
                skipped=skipped_existing,
                last_action=last_action,
            )
        if planned:
            _finish_progress()

    logger.info(
        "Identified %d planned file(s) for transfer (dry_run=%s, copied=%d, skipped_existing=%d)",
        len(planned),
        dry_run,
        0 if dry_run else len(copied),
        skipped_existing,
    )
    return copied


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Copy actigraphy CSVs into the BIDS-like directory structure."
    )
    parser.add_argument(
        "--base-path",
        help="Root directory that contains the raw and destination folders (defaults to BASE_PATH).",
    )
    parser.add_argument(
        "--raw-folder",
        default=None,
        help="Sub-path relative to base-path containing raw files.",
    )
    parser.add_argument(
        "--dest-folder",
        default=None,
        help="Sub-path relative to base-path where canonical files are written.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Path for the live-updated transfer report.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the files that would be copied without modifying the filesystem.",
    )
    args = parser.parse_args()

    kwargs = {
        "dry_run": args.dry_run,
        "raw_folder": args.raw_folder,
        "dest_folder": args.dest_folder,
    }
    if args.base_path:
        kwargs["base_path"] = Path(args.base_path)
    if args.report_path:
        kwargs["report_path"] = Path(args.report_path)

    try:
        results = copy_actigraphy_to_bids(**kwargs)
        if args.dry_run:
            for source, destination in results:
                print(f"Would copy {source} -> {destination}")
        else:
            print(f"Copied {len(results)} file(s).")
        logger.info("Transfer operation complete (dry_run=%s)", args.dry_run)
    except Exception as exc:  # pragma: no cover - convenience for CLI usage
        logger.exception("Transfer operation failed")
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)
