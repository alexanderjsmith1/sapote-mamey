"""compare.py — two-strain comparative layer for Sapote–Mamey (formerly gemini.py, renamed v9.7.191).

Sits alongside Mamey (extraction) and Sapote (judgment) as the two-strain comparison layer.
Implements the comparative workflow specified in the comparison module spec (2 July 2026),
derived from the AS-XXX × Amel2xC10 analysis. Back-compat: `mamey.gemini` re-exports this module.

This module covers the stages that run without heavy external gene-callers:
  * S5  per-BGC gene-level similarity  (the core deliverable)
  * S6  multi-source comparator recovery — already landed as retention fields on BGCRecord
        (clusterblast_ranked / mibig_ranked / subcluster_hits, v9.7.166); this module reads them.
  * S7  fragmentation / scaffold helper (boundary-profile comparison)

Stages needing pyrodigal (S1) / pyFastANI (S2) run in the companion environment; this
module's align backend is pluggable so it uses DIAMOND (mamey.diamond_align) when the
binding is compiled and falls back to a Biopython Smith–Waterman aligner otherwise.

Standing rules carried in (from the spec's guardrails):
  * every value is SIMILARITY, never product identity — labelled as such in outputs.
  * a gene is "present" at >=70% identity AND >=60% coverage (spec S5).
  * sub-70% "absent/divergent" calls are CANDIDATES until confirmed by exhaustive
    alignment — this module flags them rather than asserting absence (the BGC050 LanB
    false-negative is why).
  * Edge / Full-contig BGCs: low conservation may be truncation, not divergence — the
    boundary is carried through so the caller can label accordingly.
"""

from __future__ import annotations
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import warnings as _warnings

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import os
import tempfile
from typing import Any

# spec S5 present-gene thresholds
PRESENT_MIN_IDENTITY = 70.0
PRESENT_MIN_COVERAGE = 60.0
# below this identity, an "absent" call is only a candidate (needs exhaustive confirm)
DIVERGENT_CANDIDATE_CEIL = 70.0

# v9.7.409 (DEEP_AUDIT2_resource_dos #1): Biopython PairwiseAligner.align() materialises a
# dynamic-programming traceback whose memory is O(len(query) * len(subject)). A crafted multi-MB
# /translation makes that matrix ~10^13 cells and the OS SIGKILLs the process — uncatchably, since
# a SIGKILL cannot be caught by the try/except around .align(). The only safe guard is a pre-check
# BEFORE calling .align(). Any single sequence longer than this residue ceiling is refused (the pair
# is skipped with a typed note) instead of aligned. Configurable via MAMEY_MAX_ALIGN_AA.
_DEFAULT_MAX_ALIGN_AA = 10_000


def _max_align_aa() -> int:
    """Per-sequence residue ceiling for local alignment (env-overridable, read at call time)."""
    try:
        return int(os.environ.get("MAMEY_MAX_ALIGN_AA", str(_DEFAULT_MAX_ALIGN_AA)))
    except (TypeError, ValueError):
        return _DEFAULT_MAX_ALIGN_AA


def _aligner_backend() -> str:
    """Which alignment backend is available, in preference order:
      'diamond'  — fast C++ aligner (needs compiled diamond4py); best when present.
      'pyswrd'   — fast SW (SWORD/opal); the validated offline backend (vendored wheels).
      'biopython'— pairwise SW fallback; slow, always available.
      'none'     — no aligner.
    """
    try:
        from . import diamond_align
        ok, _ = diamond_align.diamond_available()
        if ok:
            return "diamond"
    except Exception:
        pass
    try:
        import pyswrd  # noqa: F401
        # v9.7.409 (AUDIT_cli_code_bugs #1): an import success is NOT proof of executability. On
        # the arm64 build `import pyswrd` succeeds but `pyswrd.search(...)` raises
        # "no supported SIMD backend available" (pyopal has no arm64 SIMD kernel). Run a one-pair
        # smoke align and only select pyswrd if it actually returns; otherwise fall through to
        # biopython instead of silently emitting a 0-hit table blamed on a missing install.
        list(pyswrd.search(["MKAILV"], ["MKAILV"], threads=1))
        return "pyswrd"
    except Exception as _swallowed_exc:
        _warnings.warn(f"compare.py: non-blocking step skipped ({type(_swallowed_exc).__name__}: {_swallowed_exc})", RuntimeWarning, stacklevel=2)  # v9.7.409: was a silent swallow
    try:
        import Bio.Align  # noqa: F401
        return "biopython"
    except Exception:
        return "none"


def _atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated compare-layer deliverable on disk (matches mamey/packaging.py's own helper)."""
    import os
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))


def _write_faa(records: list[tuple[str, str]], path: str) -> None:
    """Write (id, protein_seq) records to a FASTA file."""
    text = "".join(f">{rid}\n{seq}\n" for rid, seq in records if seq)
    _atomic_write_text(path, text)


def align_genes_to_proteome(
    query_genes: list[tuple[str, str]],
    reference_proteome: list[tuple[str, str]],
    threads: int = 1,
) -> dict[str, dict[str, Any]]:
    """S5 core: align each query gene (id, protein) to a reference proteome, return the
    best hit per query as {qseqid: {pident, qcovhsp, scovhsp, sseqid, bitscore, backend}}.

    Uses DIAMOND if available (fast C++), else pyswrd (SIMD Smith-Waterman), else Biopython
    pairwise SW. Returns an empty dict with no error if no backend is available (caller checks)."""
    backend = _aligner_backend()
    if backend == "diamond":
        return _align_diamond(query_genes, reference_proteome, threads)
    if backend == "pyswrd":
        # v9.7.409 (AUDIT_cli_code_bugs #1): a pyswrd runtime failure (e.g. the arm64 SIMD
        # RuntimeError) now propagates from _align_pyswrd instead of being masked as "0 hits";
        # degrade to the always-available Biopython backend rather than returning empty.
        try:
            return _align_pyswrd(query_genes, reference_proteome, threads)
        except Exception:
            return _align_biopython(query_genes, reference_proteome)
    if backend == "biopython":
        return _align_biopython(query_genes, reference_proteome)
    return {}


def _align_pyswrd(query_genes, reference_proteome, threads,
                  query_batch: int = 250) -> dict[str, dict[str, Any]]:
    """Fast SW backend (pyswrd/SWORD). Returns best hit per query with identity+coverage.
    This is the validated offline backend (vendored wheels), much faster than Biopython.
    pyswrd Hit.result carries identity and coverage as fractions (0..1) -> scaled to %.

    Memory: a single pyswrd.search() over a full draft proteome (e.g. 6k x 7k CDS) peaks
    past a ~4 GB ceiling and gets OOM-killed on memory-constrained hosts (the exact case
    pyskani was chosen for — 'drafts like AS-XXX'). Queries are therefore aligned in bounded
    batches (query_batch, default 250) with an explicit gc between batches so the C-side
    SWORD allocations are released; peak stays ~1 GB/batch. Best-hit-per-query is order-
    independent, so batching does not change results. Lower query_batch on tighter hosts."""
    import gc
    import pyswrd
    q_ids = [qid for qid, qseq in query_genes if qseq]
    q_seqs = [qseq for qid, qseq in query_genes if qseq]
    t_ids = [rid for rid, rseq in reference_proteome if rseq]
    t_seqs = [rseq for rid, rseq in reference_proteome if rseq]
    if not q_seqs or not t_seqs:
        return {}
    best: dict[str, dict[str, Any]] = {}
    try:
        for _start in range(0, len(q_seqs), max(1, query_batch)):
            _qs = q_seqs[_start:_start + query_batch]
            hits = list(pyswrd.search(_qs, t_seqs, threads=threads or 0))
            for hit in hits:
                qid = q_ids[_start + hit.query_index]
                res = hit.result
                # pyswrd FullResult.identity() and .coverage() are METHODS returning fractions
                identity = res.identity() if callable(res.identity) else res.identity
                coverage = res.coverage() if callable(res.coverage) else res.coverage
                pident = round(float(identity) * 100.0, 1)
                qcov = round(float(coverage) * 100.0, 1)
                if qid not in best or hit.score > best[qid]["_score"]:
                    best[qid] = {"sseqid": t_ids[hit.target_index], "pident": pident,
                                 "qcovhsp": qcov, "scovhsp": None,
                                 "bitscore": float(hit.score), "backend": "pyswrd",
                                 "_score": hit.score}
            del hits, _qs
            gc.collect()
    except Exception as exc:
        # v9.7.409 (AUDIT_cli_code_bugs #1): do NOT swallow an execution failure as an empty
        # result. On arm64 pyswrd.search raises "no supported SIMD backend available"; masking
        # it as {} made compare write a 0-hit table and misreport a live backend as uninstalled.
        # Propagate a distinct reason so align_genes_to_proteome falls back to Biopython.
        raise RuntimeError(f"pyswrd alignment could not execute: {type(exc).__name__}: {exc}") from exc
    for v in best.values():
        v.pop("_score", None)
    return best


def _align_diamond(query_genes, reference_proteome, threads) -> dict[str, dict[str, Any]]:
    from . import diamond_align
    tmp = tempfile.mkdtemp(prefix="gemini_")
    try:
        q = os.path.join(tmp, "query.faa")
        r = os.path.join(tmp, "ref.faa")
        _write_faa(query_genes, q)
        _write_faa(reference_proteome, r)
        res = diamond_align.align_fasta(q, r, threads=threads)
        if not res["ok"]:
            return {}
        best = diamond_align.best_hit_per_query(res["hits"])
        return {
            qid: {
                "sseqid": h["sseqid"], "pident": h["pident"],
                "qcovhsp": h.get("qcovhsp"), "scovhsp": h.get("scovhsp"),
                "bitscore": h.get("bitscore"), "backend": "diamond",
            }
            for qid, h in best.items()
        }
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _align_biopython(query_genes, reference_proteome) -> dict[str, dict[str, Any]]:
    """Fallback SW aligner (BLOSUM62, BLASTP-equivalent gaps). Slower; used only when
    DIAMOND is not compiled. No k-mer prefilter here (this is the confirm-grade path),
    but callers should still treat it as similarity, not identity-of-molecule."""
    from Bio import Align
    from Bio.Align import substitution_matrices
    aligner = Align.PairwiseAligner()
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.open_gap_score = -11
    aligner.extend_gap_score = -1
    aligner.mode = "local"
    out: dict[str, dict[str, Any]] = {}
    cap = _max_align_aa()
    for qid, qseq in query_genes:
        if not qseq:
            continue
        if len(qseq) > cap:
            # v9.7.409 (DEEP_AUDIT2_resource_dos #1): refuse an over-long query up front — aligning
            # it would build an O(L^2) DP matrix and SIGKILL the process uncatchably. Emit a typed
            # no-hit note (pident=None classifies as no_hit downstream) rather than crash.
            out[qid] = {"sseqid": None, "pident": None, "qcovhsp": None, "scovhsp": None,
                        "bitscore": None, "backend": "biopython",
                        "note": f"alignment skipped: query length {len(qseq)} exceeds "
                                f"MAX_ALIGN_AA={cap}"}
            continue
        best = None
        for rid, rseq in reference_proteome:
            if not rseq:
                continue
            if len(rseq) > cap:
                # Same O(L^2) hazard on the subject side; skip this pair, keep scanning the rest.
                continue
            try:
                aln = aligner.align(qseq, rseq)[0]
            except Exception:
                continue
            ident, positives, alen = _aln_stats(aln)
            pident = 100.0 * ident / alen if alen else 0.0
            qcov = 100.0 * alen / len(qseq) if qseq else 0.0
            score = aln.score
            if best is None or score > best["_score"]:
                best = {"sseqid": rid, "pident": round(pident, 1),
                        "qcovhsp": round(qcov, 1), "scovhsp": None,
                        "bitscore": float(score), "backend": "biopython", "_score": score}
        if best is not None:
            best.pop("_score", None)
            out[qid] = best
    return out


def _aln_stats(aln) -> tuple[int, int, int]:
    """Return (identities, positives, aligned_length) from a Biopython alignment."""
    a, b = aln[0], aln[1]
    ident = pos = alen = 0
    for ca, cb in zip(a, b):
        if ca == "-" or cb == "-":
            alen += 1
            continue
        alen += 1
        if ca == cb:
            ident += 1
            pos += 1
    return ident, pos, alen


def classify_gene(pident: float | None, qcov: float | None) -> str:
    """Spec S5 gene call: 'present' (>=70% id AND >=60% cov), 'divergent_candidate'
    (below present but a hit exists — NOT asserted absent), or 'no_hit'."""
    if pident is None:
        return "no_hit"
    if pident >= PRESENT_MIN_IDENTITY and (qcov or 0) >= PRESENT_MIN_COVERAGE:
        return "present"
    return "divergent_candidate"


def summarize_bgc(gene_hits: dict[str, dict[str, Any]], gene_ids: list[str],
                  boundary: str | None = None) -> dict[str, Any]:
    """Aggregate per-gene hits to a per-BGC summary (mean % id / % sim over core genes,
    fraction present). Carries the boundary through so the caller can apply boundary
    honesty (truncation vs divergence) to Edge/Full-contig clusters."""
    idents, covs, present = [], [], 0
    for gid in gene_ids:
        h = gene_hits.get(gid)
        if not h:
            continue
        if h.get("pident") is not None:
            idents.append(h["pident"])
        if h.get("qcovhsp") is not None:
            covs.append(h["qcovhsp"])
        if classify_gene(h.get("pident"), h.get("qcovhsp")) == "present":
            present += 1
    n = len(gene_ids)
    mean_id = round(sum(idents) / len(idents), 1) if idents else None
    frac_present = round(100.0 * present / n, 1) if n else None
    note = ""
    if boundary in ("Edge", "Full-contig") and (frac_present is not None and frac_present < 70):
        note = "low core-present on non-Interior boundary — may be truncation, not divergence"
    return {
        "n_genes": n, "mean_pident": mean_id, "frac_present": frac_present,
        "boundary": boundary, "note": note,
        "similarity_disclaimer": "values are sequence similarity, not product identity",
    }


def _ani_species_call(value: float) -> str:
    """Claim-safe ANI same/distinct-species call with an honest boundary band.

    AUDIT_374: was a crisp binary cutoff at exactly 95% ("same species (>=95%)" /
    "distinct species (<95%)") with no boundary language at all -- directly contradicting this
    same codebase's own documented claim-safety standard elsewhere (cli.py: "ANI 94-96% =
    boundary/indeterminate", "94-96% boundary; never AAI-as-ANI") and the project's own analysis
    sign-off gate ("calls within ~1% of 95% are boundary/indeterminate, not confident
    same-species"). A value inside the 94-96% band is now reported as indeterminate rather than
    asserted as a confident same/distinct-species call.
    """
    if value >= 96.0:
        return f"same species (ANI {value:.2f}% >= 96%)"
    if value <= 94.0:
        return f"distinct species (ANI {value:.2f}% <= 94%)"
    return (f"boundary/indeterminate (ANI {value:.2f}% is within the 94-96% species-boundary "
            f"band; do not assert same- or distinct-species)")


def compute_ani(contigs_a: list[str], contigs_b: list[str]) -> dict[str, Any]:
    """Whole-genome ANI (Gemini S2). Prefers pyskani (more accurate for fragmented drafts
    like AS-XXX), falls back to pyfastani. Returns {ok, ani, aligned_fraction, backend}.
    Always reports aligned_fraction alongside ANI (standing rule: ANI is meaningless without it)."""
    # pyskani first — better for fragmented assemblies
    try:
        import pyskani
        db = pyskani.Database()
        db.sketch("B", *[s.encode() for s in contigs_b])
        hits = list(db.query("A", *[s.encode() for s in contigs_a]))
        if hits:
            h = hits[0]
            return {"ok": True, "ani": round(h.identity * 100, 2),
                    "aligned_fraction": round(h.query_fraction * 100, 1), "backend": "pyskani"}
    except Exception:
        pass
    try:
        import pyfastani
        sk = pyfastani.Sketch()
        sk.add_draft("B", [s.encode() for s in contigs_b])
        mapper = sk.index()
        hits = list(mapper.query_draft([s.encode() for s in contigs_a]))
        if hits:
            h = hits[0]
            frac = round(100.0 * h.matches / h.fragments, 1) if getattr(h, "fragments", 0) else None
            return {"ok": True, "ani": round(h.identity, 2),
                    "aligned_fraction": frac, "backend": "pyfastani"}
    except Exception:
        pass
    return {"ok": False, "ani": None, "aligned_fraction": None, "backend": "none"}


def compare_command(args) -> int:
    """CLI handler for `mamey compare` — the Gemini two-strain comparison (S5 + S6).

    Extracts every BGC gene from strain A's antiSMASH ZIP, aligns each against strain B's
    full CDS set (its 'proteome' at BGC resolution), writes a per-BGC gene-level similarity
    table, and recovers the comparator layers (ClusterBlast organism / SubClusterBlast
    operon / MIBiG ranking — already retained on the BGC as of v9.7.166). ANI (S1/S2) runs
    only when genome FASTAs are supplied and pyfastani is importable.
    """
    import csv
    import json
    import os
    from .parsers import extract_cds_features

    alignment_threads = getattr(args, "alignment_threads", 1)
    if (isinstance(alignment_threads, bool) or not isinstance(alignment_threads, int)
            or alignment_threads < 1):
        emit("[gemini] --alignment-threads must be a positive integer")
        return 2

    out = args.out
    os.makedirs(out, exist_ok=True)
    backend = _aligner_backend()

    def _genes(zip_or_pkg):
        # accept an antiSMASH zip directly; extract (locus, translation) per CDS
        feats = extract_cds_features(zip_or_pkg)
        return [((f.locus_tag or f"cds_{i}"), (f.translation or "")) for i, f in enumerate(feats) if f.translation]

    # v9.7.409 (AUDIT_cli_edgecases): the strain inputs are opened as ZIPs; a non-zip file used to
    # crash with a raw zipfile.BadZipFile, and a missing path with a raw FileNotFoundError. `inspect`
    # guards this; mirror it here with a typed refusal (rc 1) instead of a traceback.
    import zipfile as _zipfile
    try:
        genes_a = _genes(args.strain_a)
        genes_b = _genes(args.strain_b)
    except FileNotFoundError as exc:
        emit(f"[gemini] ERROR: strain input not found: {getattr(exc, 'filename', None) or exc}")
        return 1
    except _zipfile.BadZipFile:
        emit("[gemini] ERROR: strain input is not a valid antiSMASH ZIP "
              f"(strain-a={args.strain_a}, strain-b={args.strain_b})")
        return 1
    if not genes_a or not genes_b:
        emit(f"[gemini] could not extract CDS translations "
              f"(A={len(genes_a)}, B={len(genes_b)}) — need antiSMASH ZIPs with CDS features")
        return 1

    emit(f"[gemini] backend={backend} · strain A {len(genes_a)} genes · strain B {len(genes_b)} genes")

    # S2 ANI when genome FASTAs supplied
    ani = None
    if getattr(args, "genome_a", None) and getattr(args, "genome_b", None):
        try:
            from Bio import SeqIO
            ca = [str(r.seq) for r in SeqIO.parse(args.genome_a, "fasta")]
            cb = [str(r.seq) for r in SeqIO.parse(args.genome_b, "fasta")]
            ani = compute_ani(ca, cb)
            if ani["ok"]:
                emit(f"[gemini] ANI ({ani['backend']}): {ani['ani']}% "
                      f"(aligned fraction {ani['aligned_fraction']}%)")
        except Exception as exc:
            emit(f"[gemini] ANI skipped: {exc}")
    hits = align_genes_to_proteome(genes_a, genes_b, threads=alignment_threads)
    if not hits and backend == "none":
        # v9.7.409 (AUDIT_cli_code_bugs #1): only a genuinely ABSENT backend is a dependency
        # problem. Previously this same message fired whenever a live backend produced no hits,
        # misdiagnosing a working install (the arm64 pyswrd-swallow case) as "not installed".
        emit("[gemini] no alignment backend is available — install DIAMOND (conda `diamond`), or "
              "pyswrd/biopython, then re-run (see install_sapote_addons.sh)")
        return 1
    if not hits:
        # A working backend that finds no shared genes is an HONEST 0-hit result, not a broken
        # install: write the (all-no_hit) S5 table + summary below and say so plainly.
        emit(f"[gemini] backend={backend}: 0 of strain A's {len(genes_a)} genes matched strain B "
              f"at reportable similarity — a real 0-hit result, not a missing dependency")

    # S5 output: one row per strain-A gene with its best strain-B match
    s5_path = os.path.join(out, "S5_gene_level_similarity.csv")
    import io as _io
    _s5_buf = _io.StringIO()
    w = _SafeWriter(_s5_buf)
    w.writerow(["query_gene", "best_match_B", "pct_identity", "pct_coverage",
                "call", "backend", "note"])
    for qid, _ in genes_a:
        h = hits.get(qid)
        if not h:
            w.writerow([qid, "", "", "", "no_hit", backend, ""])
            continue
        call = classify_gene(h.get("pident"), h.get("qcovhsp"))
        note = "similarity not identity; sub-70% = candidate, not absent" if call == "divergent_candidate" else ""
        w.writerow([qid, h["sseqid"], h["pident"], h.get("qcovhsp"), call, h["backend"], note])
    _atomic_write_text(s5_path, _s5_buf.getvalue())

    present = sum(1 for qid, _ in genes_a
                  if hits.get(qid) and classify_gene(hits[qid].get("pident"), hits[qid].get("qcovhsp")) == "present")
    summary = {
        "backend": backend,
        "alignment_threads": alignment_threads,
        "strain_a_genes": len(genes_a),
        "strain_b_genes": len(genes_b),
        "genes_present_in_B": present,
        "genes_present_pct": round(100.0 * present / len(genes_a), 1) if genes_a else None,
        "s5_table": os.path.basename(s5_path),
        "guardrails": [
            "all values are sequence similarity, NOT product identity",
            "sub-70% calls are divergent_candidate, never asserted absent (BGC050 false-negative guard)",
            "Edge/Full-contig low conservation may be truncation, not divergence",
        ],
        "diamond_status": "pyswrd/biopython backend (proven); DIAMOND fast-path is optional and auto-detected if on PATH",
    }
    if ani and ani.get("ok"):
        summary["ani"] = {"value": ani["ani"], "aligned_fraction": ani["aligned_fraction"],
                          "backend": ani["backend"],
                          "call": _ani_species_call(ani["ani"])}
    _atomic_write_text(os.path.join(out, "gemini_summary.json"), json.dumps(summary, indent=2))

    emit(f'[gemini] S5 written: {s5_path}', f"[gemini] {present}/{len(genes_a)} strain-A genes present in strain B ({summary['genes_present_pct']}%)", f"[gemini] summary: {os.path.join(out, 'gemini_summary.json')}", sep="\n")
    return 0


# Back-compat: the module was renamed gemini.py -> compare.py (v9.7.191). The old
# function name remains importable so nothing breaks mid-transition.
gemini_compare_command = compare_command
