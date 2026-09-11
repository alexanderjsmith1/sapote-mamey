"""Portable adapter for a hash-bound external MIBiG convergence extension.

This module does not create or discover databases. Callers provide the exact
database and dependency-manifest paths. The adapter emits rows compatible with
``mode_b.gene_first_explore.load_evidence_index`` and makes no biological call.
"""
from __future__ import annotations

import csv
from mamey.csv_safety import SafeDictWriter
import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Mapping

SCHEMA = "current_mibig_convergence_extension_v1"
MANIFEST_SCHEMA = "mamey.mibig-extension-dependency/1"
CLAIM_CEILING = (
    "Pathway-family sequence-similarity evidence only; not exact product identity, "
    "expression, production, bioactivity, novelty, or scientific acceptance."
)
INDEX_FIELDS = (
    "channel", "strain", "full_node", "region", "bgc_alias", "gene",
    "evidence_state", "source_locator", "source_sha256", "note",
)


class MibigExtensionHold(ValueError):
    """Typed refusal for incomplete identity, provenance, or dependency binding."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identity(strain: str, full_node: str, region: str, bgc_alias: str) -> tuple[str, ...]:
    values = tuple(str(value or "").strip() for value in (strain, full_node, region, bgc_alias))
    if any(not value for value in values):
        raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: incomplete four-part identity")
    return values


def _load_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MibigExtensionHold("MIBIG_EXTENSION_DEPENDENCY_HOLD: manifest unreadable") from exc
    required = {"schema", "extension_sha256", "reference_dependency_sha256"}
    if manifest.get("schema") != MANIFEST_SCHEMA or not required <= set(manifest):
        raise MibigExtensionHold("MIBIG_EXTENSION_DEPENDENCY_HOLD: manifest schema mismatch")
    return manifest


def open_bound_extension(database: str | Path, dependency_manifest: str | Path) -> tuple[sqlite3.Connection, str]:
    database = Path(database).expanduser().resolve()
    dependency_manifest = Path(dependency_manifest).expanduser().resolve()
    manifest = _load_manifest(dependency_manifest)
    if not database.is_file() or _sha256(database) != manifest["extension_sha256"]:
        raise MibigExtensionHold("MIBIG_EXTENSION_DEPENDENCY_HOLD: extension hash mismatch")
    con = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        meta = {row["key"]: row["value"] for row in con.execute("SELECT key,value FROM metadata")}
        if meta.get("schema_version") != SCHEMA:
            raise MibigExtensionHold("MIBIG_EXTENSION_SCHEMA_HOLD: database schema mismatch")
        dep = con.execute("SELECT sha256,bulk_rows_copied FROM reference_dependency").fetchall()
        if len(dep) != 1 or dep[0]["bulk_rows_copied"] != 0:
            raise MibigExtensionHold("MIBIG_EXTENSION_DEPENDENCY_HOLD: invalid reference dependency")
        if dep[0]["sha256"] != manifest["reference_dependency_sha256"]:
            raise MibigExtensionHold("MIBIG_EXTENSION_DEPENDENCY_HOLD: reference hash mismatch")
        vocabulary = {row[0] for row in con.execute("SELECT state FROM evidence_state_vocabulary")}
        expected = {"OBSERVED", "MISSING", "NOT_RUN", "UNBOUND", "PARSE_FAILED", "TESTED_NO_CALL"}
        if vocabulary != expected:
            raise MibigExtensionHold("MIBIG_EXTENSION_SCHEMA_HOLD: evidence-state vocabulary mismatch")
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or con.execute("PRAGMA foreign_key_check").fetchall():
            raise MibigExtensionHold("MIBIG_EXTENSION_SCHEMA_HOLD: integrity check failed")
    except MibigExtensionHold:
        con.close()
        raise
    except (sqlite3.DatabaseError, KeyError) as exc:
        con.close()
        raise MibigExtensionHold("MIBIG_EXTENSION_SCHEMA_HOLD: unreadable database") from exc
    return con, manifest["extension_sha256"]


def gene_first_rows(
    con: sqlite3.Connection,
    extension_sha256: str,
    *,
    strain: str,
    full_node: str,
    region: str,
    bgc_alias: str,
    protein_roster: Mapping[str, str],
) -> list[dict[str, str]]:
    identity = _identity(strain, full_node, region, bgc_alias)
    loci = con.execute(
        "SELECT * FROM locus WHERE strain=? AND full_contig=? AND region=? AND bgc_alias=?", identity
    ).fetchall()
    if len(loci) != 1:
        raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: locus does not resolve uniquely")
    locus = loci[0]
    genes = con.execute(
        "SELECT g.*,s.state,s.hit_row_count FROM gene g JOIN gene_channel_state s USING(gene_key) "
        "WHERE g.locus_key=? ORDER BY g.gene_order,g.locus_tag", (locus["locus_key"],)
    ).fetchall()
    if not genes or set(protein_roster) != {row["locus_tag"] for row in genes}:
        raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: protein roster gene set mismatch")
    rows = []
    for gene in genes:
        if protein_roster[gene["locus_tag"]] != gene["protein_sha256"]:
            raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: protein hash mismatch")
        bindings = Counter(row[0] for row in con.execute(
            "SELECT reference_binding_state FROM mibig_hit WHERE gene_key=?", (gene["gene_key"],)
        ) if row[0] != "BOUND_EXISTING_REFERENCE_PRODUCT")
        observed = gene["hit_row_count"] > 0
        note = (
            f"{gene['hit_row_count']} current-package manifest-bound MIBiG row(s); "
            f"external-reference holds={json.dumps(dict(bindings), sort_keys=True)}; {CLAIM_CEILING}"
            if observed else
            "No MIBiG hit reported in the current package; workflow missingness, not biological absence."
        )
        rows.append({
            "channel": "mibig", "strain": identity[0], "full_node": identity[1],
            "region": identity[2], "bgc_alias": identity[3], "gene": gene["locus_tag"],
            "evidence_state": "BOUND" if observed else "MISSING",
            "source_locator": f"evidence://current-mibig-convergence/{locus['locus_key']}#gene={gene['locus_tag']}",
            "source_sha256": extension_sha256, "note": note,
        })
    return rows


def write_gene_first_index(path: str | Path, rows: list[dict[str, str]]) -> Path:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = SafeDictWriter(handle, fieldnames=INDEX_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return path


def load_protein_roster(path: str | Path) -> dict[str, str]:
    path = Path(path).expanduser().resolve()
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != ["gene", "protein_sha256"]:
                raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: roster schema mismatch")
            roster = {}
            for row in reader:
                gene, digest = row["gene"].strip(), row["protein_sha256"].strip().lower()
                if not gene or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                    raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: malformed roster row")
                if gene in roster:
                    raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: duplicate roster gene")
                roster[gene] = digest
    except OSError as exc:
        raise MibigExtensionHold("MIBIG_EXTENSION_IDENTITY_HOLD: roster unreadable") from exc
    return roster


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--dependency-manifest", required=True)
    parser.add_argument("--strain", required=True)
    parser.add_argument("--full-node", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--bgc-alias", required=True)
    parser.add_argument("--protein-roster", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    con, digest = open_bound_extension(args.database, args.dependency_manifest)
    try:
        rows = gene_first_rows(
            con, digest, strain=args.strain, full_node=args.full_node, region=args.region,
            bgc_alias=args.bgc_alias, protein_roster=load_protein_roster(args.protein_roster),
        )
        write_gene_first_index(args.output, rows)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
