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
import hashlib
import importlib
import importlib.metadata
import platform
import sys
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


SENSITIVITIES = ("fast", "mid-sensitive", "sensitive", "more-sensitive", "very-sensitive", "ultra-sensitive")


def _sensitivity_args(sensitivity: str | None) -> list[str]:
    """DIAMOND's search mode flag. None keeps DIAMOND's default (fast), which misses many homologues under ~40%
    identity; searches for distant pathway genes should ask for more-sensitive or ultra-sensitive."""
    if sensitivity is None:
        return []
    if sensitivity not in SENSITIVITIES:
        raise ValueError(f"unknown DIAMOND sensitivity {sensitivity!r}; use one of {', '.join(SENSITIVITIES)}")
    return [f"--{sensitivity}"]


def _run_diamond_blastp_raw(db_path: str, query_fasta: str, out_path: str, threads: int,
                            sensitivity: str | None = None) -> list[str]:
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
        *_sensitivity_args(sensitivity),
    ]
    result = main(*args)
    if result not in (None, 0):
        raise RuntimeError(f"DIAMOND binding returned failure status: {result!r}")
    return args


def _forward_provenance(backend, query, reference, threads, min_pident, min_qcov, sensitivity, executable=None):
    """Record the selected backend; omitted backend defaults stay explicitly unknown.

    Fingerprints and version discovery are observational. Their failure is retained
    as a warning and never changes the search settings or the hit rows.
    """
    record = {"schema_version": "sapote.forward-alignment.v1", "backend": backend,
              "python_version": platform.python_version(), "python_executable": sys.executable,
              "threads": threads, "sensitivity": sensitivity or "BACKEND_DEFAULT",
              "backend_defaults": {"evalue": "NOT_EXPLICITLY_SET", "max_target_seqs": "NOT_EXPLICITLY_SET"},
              "post_filters": {"min_pident": min_pident, "min_qcov": min_qcov},
              "inputs": {}, "warnings": []}
    def fingerprint(path):
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            return {"path": os.path.realpath(path), "sha256": h.hexdigest()}
        except (OSError, TypeError) as exc:
            record["warnings"].append(f"fingerprint unavailable: {path}: {type(exc).__name__}")
            return {"path": str(path), "sha256": None}
    record["inputs"] = {"query": fingerprint(query), "reference": fingerprint(reference)}
    record["wrapper"] = fingerprint(__file__)
    if backend == "diamond_cli":
        record["executable"] = fingerprint(executable)
        try:
            result = subprocess.run([executable, "version"], capture_output=True, text=True, timeout=10, check=False)
            version = (result.stdout or result.stderr or "").strip()
            if result.returncode != 0 or not version:
                raise RuntimeError("empty or unsuccessful version response")
            record["engine_version_response"] = version
        except Exception as exc:
            record["engine_version_response"] = None
            record["warnings"].append(f"engine version unavailable: {type(exc).__name__}")
    else:
        # The Python distribution version is not asserted to be the embedded engine version.
        record["engine_version_response"] = None
        record["engine_version_state"] = "NOT_REPORTED_BY_BINDING"
        try:
            record["binding_package_version"] = importlib.metadata.version("diamond4py")
        except Exception:
            record["binding_package_version"] = None
            record["warnings"].append("diamond4py distribution metadata unavailable")
        for name in ("diamond4py", "diamond4py.libdiamond"):
            try:
                module = importlib.import_module(name)
                record[name] = fingerprint(getattr(module, "__file__", None))
            except Exception as exc:
                record[name] = {"path": None, "sha256": None}
                record["warnings"].append(f"module identity unavailable: {name}: {type(exc).__name__}")
    record["capture_state"] = "PARTIAL" if record["warnings"] else "CAPTURED"
    return record


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
                min_pident: float = 0.0, min_qcov: float = 0.0, sensitivity: str | None = None) -> dict[str, Any]:
    """Align query proteins against a reference protein FASTA and return parsed hits.

    Builds a temporary DIAMOND db from reference_fasta, runs blastp, parses -outfmt 6.
    Optional min_pident / min_qcov filters (both 0 = keep all) let callers apply the
    full-length-ortholog gate (e.g. min_qcov=50) that distinguishes real orthologs from
    short motif hits.

    sensitivity: DIAMOND search mode (see SENSITIVITIES); None keeps DIAMOND's default.

    Returns {ok, hits: [ {col: val, ...} ], n_hits, reason}. Degrades gracefully:
    ok=False with a reason when DIAMOND is unavailable or inputs are missing.
    """
    _sensitivity_args(sensitivity)  # refuse an unknown mode before any work
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
        return _align_fasta_cli(query_fasta, reference_fasta, threads, min_pident, min_qcov, sensitivity)

    provenance = _forward_provenance("diamond4py", query_fasta, reference_fasta, threads, min_pident, min_qcov, sensitivity)
    tmp = tempfile.mkdtemp(prefix="mamey_diamond_")
    try:
        db_path = os.path.join(tmp, "ref.dmnd")
        built = build_db(reference_fasta, db_path, threads=threads)
        if not built["ok"]:
            return {"ok": False, "hits": [], "n_hits": 0, "reason": built["reason"]}
        out_path = os.path.join(tmp, "hits.tsv")
        provenance["alignment_argv"] = _run_diamond_blastp_raw(built["db_path"], query_fasta, out_path, threads, sensitivity)
        hits = _parse_outfmt6(out_path, min_pident=min_pident, min_qcov=min_qcov)
        return {"ok": True, "hits": hits, "n_hits": len(hits), "reason": "ok", "provenance": provenance}
    except Exception as exc:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": f"blastp failed: {type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _align_fasta_cli(query_fasta: str, reference_fasta: str, threads: int,
                     min_pident: float, min_qcov: float, sensitivity: str | None = None) -> dict[str, Any]:
    """v9.7.409 (AUDIT_cli_code_bugs #1): align via the `diamond` CLI (makedb + blastp -outfmt 6)
    when the diamond4py binding is not compiled but a DIAMOND executable is on PATH. Reuses the
    same _OUTFMT6_COLS spec and _parse_outfmt6 parser as the binding path, so hit dicts are
    identical. Degrades gracefully: ok=False with a reason on any subprocess failure."""
    exe = shutil.which("diamond")
    if not exe:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": "no diamond CLI on PATH"}
    provenance = _forward_provenance("diamond_cli", query_fasta, reference_fasta, threads, min_pident, min_qcov, sensitivity, exe)
    tmp = tempfile.mkdtemp(prefix="mamey_diamondcli_")
    try:
        db_path = os.path.join(tmp, "ref.dmnd")
        out_path = os.path.join(tmp, "hits.tsv")
        subprocess.run([exe, "makedb", "--in", reference_fasta, "--db", db_path,
                        "--threads", str(threads), "--quiet"],
                       check=True, capture_output=True)
        command = [exe, "blastp", "--db", db_path, "--query", query_fasta, "--out", out_path,
                   "--outfmt", "6", *_OUTFMT6_COLS, "--threads", str(threads), "--quiet",
                   *_sensitivity_args(sensitivity)]
        provenance["alignment_argv"] = command
        subprocess.run(command, check=True, capture_output=True)
        hits = _parse_outfmt6(out_path, min_pident=min_pident, min_qcov=min_qcov)
        return {"ok": True, "hits": hits, "n_hits": len(hits), "reason": "ok (diamond CLI)", "provenance": provenance}
    except Exception as exc:
        return {"ok": False, "hits": [], "n_hits": 0,
                "reason": f"diamond CLI failed: {type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def search_db(query_fasta: str, db_path: str, threads: int = 1, sensitivity: str | None = None,
              evalue: str = "1e-5", max_target_seqs: int = 25) -> dict[str, Any]:
    """Search query proteins against a prebuilt DIAMOND database (.dmnd), e.g. the local MIBiG protein database.

    Same hit dicts as align_fasta. Uses the `diamond` CLI; returns ok=False with a reason when it is absent."""
    _sensitivity_args(sensitivity)
    exe = shutil.which("diamond")
    if not exe:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": "no diamond CLI on PATH"}
    if not os.path.exists(query_fasta) or not os.path.exists(db_path):
        return {"ok": False, "hits": [], "n_hits": 0, "reason": f"missing query or database: {query_fasta}, {db_path}"}
    tmp = tempfile.mkdtemp(prefix="mamey_diamonddb_")
    try:
        out_path = os.path.join(tmp, "hits.tsv")
        subprocess.run([exe, "blastp", "--db", db_path, "--query", query_fasta, "--out", out_path, "--outfmt", "6",
                        *_OUTFMT6_COLS, "--threads", str(threads), "--evalue", str(evalue),
                        "--max-target-seqs", str(max_target_seqs), "--quiet", *_sensitivity_args(sensitivity)],
                       check=True, capture_output=True)
        hits = _parse_outfmt6(out_path)
        return {"ok": True, "hits": hits, "n_hits": len(hits), "reason": "ok (diamond CLI, prebuilt db)"}
    except Exception as exc:
        return {"ok": False, "hits": [], "n_hits": 0, "reason": f"diamond search failed: {type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _parse_outfmt6(path: str, min_pident: float = 0.0, min_qcov: float = 0.0) -> list[dict[str, Any]]:
    """Parse a DIAMOND -outfmt 6 TSV with the _OUTFMT6_COLS column order into dicts.
    Numeric columns are cast; absent output or malformed rows refuse admission.
    A produced empty file remains a completed zero-hit output.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"DIAMOND output not produced: {path}")
    _float_cols = {"pident", "evalue", "bitscore", "qcovhsp", "scovhsp"}
    _int_cols = {"length", "mismatch", "gapopen", "qstart", "qend", "sstart", "send"}
    hits: list[dict[str, Any]] = []
    with open(path) as fh:
        for line_number, line in enumerate(fh, 1):
            parts = line.rstrip("\n").split("\t")
            if len(parts) != len(_OUTFMT6_COLS):
                raise ValueError(f"malformed DIAMOND output row {line_number}: wrong field count")
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
                raise ValueError(f"malformed DIAMOND numeric output row {line_number}")
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
