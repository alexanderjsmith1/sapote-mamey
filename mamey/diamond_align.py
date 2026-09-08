"""diamond_align.py — offline protein alignment via DIAMOND (diamond4py binding).

Purpose
-------
Resolves the recurring "this is a similarity call I can't run offline / needs a real
BLASTp against nr" wall in the saccharide/acarviostatin and cross-strain threads. With a
compiled DIAMOND available, Mamey can align a strain's BGC genes against ANY reference
FASTA (a MIBiG cluster's proteins, another strain's genes, a curated acarviostatin gene
set) and get real local-alignment identity + coverage — no NCBI, no network.

This is the deterministic evidence layer for cross-cluster comparison: it produces
identity/coverage the same way the manual `diamond blastp` calls in the analysis threads
did, but callable in-pipeline and claim-safe (identity/coverage are reported, never
interpreted as a chemistry claim here).

Dependency
----------
Requires the `diamond4py` package (a Python binding to the DIAMOND C++ aligner). That
package needs a C++ toolchain + cmake to build, so it is an OPTIONAL dependency: this
module imports lazily and every entry point degrades gracefully (returns an empty result
with a clear reason) when DIAMOND is not installed, so the rest of the pipeline is
unaffected. Install with `pip install diamond4py` in an environment that can compile it.

Output contract
---------------
align_fasta() returns a list of hit dicts with the columns the cross-strain analysis
depends on — one row per HSP, already the tabular -outfmt 6 form:
  {qseqid, sseqid, pident, length, mismatch, gapopen, qstart, qend, sstart, send,
   evalue, bitscore, qcovhsp, scovhsp}
pident = percent identity (SIMILARITY, not identity-of-molecule); qcovhsp/scovhsp = query/
subject coverage — the pair that distinguishes a real full-length ortholog (high pident AND
high coverage) from a short motif hit (high pident, tiny coverage), which was the exact
discriminator the saccharide-cluster comparisons hinged on.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any


# -outfmt 6 column spec — the identity/coverage columns the cross-strain comparisons need.
_OUTFMT6_COLS = [
    "qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
    "qstart", "qend", "sstart", "send", "evalue", "bitscore",
    "qcovhsp", "scovhsp",
]


def diamond_cli_available() -> tuple[bool, str]:
    """v9.7.409 (AUDIT_cli_code_bugs #1): probe for a `diamond` executable on PATH (a conda /
    Homebrew DIAMOND CLI). The diamond4py binding check never sees this binary, so a perfectly
    usable system DIAMOND was invisible to `compare`. Returns (available, reason)."""
    exe = shutil.which("diamond")
    if exe:
        return True, f"diamond CLI on PATH ({exe})"
    return False, "no diamond CLI on PATH"


def diamond_available() -> tuple[bool, str]:
    """Return (available, reason). True if the diamond4py binding imports and its compiled
    libdiamond loads, OR (v9.7.409) a `diamond` executable is on PATH. Cheap to call; used to
    gate every other entry point. When only the CLI is present, align_fasta drives it directly."""
    try:
        from diamond4py import Diamond  # noqa: F401
        return True, "diamond4py import OK"
    except ImportError as exc:
        cli_ok, cli_reason = diamond_cli_available()
        if cli_ok:
            return True, cli_reason
        return False, f"diamond4py not installed ({exc}); {cli_reason}"
    except Exception as exc:  # compiled extension present but failed to load
        cli_ok, cli_reason = diamond_cli_available()
        if cli_ok:
            return True, cli_reason
        return False, f"diamond4py present but failed to load: {type(exc).__name__}: {exc}"


def _run_diamond_blastp_raw(db_path: str, query_fasta: str, out_path: str, threads: int) -> None:
    """Call DIAMOND blastp with an explicit -outfmt 6 column spec via the raw argv entry
    point. The high-level diamond4py .blastp() does not forward --outfmt, so we drive
    libdiamond.main() directly to get the identity/coverage columns."""
    from diamond4py.libdiamond import main
    args = [
        "blastp",
        "--db", db_path,
        "--query", query_fasta,
        "--out", out_path,
        "--outfmt", "6", *_OUTFMT6_COLS,
        "--threads", str(threads),
        "--quiet",
    ]
    main(*args)


def build_db(reference_fasta: str, db_path: str, threads: int = 1) -> dict[str, Any]:
    """Build a DIAMOND .dmnd database from a protein FASTA (e.g. a reference cluster's
    genes, or a curated marker-gene set). Returns {ok, db_path, reason}."""
    ok, reason = diamond_available()
    if not ok:
        return {"ok": False, "db_path": None, "reason": reason}
    if not os.path.exists(reference_fasta):
        return {"ok": False, "db_path": None, "reason": f"reference FASTA not found: {reference_fasta}"}
    try:
        from diamond4py import Diamond
        # database arg is required at construction; makedb writes db_path(.dmnd)
        d = Diamond(database=db_path, n_threads=threads, quiet=True)
        d.makedb(reference_fasta)
        made = db_path if os.path.exists(db_path) else db_path + ".dmnd"
        if not os.path.exists(made):
            return {"ok": False, "db_path": None, "reason": "makedb ran but no .dmnd produced"}
        return {"ok": True, "db_path": made, "reason": "db built"}
    except Exception as exc:
        return {"ok": False, "db_path": None, "reason": f"makedb failed: {type(exc).__name__}: {exc}"}


def align_fasta(query_fasta: str, reference_fasta: str, threads: int = 1,
                min_pident: float = 0.0, min_qcov: float = 0.0) -> dict[str, Any]:
    """Align query proteins against a reference protein FASTA and return parsed hits.

    Builds a temporary DIAMOND db from reference_fasta, runs blastp, parses -outfmt 6.
    Optional min_pident / min_qcov filters (both 0 = keep all) let callers apply the
    full-length-ortholog gate (e.g. min_qcov=50) that distinguishes real orthologs from
    short motif hits.

    Returns {ok, hits: [ {col: val, ...} ], n_hits, reason}. Degrades gracefully:
    ok=False with a reason when DIAMOND is unavailable or inputs are missing.
    """
    ok, reason = diamond_available()
    if not ok:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": reason}
    for f, label in [(query_fasta, "query"), (reference_fasta, "reference")]:
        if not os.path.exists(f):
            return {"ok": False, "hits": [], "n_hits": 0, "reason": f"{label} FASTA not found: {f}"}

    # v9.7.409 (AUDIT_cli_code_bugs #1): prefer the compiled binding; when it is absent but a
    # `diamond` executable is on PATH, drive the CLI (makedb + blastp) instead of failing.
    try:
        from diamond4py import Diamond  # noqa: F401
        _have_binding = True
    except Exception:
        _have_binding = False
    if not _have_binding:
        return _align_fasta_cli(query_fasta, reference_fasta, threads, min_pident, min_qcov)

    tmp = tempfile.mkdtemp(prefix="mamey_diamond_")
    try:
        db_path = os.path.join(tmp, "ref.dmnd")
        built = build_db(reference_fasta, db_path, threads=threads)
        if not built["ok"]:
            return {"ok": False, "hits": [], "n_hits": 0, "reason": built["reason"]}
        out_path = os.path.join(tmp, "hits.tsv")
        _run_diamond_blastp_raw(built["db_path"], query_fasta, out_path, threads)
        hits = _parse_outfmt6(out_path, min_pident=min_pident, min_qcov=min_qcov)
        return {"ok": True, "hits": hits, "n_hits": len(hits), "reason": "ok"}
    except Exception as exc:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": f"blastp failed: {type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _align_fasta_cli(query_fasta: str, reference_fasta: str, threads: int,
                     min_pident: float, min_qcov: float) -> dict[str, Any]:
    """v9.7.409 (AUDIT_cli_code_bugs #1): align via the `diamond` CLI (makedb + blastp -outfmt 6)
    when the diamond4py binding is not compiled but a DIAMOND executable is on PATH. Reuses the
    same _OUTFMT6_COLS spec and _parse_outfmt6 parser as the binding path, so hit dicts are
    identical. Degrades gracefully: ok=False with a reason on any subprocess failure."""
    exe = shutil.which("diamond")
    if not exe:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": "no diamond CLI on PATH"}
    tmp = tempfile.mkdtemp(prefix="mamey_diamondcli_")
    try:
        db_path = os.path.join(tmp, "ref.dmnd")
        out_path = os.path.join(tmp, "hits.tsv")
        subprocess.run([exe, "makedb", "--in", reference_fasta, "--db", db_path,
                        "--threads", str(threads), "--quiet"],
                       check=True, capture_output=True)
        subprocess.run([exe, "blastp", "--db", db_path, "--query", query_fasta, "--out", out_path,
                        "--outfmt", "6", *_OUTFMT6_COLS, "--threads", str(threads), "--quiet"],
                       check=True, capture_output=True)
        hits = _parse_outfmt6(out_path, min_pident=min_pident, min_qcov=min_qcov)
        return {"ok": True, "hits": hits, "n_hits": len(hits), "reason": "ok (diamond CLI)"}
    except Exception as exc:
        return {"ok": False, "hits": [], "n_hits": 0,
                "reason": f"diamond CLI failed: {type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _parse_outfmt6(path: str, min_pident: float = 0.0, min_qcov: float = 0.0) -> list[dict[str, Any]]:
    """Parse a DIAMOND -outfmt 6 TSV with the _OUTFMT6_COLS column order into dicts.
    Numeric columns are cast; unparseable rows are skipped."""
    if not os.path.exists(path):
        return []
    _float_cols = {"pident", "evalue", "bitscore", "qcovhsp", "scovhsp"}
    _int_cols = {"length", "mismatch", "gapopen", "qstart", "qend", "sstart", "send"}
    hits: list[dict[str, Any]] = []
    with open(path) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != len(_OUTFMT6_COLS):
                continue
            row: dict[str, Any] = {}
            ok = True
            for col, val in zip(_OUTFMT6_COLS, parts):
                if col in _float_cols:
                    try:
                        row[col] = float(val)
                    except ValueError:
                        ok = False
                        break
                elif col in _int_cols:
                    try:
                        row[col] = int(val)
                    except ValueError:
                        ok = False
                        break
                else:
                    row[col] = val
            if not ok:
                continue
            if row.get("pident", 0.0) < min_pident:
                continue
            if row.get("qcovhsp", 0.0) < min_qcov:
                continue
            hits.append(row)
    return hits


def best_hit_per_query(hits: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Collapse HSP rows to the single best hit per query gene (max bitscore). Useful for
    the ortholog-mapping view: 'does query gene X have a full-length counterpart in the
    reference, and at what identity/coverage'."""
    best: dict[str, dict[str, Any]] = {}
    for h in hits:
        q = h.get("qseqid")
        if q is None:
            continue
        if q not in best or h.get("bitscore", 0) > best[q].get("bitscore", 0):
            best[q] = h
    return best
