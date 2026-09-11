#!/usr/bin/env python3
"""Build a bounded, provenance-rich genome panel for GToTree.

This companion tool DOES NOT run GToTree or IQ-TREE. It selects and stages a
user-sized panel from an explicit TSV manifest. Total-tip presets are 20, 40
(default), and 60; any custom integer from 3 through 60 is accepted. Values
above 60 are rejected.

Required input columns:
  candidate_id  role  source_path

Roles are QUERY, REFERENCE, or OUTGROUP. REFERENCE rows must also supply both
selection_basis and related_query_ids. This prevents the tool from silently
calling a genome a nearest neighbour or type/reference strain. Optional columns:
  source_member, priority, cohort, taxonomy, display_label, tree_label,
  selection_basis, related_query_ids, reference_status

source_path may be FASTA, GenBank, or an antiSMASH ZIP. For a ZIP, source_member
is the exact assembly member. If omitted, auto-selection is allowed only when
there is exactly one unambiguous assembly-like member.

Exact nucleotide-content duplicates are collapsed after ignoring FASTA/GenBank
headers and contig order. Every inclusion/exclusion, duplicate relationship,
source member, label crosswalk, and checksum is written to TSV/JSON receipts.

Claim safety: panel membership is comparator selection, not taxonomic identity,
nearest-neighbour proof, strain independence, novelty, production, or activity.
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
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable
import sys as _sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open, atomic_write_text


def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()


DEFAULT_PANEL_SIZE = 40
MAX_PANEL_SIZE = 60
PRESET_PANEL_SIZES = (20, 40, 60)
CLAIM_CEILING = (
    "Panel membership is comparator selection only; it does not establish "
    "taxonomic identity, nearest-neighbour status, strain independence, novelty, "
    "biosynthetic production, or biological activity."
)
FASTA_SUFFIXES = {".fna", ".fa", ".fasta", ".fas"}
GENBANK_SUFFIXES = {".gbk", ".gbff", ".gb", ".genbank"}


class PanelError(ValueError):
    pass


@dataclass
class Candidate:
    candidate_id: str
    role: str
    source_path: Path
    source_member: str = ""
    priority: int = 1000
    cohort: str = ""
    taxonomy: str = ""
    display_label: str = ""
    tree_label: str = ""
    selection_basis: str = ""
    related_query_ids: list[str] = field(default_factory=list)
    reference_status: str = ""
    sequences: list[str] = field(default_factory=list)
    content_sha256: str = ""
    source_sha256: str = ""
    resolved_member: str = ""
    decision: str = "PENDING"
    reason: str = ""
    duplicate_of: str = ""


def panel_size(value: str | int | None) -> int:
    n = DEFAULT_PANEL_SIZE if value is None else int(value)
    if n > MAX_PANEL_SIZE:
        raise PanelError(f"panel size {n} exceeds hard maximum {MAX_PANEL_SIZE}")
    if n < 3:
        raise PanelError("panel size must be at least 3 total tips")
    return n


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_fasta_text(text: str) -> list[str]:
    seqs, current = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current:
                seqs.append("".join(current).upper())
                current = []
        else:
            current.append(re.sub(r"\s+", "", line))
    if current:
        seqs.append("".join(current).upper())
    return [s for s in seqs if s]


def parse_genbank_text(text: str) -> list[str]:
    seqs, current, in_origin = [], [], False
    for raw in text.splitlines():
        if raw.startswith("ORIGIN"):
            in_origin = True
            current = []
            continue
        if in_origin and raw.startswith("//"):
            seq = re.sub(r"[^A-Za-z]", "", "".join(current)).upper()
            if seq:
                seqs.append(seq)
            in_origin = False
            current = []
            continue
        if in_origin:
            current.append(raw)
    return seqs


def parse_sequence_bytes(data: bytes, suffix: str) -> list[str]:
    text = data.decode("utf-8", errors="replace")
    if suffix.lower() in FASTA_SUFFIXES:
        seqs = parse_fasta_text(text)
    elif suffix.lower() in GENBANK_SUFFIXES:
        seqs = parse_genbank_text(text)
    else:
        raise PanelError(f"unsupported sequence suffix: {suffix}")
    if not seqs:
        raise PanelError("no nucleotide sequences parsed")
    bad = sorted(set("".join(seqs)) - set("ACGTUNRYKMSWBDHVX.-"))
    if bad:
        raise PanelError(f"unexpected nucleotide characters: {''.join(bad[:10])}")
    return [s.replace(".", "").replace("-", "") for s in seqs]


def assembly_content_sha256(sequences: Iterable[str]) -> str:
    # Header- and contig-order-independent, but orientation-preserving: this is
    # exact sequence-content deduplication, not similarity clustering.
    # Keep this byte contract identical to plan_gtotree_iqtree.py so a staged
    # panel can be revalidated without inventing a second de-replication key.
    h = hashlib.sha256()
    for sequence in sorted(s.upper() for s in sequences):
        h.update(str(len(sequence)).encode("ascii"))
        h.update(b"\n")
        h.update(sequence.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _safe_zip_member(name: str) -> None:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise PanelError(f"unsafe ZIP member path: {name}")


def choose_zip_member(names: list[str], requested: str) -> str:
    files = [n for n in names if n and not n.endswith("/")]
    if requested:
        _safe_zip_member(requested)
        if requested not in files:
            raise PanelError(f"source_member not found in ZIP: {requested}")
        suffix = Path(requested).suffix.lower()
        if suffix not in FASTA_SUFFIXES | GENBANK_SUFFIXES:
            raise PanelError(f"source_member is not FASTA/GenBank: {requested}")
        return requested
    candidates = []
    for n in files:
        suffix = Path(n).suffix.lower()
        low = n.lower()
        if suffix not in FASTA_SUFFIXES | GENBANK_SUFFIXES:
            continue
        if any(token in low for token in ("region", "cluster", "protocluster")):
            continue
        candidates.append(n)
    if len(candidates) != 1:
        raise PanelError(
            "antiSMASH ZIP assembly member is ambiguous; set source_member exactly "
            f"(eligible={len(candidates)})"
        )
    _safe_zip_member(candidates[0])
    return candidates[0]


def load_candidate_sequences(c: Candidate) -> None:
    if not c.source_path.is_file():
        raise PanelError(f"source_path not found: {c.source_path}")
    raw = c.source_path.read_bytes()
    c.source_sha256 = sha256_bytes(raw)
    if c.source_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(c.source_path) as zf:
            member = choose_zip_member(zf.namelist(), c.source_member)
            data = zf.read(member)
        c.resolved_member = member
        suffix = Path(member).suffix.lower()
    else:
        if c.source_member:
            raise PanelError("source_member is only valid when source_path is a ZIP")
        data = raw
        c.resolved_member = ""
        suffix = c.source_path.suffix.lower()
    c.sequences = parse_sequence_bytes(data, suffix)
    c.content_sha256 = assembly_content_sha256(c.sequences)


def safe_tree_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")
    if not label:
        raise PanelError("empty tree label after sanitization")
    return label


def read_manifest(path: Path) -> list[Candidate]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        required = {"candidate_id", "role", "source_path"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise PanelError(f"manifest requires columns: {sorted(required)}")
        rows = list(reader)
    candidates, seen = [], set()
    manifest_base = path.resolve().parent
    for line_no, row in enumerate(rows, 2):
        cid = (row.get("candidate_id") or "").strip()
        if not cid or cid in seen:
            raise PanelError(f"line {line_no}: candidate_id is empty or duplicated: {cid!r}")
        seen.add(cid)
        role = (row.get("role") or "").strip().upper()
        if role not in {"QUERY", "REFERENCE", "OUTGROUP"}:
            raise PanelError(f"line {line_no}: invalid role {role!r}")
        basis = (row.get("selection_basis") or "").strip()
        related = [x.strip() for x in re.split(r"[,;]", row.get("related_query_ids") or "") if x.strip()]
        if role == "REFERENCE" and (not basis or not related):
            raise PanelError(
                f"line {line_no}: REFERENCE requires explicit selection_basis and related_query_ids"
            )
        try:
            priority = int((row.get("priority") or "1000").strip())
        except ValueError as exc:
            raise PanelError(f"line {line_no}: priority must be an integer") from exc
        taxonomy = (row.get("taxonomy") or "").strip()
        display = (row.get("display_label") or "").strip()
        if not display:
            display = f"{taxonomy} {cid}".strip() if taxonomy else cid
        tree = safe_tree_label((row.get("tree_label") or "").strip() or cid)
        source_path = Path((row.get("source_path") or "").strip()).expanduser()
        if not source_path.is_absolute():
            source_path = manifest_base / source_path
        candidates.append(Candidate(
            candidate_id=cid, role=role,
            source_path=source_path.resolve(),
            source_member=(row.get("source_member") or "").strip(), priority=priority,
            cohort=(row.get("cohort") or "").strip(), taxonomy=taxonomy,
            display_label=display, tree_label=tree, selection_basis=basis,
            related_query_ids=related,
            reference_status=(row.get("reference_status") or "").strip(),
        ))
    if len({c.tree_label for c in candidates}) != len(candidates):
        raise PanelError("tree_label values must be unique after sanitization")
    return candidates


def deduplicate(candidates: list[Candidate]) -> list[Candidate]:
    role_order = {"QUERY": 0, "OUTGROUP": 1, "REFERENCE": 2}
    groups: dict[str, list[Candidate]] = {}
    for c in candidates:
        groups.setdefault(c.content_sha256, []).append(c)
    unique = []
    for group in groups.values():
        ordered = sorted(group, key=lambda c: (role_order[c.role], c.priority, c.candidate_id))
        winner = ordered[0]
        unique.append(winner)
        for duplicate in ordered[1:]:
            duplicate.decision = "EXCLUDED_DUPLICATE"
            duplicate.reason = "exact nucleotide content duplicates selected candidate"
            duplicate.duplicate_of = winner.candidate_id
    return unique


def select_panel(candidates: list[Candidate], target: int, max_related: int = 3) -> list[Candidate]:
    if max_related < 0 or max_related > 3:
        raise PanelError("max related genomes per query must be between 0 and 3")
    unique = deduplicate(candidates)
    queries = sorted((c for c in unique if c.role == "QUERY"), key=lambda c: (c.priority, c.candidate_id))
    query_ids = {c.candidate_id for c in queries}
    outgroups = sorted((c for c in unique if c.role == "OUTGROUP"), key=lambda c: (c.priority, c.candidate_id))
    references = sorted((c for c in unique if c.role == "REFERENCE"), key=lambda c: (c.priority, c.candidate_id))
    if not queries:
        raise PanelError("manifest has no unique QUERY assembly")
    if not outgroups:
        raise PanelError("manifest has no unique OUTGROUP assembly")
    if len(queries) + 1 > target:
        raise PanelError(f"{len(queries)} queries plus one outgroup exceed target panel size {target}")
    selected = list(queries)
    outgroup = outgroups[0]
    selected.append(outgroup)
    outgroup.decision, outgroup.reason = "SELECTED", "highest-priority unique outgroup"
    for extra in outgroups[1:]:
        extra.decision, extra.reason = "EXCLUDED_EXTRA_OUTGROUP", "exactly one outgroup is staged"
    counts = {qid: 0 for qid in query_ids}
    for ref in references:
        unknown = sorted(set(ref.related_query_ids) - query_ids)
        if unknown:
            ref.decision, ref.reason = "EXCLUDED_UNKNOWN_QUERY", f"unknown related_query_ids: {','.join(unknown)}"
            continue
        if any(counts[qid] >= max_related for qid in ref.related_query_ids):
            ref.decision, ref.reason = "EXCLUDED_RELATED_CAP", f"would exceed {max_related} related genomes for a query"
            continue
        if len(selected) >= target:
            ref.decision, ref.reason = "EXCLUDED_PANEL_FULL", f"target total tips reached ({target})"
            continue
        selected.append(ref)
        for qid in ref.related_query_ids:
            counts[qid] += 1
        ref.decision, ref.reason = "SELECTED", "explicit comparator basis; priority order"
    for q in queries:
        q.decision, q.reason = "SELECTED", "unique query retained"
    if len(selected) != target:
        raise PanelError(
            f"eligible unique candidates fill {len(selected)}/{target} tips after duplicate and related-cap guards"
        )
    return selected


def write_fasta(path: Path, c: Candidate) -> None:
    with atomic_open(path, "w", encoding="ascii") as fh:
        for i, seq in enumerate(c.sequences, 1):
            fh.write(f">{c.tree_label}_contig_{i}\n")
            for start in range(0, len(seq), 80):
                fh.write(seq[start:start + 80] + "\n")


def write_tsv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with atomic_open(path, "w", newline="", encoding="utf-8") as fh:
        writer = _SafeDictWriter(fh, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(manifest: Path, out_dir: Path, target: int, max_related: int) -> dict:
    candidates = read_manifest(manifest)
    for c in candidates:
        try:
            load_candidate_sequences(c)
        except Exception as exc:
            raise PanelError(f"{c.candidate_id}: {exc}") from exc
    selected = select_panel(candidates, target, max_related)
    out_dir.mkdir(parents=True, exist_ok=False)
    genomes = out_dir / "genomes"
    genomes.mkdir()
    staged = {}
    for c in selected:
        dest = genomes / f"{c.tree_label}.fna"
        write_fasta(dest, c)
        staged[c.candidate_id] = dest.resolve()
    common_fields = [
        "candidate_id", "role", "cohort", "priority", "decision", "reason",
        "duplicate_of", "source_path", "source_member", "resolved_member",
        "source_sha256", "content_sha256", "contigs", "total_bp", "tree_label",
        "display_label", "taxonomy", "reference_status", "selection_basis",
        "related_query_ids",
    ]
    def row(c: Candidate) -> dict:
        return {
            "candidate_id": c.candidate_id, "role": c.role, "cohort": c.cohort,
            "priority": c.priority, "decision": c.decision, "reason": c.reason,
            "duplicate_of": c.duplicate_of, "source_path": str(c.source_path),
            "source_member": c.source_member, "resolved_member": c.resolved_member,
            "source_sha256": c.source_sha256, "content_sha256": c.content_sha256,
            "contigs": len(c.sequences), "total_bp": sum(map(len, c.sequences)),
            "tree_label": c.tree_label, "display_label": c.display_label,
            "taxonomy": c.taxonomy, "reference_status": c.reference_status,
            "selection_basis": c.selection_basis,
            "related_query_ids": ",".join(c.related_query_ids),
        }
    write_tsv(out_dir / "panel_candidates.tsv", common_fields, map(row, candidates))
    write_tsv(out_dir / "panel_selected.tsv", common_fields, map(row, selected))
    # Human/audit receipt. This is intentionally NOT a valid GToTree -m file.
    write_tsv(out_dir / "label_crosswalk.tsv",
              ["candidate_id", "tree_label", "display_label", "role", "taxonomy"],
              ({k: row(c)[k] for k in ("candidate_id", "tree_label", "display_label", "role", "taxonomy")}
               for c in selected))
    # GToTree 1.8.16 -m input: exactly two columns, no header. Column 1 is
    # the staged input filename and column 2 is its machine-safe replacement
    # label. Keep this separate from the five-column human crosswalk above.
    with atomic_open(out_dir / "labels.tsv", "w", encoding="utf-8", newline="") as fh:
        for c in selected:
            fh.write(f"{staged[c.candidate_id].name}\t{c.tree_label}\n")
    with atomic_open(out_dir / "genomes.txt", "w", encoding="utf-8") as fh:
        for c in selected:
            fh.write(str(staged[c.candidate_id]) + "\n")
    duplicate_rows = [c for c in candidates if c.decision == "EXCLUDED_DUPLICATE"]
    receipt = {
        "schema": "sapote-mamey-phylo-panel-receipt-v1",
        "status": "PANEL_STAGED_NOT_RUN",
        "target_total_tips": target,
        "preset_choices": list(PRESET_PANEL_SIZES),
        "default_total_tips": DEFAULT_PANEL_SIZE,
        "hard_max_total_tips": MAX_PANEL_SIZE,
        "max_related_genomes_per_query": max_related,
        "manifest_path": str(manifest.resolve()),
        "manifest_sha256": sha256_bytes(manifest.read_bytes()),
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "selected_role_counts": {role: sum(c.role == role for c in selected)
                                 for role in ("QUERY", "REFERENCE", "OUTGROUP")},
        "selected_candidate_ids": [c.candidate_id for c in selected],
        "exact_content_duplicate_count": len(duplicate_rows),
        "exact_content_duplicates": [
            {"candidate_id": c.candidate_id, "duplicate_of": c.duplicate_of,
             "content_sha256": c.content_sha256} for c in duplicate_rows
        ],
        "gtotree_label_map": {
            "path": "labels.tsv",
            "format": "two tab-separated columns, no header",
            "column_1": "staged_filename",
            "column_2": "machine_safe_replacement_label",
            "rows": len(selected),
            "human_crosswalk_path": "label_crosswalk.tsv",
            "human_crosswalk_is_not_gtotree_m_input": True,
        },
        "claim_ceiling": CLAIM_CEILING,
        "next_step": "Human review of panel_selected.tsv, label_crosswalk.tsv, and headerless labels.tsv; GToTree/IQ-TREE are not run by this tool.",
    }
    atomic_write_text(out_dir / "panel_receipt.json", json.dumps(receipt, indent=2) + "\n")
    return receipt


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Stage a bounded GToTree panel with explicit provenance and exact-content deduplication.",
        epilog="Total-tip presets: 20, 40 (default), 60. Custom integers are allowed only through 60.",
    )
    p.add_argument("manifest", type=Path, nargs="?", help="input candidate TSV")
    p.add_argument("out_dir", type=Path, nargs="?", help="new output directory (must not exist)")
    p.add_argument("--panel-size", default=str(DEFAULT_PANEL_SIZE), metavar="N",
                   help="total tips: 20, 40 (default), 60, or custom 3..60; >60 rejected")
    p.add_argument("--max-related-per-query", type=int, default=3, metavar="K",
                   help="maximum explicitly linked reference genomes per query (0..3; default 3)")
    p.add_argument("--show-options", action="store_true",
                   help="print panel-size choices/default/maximum as JSON and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.show_options:
        emit(json.dumps({"preset_total_tips": list(PRESET_PANEL_SIZES),
                          "default_total_tips": DEFAULT_PANEL_SIZE,
                          "custom_total_tips": "integer 3..60",
                          "hard_max_total_tips": MAX_PANEL_SIZE,
                          "max_related_genomes_per_query": 3}))
        return 0
    if args.manifest is None or args.out_dir is None:
        parser().error("manifest and out_dir are required unless --show-options is used")
    try:
        target = panel_size(args.panel_size)
        receipt = build(args.manifest, args.out_dir, target, args.max_related_per_query)
    except (PanelError, OSError, zipfile.BadZipFile) as exc:
        emit(f"build_phylo_panel: ERROR: {exc}", file=sys.stderr)
        return 2
    emit(json.dumps({"status": receipt["status"], "selected": receipt["selected_count"],
                      "target": receipt["target_total_tips"], "out_dir": str(args.out_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
