"""Build per-strain BLASTp databases from a read-only cohort or strain store."""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

from .blastp_ingest import BLASTP_HITS_COLUMNS, BLASTP_HITS_SCHEMA


class StrainBlastpHold(ValueError):
    """A source or identity ambiguity prevents a reliable export."""


_STRAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise StrainBlastpHold("SOURCE_MISSING")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _roster(package: Path) -> tuple[str, list[tuple], Path, Path]:
    manifest = package / "manifest.json"
    tables = sorted(package.glob("*cds_table.csv"))
    if not manifest.is_file() or len(tables) != 1:
        raise StrainBlastpHold("PACKAGE_BINDING")
    try:
        strain = str(json.loads(manifest.read_text(encoding="utf-8"))["strain_id"]).strip()
    except (ValueError, KeyError, TypeError) as exc:
        raise StrainBlastpHold("MANIFEST_INVALID") from exc
    if not _STRAIN_RE.fullmatch(strain):
        raise StrainBlastpHold("STRAIN_ID_INVALID")
    found: dict[str, tuple] = {}
    with tables[0].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"strain", "contig", "region", "bgc_id", "locus_tag", "length_aa"}
        if not required.issubset(reader.fieldnames or []):
            raise StrainBlastpHold("CDS_SCHEMA")
        for row in reader:
            gene = str(row["locus_tag"] or "").strip()
            contig = str(row["contig"] or "").strip()
            region = str(row["region"] or "").strip()
            alias = str(row["bgc_id"] or "").strip()
            if ((row["strain"] or "").strip() != strain or not gene or not contig
                    or not re.fullmatch(r"region\d+", region)
                    or not re.fullmatch(r"BGC\d+", alias)):
                raise StrainBlastpHold("CDS_IDENTITY")
            try:
                aa = int(row["length_aa"])
            except (ValueError, TypeError) as exc:
                raise StrainBlastpHold("CDS_LENGTH") from exc
            if aa <= 0:
                raise StrainBlastpHold("CDS_LENGTH")
            identity = (gene, contig, region, alias, aa)
            if gene in found and found[gene] != identity:
                raise StrainBlastpHold("GENE_AMBIGUOUS")
            found[gene] = identity
    if not found:
        raise StrainBlastpHold("EMPTY_ROSTER")
    return strain, sorted(found.values()), manifest, tables[0]


def _source_schema(connection: sqlite3.Connection) -> None:
    columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(hits)"))
    if columns != BLASTP_HITS_COLUMNS:
        raise StrainBlastpHold("HITS_SCHEMA")


def _create_schema(connection: sqlite3.Connection) -> None:
    columns = ", ".join(
        f"{name} {kind}{' NOT NULL' if required else ''}"
        for name, kind, required in BLASTP_HITS_SCHEMA
    )
    connection.execute(f"CREATE TABLE hits ({columns})")
    connection.execute(
        "CREATE TABLE locus_identity (gene TEXT PRIMARY KEY, contig TEXT NOT NULL, "
        "region TEXT NOT NULL, bgc_alias TEXT NOT NULL, aa_length INTEGER NOT NULL)"
    )
    connection.execute("CREATE INDEX hits_by_gene_channel ON hits(strain,gene,channel,hit_rank)")
    connection.execute(
        """CREATE VIEW hit_binding AS
        SELECT h.rowid AS hit_rowid,h.gene,h.channel,
          CASE
            WHEN i.gene IS NULL THEN 'NONCURRENT_LOCUS'
            WHEN h.aa_length IS NULL OR typeof(h.aa_length) != 'integer'
                 OR h.aa_length <= 0 THEN 'ZERO_OR_BLANK_AA_LENGTH'
            WHEN h.aa_length != i.aa_length THEN 'QUERY_CURRENT_AA_LENGTH_MISMATCH'
            WHEN h.provenance_suspect IS NOT NULL AND h.provenance_suspect != 0
                 THEN 'PROVENANCE_SUSPECT'
            ELSE 'LOCUS_BOUND'
          END AS binding_state
        FROM hits h LEFT JOIN locus_identity i ON i.gene=h.gene"""
    )
    connection.execute(
        "CREATE VIEW locus_bound_hits AS SELECT h.* FROM hits h JOIN hit_binding b "
        "ON b.hit_rowid=h.rowid WHERE b.binding_state='LOCUS_BOUND'"
    )
    connection.execute(
        "CREATE VIEW held_hits AS SELECT b.binding_state,h.* FROM hits h JOIN hit_binding b "
        "ON b.hit_rowid=h.rowid WHERE b.binding_state!='LOCUS_BOUND'"
    )
    connection.execute(
        """CREATE VIEW coverage AS
        SELECT i.gene,i.contig,i.region,i.bgc_alias,i.aa_length,
          MAX(CASE WHEN h.channel='ncbi_nr' THEN 1 ELSE 0 END) AS has_nr,
          MAX(CASE WHEN h.channel='ncbi_clustered_nr' THEN 1 ELSE 0 END) AS has_clustered_nr,
          MAX(CASE WHEN h.channel='local_swissprot' THEN 1 ELSE 0 END) AS has_swissprot,
          MAX(CASE WHEN h.channel='ncbi_nr' THEN h.pct_identity END) AS best_nr,
          MAX(CASE WHEN h.channel='ncbi_clustered_nr' THEN h.pct_identity END) AS best_clustered
        FROM locus_identity i LEFT JOIN locus_bound_hits h ON h.gene=i.gene
        GROUP BY i.gene"""
    )
    connection.execute(
        "CREATE VIEW clustered_gap AS SELECT gene,contig,region,bgc_alias,aa_length "
        "FROM coverage WHERE has_nr=1 AND has_clustered_nr=0"
    )
    connection.execute(
        "CREATE VIEW unbound_hits AS SELECT h.* FROM hits h LEFT JOIN locus_identity i "
        "ON i.gene=h.gene WHERE i.gene IS NULL"
    )
    connection.execute("CREATE TABLE source_receipt (key TEXT PRIMARY KEY,value TEXT NOT NULL)")


def _snapshot_source(source_db: Path, out_root: Path) -> tuple[Path, str]:
    """Keep one transactionally consistent SQLite backup, including committed WAL rows."""
    temporary = out_root / f".blastp_source.{uuid.uuid4().hex}.tmp"
    try:
        with contextlib.closing(_readonly(source_db)) as source:
            _source_schema(source)
            with contextlib.closing(sqlite3.connect(temporary)) as destination:
                source.backup(destination)
        with contextlib.closing(_readonly(temporary)) as snapshot:
            _source_schema(snapshot)
            if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise StrainBlastpHold("SOURCE_SNAPSHOT_INTEGRITY")
        digest = _sha256(temporary)
        target = out_root / f"source_snapshot_{digest}.sqlite"
        if target.exists():
            if _sha256(target) != digest:
                raise StrainBlastpHold("SOURCE_SNAPSHOT_COLLISION")
        else:
            os.replace(temporary, target)
        return target, digest
    finally:
        temporary.unlink(missing_ok=True)


def _build_from_snapshot(
    snapshot: Path, snapshot_hash: str, binding: tuple, source_strain: str,
    out_root: Path,
    *, replace: bool = False,
) -> dict:
    strain, roster, manifest, cds = binding
    target = out_root / f"{strain}_blastp.db"
    if target.exists() and not replace:
        raise StrainBlastpHold("OUTPUT_EXISTS")
    temporary = out_root / f".{strain}_blastp.{uuid.uuid4().hex}.tmp"
    try:
        with contextlib.closing(_readonly(snapshot)) as source:
            with contextlib.closing(sqlite3.connect(temporary)) as output:
                with output:
                    _create_schema(output)
                    output.executemany("INSERT INTO locus_identity VALUES (?,?,?,?,?)", roster)
                    names = ", ".join(BLASTP_HITS_COLUMNS)
                    placeholders = ", ".join("?" for _ in BLASTP_HITS_COLUMNS)
                    cursor = source.execute(
                        f"SELECT {names} FROM hits WHERE strain=? ORDER BY gene,channel,hit_rank",
                        (source_strain,),
                    )
                    output.executemany(
                        f"INSERT INTO hits ({names}) VALUES ({placeholders})", cursor
                    )
                    counts = {
                        "strain": strain,
                        "source_strain": source_strain,
                        "genes": output.execute("SELECT COUNT(*) FROM locus_identity").fetchone()[0],
                        "raw_hits": output.execute("SELECT COUNT(*) FROM hits").fetchone()[0],
                        "locus_bound_hits": output.execute("SELECT COUNT(*) FROM locus_bound_hits").fetchone()[0],
                        "held_hit_rows": output.execute("SELECT COUNT(*) FROM held_hits").fetchone()[0],
                        "unbound_hit_rows": output.execute("SELECT COUNT(*) FROM unbound_hits").fetchone()[0],
                        "with_nr": output.execute("SELECT COUNT(*) FROM coverage WHERE has_nr=1").fetchone()[0],
                        "with_clustered_nr": output.execute("SELECT COUNT(*) FROM coverage WHERE has_clustered_nr=1").fetchone()[0],
                        "with_swissprot": output.execute("SELECT COUNT(*) FROM coverage WHERE has_swissprot=1").fetchone()[0],
                    }
                    receipt = {
                        "schema": "mamey_blastp_strain_db_v2",
                        "source_snapshot_sha256": snapshot_hash,
                        "source_snapshot_file": snapshot.name,
                        "package_strain": strain,
                        "source_strain": source_strain,
                        "package_manifest_sha256": _sha256(manifest),
                        "package_cds_sha256": _sha256(cds),
                        **counts,
                    }
                    output.executemany(
                        "INSERT INTO source_receipt VALUES (?,?)",
                        [(key, str(value)) for key, value in receipt.items()],
                    )
                    if output.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise StrainBlastpHold("OUTPUT_INTEGRITY")
        if target.exists() and not replace:
            raise StrainBlastpHold("OUTPUT_EXISTS")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(target), **counts}


def build_many(
    source_db: Path, packages: list[Path], out_root: Path, *, replace: bool = False,
    source_strains: dict[str, str] | None = None, allow_empty: bool = False,
) -> list[dict]:
    source_db = Path(source_db).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    bindings = [_roster(Path(package).expanduser().resolve()) for package in packages]
    if not bindings:
        raise StrainBlastpHold("NO_PACKAGES")
    strains = [item[0] for item in bindings]
    if len(strains) != len(set(strains)):
        raise StrainBlastpHold("DUPLICATE_STRAIN_PACKAGE")
    source_strains = source_strains or {}
    if set(source_strains) - set(strains):
        raise StrainBlastpHold("STRAIN_MAP_UNUSED_PACKAGE")
    selected = [source_strains.get(strain, strain) for strain in strains]
    if any(not _STRAIN_RE.fullmatch(strain) for strain in selected):
        raise StrainBlastpHold("SOURCE_STRAIN_INVALID")
    if len(selected) != len(set(selected)):
        raise StrainBlastpHold("SOURCE_STRAIN_REUSED")
    targets = [out_root / f"{strain}_blastp.db" for strain in strains]
    if source_db in targets:
        raise StrainBlastpHold("SOURCE_EQUALS_OUTPUT")
    if not replace and any(target.exists() for target in targets):
        raise StrainBlastpHold("OUTPUT_EXISTS")
    out_root.mkdir(parents=True, exist_ok=True)
    snapshot, digest = _snapshot_source(source_db, out_root)
    with contextlib.closing(_readonly(snapshot)) as source:
        present = {row[0] for row in source.execute(
            "SELECT DISTINCT strain FROM hits WHERE strain IN ("
            + ",".join("?" for _ in selected) + ")", selected
        )}
    if not allow_empty and set(selected) - present:
        raise StrainBlastpHold("SOURCE_STRAIN_ABSENT: "
                               + ",".join(sorted(set(selected) - present)))
    return [_build_from_snapshot(snapshot, digest, binding, source_strain,
                                 out_root, replace=replace)
            for binding, source_strain in zip(bindings, selected)]


def build(
    source_db: Path, package: Path, out_root: Path, *, replace: bool = False,
) -> dict:
    return build_many(source_db, [package], out_root, replace=replace)[0]


def _read_strain_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["package_strain", "source_strain"]:
            raise StrainBlastpHold("STRAIN_MAP_SCHEMA")
        for row in reader:
            package_strain = str(row["package_strain"] or "").strip()
            source_strain = str(row["source_strain"] or "").strip()
            if (not _STRAIN_RE.fullmatch(package_strain)
                    or not _STRAIN_RE.fullmatch(source_strain)):
                raise StrainBlastpHold("STRAIN_MAP_ID_INVALID")
            if package_strain in mapping:
                raise StrainBlastpHold("STRAIN_MAP_DUPLICATE")
            mapping[package_strain] = source_strain
    return mapping


def inspect(database: Path) -> dict:
    database = Path(database).expanduser().resolve()
    with contextlib.closing(_readonly(database)) as connection:
        _source_schema(connection)
        names = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )}
        if not {"coverage", "clustered_gap"}.issubset(names):
            raise StrainBlastpHold("COVERAGE_SCHEMA")
        strains = [row[0] for row in connection.execute(
            "SELECT DISTINCT strain FROM hits ORDER BY strain"
        )]
        if len(strains) > 1:
            raise StrainBlastpHold("MIXED_SOURCE")
        return {
            "path": str(database),
            "schema": (
                "mamey_blastp_strain_db_v2" if "hit_binding" in names
                else "mamey_blastp_strain_db_v1" if "locus_identity" in names
                else "legacy_per_strain"
            ),
            "strains_in_hits": strains,
            "hits": connection.execute("SELECT COUNT(*) FROM hits").fetchone()[0],
            "genes": connection.execute("SELECT COUNT(*) FROM coverage").fetchone()[0],
            "clustered_gap": connection.execute("SELECT COUNT(*) FROM clustered_gap").fetchone()[0],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("build", help="Export packages into separate per-strain DBs")
    make.add_argument("--source-db", required=True, type=Path)
    make.add_argument("--package", required=True, type=Path, nargs="+")
    make.add_argument("--out", required=True, type=Path)
    make.add_argument("--replace", action="store_true")
    make.add_argument("--strain-map", type=Path,
                      help="reviewed TSV: package_strain, source_strain")
    make.add_argument("--allow-empty", action="store_true",
                      help="explicitly permit a strain with zero source hits")
    check = sub.add_parser("inspect", help="Read an existing per-strain DB")
    check.add_argument("--db", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect(args.db)
        else:
            mapping = _read_strain_map(args.strain_map) if args.strain_map else None
            result = build_many(args.source_db, args.package, args.out,
                                replace=args.replace, source_strains=mapping,
                                allow_empty=args.allow_empty)
    except (StrainBlastpHold, sqlite3.DatabaseError, OSError) as exc:
        sys.stderr.write(f"BLASTP_STRAIN_DB_HOLD: {type(exc).__name__}: {exc}\n")
        return 2
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
