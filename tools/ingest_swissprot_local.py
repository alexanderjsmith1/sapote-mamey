#!/usr/bin/env python3
"""ingest_swissprot_local.py — fold the local SwissProt BLASTp CSVs into blastp.sqlite.

The default is a read-only dry run.  ``--execute`` requires an explicit portable
``--source-workspace`` provenance label and performs one atomic named-column insert.
Missing or look-alike databases are typed holds and are never created.  Imported
similarity remains on the separate ``local_swissprot`` channel.

Usage:
  python tools/ingest_swissprot_local.py
  python tools/ingest_swissprot_local.py --execute --source-workspace operator-import
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
from mamey.exclusions import raw_analysis_excluded
from mamey.workspace_root import workspace_root


SUFFIX = "_blastp_top10_local.csv"
CHANNEL = "local_swissprot"
SUBJECT_DB = "swissprot"
EXCLUDE_STRAINS = raw_analysis_excluded() | {"AS-000_CONSDARK"}


def _num(value, cast=float):
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def is_target(path: str | Path) -> bool:
    candidate = Path(path)
    if "_top_hit_per_gene" in candidate.name:
        return False
    if "_raw" in candidate.parts:
        return False
    return candidate.name.endswith(SUFFIX)


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
        have = set(
            cursor.execute(
                "SELECT strain, channel, gene FROM hits WHERE channel=?", (CHANNEL,)
            )
        )
        scan_roots = (
            root / "Local Blastp RESULTS (SwissProt)",
            root / "Blastp RESULTS" / "_SWISSPROT_RETRY",
        )
        files: list[Path] = []
        for scan_root in scan_roots:
            files.extend(
                Path(path)
                for path in glob.glob(str(scan_root / "**" / "*.csv"), recursive=True)
            )
        files = sorted(path for path in set(files) if is_target(path))

        added: defaultdict[str, int] = defaultdict(int)
        newkeys: set[tuple[str, str, str]] = set()
        batch: list[tuple[object, ...]] = []
        skipped_source_file = 0
        unreadable = 0
        for path in files:
            rel = os.path.relpath(path, root)
            if cursor.execute(
                "SELECT 1 FROM hits WHERE source_file=? LIMIT 1", (rel,)
            ).fetchone():
                skipped_source_file += 1
                continue
            mtime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)
            )
            try:
                with path.open(newline="", encoding="utf-8", errors="replace") as handle:
                    rows = list(csv.DictReader(handle))
            except (OSError, csv.Error) as exc:
                emit(f"  ! skip {rel}: {exc}", file=sys.stderr)
                unreadable += 1
                continue
            for row in rows:
                strain = (row.get("strain") or "").strip()
                gene = (row.get("gene") or "").strip()
                if not strain or not gene or strain in EXCLUDE_STRAINS:
                    continue
                key = (strain, CHANNEL, gene)
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
                        (row.get("subject_db") or SUBJECT_DB).strip() or SUBJECT_DB,
                        _num(row.get("pct_identity")),
                        _num(row.get("align_length"), int),
                        _num(row.get("query_coverage")),
                        _num(row.get("evalue")),
                        _num(row.get("bitscore")),
                        _num(row.get("pct_positives")),
                        CHANNEL,
                        rel,
                        mtime,
                        0,
                    )
                )

        emit(f'swissprot local csv files: {len(files)}  | skipped already-ingested source_files: {skipped_source_file}  | unreadable: {unreadable}', f"NEW (strain,'{CHANNEL}',gene) rows to add: {len(batch)}  across {len(added)} strains", sep="\n")
        for strain in sorted(added):
            emit(f"   {strain}: +{added[strain]}")
        if args.execute:
            inserted = insert_blastp_hits(connection, batch)
            emit(f"\nEXECUTED: inserted {inserted} {CHANNEL} rows.")
        else:
            emit("\nDRY-RUN — read-only store opened; nothing written.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
