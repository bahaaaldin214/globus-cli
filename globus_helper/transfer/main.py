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


def _count_source_files(source_root: Path) -> tuple[int, int, int]:
    raw_count = sum(1 for _ in source_root.rglob("*RAW.csv"))
    sixty_sec_count = sum(1 for _ in source_root.rglob("*60sec.csv"))
    gt3x_count = sum(1 for _ in source_root.rglob("*.gt3x"))
    return raw_count, sixty_sec_count, gt3x_count


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
    gt3x_count: int,
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
        f"GT3X binary files found: {gt3x_count}",
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
    """Copy the actigraphy files into a BIDS-compliant directory structure.

    Prioritizes .gt3x files over RAW.csv to save storage space.
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
    raw_count, sixty_sec_count, gt3x_count = _count_source_files(source_root)

    dump_dirs = [
        dump_dir
        for dump_dir in sorted(source_root.iterdir())
        if dump_dir.is_dir() and dump_dir.name in DUMP_TO_SESSION
    ]

    def _plan_file(
        *, subject_id: str, session_id: str, source_file: Path
    ) -> None:
        destination_dir = destination_root / f"sub-{subject_id}" / "accel" / f"ses-{session_id}"
        ext = source_file.suffix.lower()
        destination_file = destination_dir / f"sub-{subject_id}_ses-{session_id}_accel{ext}"

        logger.debug("Planned copy %s -> %s", source_file, destination_file)
        planned.append((source_file, destination_file))

    def _iter_session_files(session_root: Path) -> List[Path]:
        """Find candidates, prioritizing .gt3x over RAW.csv."""
        # Check for .gt3x in this dir
        gt3x_files = list(session_root.glob("*.gt3x"))
        if gt3x_files:
            return sorted(gt3x_files)

        # Fallback to RAW.csv
        raw_files = [f for f in sorted(session_root.glob("*RAW.csv")) if f.is_file()]
        
        for version_dir in sorted(session_root.iterdir()):
            if not version_dir.is_dir() or version_dir.name.upper() not in VERSION_TO_SESSION:
                continue
            
            v_gt3x = list(version_dir.glob("*.gt3x"))
            if v_gt3x:
                return sorted(v_gt3x)
                
            raw_files.extend(
                f for f in sorted(version_dir.glob("*RAW.csv")) if f.is_file()
            )
        return raw_files

    if dump_dirs:
        logger.debug("Detected dump-aware layout with %d dump directory(ies)", len(dump_dirs))
        for dump_dir in dump_dirs:
            session_id = DUMP_TO_SESSION[dump_dir.name]
            for subject_dir in sorted(dump_dir.glob("*_Actigraphy")):
                if not subject_dir.is_dir():
                    continue

                subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
                if not subject_id:
                    continue

                for f in _iter_session_files(subject_dir):
                    _plan_file(subject_id=subject_id, session_id=session_id, source_file=f)
    else:
        logger.debug("Detected legacy layout")
        for subject_dir in sorted(source_root.glob("*_Actigraphy")):
            if not subject_dir.is_dir():
                continue

            subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
            if not subject_id:
                continue

            for session_dir in sorted(subject_dir.iterdir()):
                if not session_dir.is_dir():
                    continue

                session_id = DUMP_TO_SESSION.get(session_dir.name)
                if session_id is not None:
                    for f in _iter_session_files(session_dir):
                        _plan_file(subject_id=subject_id, session_id=session_id, source_file=f)
                    continue

                session_id = VERSION_TO_SESSION.get(session_dir.name)
                if session_id is None:
                    continue

                for f in sorted(session_dir.glob("*.gt3x")):
                    _plan_file(subject_id=subject_id, session_id=session_id, source_file=f)
                
                # Only if no gt3x found in this session_dir
                if not list(session_dir.glob("*.gt3x")):
                    for f in sorted(session_dir.glob("*RAW.csv")):
                        _plan_file(subject_id=subject_id, session_id=session_id, source_file=f)

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
            gt3x_count=gt3x_count,
            processed=len(planned),
            copied=0,
            skipped=0,
            last_action="dry run complete",
        )
    else:
        copied = []

        def _copy_one(item: Tuple[Path, Path]) -> Tuple[str, Path, Path]:
            source, destination = item
            if _needs_copy(source, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary_destination = destination.with_suffix(
                    f"{destination.suffix}.tmp"
                )
                shutil.copyfile(source, temporary_destination)
                temporary_destination.replace(destination)
                return ("copied", source, destination)
            return ("skipped existing", source, destination)

        # ponytail: copies are I/O-bound over a network mount, so a thread pool
        # (GIL released during I/O) parallelizes well. TRANSFER_WORKERS tunes it;
        # set 1 for serial. Report is written periodically, not per file.
        workers = int(os.environ.get("TRANSFER_WORKERS", "8"))
        workers = max(1, workers)
        if planned:
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=workers) as executor:
                for index, (last_action, _src, _dst) in enumerate(
                    executor.map(_copy_one, planned), start=1
                ):
                    if last_action == "copied":
                        copied.append((_src, _dst))
                    else:
                        skipped_existing += 1

                    _render_progress(
                        index,
                        len(planned),
                        copied=len(copied),
                        skipped=skipped_existing,
                    )
                    if index % 25 == 0 or index == len(planned):
                        _write_report(
                            report_path,
                            source_root=source_root,
                            destination_root=destination_root,
                            dry_run=dry_run,
                            expected_copies=len(planned),
                            raw_count=raw_count,
                            sixty_sec_count=sixty_sec_count,
                            gt3x_count=gt3x_count,
                            processed=index,
                            copied=len(copied),
                            skipped=skipped_existing,
                            last_action=last_action,
                        )
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
