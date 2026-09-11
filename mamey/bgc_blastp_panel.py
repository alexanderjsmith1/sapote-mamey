"""BGC BLASTP panel exporter (v9.7.142 starter).

Selects small, claim-safe protein panels from antiSMASH BGCs so users can run
manual NCBI web BLASTP iteratively rather than blasting whole contigs or every
BGC protein at once.

The exporter does not run BLASTP and does not infer product identity. It only
exports source-derived protein translations with a manifest explaining why each
sequence was selected.
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
import io
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

from .crosswalk import bgc_proteins, assembly_locator
from .models import BGCRecord, CDSFeature

CORE_TERMS: tuple[str, ...] = (
    "phosphoenolpyruvate mutase", "pep mutase", "pepm", "phosphonopyruvate",
    "phosphonate", "ketosynthase", "ks domain", "pks", "polyketide",
    "nonribosomal", "nrps", "adenylation", "condensation", "carrier protein",
    "acyltransferase", "dehydratase", "terpene", "cyclase", "lanthipeptide",
    "lassopeptide", "precursor peptide", "radical sam", "sactipeptide",
    "thiopeptide", "tomm", "azole", "dehydrogenase", "aminotransferase",
    "halogenase", "glycosyltransferase", "p450", "cytochrome p450",
    "methyltransferase", "oxygenase", "oxidoreductase", "epimerase",
    "nucleoside", "siderophore", "luca", "lucb", "ectoine",
)

CONTEXT_TERMS: tuple[str, ...] = (
    "resistance", "self-resistance", "efflux", "transporter", "abc transporter",
    "mfs transporter", "major facilitator", "regulator", "transcriptional",
    "luxr", "tetr", "sarp", "streptomyces antibiotic regulatory protein",
    "two-component", "sensor kinase", "response regulator", "export", "immunity",
    "peptidase", "protease", "maturation", "thioesterase", "hydrolase",
)

UPGRADE_TERMS: tuple[str, ...] = (
    "phosphonate", "pep mutase", "phosphoenolpyruvate mutase", "resistance",
    "self-resistance", "transporter", "halogenase", "glycosyltransferase",
    "radical sam", "precursor peptide", "lanthipeptide", "lassopeptide",
    "tomm", "thiopeptide", "nucleoside", "siderophore",
)

SKIP_PRODUCTS: tuple[str, ...] = (
    "hypothetical protein", "uncharacterized protein", "conserved hypothetical",
)

CLAIM_SAFETY = (
    "manual BLASTP candidate only; similarity is not product identity, pathway "
    "completeness, expression, or bioactivity proof"
)


@dataclass(frozen=True)
class PanelCandidate:
    bgc: BGCRecord
    cds: CDSFeature
    role: str
    reason: str
    score: int


def _atomic_write_text(path: Path, text: str) -> None:
    """Write to a temp sibling then atomically replace (mirrors packaging.py's
    ``_atomic_write_text``). This module's five outputs per scope/panel (round .faa files,
    selection manifest CSV, batch-summary CSV, summary JSON, USER_GUIDE.md) were all bare
    write_text()/open("w") calls; an interrupted write (kill -9, disk full, crash mid-run) can
    leave a truncated file. The selection-manifest CSV specifically is read back by
    authored_verify.py's PANEL_ABSENT_CLAIM claim-safety check and modeb_blastp.py's
    ``_read_manifest`` (which drives per-BGC Mode-B BLASTp batch emission) -- both degrade a
    truncated/malformed read silently rather than surfacing the corruption."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _qual_text(cds: CDSFeature, key: str) -> str:
    vals = (getattr(cds, "qualifiers", {}) or {}).get(key, [])
    if isinstance(vals, (list, tuple)):
        return " ".join(str(v) for v in vals)
    return str(vals or "")


def annotation_blob(cds: CDSFeature) -> str:
    parts = [
        cds.locus_tag or "",
        cds.product or "",
        _qual_text(cds, "gene"),
        _qual_text(cds, "gene_functions"),
        _qual_text(cds, "sec_met_domain"),
        _qual_text(cds, "note"),
        _qual_text(cds, "protein_id"),
    ]
    return " ".join(parts).lower()


def _count_terms(blob: str, terms: Iterable[str]) -> tuple[int, list[str]]:
    hits = [t for t in terms if t in blob]
    return len(hits), hits


def _seq(cds: CDSFeature) -> str:
    return re.sub(r"[^A-Za-z]", "", (cds.translation or "").replace("*", "")).upper()


def classify_candidate(bgc: BGCRecord, cds: CDSFeature) -> PanelCandidate | None:
    seq = _seq(cds)
    if not seq:
        return None
    blob = annotation_blob(cds)
    core_n, core_hits = _count_terms(blob, CORE_TERMS)
    context_n, context_hits = _count_terms(blob, CONTEXT_TERMS)
    upgrade_n, _upgrade_hits = _count_terms(blob, UPGRADE_TERMS)
    product = (cds.product or "").lower()
    skip_penalty = 1 if any(t in product for t in SKIP_PRODUCTS) else 0
    aa_len = len(seq)
    length_bonus = 1 if aa_len >= 180 else 0
    rare_bonus = min(3, upgrade_n)
    if core_n >= context_n and core_n > 0:
        role = "core"
        hits = core_hits
        score = 100 + core_n * 10 + rare_bonus * 5 + length_bonus - skip_penalty
    elif context_n > 0:
        role = "context"
        hits = context_hits
        score = 70 + context_n * 10 + rare_bonus * 5 + length_bonus - skip_penalty
    else:
        role = "fallback"
        hits = ["longest translated CDS"]
        score = min(50, max(1, aa_len // 50)) - skip_penalty
    reason = "+".join(h.replace(" ", "_") for h in hits[:4])
    return PanelCandidate(bgc=bgc, cds=cds, role=role, reason=reason, score=score)


def select_panel(bgcs: Iterable[BGCRecord], cds_list: Iterable[CDSFeature],
                 genes_per_bgc: int = 2) -> list[PanelCandidate]:
    """Return up to ``genes_per_bgc`` translated proteins per BGC.

    Preference order is one core biosynthetic marker plus one context/accessory
    marker when available. If one role is missing, the next highest-confidence
    translated CDS fills the slot so every BGC with translations contributes.
    """
    cds_list = list(cds_list)
    selected: list[PanelCandidate] = []
    for bgc in sorted(list(bgcs), key=lambda b: b.bgc_id):
        candidates = [c for cds in bgc_proteins(cds_list, bgc) if (c := classify_candidate(bgc, cds))]
        candidates.sort(key=lambda c: (-c.score, c.cds.start or 0, c.cds.locus_tag or ""))
        if not candidates:
            continue
        picks: list[PanelCandidate] = []
        core = next((c for c in candidates if c.role == "core"), None)
        context = next((c for c in candidates if c.role == "context"), None)
        if core:
            picks.append(core)
        if context and context.cds is not (core.cds if core else None):
            picks.append(context)
        for c in candidates:
            if len(picks) >= genes_per_bgc:
                break
            if all(c.cds is not p.cds for p in picks):
                picks.append(c)
        selected.extend(picks[:genes_per_bgc])
    return selected


def _safe_token(s: Any, fallback: str = "NA") -> str:
    t = re.sub(r"[^A-Za-z0-9_.:+-]+", "_", str(s or "")).strip("_")
    return t or fallback


def fasta_header(strain: str, row: dict) -> str:
    fields = [
        _safe_token(strain),
        _safe_token(row.get("bgc_id")),
        f"slot={row.get('slot')}",
        f"role={_safe_token(row.get('selection_role'))}",
        f"gene={_safe_token(row.get('locus_tag') or row.get('protein_id'))}",
        f"node={_safe_token(row.get('node_id') or row.get('contig'))}",
        f"region={_safe_token(row.get('antismash_region'))}",
        f"coords={row.get('start')}-{row.get('end')}",
        f"aa={row.get('aa_len')}",
        f"reason={_safe_token(row.get('selection_reason'))}",
    ]
    return ">" + "|".join(fields)


def wrap_fasta(header: str, seq: str, width: int = 60) -> str:
    lines = [header]
    lines.extend(seq[i:i + width] for i in range(0, len(seq), width))
    return "\n".join(lines) + "\n"


def panel_rows(bgcs: Iterable[BGCRecord], cds_list: Iterable[CDSFeature],
               strain: str, genes_per_bgc: int = 2) -> list[dict]:
    picks = select_panel(list(bgcs), list(cds_list), genes_per_bgc=genes_per_bgc)
    per_bgc_slot: dict[str, int] = {}
    rows: list[dict] = []
    for p in picks:
        bid = p.bgc.bgc_id
        per_bgc_slot[bid] = per_bgc_slot.get(bid, 0) + 1
        seq = _seq(p.cds)
        protein_id = _clean(_qual_text(p.cds, "protein_id")) or p.cds.locus_tag or ""
        products = ";".join(getattr(p.bgc, "products", []) or [])
        warning = ""
        if len(seq) >= 2500:
            warning = "giant_multidomain_protein_consider_domain_followup"
        row = {
            "strain": strain,
            "bgc_id": bid,
            "slot": per_bgc_slot[bid],
            "locus_tag": p.cds.locus_tag or "",
            "protein_id": protein_id,
            "contig": p.bgc.contig,
            "node_id": p.bgc.node_id,
            "antismash_region": p.bgc.antismash_region,
            "source_gbk": p.bgc.source_gbk,
            "start": p.cds.start,
            "end": p.cds.end,
            "strand": p.cds.strand,
            "aa_len": len(seq),
            "selection_role": p.role,
            "selection_reason": p.reason,
            "selection_score": p.score,
            "bgc_products": products,
            "assembly_locator": assembly_locator(p.bgc),
            "product_annotation": p.cds.product or _qual_text(p.cds, "sec_met_domain")[:120],
            "blastp_claim_safety": CLAIM_SAFETY,
            "warning": warning,
            "sequence": seq,
        }
        rows.append(row)
    return rows


def _row_identity(row: dict) -> tuple[str, str, str]:
    return (str(row.get("bgc_id", "")), str(row.get("locus_tag", "")), str(row.get("protein_id", "")))


def first_pass_rows(curated_rows: list[dict], first_pass_size: int = 30,
                    giant_aa_threshold: int = 2500) -> list[dict]:
    """Select a high-value first pass across BGCs for iterative web BLASTP.

    The first pass is not intended to cover every protein. It prioritizes class-
    defining core genes, resistance/transport/regulatory context, and product-
    relevant annotations, while slightly deferring giant multidomain proteins.
    """
    role_rank = {"core": 0, "context": 1, "fallback": 2}

    def base_key(row: dict):
        # Ordering within a BGC ignoring giant status (role, then score).
        return (role_rank.get(row.get("selection_role"), 9),
                -int(row.get("selection_score") or 0),
                str(row.get("bgc_id", "")), row.get("slot", 0))

    # v9.7.338 (BLP-01): guarantee every BGC a shot at a first-pass slot even when its
    # class-defining core is only available as a giant multidomain protein. The plain
    # giant_penalty sorts a giant-core BGC's *only* representative behind every non-giant
    # core of every other BGC, so with the shipped default first_pass_size=30 on a 46-BGC
    # strain the flagship giant-core leads fell off the first pass entirely (AS-XXX BGC041,
    # its top-ranked Exceptional lead, whose only core is a 3116-aa PKS: giant, so penalized).
    # Fix: when a BGC has NO non-giant core row, exempt that BGC's best row from the
    # giant_penalty so it competes for a first-pass slot on role/score like everyone else.
    _by_bgc: dict[str, list[dict]] = defaultdict(list)
    for _r in curated_rows:
        _by_bgc[str(_r.get("bgc_id", ""))].append(_r)
    exempt_row_ids: set[int] = set()
    for _bid, _brows in _by_bgc.items():
        has_nongiant_core = any(
            _r.get("selection_role") == "core"
            and int(_r.get("aa_len") or 0) < giant_aa_threshold
            for _r in _brows
        )
        if not has_nongiant_core and _brows:
            exempt_row_ids.add(id(min(_brows, key=base_key)))

    def key(row: dict):
        aa = int(row.get("aa_len") or 0)
        giant_penalty = 1 if (aa >= giant_aa_threshold and id(row) not in exempt_row_ids) else 0
        return (giant_penalty, role_rank.get(row.get("selection_role"), 9), -int(row.get("selection_score") or 0), row.get("bgc_id", ""), row.get("slot", 0))

    # Keep at most one row per BGC in the first sweep before allowing seconds.
    ordered = sorted(curated_rows, key=key)
    chosen: list[dict] = []
    seen_bgcs: set[str] = set()
    # v9.7.335: this `return` (not `break`) exited the whole function once the cap was hit, so
    # with the shipped default first_pass_size=30 a 46-BGC strain got NO row for 16 of its BGCs.
    # The `return`→`break` change fixed premature exit but did NOT restore giant-core leads like
    # BGC041 (a false claim in the pre-338 comment); the giant_penalty exemption above does.
    # The guide says "approximately 30 high-value proteins" and never says a third of the
    # clusters are absent.
    for row in ordered:
        if len(chosen) >= first_pass_size:
            break
        bid = str(row.get("bgc_id", ""))
        if bid not in seen_bgcs:
            chosen.append(row)
            seen_bgcs.add(bid)
    for row in ordered:
        if len(chosen) >= first_pass_size:
            break
        if _row_identity(row) not in {_row_identity(r) for r in chosen}:
            chosen.append(row)
    return chosen


def _fasta_record_chars(row: dict, strain: str) -> int:
    return len(wrap_fasta(fasta_header(strain, row), row.get("sequence", "")))


def _residues(row: dict) -> int:
    return len(row.get("sequence", ""))


def assign_rounds(rows: list[dict], strain: str, proteins_per_file: int = 20,
                  max_residues: int = 85000, giant_aa_threshold: int = 2500,
                  preserve_bgc_boundaries: bool = True,
                  isolate_giants: bool = False) -> list[list[dict]]:
    """Pack rows into NCBI-safe BLASTP rounds.

    NCBI web BLASTP rejects queries by total amino-acid residues, so the load-
    bearing cap is ``max_residues``. The record-count cap keeps ChatGPT/manual
    review manageable. Giant proteins are flagged in the manifest by default,
    but not isolated unless ``isolate_giants`` is requested. This keeps the
    default output compact while still supporting reduced troubleshooting batches
    if NCBI reports CPU-limit/timeouts.
    """
    rows = list(rows)
    if not rows:
        return []

    groups: list[list[dict]]
    if preserve_bgc_boundaries:
        grouped: dict[str, list[dict]] = defaultdict(list)
        order: list[str] = []
        for row in rows:
            bid = str(row.get("bgc_id", ""))
            if bid not in grouped:
                order.append(bid)
            grouped[bid].append(row)
        groups = [grouped[bid] for bid in order]
    else:
        groups = [[r] for r in rows]

    rounds: list[list[dict]] = []
    cur: list[dict] = []
    cur_residues = 0

    def flush():
        nonlocal cur, cur_residues
        if cur:
            rounds.append(cur)
            cur = []
            cur_residues = 0

    for group in groups:
        group_residues = sum(_residues(r) for r in group)
        # Optional troubleshooting mode: isolate giant multidomain proteins when
        # NCBI reports CPU-limit or timeout problems. The default is to flag,
        # not isolate, because the residue cap is the load-bearing web limit.
        #
        # v9.7.240 (P4a): this previously emitted EVERY protein of a giant-bearing BGC
        # as its own one-protein round, not just the giant. On AS-XXX with
        # --genes-per-bgc 8 that turned 13 rounds into 48, most of them singletons of a
        # ~200 aa regulator -- unusable as a manual BLASTp handoff. Isolate the giants;
        # let the non-giants pack normally.
        if isolate_giants and any(_residues(r) >= giant_aa_threshold for r in group):
            giants = [r for r in group if _residues(r) >= giant_aa_threshold]
            rest = [r for r in group if _residues(r) < giant_aa_threshold]
            flush()
            for row in giants:
                rounds.append([row])
            if not rest:
                continue
            group = rest
            group_residues = sum(_residues(r) for r in group)
        if cur and (len(cur) + len(group) > proteins_per_file or cur_residues + group_residues > max_residues):
            flush()
        if len(group) > proteins_per_file or group_residues > max_residues:
            # A BGC group itself is too large; split within group and make the
            # break visible via manifest warnings already carried by rows.
            for row in group:
                if cur and (len(cur) >= proteins_per_file or cur_residues + _residues(row) > max_residues):
                    flush()
                cur.append(row)
                cur_residues += _residues(row)
            continue
        cur.extend(group)
        cur_residues += group_residues
    flush()
    return rounds


def _write_scope(out: Path, strain: str, scope_name: str, rows: list[dict],
                 proteins_per_file: int, max_residues: int, giant_aa_threshold: int,
                 preserve_bgc_boundaries: bool, isolate_giants: bool,
                 manifest_rows: list[dict]) -> list[dict]:
    rounds = assign_rounds(rows, strain, proteins_per_file=proteins_per_file,
                           max_residues=max_residues,
                           giant_aa_threshold=giant_aa_threshold,
                           preserve_bgc_boundaries=preserve_bgc_boundaries,
                           isolate_giants=isolate_giants)
    batch_summaries: list[dict] = []
    for i, chunk in enumerate(rounds, 1):
        fname = f"{_safe_token(strain)}_{scope_name}_round{i:03d}_for_BLASTP.faa"
        fpath = out / fname
        text = ""
        residues = 0
        chars = 0
        bgcs = []
        for row in chunk:
            row2 = dict(row)
            row2["panel_scope"] = scope_name
            row2["round_file"] = fname
            record = wrap_fasta(fasta_header(strain, row2), row2["sequence"])
            text += record
            residues += _residues(row2)
            chars += len(record)
            if row2.get("bgc_id") not in bgcs:
                bgcs.append(row2.get("bgc_id"))
            manifest_rows.append(row2)
        _atomic_write_text(fpath, text)
        status = "OK"
        if residues > 100000:
            status = "EXCEEDS_NCBI_WEB_LIMIT"
        elif residues > max_residues:
            status = "WARN_ABOVE_SAFETY_CAP"
        batch_summaries.append({
            "panel_scope": scope_name,
            "round": i,
            "filename": fname,
            "proteins": len(chunk),
            "residues": residues,
            "fasta_characters": chars,
            "BGCs": ";".join(str(b) for b in bgcs[:12]) + (";..." if len(bgcs) > 12 else ""),
            "BGC_count": len(bgcs),
            "status": status,
        })
    return batch_summaries


def write_panel(outdir: str | Path, strain: str, bgcs: Iterable[BGCRecord],
                cds_list: Iterable[CDSFeature], genes_per_bgc: int = 2,
                proteins_per_file: int = 20, max_residues: int = 85000,
                first_pass_size: int = 30, giant_aa_threshold: int = 2500,
                emit_one_best: bool = True, emit_first_pass: bool = True,
                emit_curated: bool = True, max_query_chars: int | None = None,
                isolate_giants: bool = False) -> dict[str, Any]:
    """Write iterative BLASTP FASTA panels and manifests.

    ``max_query_chars`` is accepted as a legacy alias from REV1 but no longer
    drives safety. NCBI's web BLASTP query cap is residue-count based, so
    ``max_residues`` is the authoritative cap.
    """
    if max_query_chars is not None:
        # Compatibility for the first starter patch / old CLI flag. Keep the
        # numeric value conservative by treating it as a residue cap if supplied.
        max_residues = min(max_residues, int(max_query_chars))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    bgcs = list(bgcs)
    cds_list = list(cds_list)

    curated_rows = panel_rows(bgcs, cds_list, strain, genes_per_bgc=genes_per_bgc)
    one_best_rows = panel_rows(bgcs, cds_list, strain, genes_per_bgc=1)
    top_rows = first_pass_rows(curated_rows, first_pass_size=first_pass_size,
                               giant_aa_threshold=giant_aa_threshold)

    manifest_rows: list[dict] = []
    batch_summaries: list[dict] = []
    if emit_first_pass:
        batch_summaries.extend(_write_scope(
            out, strain, f"BLASTP_FIRST_PASS_top{first_pass_size:03d}", top_rows,
            proteins_per_file=proteins_per_file, max_residues=max_residues,
            giant_aa_threshold=giant_aa_threshold, preserve_bgc_boundaries=False,
            isolate_giants=isolate_giants, manifest_rows=manifest_rows,
        ))
    if emit_one_best:
        # v9.7.240 (P4b): this scope hardcoded proteins_per_file=1000000, so it silently
        # ignored --proteins-per-file and always wrote one file holding one protein per BGC
        # (AS-XXX: 46 records / 48,840 residues in a single .faa). A caller asking for <=30
        # records per file got 46 with no warning. The residue cap prevented an over-length
        # NCBI query, but not an over-count one. Honour the caller's cap.
        batch_summaries.extend(_write_scope(
            out, strain, "one_best_protein_per_BGC_NCBI_safe", one_best_rows,
            proteins_per_file=proteins_per_file, max_residues=max_residues,
            giant_aa_threshold=giant_aa_threshold, preserve_bgc_boundaries=True,
            isolate_giants=False, manifest_rows=manifest_rows,
        ))
    if emit_curated:
        batch_summaries.extend(_write_scope(
            out, strain, f"curated_{genes_per_bgc}_per_BGC_NCBI_safe", curated_rows,
            proteins_per_file=proteins_per_file, max_residues=max_residues,
            giant_aa_threshold=giant_aa_threshold, preserve_bgc_boundaries=True,
            isolate_giants=isolate_giants, manifest_rows=manifest_rows,
        ))

    manifest_fields = [
        "panel_scope", "round_file", "strain", "bgc_id", "slot", "locus_tag", "protein_id", "contig",
        "node_id", "antismash_region", "source_gbk", "start", "end", "strand", "aa_len",
        "selection_role", "selection_reason", "selection_score", "bgc_products",
        "assembly_locator", "product_annotation", "warning", "blastp_claim_safety",
    ]
    manifest_path = out / f"{_safe_token(strain)}_BGC_BLASTP_PANEL_selection_manifest.csv"
    _manifest_buf = io.StringIO(newline="")
    _mw = _SafeDictWriter(_manifest_buf, fieldnames=manifest_fields, lineterminator="\n")
    _mw.writeheader()
    for row in manifest_rows:
        _mw.writerow({k: row.get(k, "") for k in manifest_fields})
    _atomic_write_text(manifest_path, _manifest_buf.getvalue())

    batch_summary_path = out / f"{_safe_token(strain)}_NCBI_safe_batch_summary.csv"
    _bs_fields = ["panel_scope", "round", "filename", "proteins", "residues", "fasta_characters", "BGCs", "BGC_count", "status"]
    _bs_buf = io.StringIO(newline="")
    _bw = _SafeDictWriter(_bs_buf, fieldnames=_bs_fields, lineterminator="\n")
    _bw.writeheader()
    for row in batch_summaries:
        _bw.writerow(row)
    _atomic_write_text(batch_summary_path, _bs_buf.getvalue())

    summary = {
        "schema": "bgc_blastp_iterative_panel_v2",
        "strain": strain,
        "genes_per_bgc_requested": genes_per_bgc,
        "first_pass_size_requested": first_pass_size,
        "proteins_per_file_limit": proteins_per_file,
        "max_residues_limit": max_residues,
        "wise_fragmented_pks_target_residues": 85000,
        "ncbi_web_residue_hard_limit": 100000,
        "giant_aa_threshold": giant_aa_threshold,
        "isolate_giants": isolate_giants,
        "bgc_count": len(bgcs),
        "curated_unique_proteins": len(curated_rows),
        "one_best_unique_proteins": len(one_best_rows),
        "first_pass_unique_proteins": len(top_rows),
        "round_count": len(batch_summaries),
        "batch_summary": batch_summary_path.name,
        "manifest": manifest_path.name,
        "claim_safety": "FASTA contains candidate proteins for manual BLASTP; hits are similarity evidence only.",
        "workflow": "iterative: run first pass, download BOTH the Hit Table CSV and the Single-file XML2, ingest offline with --hit-table and --xml, then reprioritize.",
    }
    _atomic_write_text(out / f"{_safe_token(strain)}_BGC_BLASTP_PANEL_summary.json",
                       json.dumps(summary, indent=2))

    guide = [
        f"# {strain} iterative BGC BLASTP panel",
        "",
        "This folder contains NCBI web BLASTP-ready FASTA batches for iterative BGC troubleshooting.",
        "It is intentionally not a whole-contig or all-protein dump.",
        "",
        "## Recommended workflow",
        "",
        "1. Start with the `BLASTP_FIRST_PASS_top030` FASTA round(s).",
        "2. In NCBI BLASTP, set **Max target sequences = 10**.",
        "3. When the search finishes, download **both** result files from the NCBI results page:",
        "   - **Hit Table (CSV)** — Download menu -> `Hit Table(CSV)`. This is the hit list `ingest-blastp` reads.",
        "   - **Single-file XML2** — Download menu -> `XML2` (single file). `ingest-blastp` uses this for",
        "     enrichment (query coverage, alignment detail, subject titles). Pass it via `--xml`.",
        "   The CSV alone works; adding the XML2 makes the evidence proof-grade, so download both when you can.",
        "4. Ingest both offline (zero network): `mamey ingest-blastp --hit-table <HitTable.csv> --xml <Alignment.xml>"
        " --strain <ID> --master <workbook.xlsx> --package <package>`.",
        "5. Upload/paste RID/results back into Sapote/Mamey for reprioritization of remaining proteins.",
        "6. If NCBI reports a CPU limit, timeout, or huge output, reduce to 10 proteins and isolate giant NRPS/PKS proteins.",
        "",
        "## Output scopes",
        "",
        "- `BLASTP_FIRST_PASS_top030`: approximately 30 high-value proteins for first triage.",
        "- `one_best_protein_per_BGC_NCBI_safe`: one selected protein per BGC for broad overview.",
        f"- `curated_{genes_per_bgc}_per_BGC_NCBI_safe`: up to {genes_per_bgc} representative proteins per BGC, split into smaller rounds.",
        "",
        f"Safety caps: <= {max_residues} amino-acid residues per FASTA by default; NCBI web hard limit is treated as 100,000 residues.",
        f"Manual-review cap: <= {proteins_per_file} proteins per curated/first-pass file.",
        f"Giant multidomain proteins are flagged; isolated only if isolate_giants is requested.",
        "",
        "## Claim-safety rule",
        "",
        "BLASTP hits are sequence-similarity evidence only. They are not proof of compound identity, pathway completeness, expression, or bioactivity.",
        "",
        "## Files",
        "",
    ]
    for row in batch_summaries:
        guide.append(f"- `{row['filename']}` — {row['proteins']} proteins, {row['residues']} residues, {row['status']}")
    guide += ["", f"- `{manifest_path.name}`", f"- `{batch_summary_path.name}`", f"- `{_safe_token(strain)}_BGC_BLASTP_PANEL_summary.json`", ""]
    _atomic_write_text(out / f"{_safe_token(strain)}_BGC_BLASTP_PANEL_USER_GUIDE.md", "\n".join(guide))
    return summary


def command(args) -> int:
    from .parsers import parse_bgcs_from_zip, extract_cds_features

    strain = getattr(args, "strain", None) or Path(args.input_zip).stem
    outdir = getattr(args, "outdir", None) or Path.cwd() / f"{_safe_token(strain)}_bgc_blastp_panel"
    bgcs = parse_bgcs_from_zip(args.input_zip, json_mode=getattr(args, "json_evidence", "off"))
    cds = extract_cds_features(args.input_zip)
    max_residues = getattr(args, "max_residues", 85000)
    max_query_chars = getattr(args, "max_query_chars", None)
    summary = write_panel(outdir, strain, bgcs, cds,
                          genes_per_bgc=getattr(args, "genes_per_bgc", 2),
                          proteins_per_file=getattr(args, "proteins_per_file", 20),
                          max_residues=max_residues,
                          max_query_chars=max_query_chars,
                          first_pass_size=getattr(args, "first_pass_size", 30),
                          giant_aa_threshold=getattr(args, "giant_aa_threshold", 2500),
                          isolate_giants=getattr(args, "isolate_giants", False))
    emit(f"bgc-blastp-panel: first-pass {summary['first_pass_unique_proteins']} proteins; curated {summary['curated_unique_proteins']} proteins from {summary['bgc_count']} BGCs -> {outdir}", f"  summary: {summary['batch_summary']}  manifest: {summary['manifest']}", sep="\n")
    return 0 if summary["curated_unique_proteins"] else 1
