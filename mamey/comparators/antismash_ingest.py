"""Comparator antiSMASH / GenBank ingestor with domain parsing.

This module parses comparator antiSMASH/GBK files from zip files, directories, or
individual GBK files. It emits gene/domain tables suitable for Directed PKS
comparator-context tracks.

It is intentionally dependency-light and does not require Biopython.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import zipfile

from ..ziputil import safe_extract_all


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated comparator-ingest deliverable on disk (matches mamey/packaging.py's helper)."""
    path = Path(path)
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))

DOMAIN_KEYS = ("aSDomain", "domain", "label", "aSModule")
DOMAIN_ALIASES = {
    "PKS_KS": "KS",
    "PKS_AT": "AT",
    "PKS_DH": "DH",
    "PKS_DH2": "DH2",
    "PKS_DHt": "DHt",
    "PKS_KR": "KR",
    "PKS_ER": "ER",
    "PKS_PP": "PP",
    "Thioesterase": "TE",
    "AMP-binding": "A",
    "Heterocyclization": "Cy",
    "Trans-AT_docking": "TransAT-dock",
    "PKS_Docking_Nterm": "Dock-N",
    "PKS_Docking_Cterm": "Dock-C",
}

@dataclass(frozen=True)
class GBKFeature:
    feature_type: str
    start: int
    end: int
    strand: str
    qualifiers: dict[str, list[str]]

@dataclass(frozen=True)
class ComparatorGene:
    comparator_id: str
    source_file: str
    sequence_sha256: str
    locus_name: str
    region_length: int | None
    gene_index: int
    locus_tag: str
    protein_id: str
    product: str
    start: int
    end: int
    strand: str
    aa_len: int | None
    domain_order: str
    domain_count: int

def _read_text(path: Path) -> str:
    return path.read_text(errors="replace")

def _sequence_sha256(gbk_text: str) -> str:
    m = re.search(r"\nORIGIN\s+(.+?)//", gbk_text, flags=re.S)
    if not m:
        return hashlib.sha256(gbk_text.encode("utf-8", errors="replace")).hexdigest()
    seq = re.sub(r"[^A-Za-z]", "", m.group(1)).upper()
    return hashlib.sha256(seq.encode("ascii")).hexdigest()

def _locus_name_and_length(gbk_text: str) -> tuple[str, int | None]:
    m = re.search(r"^LOCUS\s+(\S+)\s+(\d+)", gbk_text, flags=re.M)
    if not m:
        return ("unknown_locus", None)
    return (m.group(1), int(m.group(2)))

def _parse_location(location: str) -> tuple[int, int, str]:
    strand = "-"
    text = location.strip()
    if "complement" not in text:
        strand = "+"
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if not nums:
        return (0, 0, strand)
    return (min(nums), max(nums), strand)

def _append_qualifier(qualifiers: dict[str, list[str]], key: str, value: str) -> None:
    qualifiers.setdefault(key, []).append(value)

def parse_gbk_features(gbk_text: str) -> list[GBKFeature]:
    """Parse FEATURES from a GenBank/antiSMASH GBK text.

    Handles normal qualifier continuations well enough for antiSMASH CDS and
    aSDomain annotations.
    """
    m = re.search(r"\nFEATURES\s+Location/Qualifiers\s*\n(.+?)\nORIGIN", gbk_text, flags=re.S)
    if not m:
        return []
    lines = m.group(1).splitlines()
    features: list[GBKFeature] = []
    current: dict | None = None
    current_key: str | None = None

    def finish_current() -> None:
        nonlocal current
        if current is not None:
            start, end, strand = _parse_location(current["location"])
            features.append(GBKFeature(current["type"], start, end, strand, current["qualifiers"]))
            current = None

    for line in lines:
        feature_match = re.match(r"^     (\S+)\s+(.+)$", line)
        if feature_match and not line[5:].startswith("/"):
            finish_current()
            current = {"type": feature_match.group(1), "location": feature_match.group(2).strip(), "qualifiers": {}}
            current_key = None
            continue
        if current is None:
            continue
        q_match = re.match(r"^\s+/([^=\s]+)(?:=(.*))?$", line)
        if q_match:
            key = q_match.group(1)
            raw = q_match.group(2)
            if raw is None:
                value = "true"
            else:
                value = raw.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith('"'):
                    value = value[1:]
            _append_qualifier(current["qualifiers"], key, value)
            current_key = key
        elif current_key and line.startswith("                     "):
            cont = line.strip()
            if cont.endswith('"'):
                cont = cont[:-1]
            if cont.startswith('"'):
                cont = cont[1:]
            current["qualifiers"][current_key][-1] += cont
    finish_current()
    return features

def _first(qualifiers: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        values = qualifiers.get(key)
        if values:
            return values[0]
    return ""

def _translation_len(qualifiers: dict[str, list[str]]) -> int | None:
    translation = _first(qualifiers, "translation")
    if not translation:
        return None
    return len(re.sub(r"\s+", "", translation))

def _domain_name(feature: GBKFeature) -> str:
    for key in DOMAIN_KEYS:
        value = _first(feature.qualifiers, key)
        if value:
            return DOMAIN_ALIASES.get(value, value)
    # antiSMASH can store domain-like info as note text
    note = _first(feature.qualifiers, "note")
    if note:
        for token in DOMAIN_ALIASES:
            if token in note:
                return DOMAIN_ALIASES[token]
        short = note.split(";")[0].strip()
        if short:
            return short[:60]
    return ""

def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return max(a_start, b_start) <= min(a_end, b_end)

def genes_from_gbk(path: Path, comparator_id: str | None = None) -> list[ComparatorGene]:
    text = _read_text(path)
    locus_name, region_length = _locus_name_and_length(text)
    comparator = comparator_id or path.stem
    seq_hash = _sequence_sha256(text)
    features = parse_gbk_features(text)
    cds = [f for f in features if f.feature_type == "CDS"]
    domains = [f for f in features if f.feature_type in {"aSDomain", "CDS_motif", "misc_feature"} and _domain_name(f)]

    genes: list[ComparatorGene] = []
    for idx, feature in enumerate(sorted(cds, key=lambda f: (f.start, f.end)), start=1):
        domain_hits = []
        for domain in sorted(domains, key=lambda d: (d.start, d.end)):
            if _overlaps(feature.start, feature.end, domain.start, domain.end):
                name = _domain_name(domain)
                if name and (not domain_hits or domain_hits[-1] != name):
                    domain_hits.append(name)
        qualifiers = feature.qualifiers
        locus_tag = _first(qualifiers, "locus_tag", "gene", "old_locus_tag") or f"{path.stem}_gene_{idx}"
        protein_id = _first(qualifiers, "protein_id")
        product = _first(qualifiers, "product")
        genes.append(ComparatorGene(
            comparator_id=comparator,
            source_file=str(path.name),
            sequence_sha256=seq_hash,
            locus_name=locus_name,
            region_length=region_length,
            gene_index=idx,
            locus_tag=locus_tag,
            protein_id=protein_id,
            product=product,
            start=feature.start,
            end=feature.end,
            strand=feature.strand,
            aa_len=_translation_len(qualifiers),
            domain_order=";".join(domain_hits),
            domain_count=len(domain_hits),
        ))
    return genes

def _collect_gbk_paths(input_paths: Iterable[Path], tmp_dir: Path) -> list[Path]:
    from ..parsers import is_macos_cruft  # COMP-P05: skip ._*/.DS_Store AppleDouble shadows
    gbks: list[Path] = []
    for path in input_paths:
        if path.is_dir():
            gbks.extend([p for p in path.rglob("*") if p.suffix.lower() in {".gbk", ".gb", ".gbff"} and not is_macos_cruft(p.name)])
        elif zipfile.is_zipfile(path):
            extract_dir = tmp_dir / path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path) as zf:
                safe_extract_all(zf, extract_dir)  # fail-closed: reject ../ and absolute members
            gbks.extend([p for p in extract_dir.rglob("*") if p.suffix.lower() in {".gbk", ".gb", ".gbff"} and not is_macos_cruft(p.name)])
        elif path.suffix.lower() in {".gbk", ".gb", ".gbff"}:
            gbks.append(path)
    return sorted(gbks)

def ingest_comparator_inputs(input_paths: list[Path], out_dir: Path) -> dict[str, str]:
    """Ingest comparator GBKs/ZIPs/directories and write comparator tables."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / "_extracted_comparators"
    tmp_dir.mkdir(exist_ok=True)
    # COMP-P07: untrusted comparator ZIPs are extracted under out_dir only to parse CDS genes; once
    # all_genes is built the extracted tree is no longer referenced (outputs live in out_dir itself).
    # Remove it in a finally so extracted GBKs don't persist in the sealed package tree, even if a
    # GBK parse raises mid-way.
    try:
        gbk_paths = _collect_gbk_paths(input_paths, tmp_dir)

        all_genes: list[ComparatorGene] = []
        for gbk in gbk_paths:
            all_genes.extend(genes_from_gbk(gbk))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    gene_table = out_dir / "comparator_gene_table.csv"
    fieldnames = list(asdict(all_genes[0]).keys()) if all_genes else list(ComparatorGene.__dataclass_fields__.keys())
    _gt_buf = io.StringIO()
    writer = _SafeDictWriter(_gt_buf, fieldnames=fieldnames)
    writer.writeheader()
    for gene in all_genes:
        writer.writerow(asdict(gene))
    _atomic_write_text(gene_table, _gt_buf.getvalue())

    # Deduplicate by sequence hash.
    seen: dict[str, list[str]] = {}
    for gene in all_genes:
        seen.setdefault(gene.sequence_sha256, [])
        if gene.comparator_id not in seen[gene.sequence_sha256]:
            seen[gene.sequence_sha256].append(gene.comparator_id)

    context_table = out_dir / "comparator_context_table.csv"
    _ct_buf = io.StringIO()
    writer = _SafeDictWriter(_ct_buf, fieldnames=[
        "sequence_sha256", "comparator_ids", "comparator_count", "gene_count", "deduplication_status"
    ])
    writer.writeheader()
    for seq_hash, ids in sorted(seen.items()):
        gene_count = sum(1 for g in all_genes if g.sequence_sha256 == seq_hash)
        writer.writerow({
            "sequence_sha256": seq_hash,
            "comparator_ids": ";".join(ids),
            "comparator_count": len(ids),
            "gene_count": gene_count,
            "deduplication_status": "duplicate_sequence_context" if len(ids) > 1 else "unique_sequence_context",
        })
    _atomic_write_text(context_table, _ct_buf.getvalue())

    report = out_dir / "comparator_context_report.md"
    lines = ["# Comparator antiSMASH Ingest Report", "", f"Parsed GBK files: {len(gbk_paths)}", f"Parsed CDS genes: {len(all_genes)}", ""]
    lines.append("## Sequence contexts")
    for seq_hash, ids in sorted(seen.items()):
        lines.append(f"- `{seq_hash[:12]}`: {', '.join(ids)}")
    lines.append("")
    lines.append("Comparator context is not product identity.")
    _atomic_write_text(report, "\n".join(lines))

    receipt = {
        "input_paths": [str(p) for p in input_paths],
        "gbk_file_count": len(gbk_paths),
        "gene_count": len(all_genes),
        "outputs": {
            "comparator_gene_table": str(gene_table),
            "comparator_context_table": str(context_table),
            "comparator_context_report": str(report),
        },
    }
    receipt_path = out_dir / "COMPARATOR_INGEST_RECEIPT.json"
    _atomic_write_text(receipt_path, json.dumps(receipt, indent=2))
    return {**receipt["outputs"], "receipt": str(receipt_path)}

# Backward-compatible function names from starter patch.
def ingest_comparator_antismash(zip_path: Path, out_dir: Path) -> Path:
    return Path(ingest_comparator_inputs([zip_path], out_dir)["comparator_gene_table"])

def comparator_context_not_identity(product_name: str) -> str:
    return f"comparator_context: {product_name}; not product_identity"

def compare_domain_order(query_domains: str, comparator_domains: str) -> float:
    q = [x for x in re.split(r"[;–, ]+", query_domains) if x]
    c = [x for x in re.split(r"[;–, ]+", comparator_domains) if x]
    if not q or not c:
        return 0.0
    qset, cset = set(q), set(c)
    jaccard = len(qset & cset) / len(qset | cset)
    prefix = 0
    for a, b in zip(q, c):
        if a == b:
            prefix += 1
        else:
            break
    order_bonus = prefix / max(len(q), len(c))
    return round(min(1.0, 0.75 * jaccard + 0.25 * order_bonus), 3)

def compare_query_to_comparator(query_gene_table: Path, comparator_gene_table: Path, out_dir: Path) -> Path:
    """Compare query gene evidence rows to comparator genes by domain overlap."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with query_gene_table.open(newline="", encoding="utf-8") as handle:
        query_rows = list(csv.DictReader(handle))
    with comparator_gene_table.open(newline="", encoding="utf-8") as handle:
        comp_rows = list(csv.DictReader(handle))

    out = out_dir / "pairwise_domain_table.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "query_locus_tag", "query_node", "comparator_id", "comparator_locus_tag",
            "comparator_product", "query_domains", "comparator_domains", "domain_order_similarity",
            "interpretation_scope"
        ]
        writer = _SafeDictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for q in query_rows:
            qdom = q.get("antiSMASH_domains", "")
            if not qdom:
                continue
            best = []
            for c in comp_rows:
                cdom = c.get("domain_order", "")
                score = compare_domain_order(qdom, cdom)
                if score > 0:
                    best.append((score, c))
            for score, c in sorted(best, key=lambda x: x[0], reverse=True)[:5]:
                writer.writerow({
                    "query_locus_tag": q.get("locus_tag", ""),
                    "query_node": q.get("node", ""),
                    "comparator_id": c.get("comparator_id", ""),
                    "comparator_locus_tag": c.get("locus_tag", ""),
                    "comparator_product": c.get("product", ""),
                    "query_domains": qdom,
                    "comparator_domains": c.get("domain_order", ""),
                    "domain_order_similarity": score,
                    "interpretation_scope": "comparator_context_not_product_identity",
                })
    return out
