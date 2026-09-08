#!/usr/bin/env python3
"""Rank ClusterBlast-derived candidate comparator assemblies for phylogenomics.

This post-seal companion reads raw antiSMASH ZIPs plus exact Mamey BGC
inventories. It parses only the raw `clusterblast/` channel, preserving exact
strain+BGC child rows and per-gene similarity/coverage evidence. It does not
mix KnownClusterBlast/MIBiG, SubClusterBlast, nr, Swiss-Prot, or EBI evidence.

Candidate priority is driven first by the number of distinct query BGCs that
support a resolved reference assembly, then by transparent strain, similarity,
coverage, gene-count, and reference-rank fields. Repeated genes, blocks, or
reference accessions collapsed to one assembly do not become independent BGC
support.

A nucleotide/contig accession is not silently treated as a complete assembly.
An explicit resolver TSV must map it to a GCA_/GCF_ assembly accession, with a
resolution evidence note, or the candidate remains HOLD/REQUEST. No genomes are
downloaded and no GToTree/IQ-TREE process is started.

Input manifest columns:
  strain_id, cohort, antismash_zip, assembly_member, bgc_inventory_csv
Optional:
  mamey_clusterblast_csv

Resolver columns:
  reference_accession, assembly_accession, organism_label, resolution_evidence
"""
from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import re
import statistics
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()


CLAIM_CEILING = (
    "ClusterBlast similarity can prioritize comparator candidates but does not prove "
    "organism relatedness, species identity, strain independence, product identity, "
    "biosynthetic production, or biological activity."
)
PANEL_OPTIONS = (20, 40, 60)
ASSEMBLY_RE = re.compile(r"^GC[AF]_\d+\.\d+$", re.I)
REGION_FILE_RE = re.compile(r"(.+)_c(\d+)\.txt$", re.I)
BLOCK_SPLIT_RE = re.compile(r"\n>>\n")
HIT_TABLE_RE = re.compile(r"Table of Blast hits.*?\n(.*)", re.S)
FASTA_SUFFIXES = {".fna", ".fa", ".fasta", ".fas"}
GENBANK_SUFFIXES = {".gbk", ".gbff", ".gb", ".genbank"}


class CandidateError(ValueError):
    pass


@dataclass
class SourceRow:
    strain_id: str
    cohort: str
    antismash_zip: Path
    assembly_member: str
    bgc_inventory_csv: Path
    mamey_clusterblast_csv: Path | None = None


@dataclass
class Resolution:
    reference_accession: str
    assembly_accession: str
    organism_label: str
    resolution_evidence: str


@dataclass
class Block:
    strain_id: str
    bgc_id: str
    region_key: str
    source_file: str
    reference_accession: str
    reference_source: str
    reference_type: str
    reference_rank: int
    nprot_reported: int | None
    cumulative_score: float | None
    hits: list[dict]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member(name: str) -> None:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise CandidateError(f"unsafe ZIP member path: {name}")


def parse_fasta(text: str) -> list[str]:
    seqs, cur = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if cur:
                seqs.append("".join(cur).upper())
                cur = []
        else:
            cur.append(re.sub(r"\s+", "", line))
    if cur:
        seqs.append("".join(cur).upper())
    return [s for s in seqs if s]


def parse_genbank(text: str) -> list[str]:
    seqs, cur, active = [], [], False
    for raw in text.splitlines():
        if raw.startswith("ORIGIN"):
            active, cur = True, []
        elif active and raw.startswith("//"):
            seq = re.sub(r"[^A-Za-z]", "", "".join(cur)).upper()
            if seq:
                seqs.append(seq)
            active, cur = False, []
        elif active:
            cur.append(raw)
    return seqs


def assembly_provenance(source: SourceRow) -> dict:
    if not source.antismash_zip.is_file():
        raise CandidateError(f"{source.strain_id}: antiSMASH ZIP not found: {source.antismash_zip}")
    _safe_member(source.assembly_member)
    with zipfile.ZipFile(source.antismash_zip) as zf:
        names = set(zf.namelist())
        if source.assembly_member not in names:
            raise CandidateError(
                f"{source.strain_id}: assembly_member not found: {source.assembly_member}"
            )
        data = zf.read(source.assembly_member)
    suffix = Path(source.assembly_member).suffix.lower()
    if suffix in FASTA_SUFFIXES:
        seqs = parse_fasta(data.decode("utf-8", errors="replace"))
    elif suffix in GENBANK_SUFFIXES:
        seqs = parse_genbank(data.decode("utf-8", errors="replace"))
    else:
        raise CandidateError(f"{source.strain_id}: assembly_member is not FASTA/GenBank")
    if not seqs:
        raise CandidateError(f"{source.strain_id}: no assembly sequences parsed")
    content_hash = hashlib.sha256()
    for sequence in sorted(s.upper() for s in seqs):
        content_hash.update(str(len(sequence)).encode("ascii"))
        content_hash.update(b"\n")
        content_hash.update(sequence.encode("ascii"))
        content_hash.update(b"\n")
    return {
        "strain_id": source.strain_id,
        "cohort": source.cohort,
        "antismash_zip": str(source.antismash_zip),
        "antismash_zip_sha256": sha256_file(source.antismash_zip),
        "assembly_member": source.assembly_member,
        "assembly_member_sha256": sha256_bytes(data),
        "assembly_content_sha256": content_hash.hexdigest(),
        "assembly_records": len(seqs),
        "assembly_total_bp": sum(map(len, seqs)),
    }


def read_manifest(path: Path) -> list[SourceRow]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        required = {"strain_id", "cohort", "antismash_zip", "assembly_member", "bgc_inventory_csv"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise CandidateError(f"manifest requires columns: {sorted(required)}")
        rows = list(reader)
    out, seen = [], set()
    manifest_base = path.resolve().parent
    for n, row in enumerate(rows, 2):
        strain = (row.get("strain_id") or "").strip()
        if not strain or strain in seen:
            raise CandidateError(f"manifest line {n}: empty or duplicate strain_id {strain!r}")
        seen.add(strain)
        def p(key: str) -> Path:
            candidate = Path((row.get(key) or "").strip()).expanduser()
            return (candidate if candidate.is_absolute() else manifest_base / candidate).resolve()
        legacy = (row.get("mamey_clusterblast_csv") or "").strip()
        legacy_path = Path(legacy).expanduser() if legacy else None
        if legacy_path is not None and not legacy_path.is_absolute():
            legacy_path = manifest_base / legacy_path
        out.append(SourceRow(
            strain_id=strain, cohort=(row.get("cohort") or "").strip(),
            antismash_zip=p("antismash_zip"),
            assembly_member=(row.get("assembly_member") or "").strip(),
            bgc_inventory_csv=p("bgc_inventory_csv"),
            mamey_clusterblast_csv=legacy_path.resolve() if legacy_path else None,
        ))
    if not out:
        raise CandidateError("manifest has no strains")
    return out


def read_resolver(path: Path | None) -> dict[str, Resolution]:
    if path is None:
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        required = {"reference_accession", "assembly_accession", "organism_label", "resolution_evidence"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise CandidateError(f"resolver requires columns: {sorted(required)}")
        rows = list(reader)
    out = {}
    for n, row in enumerate(rows, 2):
        ref = (row.get("reference_accession") or "").strip()
        assembly = (row.get("assembly_accession") or "").strip().upper()
        evidence = (row.get("resolution_evidence") or "").strip()
        if not ref or not ASSEMBLY_RE.fullmatch(assembly) or not evidence:
            raise CandidateError(f"resolver line {n}: valid reference, GCA/GCF accession, and evidence required")
        item = Resolution(ref, assembly, (row.get("organism_label") or "").strip(), evidence)
        if ref in out and out[ref].assembly_accession != assembly:
            raise CandidateError(f"resolver maps {ref} to multiple assemblies")
        out[ref] = item
    return out


def _pick(row: dict, names: tuple[str, ...]) -> str:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return str(row[name]).strip()
    return ""


def inventory_region_map(path: Path) -> tuple[dict[str, str], int]:
    if not path.is_file():
        raise CandidateError(f"BGC inventory not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    mapping = {}
    for row in rows:
        bgc = _pick(row, ("BGC_ID", "bgc_id"))
        contig = _pick(row, ("Contig", "contig"))
        region = _pick(row, ("Region", "region_number"))
        if not (bgc and contig and region):
            continue
        try:
            region = str(int(float(region)))
        except ValueError:
            continue
        key = f"{contig}_c{region}"
        if key in mapping and mapping[key] != bgc:
            raise CandidateError(f"inventory region key maps to multiple BGCs: {key}")
        mapping[key] = bgc
    return mapping, len(rows)


def channel_of_member(name: str) -> str | None:
    parts = [p.lower() for p in PurePosixPath(name).parts]
    if "knownclusterblast" in parts:
        return "knownclusterblast"
    if "subclusterblast" in parts:
        return "subclusterblast"
    if "clusterblast" in parts:
        return "clusterblast"
    return None


def parse_hit_rows(block: str) -> list[dict]:
    m = HIT_TABLE_RE.search(block)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            identity = float(parts[2])
        except ValueError:
            continue
        def num(value: str) -> float | None:
            try:
                return float(value)
            except ValueError:
                return None
        if parts[0].strip() and parts[1].strip():
            out.append({
                "query_gene": parts[0].strip(), "subject_gene": parts[1].strip(),
                "pct_identity": identity, "blast_score": num(parts[3]),
                "pct_coverage": num(parts[4]), "evalue": parts[5].strip(),
            })
    return out


def parse_clusterblast_txt(strain_id: str, bgc_id: str, region_key: str,
                           source_file: str, text: str, max_rank: int) -> list[Block]:
    blocks = []
    for raw in BLOCK_SPLIT_RE.split(text)[1:]:
        rank_m = re.match(r"\s*(\d+)\.\s+(\S+)", raw)
        if not rank_m:
            continue
        rank = int(rank_m.group(1))
        if rank > max_rank:
            continue
        source = re.search(r"^Source:\s*(.+)$", raw, re.M)
        typ = re.search(r"^Type:\s*(.+)$", raw, re.M)
        nprot = re.search(r"Number of proteins with BLAST hits to this cluster:\s*(\d+)", raw)
        score = re.search(r"Cumulative BLAST score:\s*([\d.]+)", raw)
        hits = parse_hit_rows(raw)
        if not hits:
            continue
        blocks.append(Block(
            strain_id=strain_id, bgc_id=bgc_id, region_key=region_key,
            source_file=source_file, reference_accession=rank_m.group(2),
            reference_source=source.group(1).strip() if source else "",
            reference_type=typ.group(1).strip() if typ else "",
            reference_rank=rank,
            nprot_reported=int(nprot.group(1)) if nprot else None,
            cumulative_score=float(score.group(1)) if score else None,
            hits=hits,
        ))
    return blocks


def legacy_export_audit(source: SourceRow) -> dict:
    p = source.mamey_clusterblast_csv
    if p is None:
        return {
            "strain_id": source.strain_id, "path": "", "sha256": "", "rows": 0,
            "channel_column_present": False, "use": "NOT_PROVIDED_NOT_RANKED",
        }
    if not p.is_file():
        raise CandidateError(f"{source.strain_id}: Mamey ClusterBlast CSV not found: {p}")
    with p.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = sum(1 for _ in reader)
        fields = {x.lower() for x in (reader.fieldnames or [])}
    has_channel = bool(fields & {"channel", "evidence_channel", "db_kind"})
    return {
        "strain_id": source.strain_id, "path": str(p), "sha256": sha256_file(p),
        "rows": rows, "channel_column_present": has_channel,
        "use": "AUDIT_ONLY_NOT_RANKED" if has_channel else "AUDIT_ONLY_CHANNEL_COLLAPSED_NOT_RANKED",
    }


def extract_sources(sources: list[SourceRow], max_rank: int):
    all_blocks, provenance, channels, unmapped, legacy = [], [], [], [], []
    for source in sources:
        provenance.append(assembly_provenance(source))
        legacy.append(legacy_export_audit(source))
        region_map, inventory_rows = inventory_region_map(source.bgc_inventory_csv)
        with zipfile.ZipFile(source.antismash_zip) as zf:
            members = [n for n in zf.namelist()
                       if n.lower().endswith(".txt") and "__macosx" not in n.lower()
                       and not PurePosixPath(n).name.startswith("._")]
            counts = defaultdict(int)
            for member in members:
                channel = channel_of_member(member)
                if channel:
                    counts[channel] += 1
                if channel != "clusterblast":
                    continue
                m = REGION_FILE_RE.fullmatch(PurePosixPath(member).name)
                if not m:
                    unmapped.append({"strain_id": source.strain_id, "source_file": member,
                                     "region_key": "", "reason": "filename region key unresolved"})
                    continue
                key = f"{m.group(1)}_c{int(m.group(2))}"
                bgc = region_map.get(key)
                if not bgc:
                    unmapped.append({"strain_id": source.strain_id, "source_file": member,
                                     "region_key": key, "reason": "no exact inventory strain+BGC mapping"})
                    continue
                text = zf.read(member).decode("utf-8", errors="replace")
                all_blocks.extend(parse_clusterblast_txt(source.strain_id, bgc, key, member, text, max_rank))
        for channel in ("clusterblast", "knownclusterblast", "subclusterblast"):
            channels.append({
                "strain_id": source.strain_id, "channel": channel,
                "txt_members": counts[channel],
                "ranking_use": "USED_RAW_EXACT_CHANNEL" if channel == "clusterblast" else "NOT_USED_KEPT_SEPARATE",
                "inventory_rows": inventory_rows,
            })
        for channel in ("mibig", "nr", "swissprot", "ebi"):
            channels.append({
                "strain_id": source.strain_id, "channel": channel, "txt_members": 0,
                "ranking_use": "NOT_INGESTED_NOT_USED", "inventory_rows": inventory_rows,
            })
    return all_blocks, provenance, channels, unmapped, legacy


def median(values: Iterable[float | None]) -> float | None:
    vals = [float(x) for x in values if x is not None]
    return round(statistics.median(vals), 3) if vals else None


def aggregate(blocks: list[Block], resolver: dict[str, Resolution]):
    gene_rows = []
    for block in blocks:
        resolution = resolver.get(block.reference_accession)
        assembly = resolution.assembly_accession if resolution else ""
        candidate_key = assembly or f"UNRESOLVED:{block.reference_accession}"
        for hit in block.hits:
            gene_rows.append({
                "channel": "clusterblast", "strain_id": block.strain_id,
                "bgc_id": block.bgc_id, "region_key": block.region_key,
                "source_file": block.source_file, "candidate_key": candidate_key,
                "assembly_accession": assembly,
                "reference_accession": block.reference_accession,
                "reference_source": block.reference_source,
                "reference_type": block.reference_type,
                "reference_rank": block.reference_rank,
                "nprot_reported": block.nprot_reported,
                "cumulative_score": block.cumulative_score,
                **hit,
            })
    # One child row per exact strain+BGC+candidate. Repeated genes/blocks/accessions
    # stay visible below but count once toward distinct-BGC support.
    child_groups = defaultdict(list)
    for row in gene_rows:
        child_groups[(row["strain_id"], row["bgc_id"], row["candidate_key"])].append(row)
    children = []
    for (strain, bgc, key), rows in child_groups.items():
        assemblies = sorted({r["assembly_accession"] for r in rows if r["assembly_accession"]})
        refs = sorted({r["reference_accession"] for r in rows})
        sources = sorted({r["reference_source"] for r in rows if r["reference_source"]})
        children.append({
            "channel": "clusterblast", "strain_id": strain, "bgc_id": bgc,
            "candidate_key": key, "assembly_accession": assemblies[0] if assemblies else "",
            "resolution_status": "RESOLVED_ASSEMBLY_ACCESSION" if assemblies else "HOLD_REQUEST_ASSEMBLY_ACCESSION",
            "reference_accessions": ";".join(refs), "reference_sources": " | ".join(sources),
            "n_reference_accessions_collapsed": len(refs),
            "n_gene_hit_rows": len(rows),
            "n_distinct_query_genes": len({r["query_gene"] for r in rows}),
            "n_distinct_subject_genes": len({r["subject_gene"] for r in rows}),
            "median_pct_identity": median(r["pct_identity"] for r in rows),
            "median_pct_coverage": median(r["pct_coverage"] for r in rows),
            "best_reference_rank": min(r["reference_rank"] for r in rows),
            "max_cumulative_score": max((r["cumulative_score"] or 0) for r in rows),
            "support_unit": "ONE_DISTINCT_QUERY_BGC",
        })
    candidate_groups = defaultdict(list)
    for child in children:
        candidate_groups[child["candidate_key"]].append(child)
    candidates = []
    for key, rows in candidate_groups.items():
        resolved = not key.startswith("UNRESOLVED:")
        assembly = key if resolved else ""
        refs = sorted({x for row in rows for x in row["reference_accessions"].split(";") if x})
        resolutions = [resolver[r] for r in refs if r in resolver]
        organisms = sorted({r.organism_label for r in resolutions if r.organism_label} |
                           {x for row in rows for x in row["reference_sources"].split(" | ") if x})
        candidates.append({
            "candidate_key": key, "assembly_accession": assembly,
            "selection_status": "RESOLVED_ASSEMBLY_ACCESSION_CANDIDATE" if resolved else "HOLD_REQUEST_ASSEMBLY_ACCESSION",
            "organism_labels": " | ".join(organisms),
            "resolution_evidence": " | ".join(sorted({r.resolution_evidence for r in resolutions})),
            "n_distinct_query_bgcs": len({(r["strain_id"], r["bgc_id"]) for r in rows}),
            "n_distinct_query_strains": len({r["strain_id"] for r in rows}),
            "n_bgc_child_rows": len(rows),
            "n_reference_accessions_collapsed": len(refs),
            "reference_accessions": ";".join(refs),
            "total_gene_hit_rows": sum(int(r["n_gene_hit_rows"]) for r in rows),
            "median_child_pct_identity": median(r["median_pct_identity"] for r in rows),
            "median_child_pct_coverage": median(r["median_pct_coverage"] for r in rows),
            "best_reference_rank": min(int(r["best_reference_rank"]) for r in rows),
            "max_cumulative_score": max(float(r["max_cumulative_score"]) for r in rows),
            "ranking_basis": "distinct_query_bgcs desc; distinct_query_strains desc; median identity/coverage desc; best reference rank asc",
            "claim_ceiling": CLAIM_CEILING,
        })
    candidates.sort(key=lambda r: (
        -int(r["n_distinct_query_bgcs"]), -int(r["n_distinct_query_strains"]),
        -(r["median_child_pct_identity"] or -1), -(r["median_child_pct_coverage"] or -1),
        int(r["best_reference_rank"]), r["candidate_key"],
    ))
    eligible_rank = 0
    for evidence_rank, row in enumerate(candidates, 1):
        row["evidence_rank"] = evidence_rank
        if row["assembly_accession"]:
            eligible_rank += 1
            row["resolved_candidate_rank"] = eligible_rank
        else:
            row["resolved_candidate_rank"] = ""
        for n in PANEL_OPTIONS:
            row[f"resolved_pool_top{n}"] = "YES" if row["resolved_candidate_rank"] and eligible_rank <= n else "NO"
    children.sort(key=lambda r: (r["candidate_key"], r["strain_id"], r["bgc_id"]))
    gene_rows.sort(key=lambda r: (r["candidate_key"], r["strain_id"], r["bgc_id"], r["query_gene"]))
    return candidates, children, gene_rows


def write_tsv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = _SafeDictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(manifest: Path, out_dir: Path, resolver_path: Path | None = None,
          max_reference_rank: int = 5) -> dict:
    if max_reference_rank < 1 or max_reference_rank > 50:
        raise CandidateError("max_reference_rank must be 1..50")
    sources = read_manifest(manifest)
    resolver = read_resolver(resolver_path)
    blocks, provenance, channels, unmapped, legacy = extract_sources(sources, max_reference_rank)
    candidates, children, gene_rows = aggregate(blocks, resolver)
    out_dir.mkdir(parents=True, exist_ok=False)
    write_tsv(out_dir / "source_assembly_provenance.tsv", provenance)
    write_tsv(out_dir / "channel_inventory.tsv", channels)
    write_tsv(out_dir / "legacy_mamey_export_audit.tsv", legacy)
    write_tsv(out_dir / "unmapped_region_holds.tsv", unmapped,
              ["strain_id", "source_file", "region_key", "reason"])
    write_tsv(out_dir / "clusterblast_gene_hits.tsv", gene_rows)
    write_tsv(out_dir / "clusterblast_bgc_children.tsv", children)
    write_tsv(out_dir / "clusterblast_phylo_candidates.tsv", candidates)
    holds = [r for r in candidates if not r["assembly_accession"]]
    write_tsv(out_dir / "assembly_accession_holds.tsv", holds)
    receipt = {
        "schema": "sapote-mamey-clusterblast-phylo-candidates-v1",
        "status": "CANDIDATE_LEDGER_ONLY_NOT_DOWNLOADED_NOT_RUN",
        "manifest_path": str(manifest.resolve()),
        "manifest_sha256": sha256_file(manifest),
        "resolver_path": str(resolver_path.resolve()) if resolver_path else "",
        "resolver_sha256": sha256_file(resolver_path) if resolver_path else "",
        "strain_count": len(sources),
        "raw_clusterblast_blocks_used": len(blocks),
        "gene_hit_rows": len(gene_rows),
        "distinct_bgc_child_rows": len(children),
        "candidate_rows": len(candidates),
        "resolved_assembly_candidates": sum(bool(r["assembly_accession"]) for r in candidates),
        "assembly_accession_holds": len(holds),
        "unmapped_region_holds": len(unmapped),
        "max_reference_rank_used_per_bgc": max_reference_rank,
        "panel_total_tip_options": list(PANEL_OPTIONS),
        "candidate_pool_note": "top20/top40/top60 flags are resolved-reference candidate pools, not final total-tip trees; query and outgroup slots remain governed by build_phylo_panel.py",
        "channel_policy": {
            "clusterblast": "USED from raw ZIP clusterblast/ members only",
            "knownclusterblast": "NOT USED; kept separate",
            "mibig": "NOT USED; kept separate",
            "subclusterblast": "NOT USED; kept separate",
            "nr": "NOT USED; kept separate",
            "swissprot": "NOT USED; kept separate",
            "ebi": "NOT USED; kept separate",
            "legacy_mamey_clusterblast_csv": "AUDIT ONLY because current export does not preserve raw channel on every row",
        },
        "support_unit": "distinct exact (strain_id,bgc_id) child row per collapsed candidate assembly",
        "no_network_downloads": True,
        "tree_software_invoked": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    (out_dir / "candidate_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build a claim-safe ClusterBlast candidate ledger for later phylogeny panel selection.")
    p.add_argument("manifest", type=Path)
    p.add_argument("out_dir", type=Path, help="new output directory")
    p.add_argument("--assembly-resolver", type=Path,
                   help="explicit nucleotide-reference to GCA/GCF assembly TSV; no network resolution is attempted")
    p.add_argument("--max-reference-rank", type=int, default=5,
                   help="raw ClusterBlast references retained per exact strain+BGC (default 5; 1..50)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        receipt = build(args.manifest, args.out_dir, args.assembly_resolver, args.max_reference_rank)
    except (CandidateError, OSError, zipfile.BadZipFile) as exc:
        emit(f"rank_clusterblast_phylo_candidates: ERROR: {exc}", file=sys.stderr)
        return 2
    emit(json.dumps({"status": receipt["status"], "candidates": receipt["candidate_rows"],
                      "resolved": receipt["resolved_assembly_candidates"],
                      "holds": receipt["assembly_accession_holds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
