#!/usr/bin/env python3
"""ingest_blastp_rollups.py — fold the per-strain DATED rollup CSVs into blastp.sqlite.

The default is a read-only dry run.  ``--execute`` requires an explicit portable
``--source-workspace`` provenance label and performs one atomic named-column insert.
Missing or look-alike databases are typed holds and are never created.

Usage:
  python tools/ingest_blastp_rollups.py
  python tools/ingest_blastp_rollups.py --execute --source-workspace operator-import
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
import glob
import os
from pathlib import Path
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mamey.blastp_ingest import (
    BlastpStoreSchemaError,
    insert_blastp_hits,
    open_blastp_hits_store,
    validate_blastp_source_workspace,
)
from mamey.workspace_root import workspace_root


PATTERNS = (
    "strain_data/*/blastp_nr_*/*_nr_top10_*.csv",
    "strain_data/*/blastp_clustered_nr_*/*_clustered_nr_top10_*.csv",
)
EXCLUDE_STRAINS = {
    value.strip()
    for value in os.environ.get("SAPOTE_EXCLUDE_STRAINS", "").split(",")
    if value.strip()
}


def _num(value, cast=float):
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _allowed_channels(path: Path) -> set[str]:
    if "_clustered_nr_top10_" in path.name:
        return {"clustered_nr", "ncbi_clustered_nr"}
    return {"nr", "ncbi_nr"}


def _arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--execute", action="store_true", help="Commit admitted rows atomically.")
    parser.add_argument("--root", help="Logical source root; defaults to the workspace-root contract.")
    parser.add_argument("--db", help="Existing BLASTP SQLite store; defaults below --root.")
    parser.add_argument(
        "--source-workspace",
        help="Portable provenance label; mandatory with --execute (for example operator-import).",
    )
    args = parser.parse_args(argv)
    if args.execute and not str(args.source_workspace or "").strip():
        parser.error("--source-workspace is required with --execute")
    return args


def main(argv=None) -> int:
    args = _arguments(argv)
    root = Path(args.root).expanduser().resolve() if args.root else workspace_root().resolve()
    database = (
        Path(args.db).expanduser().resolve()
        if args.db
        else root / "BLASTp Database" / "blastp.sqlite"
    )
    source_workspace = "DRY_RUN_UNBOUND_SOURCE"
    if args.source_workspace:
        try:
            source_workspace = validate_blastp_source_workspace(args.source_workspace)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    try:
        connection = open_blastp_hits_store(database, writable=args.execute)
    except (FileNotFoundError, BlastpStoreSchemaError) as exc:
        raise SystemExit(str(exc)) from exc

    try:
        cursor = connection.cursor()
        have = set(cursor.execute("SELECT strain, channel, gene FROM hits"))
        files: list[Path] = []
        for pattern in PATTERNS:
            files.extend(Path(path) for path in glob.glob(str(root / pattern)))
        files = sorted(set(files))

        added: defaultdict[str, int] = defaultdict(int)
        newkeys: set[tuple[str, str, str]] = set()
        batch: list[tuple[object, ...]] = []
        skipped_files = 0
        for path in files:
            rel = os.path.relpath(path, root)
            if cursor.execute(
                "SELECT 1 FROM hits WHERE source_file=? LIMIT 1", (rel,)
            ).fetchone():
                skipped_files += 1
                continue
            mtime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)
            )
            try:
                with path.open(newline="", encoding="utf-8", errors="replace") as handle:
                    rows = list(csv.DictReader(handle))
            except (OSError, csv.Error) as exc:
                emit(f"  ! skip {rel}: {exc}", file=sys.stderr)
                continue
            allowed = _allowed_channels(path)
            for row_number, row in enumerate(rows, start=2):
                strain = (row.get("strain") or "").strip()
                if strain in EXCLUDE_STRAINS:
                    continue
                channel = (row.get("channel") or "").strip()
                gene = (row.get("gene") or "").strip()
                if channel not in allowed:
                    raise SystemExit(
                        "BLASTP_ROLLUP_CHANNEL_HOLD: "
                        f"{rel}:{row_number} channel={channel!r}; expected one of {sorted(allowed)!r}"
                    )
                if not strain or not gene:
                    continue
                key = (strain, channel, gene)
                if key in have or key in newkeys:
                    continue
                newkeys.add(key)
                added[strain] += 1
                batch.append(
                    (
                        source_workspace,
                        strain,
                        (row.get("bgc_id") or "").strip(),
                        gene,
                        _num(row.get("aa_length"), int),
                        row.get("role") or "",
                        row.get("domains") or "",
                        _num(row.get("hit_rank"), int),
                        (row.get("subject_acc") or "").strip(),
                        row.get("subject_organism") or "",
                        row.get("subject_def") or "",
                        row.get("subject_db") or "",
                        _num(row.get("pct_identity")),
                        _num(row.get("align_length"), int),
                        _num(row.get("query_coverage")),
                        _num(row.get("evalue")),
                        _num(row.get("bitscore")),
                        _num(row.get("pct_positives")),
                        channel,
                        rel,
                        mtime,
                        0,
                    )
                )

        emit(f'rollup files found: {len(files)}  (already-ingested source_files skipped: {skipped_files})', f'NEW (strain,channel,gene) rows to add: {len(batch)}  across {len(added)} strains', sep="\n")
        for strain in sorted(added):
            emit(f"   {strain}: +{added[strain]}")
        if args.execute:
            inserted = insert_blastp_hits(connection, batch)
            emit(f"\nEXECUTED: inserted {inserted} rows.")
        else:
            emit("\nDRY-RUN — read-only store opened; nothing written.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
