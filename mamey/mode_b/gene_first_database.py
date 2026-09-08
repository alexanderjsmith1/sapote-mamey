"""Pinned offline database observations for the existing gene-first composer.

Package roster is conserved. Census geometry and package protein sequence must
both agree before a search projection is bound. No scientific admission occurs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import Counter

from ..tool_database_reader import inspect_tool_database, ToolDatabaseInspectionError
from .gene_first_explore import GeneFirstHold, _sha256, _observation, _md_escape
from .gene_first_store_bridge import read_round_fasta

ADAPTERS = {"census": "gene-census-v1", "nr": "blastp-nr-v1",
            "clusterednr": "blastp-clustered-nr-v1", "local_swissprot": "blastp-swissprot-v2"}


def _hold(code):
    raise GeneFirstHold("MODEB_GENE_FIRST_DATABASE_HOLD: " + code)


def _unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            _hold("DUPLICATE_SELECTION_KEY")
        result[k] = v
    return result


def _sealed_file(package, path, manifest):
    if path.parent != package or not path.is_file() or path.is_symlink():
        _hold("PACKAGE_FILE_NOT_LOCAL")
    records = [x for x in manifest.get("files", []) if x.get("path") == path.name]
    digest = _sha256(path)
    if len(records) != 1 or records[0].get("sha256") != digest:
        _hold("PACKAGE_FILE_HASH_MISMATCH")
    return digest


def _all_records(report):
    result = report["results"]
    if result.get("locus_query_state") == "LOCUS_NOT_FOUND_NOT_BIOLOGICAL_ABSENCE":
        return []
    if result.get("locus_query_state") != "RECORDED_ROWS_NOT_ADMITTED" or result.get("next_offset") is not None:
        _hold("INCOMPLETE_OR_HELD_DATABASE_ROSTER")
    rows = result["records"]
    tags = [x["locus_tag"] for x in rows]
    if len(set(tags)) != len(tags):
        _hold("DUPLICATE_DATABASE_GENE")
    return rows


def join_selected_databases(selection_path, package, gene_path, identity, bgc, manifest, genes):
    if not genes:
        _hold("EMPTY_PACKAGE_ROSTER")
    selection_path = selection_path.expanduser().resolve()
    try:
        selection_hash = _sha256(selection_path)
        selection = json.loads(selection_path.read_text(), object_pairs_hook=_unique)
        if selection.get("schema") != "mamey.gene-first-database-selection/1":
            _hold("SELECTION_SCHEMA")
        if selection["package_manifest_sha256"] != _sha256(package / "manifest.json"):
            _hold("PACKAGE_MANIFEST_HASH_MISMATCH")
        if set(selection["databases"]) != set(ADAPTERS):
            _hold("EXACT_FOUR_DATABASE_PINS_REQUIRED")
        inputs = {"manifest": selection["package_manifest_sha256"],
                  "gene_table": _sealed_file(package, gene_path, manifest)}
        fasta = package / (identity["strain"] + "_proteins.faa")
        inputs["proteins"] = _sealed_file(package, fasta, manifest)
        headers = [line[1:].strip() for line in fasta.read_text().splitlines() if line.startswith(">")]
        tags = [h.split()[0] for h in headers if h.split()]
        if len(headers) != len(tags) or len(tags) != len(set(tags)):
            _hold("DUPLICATE_OR_EMPTY_PROTEIN_HEADER")
        # Reuse the existing sequence canonicalization owner.
        sequence_hashes = {h.split()[0]: sha for h, sha in read_round_fasta(fasta).items()}
        reports = {}
        key = tuple(identity[k] for k in ("strain", "full_node", "region", "bgc_alias"))
        for channel, adapter in ADAPTERS.items():
            pin = selection["databases"][channel]
            if not re.fullmatch(r"[0-9a-f]{64}", pin["manifest_sha256"]):
                _hold("MANIFEST_PIN_REQUIRED")
            root = Path(pin["root"]).expanduser()
            if not root.is_absolute():
                root = selection_path.parent / root
            reports[channel] = inspect_tool_database(root, pin["manifest"], adapter=adapter,
                identity=key, limit=1000, expected_manifest_sha256=pin["manifest_sha256"],
                view="genes" if channel == "census" else "history")
        census = {g["locus_tag"]: g for g in _all_records(reports["census"])}
        geometry = reports["census"]["results"].get("locus_geometry")
        if census and geometry != {"region_start_1based": int(bgc["start"]) + 1,
                                   "region_end_1based": int(bgc["end"])}:
            _hold("REGION_GEOMETRY_MISMATCH")
        db_genes = {ch: {g["locus_tag"]: g for g in _all_records(rep)}
                    for ch, rep in reports.items() if ch != "census"}
        observations, joined = [], []
        for gene in genes:
            tag = gene["locus_tag"]
            current_sha = sequence_hashes.get(tag)
            canonical = census.get(tag)
            geometry_bound = False
            if canonical:
                geometry_bound = (int(gene["cds_start"]) == canonical["cds_start"] and
                    int(gene["cds_end"]) == canonical["cds_end"] and
                    {"+": 1, "-": -1, "1": 1, "-1": -1}.get(gene["strand"]) == canonical["strand"] and
                    int(gene["aa_length"]) == canonical["protein_length"] and
                    canonical["membership"] == "EXACT_REGION" and not canonical["hold"])
            for channel, by_tag in db_genes.items():
                record = by_tag.get(tag)
                reason = "AVAILABLE_SEQUENCE_PROJECTION"
                if not canonical or not record:
                    reason = "UNAVAILABLE_IN_SELECTED_DATABASE"
                elif not current_sha or current_sha != canonical["protein_sha256"]:
                    reason = "PACKAGE_SEQUENCE_UNBOUND"
                elif not geometry_bound:
                    reason = "PACKAGE_GENE_GEOMETRY_UNBOUND"
                elif (record["query_sha256"] != current_sha or
                      record["protein_length"] != canonical["protein_length"] or
                      record["locus_key"] != canonical["locus_key"] or
                      record["gene_order"] != canonical["gene_order"] or
                      record["binding_state"] != ("SEQUENCE_BOUND_CURRENT_LOCUS_PROJECTION" if channel == "local_swissprot" else "CENSUS_SEQUENCE_BOUND")):
                    reason = "DATABASE_SEQUENCE_BINDING_CONFLICT"
                available = reason == "AVAILABLE_SEQUENCE_PROJECTION"
                history = record["search_history"] if available else []
                state = record["availability_state"] if available else reason
                evidence_state = "BOUND" if available and history else "UNBOUND"
                rep = reports[channel]
                note = state + "; sequence projection only, no historical job-locus or scientific admission"
                observations.append(_observation(channel, tag, evidence_state,
                    "evidence://sha256/" + rep["database_sha256"], rep["database_sha256"], note, "selected_database"))
                joined.append({"exact_identity": " / ".join(key), "gene": tag, "channel": channel,
                    "package_query_sha256": current_sha, "state": state, "binding_reason": reason,
                    "search_history": history})
        # Detect source drift before returning observations to the composer.
        if (_sha256(selection_path) != selection_hash or _sha256(package / "manifest.json") != inputs["manifest"]
                or _sha256(gene_path) != inputs["gene_table"] or _sha256(fasta) != inputs["proteins"]):
            _hold("PACKAGE_OR_SELECTION_CHANGED")
        tallies = {ch: dict(Counter(g["state"] for g in joined if g["channel"] == ch)) for ch in db_genes}
        lines = ["Package roster is the denominator. Unavailable means unavailable in the selected database; search history elsewhere is unknown.",
                 "BOUND means sequence-projected evidence, including verified no-hit outcomes; it does not mean a hit or scientific acceptance.",
                 "Each search retains its own lowest source-rank representative. Raw query_union_coverage_pct is query coverage as recorded by the source; it is not reference coverage or percent identity. No values are clamped. HSPs remain in the receipt; metric validation is separate.",
                 "", "| Channel | State | Genes / package roster |", "|---|---|---|"]
        for ch, counts in tallies.items():
            for state, count in sorted(counts.items()):
                lines.append(f"| {ch} | {state} | {count} / {len(genes)} |")
        lines += ["", "The existing important-gene table preserves every package gene and its three database states. The exploration receipt preserves every bound search outcome, its source provenance, retained-hit count, source-rank representative and HSPs."]
        return {"selection_sha256": selection_hash, "package_hashes": inputs, "roster_count": len(genes),
                "channel_tallies": tallies, "genes": joined,
                "database_only_genes": {ch: sorted(set(rows) - {g["locus_tag"] for g in genes}) for ch, rows in db_genes.items()},
                "database_receipts": {ch: {k: v for k, v in rep.items() if k != "results"} for ch, rep in reports.items()},
                "rendered_markdown": "\n".join(lines) + "\n"}, observations
    except ToolDatabaseInspectionError as exc:
        _hold(exc.code)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, GeneFirstHold):
            raise
        _hold("INPUT_SHAPE_OR_BINDING_INVALID")
