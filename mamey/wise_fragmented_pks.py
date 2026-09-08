"""Wise fragmented PKS/NRPS BLASTP queue workflow (v9.7.144).

Offline, residue-aware helpers for large modular-protein follow-up. This module
does not run BLASTP. It emits NCBI-web-safe FASTA batches, unique queue IDs,
and a stable queue ledger so completed ranks are never rerun.
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
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

NCBI_WEB_HARD_CAP = 100_000
DEFAULT_TARGET_RESIDUES = 85_000
EXTRA_SAFE_TARGET_RESIDUES = 50_000  # Conservative batching target; select via split_ranked_fasta_by_residues(..., extra_safe=True)

@dataclass(frozen=True)
class RankedProteinRecord:
    rank: int
    header: str
    sequence: str
    strain: str = ""
    region: str = ""
    locus: str = ""
    warning: str = ""

    @property
    def residues(self) -> int:
        return len(re.sub(r"[^A-Za-z]", "", self.sequence or ""))

def _rank_from_header(header: str, fallback: int) -> int:
    m = re.search(r"(?:^|[|_])rank=(\d+)(?:[|_]|$)", header)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:^|[|_])r(?:ank)?(\d+)(?:[|_]|$)", header, flags=re.I)
    if m:
        return int(m.group(1))
    return fallback

def parse_ranked_fasta(path: str | Path) -> list[RankedProteinRecord]:
    records: list[RankedProteinRecord] = []
    header = None
    chunks: list[str] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append(_record_from_header_seq(header, "".join(chunks), len(records)+1))
            header = line[1:].strip()
            chunks = []
        else:
            chunks.append(line.strip())
    if header is not None:
        records.append(_record_from_header_seq(header, "".join(chunks), len(records)+1))
    return sorted(records, key=lambda r: r.rank)

def _record_from_header_seq(header: str, seq: str, fallback_rank: int) -> RankedProteinRecord:
    parts = header.split("|")
    strain = parts[0] if parts else ""
    region = next((p for p in parts if p.startswith("NODE") or ".region" in p or p.startswith("BGC")), "")
    locus = next((p for p in parts if p.startswith("ctg") or p.startswith("gene=")), "")
    rank = _rank_from_header(header, fallback_rank)
    return RankedProteinRecord(rank=rank, header=header, sequence=re.sub(r"[^A-Za-z]", "", seq).upper(), strain=strain, region=region, locus=locus)

def split_ranked_fasta_by_residues(records: Iterable[RankedProteinRecord], target_residues: int = DEFAULT_TARGET_RESIDUES, hard_cap: int = NCBI_WEB_HARD_CAP, extra_safe: bool = False) -> list[list[RankedProteinRecord]]:
    # F004: when extra_safe is set, use the conservative target so callers get a single
    # documented switch instead of an unreferenced module constant.
    if extra_safe:
        target_residues = EXTRA_SAFE_TARGET_RESIDUES
    batches: list[list[RankedProteinRecord]] = []
    cur: list[RankedProteinRecord] = []
    cur_res = 0
    for rec in sorted(list(records), key=lambda r: r.rank):
        if rec.residues > hard_cap:  # F003: exactly hard_cap residues is within the NCBI web BLASTP limit, not over it
            if cur:
                batches.append(cur); cur=[]; cur_res=0
            batches.append([RankedProteinRecord(**{**asdict(rec), "warning": "single_sequence_exceeds_NCBI_web_BLASTP_cap_use_domain_HMMER_or_standalone_BLAST"})])
            continue
        if cur and cur_res + rec.residues > target_residues:
            batches.append(cur); cur=[]; cur_res=0
        cur.append(rec); cur_res += rec.residues
    if cur:
        batches.append(cur)
    for b in batches:
        # An intentionally-isolated oversized sequence carries a warning and is allowed
        # through as its own batch; the cap guard only polices *multi-record* packing.
        if len(b) == 1 and b[0].warning:
            continue
        total = sum(r.residues for r in b)
        if total > hard_cap:
            raise ValueError(f"NCBI batch exceeds hard cap: {total}")
    return batches

def _wrap(header: str, seq: str, width: int = 70) -> str:
    lines = [">" + header.lstrip(">")]
    lines.extend(seq[i:i+width] for i in range(0, len(seq), width))
    return "\n".join(lines) + "\n"

def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:+-]+", "_", str(s or "")).strip("_") or "NA"

def write_wise_batches(records: Iterable[RankedProteinRecord], outdir: str | Path, prefix: str = "ALL_STRAINS_RANKED", target_residues: int = DEFAULT_TARGET_RESIDUES, hard_cap: int = NCBI_WEB_HARD_CAP, active_files: int = 2, emit_all: bool = False, start_q: int = 1) -> dict:
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    fasta_dir = out / "fasta"; fasta_dir.mkdir(exist_ok=True)
    records = sorted(list(records), key=lambda r: r.rank)
    batches = split_ranked_fasta_by_residues(records, target_residues=target_residues, hard_cap=hard_cap)
    n_emit = len(batches) if emit_all else min(active_files, len(batches))
    batch_rows=[]; ledger_rows=[]
    # BC2_399 fix: the queue_id's own "85K" segment was a hardcoded literal describing the
    # DEFAULT target_residues (85_000), regardless of the actual `target_residues` this call
    # was given -- a caller using EXTRA_SAFE_TARGET_RESIDUES (50K) or any other custom value
    # still got a queue ID that claimed "85K". Reproduced directly: write_wise_batches(...,
    # target_residues=50_000) emits queue_id "...85K_ranks1_3". No downstream code parses this
    # string (verified: no other tools/*.py or mamey/*.py reads queue_id), so this is purely
    # human-facing, but the whole point of a "stable queue ledger" (this module's own docstring)
    # is a human operator trusting what the ID says. Derived from the real value instead.
    target_label = f"{round(target_residues / 1000)}K"
    for i,b in enumerate(batches, start=1):
        ranks=[r.rank for r in b]
        residues=sum(r.residues for r in b)
        qid=f"BLASTP_Q{start_q+i-1:03d}_{_safe(prefix)}_{target_label}_ranks{min(ranks)}_{max(ranks)}"
        fname=f"{qid}.fasta.txt"
        status="ready_to_run" if i<=n_emit else "deferred_pending"
        if i<=n_emit:
            text=""
            for r in b:
                h=r.header
                if "queue=" not in h:
                    h += f"|rank={r.rank}|queue={qid}"
                text += _wrap(h, r.sequence)
            (fasta_dir/fname).write_text(text, encoding="utf-8")
        batch_rows.append({"queue_id":qid,"file":f"fasta/{fname}" if i<=n_emit else "DEFERRED_NOT_EMITTED","sequence_count":len(b),"residue_count":residues,"rank_range":f"{min(ranks)}-{max(ranks)}","under_100k":residues<=hard_cap,"status":status})
        for r in b:
            ledger_rows.append({"rank":r.rank,"queue_id":qid,"emitted_file":fname if i<=n_emit else "DEFERRED_NOT_EMITTED","status":"pending" if i<=n_emit else "deferred_pending","strain":r.strain,"region":r.region,"locus":r.locus,"residues":r.residues,"warning":r.warning})
    _write_csv(out/"ACTIVE_AND_DEFERRED_QUEUE_FILES.csv", batch_rows)
    _write_csv(out/"STABLE_QUEUE_LEDGER.csv", ledger_rows)
    guide = ["# Wise fragmented PKS BLASTP queue", "", f"Target residues per batch: {target_residues}; hard cap: {hard_cap}.", "", "Run only the ready_to_run files first. Upload results before broad prospecting.", "", "Completed ranks must be marked complete and never rerun. Failed ranks remain pending and are carried forward with new Q IDs.", ""]
    for row in batch_rows:
        guide.append(f"- {row['queue_id']}: {row['sequence_count']} proteins, {row['residue_count']} residues, {row['rank_range']}, {row['status']}")
    (out/"README_WISE_FRAGMENTED_PKS_QUEUE.md").write_text("\n".join(guide), encoding="utf-8")
    summary={"schema":"wise_fragmented_pks_queue_v1","record_count":len(records),"target_residues":target_residues,"hard_cap":hard_cap,"active_files_emitted":n_emit,"total_batches":len(batches),"queue_table":"ACTIVE_AND_DEFERRED_QUEUE_FILES.csv","ledger":"STABLE_QUEUE_LEDGER.csv"}
    (out/"WISE_FRAGMENTED_PKS_QUEUE_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

def _write_csv(path: Path, rows: list[dict]) -> None:
    keys=[]
    for row in rows:
        for k in row:
            if k not in keys: keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=_SafeDictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def plan_cpu_failure_recovery(active_rows: list[dict], failed_queue_ids: set[str], next_q: int, max_proteins: int = 10) -> list[dict]:
    """Return stable recovery batches after CPU failure without marking failed ranks complete."""
    pending=[r for r in sorted(active_rows, key=lambda x:int(x.get('rank',0))) if r.get('queue_id') in failed_queue_ids and r.get('status') != 'complete']
    out=[]
    for i in range(0, len(pending), max_proteins):
        chunk=pending[i:i+max_proteins]
        if not chunk: continue
        q=f"BLASTP_Q{next_q + len(out):03d}_CPU_RETRY_{max_proteins}"
        out.append({"queue_id":q,"ranks":",".join(str(r['rank']) for r in chunk),"sequence_count":len(chunk),"status":"ready_to_run"})
    return out

def command(args) -> int:
    records=parse_ranked_fasta(args.input_fasta)
    summary=write_wise_batches(records, args.outdir, prefix=getattr(args,'prefix','ALL_STRAINS_RANKED'), target_residues=getattr(args,'target_residues',DEFAULT_TARGET_RESIDUES), hard_cap=getattr(args,'hard_cap',NCBI_WEB_HARD_CAP), active_files=getattr(args,'active_files',2), emit_all=getattr(args,'emit_all',False), start_q=getattr(args,'start_q',1))
    emit(f"wise-fragmented-pks: {summary['record_count']} proteins -> {summary['active_files_emitted']} active / {summary['total_batches']} total batches")
    return 0
