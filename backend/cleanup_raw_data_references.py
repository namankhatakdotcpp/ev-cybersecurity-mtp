"""
cleanup_raw_data_references.py
Remove stale rows from backend/raw_data/sessions_reference.csv when the session folder no longer exists.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple


BACKEND_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BACKEND_DIR / "raw_data"
REFERENCE_CSV = RAW_DATA_DIR / "sessions_reference.csv"


def _load_rows(csv_path: Path) -> Tuple[List[str], List[dict]]:
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def _filter_existing_session_rows(rows: List[dict]) -> Tuple[List[dict], List[dict]]:
    kept: List[dict] = []
    removed: List[dict] = []

    for row in rows:
        session_folder = str(row.get("session_folder", "")).strip()
        if not session_folder:
            removed.append(row)
            continue

        session_path = RAW_DATA_DIR / session_folder
        if session_path.exists() and session_path.is_dir():
            kept.append(row)
        else:
            removed.append(row)

    return kept, removed


def _write_rows(csv_path: Path, fieldnames: List[str], rows: List[dict]) -> None:
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean stale session rows from backend/raw_data reference CSV")
    parser.add_argument("--dry-run", action="store_true", help="Show rows that would be removed without writing changes")
    args = parser.parse_args()

    if not REFERENCE_CSV.exists():
        print(f"[cleanup] Reference file not found: {REFERENCE_CSV}")
        return

    fieldnames, rows = _load_rows(REFERENCE_CSV)
    if not fieldnames:
        print("[cleanup] Reference CSV has no header; nothing to clean.")
        return

    kept, removed = _filter_existing_session_rows(rows)

    print(f"[cleanup] Total rows: {len(rows)}")
    print(f"[cleanup] Rows to keep: {len(kept)}")
    print(f"[cleanup] Rows to remove: {len(removed)}")

    if removed:
        print("[cleanup] Removed session folders:")
        for row in removed:
            print(f"  - {row.get('session_folder', '')}")

    if args.dry_run:
        print("[cleanup] Dry-run mode: no file changes written.")
        return

    _write_rows(REFERENCE_CSV, fieldnames, kept)
    print(f"[cleanup] Updated reference CSV: {REFERENCE_CSV}")


if __name__ == "__main__":
    main()
