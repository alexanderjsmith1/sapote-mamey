"""Pre-Sapote Lite annotation gate.

This module creates the gene evidence table that controls Directed PKS figures
and Mode B cards. It is deliberately local-file/LLM-friendly: no Galaxy, no
eggNOG, no full external HMMER requirement by default.
"""

from __future__ import annotations

from pathlib import Path
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import io
import json
import os
from dataclasses import dataclass
from typing import Iterable


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated gene-evidence/figure-label/tier-count deliverable on disk (matches
    mamey/packaging.py's helper). These three outputs directly gate Directed PKS figures and
    Mode B cards per this module's own docstring, so a half-written one is not cosmetic."""
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

DOMAIN_REPLACEMENTS = {
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
    "PP-binding": "PP-bind",
}

FORBIDDEN_WEAK_LABELS = {
    "p450", "cytochrome", "transporter", "regulator",
    "oxidoreductase", "mfs", "tetr", "tailoring",
}

@dataclass(frozen=True)
class LiteConfig:
    groups: dict[str, list[str]]
    excluded_bgcs: dict[str, str] | None = None

def concise_domains(raw_domains: str | None) -> str:
    if not raw_domains or str(raw_domains).lower() == "nan":
        return ""
    tokens: list[str] = []
    for token in str(raw_domains).split(";"):
        token = token.strip()
        if not token or token.startswith("nrpspksdomains_"):
            continue
        token = token.replace("(Modular-KS)", "").replace("(Hybrid-KS)", "")
        tokens.append(DOMAIN_REPLACEMENTS.get(token, token))
    deduped: list[str] = []
    for token in tokens:
        if not deduped or deduped[-1] != token:
            deduped.append(token)
    return "–".join(deduped)

def _node_token(value: object) -> str:
    text = str(value)
    if text.startswith("NODE_"):
        return text
    try:
        return f"NODE_{int(float(text))}"
    except Exception:
        return text

def _node_num(value: object) -> int | None:
    text = str(value).replace("NODE_", "")
    try:
        return int(float(text))
    except Exception:
        return None

def _infer_node(row: dict) -> str:
    for key in ("node", "node_id", "node_name"):
        if row.get(key):
            return _node_token(row[key])
    for key in ("node_num", "contig_num"):
        if row.get(key):
            return _node_token(row[key])
    return "NODE_UNKNOWN"

def _role(row: dict) -> str:
    role = str(row.get("source_role") or row.get("role") or "").strip()
    if role:
        return role
    domains = concise_domains(row.get("domains_order") or row.get("antiSMASH_domains") or row.get("domains"))
    if "KS" in domains or "AT" in domains or "TE" in domains or "CAL" in domains:
        return "PKS core"
    if "A" in domains or "PCP" in domains or "Cy" in domains:
        return "NRPS/adenylation"
    return "other"

def _modeb_function(domains: str, role: str, tier: str) -> str:
    if domains:
        if "CAL" in domains and "TE" in domains:
            return "modular T1PKS/NRPS-like megasynthase fragment"
        if "KS" in domains and "AT" in domains:
            return "PKS chain-extension fragment"
        if "A" in domains and "PCP" in domains:
            return "NRPS/adenylation hybrid module"
        if domains == "TE":
            return "thioesterase/release fragment"
        if domains == "KR":
            return "ketoreductase fragment"
        return "domain-supported biosynthetic fragment"
    if tier == "B":
        return "putative product-annotation-supported gene"
    if tier == "C":
        return "comparator-supported gene"
    return "context/hypothetical ORF"

def _is_unknown_product(product: str) -> bool:
    low = product.strip().lower()
    return low in {"", "nan", "hypothetical protein", "hypothetical", "unknown", "uncharacterized protein"}

def _group_for_node(node: str, groups: dict[str, list[str]]) -> str:
    # v9.7.371 fix: node is always canonicalized to uppercase "NODE_<int>" by _node_token before
    # this call, but `groups` comes straight from the user-authored study-spec JSON with no
    # normalization -- a spec that writes lowercase node ids (e.g. "node_456", a plausible human
    # typo) silently never matched, and every gene in that group fell into "Ungrouped" with no
    # error or warning.
    node_u = node.upper()
    for set_id, nodes in groups.items():
        nodes_u = [n.upper() for n in nodes]
        if node_u in nodes_u or node_u.replace("NODE_", "") in [n.replace("NODE_", "") for n in nodes_u]:
            return set_id
    return "Ungrouped"

def evidence_row_from_source(row: dict, groups: dict[str, list[str]]) -> dict:
    node = _infer_node(row)
    set_id = _group_for_node(node, groups)
    domains = concise_domains(row.get("domains_order") or row.get("antiSMASH_domains") or row.get("domains"))
    product = str(row.get("product_annotation") or row.get("product") or "").strip()
    blast = str(row.get("blastp_support") or row.get("blastp_top_hit") or "").strip()
    mibig = str(row.get("mibig_context") or row.get("mibig_id") or row.get("most_similar_known_cluster") or "").strip()
    role = _role(row)

    if domains:
        tier = "A"
        confidence = "high"
        label = f"{row.get('locus_tag', 'gene')}: {domains}"
        do_not = False
    elif not _is_unknown_product(product):
        tier = "B"
        confidence = "medium"
        label = f"{row.get('locus_tag', 'gene')}: putative {product}"
        do_not = False
    elif blast:
        tier = "C"
        confidence = "medium"
        label = f"{row.get('locus_tag', 'gene')}: comparator-supported"
        do_not = False
    else:
        tier = "D" if mibig else "U"
        confidence = "low"
        label = f"{row.get('locus_tag', 'gene')}: hypothetical/context ORF"
        do_not = True

    # v9.7.371 fix: was `tier in {"D", "U"}` -- do_not is ALREADY unconditionally True for every
    # D/U row (set on the same statement that assigns those tiers, 2 lines above), so this check
    # was provably dead code for the tiers it was scoped to. FORBIDDEN_WEAK_LABELS
    # (p450/cytochrome/transporter/regulator/oxidoreductase/mfs/tetr/tailoring) are exactly the
    # kind of weak, generic product annotations that land a gene in tier B ("putative <product>")
    # -- the evident original intent -- so scope the check there instead, where it can actually
    # change do_not_overlabel_flag from False to True for a weakly-labeled gene.
    if tier in {"B", "C"} and any(term in label.lower() for term in FORBIDDEN_WEAK_LABELS):
        do_not = True

    start = int(float(row.get("start") or 0))
    end = int(float(row.get("end") or max(start + 1, 1)))
    strand = str(row.get("strand") or "+")
    if strand not in {"+", "-"}:
        strand = "+"
    node_num = _node_num(node)

    return {
        "set_id": set_id,
        "node": node,
        "node_num": node_num if node_num is not None else "",
        "record_length": row.get("record_length") or row.get("region_length") or row.get("length") or "",
        "locus_tag": row.get("locus_tag") or row.get("gene") or row.get("query") or "gene",
        "start": start,
        "end": end,
        "strand": strand,
        "aa_len": row.get("aa_len") or row.get("protein_length") or "",
        "source_role": role,
        "antiSMASH_domains": domains,
        "product_annotation": product,
        "blastp_support": blast,
        "mibig_context": mibig,
        "evidence_tier": tier,
        "allowed_figure_label": label,
        "label_confidence": confidence,
        "modeb_function": _modeb_function(domains, role, tier),
        "do_not_overlabel_flag": do_not,
    }

def build_gene_evidence_table(source_csv: Path, groups: dict[str, list[str]], out_csv: Path) -> Path:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with source_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [evidence_row_from_source(row, groups) for row in reader]
    fieldnames = [
        "set_id", "node", "node_num", "record_length", "locus_tag", "start", "end",
        "strand", "aa_len", "source_role", "antiSMASH_domains", "product_annotation",
        "blastp_support", "mibig_context", "evidence_tier", "allowed_figure_label",
        "label_confidence", "modeb_function", "do_not_overlabel_flag",
    ]
    buf = io.StringIO()
    writer = _SafeDictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write_text(out_csv, buf.getvalue())
    return out_csv

def write_figure_labels_json(gene_evidence_csv: Path, out_json: Path) -> Path:
    labels: dict[str, dict[str, object]] = {}
    with gene_evidence_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            set_id = row["set_id"]
            labels.setdefault(set_id, {})
            labels[set_id][row["locus_tag"]] = {
                "label": row["allowed_figure_label"],
                "tier": row["evidence_tier"],
                "confidence": row["label_confidence"],
                "show_on_figure": row["evidence_tier"] in {"A", "B", "C"},
                "do_not_overlabel_flag": str(row["do_not_overlabel_flag"]).lower() == "true",
            }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(out_json, json.dumps(labels, indent=2))
    return out_json

def tier_counts(gene_evidence_csv: Path, out_csv: Path) -> Path:
    counts: dict[tuple[str, str], int] = {}
    with gene_evidence_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["set_id"], row["evidence_tier"])
            counts[key] = counts.get(key, 0) + 1
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    writer = _SafeDictWriter(buf, fieldnames=["set_id", "evidence_tier", "gene_count"])
    writer.writeheader()
    for (set_id, tier), count in sorted(counts.items()):
        writer.writerow({"set_id": set_id, "evidence_tier": tier, "gene_count": count})
    _atomic_write_text(out_csv, buf.getvalue())
    return out_csv

def run_pre_sapote_lite(source_csv: Path, groups: dict[str, list[str]], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence = build_gene_evidence_table(source_csv, groups, out_dir / "gene_evidence_table.csv")
    labels = write_figure_labels_json(evidence, out_dir / "figure_labels.json")
    counts = tier_counts(evidence, out_dir / "evidence_tier_counts.csv")
    return {
        "gene_evidence_table": str(evidence),
        "figure_labels": str(labels),
        "evidence_tier_counts": str(counts),
    }
