"""modeb_blastp.py — deterministic per-BGC BLASTP FASTA emitter (v9.7.148).

Wires the panel manifest → BlastpBatchEmitter so that completing a Mode B §16
(BLASTP priority queue) automatically produces ready-to-submit FASTA batches.

Design contract:
  - Reads the sealed package's bgc_blastp_panel manifest CSV for sequence metadata
  - Reads sequences from the curated panel FASTA files (already written by mamey run)
  - Falls back to first-pass FASTA if curated scope returns no sequences
  - Feeds to BlastpBatchEmitter(batch_size=3) — same rules as manual batches
  - Writes to <out_dir>/BGC044_blastp_batch{N}.fasta + _README.txt
  - Returns a manifest dict for the caller (CLI or Sapote layer)
  - Non-blocking: any failure returns an error manifest, never raises to caller

CLI:
    mamey modeb-blastp --package <pkg_dir> --bgc BGC044
    mamey modeb-blastp --package <pkg_dir> --bgc BGC044 --out <dir> --start-batch 10
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import csv
import re
from pathlib import Path
from typing import Any

from .blastp_batch_emitter import BlastpBatchEmitter
from .modeb_evidence_state import EVIDENCE_STATES

_QUERY_EMISSION_STATE = "UNBOUND"
assert _QUERY_EMISSION_STATE in EVIDENCE_STATES

# ── FASTA parsing ─────────────────────────────────────────────────────────────

def _parse_fasta(fasta_path: Path) -> dict[str, str]:
    """Return {locus_tag: sequence} from a panel FASTA file.

    Tolerates two real header formats:

      Pipe-delimited (bgc_blastp_panel.fasta_header):
        >strain|BGC_ID|slot=N|role=...|gene=<locus_tag>|node=...|...

      Space-delimited (modeb_blastp emit, AS-XXX-style):
        >ctg107_3 gene=ctg107_3 BGC=BGC003 length=619 product=hypothetical protein

    The gene= regex stops at the first whitespace OR pipe — earlier versions
    used `[^|]+` which silently swallowed the whole tail of space-delimited
    headers. W7 fix (v9.7.149c).
    """
    seqs: dict[str, str] = {}
    current_tag: str | None = None
    current_seq: list[str] = []

    try:
        text = fasta_path.read_text(encoding="utf-8")
    except OSError:
        return seqs

    for line in text.splitlines():
        if line.startswith(">"):
            if current_tag:
                seqs[current_tag] = "".join(current_seq)
            # Extract gene= field from header. Stop at whitespace OR pipe so
            # both pipe- and space-delimited headers parse correctly.
            m = re.search(r"gene=([^|\s]+)", line)
            current_tag = m.group(1) if m else line[1:].split("|")[0].strip() or None
            current_seq = []
        else:
            current_seq.append(line.strip())

    if current_tag:
        seqs[current_tag] = "".join(current_seq)

    return seqs


def _load_panel_sequences(panel_dir: Path) -> dict[str, str]:
    """Return {locus_tag: sequence} for all proteins in the panel FASTAs.

    Sequences are keyed by locus_tag extracted from the FASTA header gene= field.
    Preference order (first non-empty wins):
      1. curated_N_per_BGC files (priority-ranked subset)
      2. BLASTP_FIRST_PASS files (wider coverage, up to 30 proteins)
      3. one_best files (fallback — 1 protein per BGC)
    Filtering by BGC_ID is done by the caller using the manifest, not here.
    """
    if not panel_dir.exists():
        return {}

    # Collect FASTA files by scope priority
    curated = sorted(panel_dir.glob("*curated_*for_BLASTP.faa"))
    first_pass = sorted(panel_dir.glob("*FIRST_PASS*for_BLASTP.faa"))
    one_best = sorted(panel_dir.glob("*one_best*for_BLASTP.faa"))

    seqs_by_tag: dict[str, str] = {}

    for fasta_files in (curated, first_pass, one_best):
        for fasta_path in fasta_files:
            parsed = _parse_fasta(fasta_path)
            seqs_by_tag.update(parsed)
        if seqs_by_tag:
            break  # found sequences, stop escalating

    return seqs_by_tag


# ── Manifest reading ──────────────────────────────────────────────────────────

def _read_manifest(panel_dir: Path) -> list[dict]:
    candidates = sorted(panel_dir.glob("*_BGC_BLASTP_PANEL_selection_manifest.csv"))
    if not candidates:
        return []
    try:
        with candidates[0].open(newline="", encoding="utf-8-sig") as f:
            return [r for r in csv.DictReader(f) if not r.get("panel_scope", "").startswith("#")]
    except OSError:
        return []


# ── Core emission function ────────────────────────────────────────────────────

def emit_for_bgc(
    package_dir: str | Path,
    bgc_id: str,
    out_dir: str | Path | None = None,
    start_batch: int = 1,
    batch_size: int = 3,
) -> dict[str, Any]:
    """Emit per-BGC BLASTP batches from the sealed package panel.

    Returns a manifest dict:
        {
            "bgc_id": str,
            "status": "OK" | "SKIPPED" | "ERROR",
            "proteins_found": int,
            "batch_count": int,
            "files_written": [str, ...],
            "out_dir": str,
            "note": str,        # only on SKIPPED/ERROR
        }
    """
    pkg = Path(package_dir)
    panel_dir = pkg / "bgc_blastp_panel"

    if out_dir is None:
        out_dir = pkg / "modeb_blastp" / bgc_id
    out_path = Path(out_dir)

    # ── 1. Read manifest ───────────────────────────────────────────────────────
    all_rows = _read_manifest(panel_dir)
    if not all_rows:
        return {
            "bgc_id": bgc_id,
            "status": "SKIPPED",
            "proteins_found": 0,
            "batch_count": 0,
            "files_written": [],
            "out_dir": str(out_path),
            "evidence_state": _QUERY_EMISSION_STATE,
            "note": "no panel manifest found — run mamey in standard or gold mode first",
        }

    # ── 2. Filter to requested BGC; prefer curated scope ──────────────────────
    bgc_rows = [r for r in all_rows if r.get("bgc_id", "").upper() == bgc_id.upper()]
    if not bgc_rows:
        return {
            "bgc_id": bgc_id,
            "status": "SKIPPED",
            "proteins_found": 0,
            "batch_count": 0,
            "files_written": [],
            "out_dir": str(out_path),
            "evidence_state": _QUERY_EMISSION_STATE,
            "note": f"BGC {bgc_id!r} not found in panel manifest ({len(all_rows)} total rows)",
        }

    # Prefer curated scope; fall back to first_pass; then all scopes
    def _scope_priority(row: dict) -> int:
        scope = row.get("panel_scope", "")
        if "curated" in scope: return 0
        if "FIRST_PASS" in scope: return 1
        if "one_best" in scope: return 2
        return 3

    bgc_rows.sort(key=lambda r: (_scope_priority(r), -float(r.get("selection_score") or 0)))

    # Deduplicate by locus_tag (keep highest-priority occurrence)
    seen_tags: set[str] = set()
    deduped_rows: list[dict] = []
    for row in bgc_rows:
        tag = row.get("locus_tag") or row.get("protein_id", "")
        if tag and tag not in seen_tags:
            seen_tags.add(tag)
            deduped_rows.append(row)

    # bgc_rows being non-empty does NOT guarantee deduped_rows is non-empty: every
    # matching row is dropped here if it carries neither a locus_tag nor a protein_id
    # (e.g. edge/prodigal-called CDS features with no assigned identifier). Without
    # this guard, deduped_rows[0] below raises IndexError straight to the caller,
    # contradicting this module's own "never raises to caller" contract (see module
    # docstring). Fail soft with a SKIPPED manifest instead.
    if not deduped_rows:
        return {
            "bgc_id": bgc_id,
            "status": "SKIPPED",
            "proteins_found": 0,
            "batch_count": 0,
            "files_written": [],
            "out_dir": str(out_path),
            "evidence_state": _QUERY_EMISSION_STATE,
            "note": (
                f"{len(bgc_rows)} manifest row(s) matched {bgc_id!r} but none carried a "
                "usable locus_tag or protein_id — nothing to identify sequences by."
            ),
        }

    # ── 3. Load sequences from panel FASTAs ───────────────────────────────────
    panel_seqs = _load_panel_sequences(panel_dir)

    # ── 4. Build emitter entries ───────────────────────────────────────────────
    strain = (deduped_rows[0].get("strain") or pkg.name.replace("_package", "")
              .replace("/package", "").split("/")[-1])
    bgc_context = (deduped_rows[0].get("assembly_locator")
                   or f"{bgc_id} — {deduped_rows[0].get('bgc_products', 'unknown class')}")

    emitter = BlastpBatchEmitter(
        batch_size=batch_size,
        strain=strain,
        bgc_context=bgc_context,
    )

    proteins_added = 0
    missing_seqs: list[str] = []

    for row in deduped_rows:
        tag = row.get("locus_tag") or row.get("protein_id", "")
        seq = panel_seqs.get(tag, "")
        if not seq:
            missing_seqs.append(tag)
            continue

        aa_len = row.get("aa_len") or row.get("aa_length", "?")
        role = row.get("selection_role", "")
        reason = row.get("selection_reason", "")
        node = row.get("node_id") or row.get("contig", "")
        region = row.get("antismash_region", "")
        products = row.get("bgc_products", "")

        header = (
            f">{strain}|{bgc_id}|{tag}|{aa_len}aa"
            f"|{node}·{region}"
            f"|{products}"
            f"|role={role}|reason={reason}"
        )
        emitter.add(header, seq)
        proteins_added += 1

    if proteins_added == 0:
        return {
            "bgc_id": bgc_id,
            "status": "SKIPPED",
            "proteins_found": 0,
            "batch_count": 0,
            "files_written": [],
            "out_dir": str(out_path),
            "evidence_state": _QUERY_EMISSION_STATE,
            "note": (
                f"sequences not found for {len(deduped_rows)} manifest rows — "
                f"missing tags: {missing_seqs[:5]}. "
                f"Panel may not include sequences for this BGC."
            ),
        }

    # ── 5. Write batches ───────────────────────────────────────────────────────
    prefix = bgc_id
    written = emitter.write_batches(out_path, start_batch=start_batch, prefix=prefix)

    note_parts = []
    if missing_seqs:
        note_parts.append(f"{len(missing_seqs)} locus tag(s) had no sequence in panel "
                          f"(run gold mode or check panel completeness): {missing_seqs[:3]}")

    return {
        "bgc_id": bgc_id,
        "status": "OK",
        "proteins_found": proteins_added,
        "batch_count": len(written),
        "files_written": [str(p) for p in written],
        "out_dir": str(out_path),
        "evidence_state": _QUERY_EMISSION_STATE,
        "note": "; ".join(note_parts) if note_parts else "",
    }


# ── CLI command function (called from cli.py) ─────────────────────────────────

def command(args) -> int:
    """Entry point for `mamey modeb-blastp` CLI subcommand."""
    result = emit_for_bgc(
        package_dir=args.package,
        bgc_id=args.bgc,
        out_dir=getattr(args, "out", None),
        start_batch=getattr(args, "start_batch", 1),
        batch_size=getattr(args, "batch_size", 3),
    )

    status = result["status"]
    if status == "OK":
        emit(f"modeb-blastp: {result['bgc_id']} — {result['proteins_found']} protein(s) "
              f"→ {result['batch_count']} batch(es) in {result['out_dir']}")
        for f in result["files_written"]:
            emit(f"  {f}")
        if result.get("note"):
            emit(f"  NOTE: {result['note']}")
        return 0
    else:
        emit(f"modeb-blastp SKIPPED: {result.get('note', 'unknown reason')}")
        return 1
