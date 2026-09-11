"""Mamey CLI.

Usage:
    # Single strain
    python mamey_run.py run \\
        --strain Actinomadura_rubrisoli_H3C3 \\
        --input-zip H3C3.zip \\
        --taxonomy "Actinomadura rubrisoli" \\
        --source "Type strain; red-coloured arid soil" \\
        --master project_master.xlsx \\
        --outdir ./runs \\
        --mode gold

    # Batch of up to 3 strains
    python mamey_run.py run \\
        --strains H3C3.zip AS-XXX.zip AS-XXX.zip \\
        --master project_master.xlsx \\
        --outdir ./runs \\
        --mode gold        # gold (default; the only analysis mode) | `standard` retired v9.7.92 (aliases to gold); `smoke` removed v9.7.161

    # Validate an existing package
    python mamey_run.py validate ./runs/H3C3/package
"""
from __future__ import annotations
import logging as _logging
import warnings as _warnings
from contextlib import suppress as _suppress

_LOGGER = _logging.getLogger(__name__)

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import contextlib as _contextlib
import os
from .workspace_root import workspace_root
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import shutil
from datetime import date
from pathlib import Path

from . import __version__, BUNDLE_VERSION
from . import discover as _discover
from . import genus_appendix as _genus_appendix
from . import af_dossier as _af_dossier  # D2: Antifungal (AF) Lead Dossier (report-only)
from . import good_guesses as _good_guesses  # FA7: Good Guesses interpretive-priors report (report-only)
from . import reference_dark_prior as _reference_dark  # v9.7.343: wire the orphaned reference-dark prior (report-only)
from .models import RunContext, MameyRun
from .bioactivity_metadata import BioactivityMetadataError, normalize_bioactivity
from .antismash_input import identify as identify_antismash_input
from .parsers import (
    GbkSizeGuardRefusal, parse_bgcs_from_zip, assembly_metrics_from_zip,
    extract_antismash_version, extract_cds_features,
    extract_contig_sequences, extract_domain_features,
    parse_antismash_evidence_status,
)
from .antismash_evidence import parse_antismash_evidence, apply_evidence_to_bgcs, extract_gbk_pfam_hits, merge_tigrfam_into_pfam_hits
from .source_scans import run_source_scans
from .rggmci import run_rggmci
from .pks_ks_scan import run_pks_ks_scan, write_pks_ks_csv  # .359 (phylogenomics-lane P358): _4B intrinsic PKS-KS clade scan
from .bgc_decomp import (
    TWO_MODEL_DECOMP_HEADERS,
    run_bgc_decomp,
    two_model_flag_cell as _two_model_flag_cell,
)
from .external_adapters import run_external_scan_pack
# v9.7.409 (A1 / RUN-1): master_workbook is imported lazily at its two call sites below. It
# hard-imports openpyxl at module load, which made openpyxl a requirement for EVERY verb --
# `doctor`, `--help` and `--version` crashed with a raw ModuleNotFoundError before doctor
# could print its own "openpyxl MISSING" line. Verified: with openpyxl blocked, deferring
# this one import is sufficient for `import mamey.cli` to succeed.
from .validate import validate_package
from .output_checklist import write_output_checklist
from .cell_provenance import write_cell_provenance
from .packaging import write_manifest, zip_package
from .packaging import write_post_seal_checksums  # v9.7.409: post-seal integrity manifest (N1/N2/N9)
from .ziputil import regular_file_names
from .packaging import _atomic_write_text as _atomic_write_manifest_text  # AUDIT_371: reuse the established CORE-P04 atomic-write pattern for cli.py's own
from .packaging import atomic_open as _atomic_open_pkg  # AUDIT_374: same CORE-P04 pattern for _write_package()'s streamed/CSV writes
# manifest.json writes (see fix sites below) instead of plain write_text(), which can leave a
# truncated/corrupt-but-parseable manifest.json on an interrupted write -- silently stripped of
# all scientific metadata (mode, bgcs, scans) by packaging.write_manifest()'s own silent
# except-Exception base-reload fallback, sailing past validate.py's manifest_unreadable check
# (which only catches JSON parse failures, not valid-but-empty JSON).
from .render_brief import render_brief
from .chatgpt_commands import render_figures_command, mode_b_command
from .bgc_blastp_panel import command as bgc_blastp_panel_command, write_panel as write_bgc_blastp_panel
from .blastp_followup import command as blastp_followup_command
from .wise_fragmented_pks import command as wise_fragmented_pks_command
# Wave A (v9.7.341, bundle-only report/tooling layers) — post-seal, non-blocking subcommands
from .compound_family_report import compound_families_command
from .p450_tailoring import p450_tailoring_command
from .dualpass_ledger import dualpass_command
from .assembly_line import assembly_line_command
# Wave B (v9.7.341 follow-up) — lead-only §31–40 + related-genomes dossier pages
from .lead_pages import lead_pages_command
# render-widgets (Group D, .344): Codex native post-seal widget deliverable
from .widget_deliverable import render_widgets_command
from .package_inspector import inspect_command, explain_command, list_bgcs_command
from .session_resume import resume_command
from .packaging import fingerprint_command  # v9.7.199: determinism fingerprint verb
from .handoff import handoff_command          # v9.7.199: portable handoff bundler verb
from .compile_report import compile_report_command
from .mode_b_receipt import (
    ingest_receipts_command,
    validate_finished_review_request_command,
)
from .timing import TimingRecorder, heartbeat_context
from .gene_by_gene import build_gene_by_gene_table
from .crosswalk import build_bgc_crosswalk, candidate_blastp_rows, assembly_locator


RUN_STATEMENT = (
    "Mamey is running extraction analysis. "
    "All source-derived scans are performed from antiSMASH/GBK/JSON/TXT evidence. "
    "Judgment (Mode B, ecological synthesis, WL interpretation) requires the "
    "Mamey v1.2 prompt in a Claude session or Sapote-slim."
)


def _chatgpt_safe_strain_guess(path: str | Path) -> str:
    """Derive a stable strain ID from uploaded ZIP names.

    ChatGPT/iPhoto/browser uploads often append copy suffixes such as
    ``(4)``, ``copy``, or ``loose``. These are file-transfer artifacts, not
    strain identifiers, and should not leak into suggested commands or default
    output paths.
    """
    import re as _re
    stem = Path(path).stem
    for suffix in ("_genomic", "_antismash", "_results"):
        stem = _re.sub(_re.escape(suffix) + r"$", "", stem, flags=_re.I)
    # Browser/ChatGPT duplicate-upload suffixes: TESTSTRAIN385(4), TESTSTRAIN441 loose(6).
    stem = _re.sub(r"\s*\(\d+\)\s*$", "", stem)
    # Common informal copy/profile words in uploaded filenames, not strain IDs.
    stem = _re.sub(r"(?i)(?:[ _-]+(?:loose|copy|new))+\s*$", "", stem)
    stem = stem.replace(" ", "_")
    stem = _re.sub(r"[^A-Za-z0-9_.-]+", "_", stem)
    stem = _re.sub(r"_+", "_", stem).strip("_")
    return stem or Path(path).stem


def _count_antismash_region_gbks(zip_path: str | Path) -> int:
    """Cheap preflight BGC count for ChatGPT-safe batch sizing.

    Delegates to parsers.region_gbk_count so this count matches what the parser will
    actually read. The previous inline test (`endswith(".gbk") and "region" in name`)
    counted macOS AppleDouble shadows too, so a Finder-made ZIP reported DOUBLE its real
    region count and could trip the batch-size guard on a batch that was never too large.
    """
    from .parsers import region_gbk_count
    return region_gbk_count(zip_path)


def _chatgpt_safe_batch_too_large(input_zips: list[str]) -> tuple[bool, str]:
    """Return whether a ChatGPT-safe multi-strain batch should be split.

    Capped ChatGPT sessions are more reliable when large uploaded antiSMASH ZIPs
    are run one strain at a time. This is intentionally a ChatGPT-only guard;
    Claude/local users may still run multi-strain batches.
    """
    counts = [(str(_p), _count_antismash_region_gbks(_p)) for _p in input_zips]
    total = sum(_c for _, _c in counts)
    # Allow small smoke batches, but split large aggregate work before partial runs waste time.
    too_large = len(counts) > 1 and (total > 40 or any(_c > 25 for _, _c in counts))
    detail = ", ".join(f"{Path(_p).name}:{_c}" for _p, _c in counts)
    return too_large, f"{total} region GBKs across {len(counts)} ZIP(s): {detail}"


# ---------------------------------------------------------------------------
# Depth floor (v1.2 §0) — determines what the prompt needs to do
# ---------------------------------------------------------------------------

def _dependency_banner() -> str:
    """One-line per-run declaration of dependency status — so the user and Mamey both see,
    every run, exactly which optional capabilities are active and what (if anything) to drop in.
    Nothing here is fatal on its own; it tells you which deliverables are available."""
    import importlib.util as _u
    def have(mod):
        try:
            return _u.find_spec(mod) is not None
        except Exception:
            return False
    # ijson: report system vs vendored vs absent
    try:
        from . import antismash_evidence as _ae
        if _ae._HAVE_IJSON:
            ij = "system" if have("ijson") else "vendored"
            ij_line = "ijson(%s)\u2713 JSON streaming on" % ij
        else:
            ij_line = "ijson\u2717 bounded\u2192TXT-only (drop in ijson, or it ships vendored)"
    except Exception:
        ij_line = "ijson?"
    core = "openpyxl\u2713" if have("openpyxl") else "openpyxl\u2717 REQUIRED for workbooks \u2014 install it"
    # F2a (v9.7.247): pandas is REQUIRED by the mamey-native figure set
    # (mamey_native_figures._require_deps raises without it), not optional. The banner used to print
    # figures✓ on a tree where render-all-figures --all raises at run time, after a green preflight.
    figs_ok = have("numpy") and have("matplotlib") and have("pandas")
    figs = "figures\u2713" if figs_ok else "figures\u2717 (need numpy+matplotlib for FULL-ANALYSIS figure deliverables)"
    bio = "biopython\u2713" if have("Bio") else "biopython\u2014(optional for core; shim covers GBK parsing \u2014 but triage-raw AND blastp-online need it; bundled wheel is Linux-only)"
    # C4 v9.7.58: surface REGISTRY_DETECTOR_ACTIVE so silent fallback to hardcoded patterns is visible
    try:
        from .source_scans import REGISTRY_DETECTOR_ACTIVE as _rda
        reg = "registry_detector\u2713" if _rda else "registry_detector\u2014(fallback to hardcoded patterns)"
    except Exception:
        reg = "registry_detector?"
    # F2d (v9.7.247): offline_deps/ ships in the MERGED and SID tiers only. The CODE tier printed a
    # pointer to a bootstrap script that is not in the tree. Say it only when it is true.
    from pathlib import Path as _P
    _offline = "\n        offline installs in offline_deps/ (bash offline_deps/bootstrap_offline.sh) \u2014 see docs/PREREQUISITES.md" \
        if (_P(__file__).resolve().parents[1] / "offline_deps").is_dir() else ""
    return "  deps: %s | %s | %s | %s\n        registry: %s%s" % (
        core, ij_line, figs, bio, reg, _offline)


def _depth_floor(bgc, cctt_coupling: dict | None = None, mode: str = "gold",
                  rt_per_bgc: dict | None = None) -> str:
    """Depth-floor assignment for a BGC's Mode B treatment.

    v9.7.93 (Cut 2): standard mode is retired (v9.7.92) and gold is the engine's
    only full-analysis mode — it gives EVERY BGC full Mode B (edge / Full-contig
    included). The former standard depth-floor heuristic (Interior → CCTT trigger →
    KCB-cumulative threshold → T1-dark-BGC promotion) is removed. Under gold every
    BGC floors to full_mode_b, so the dark-BGC novelty profile that the heuristic
    specifically rescued (T1 self-protection + no MIBiG KCB) is now covered by
    gold-uniformity rather than a special rule, and nothing is ever abbreviated.

    smoke mode is triage-only and never reaches this function. The parameters
    (cctt_coupling, mode, rt_per_bgc) are retained for call-site compatibility.
    """
    return "full_mode_b"


# ---------------------------------------------------------------------------
# Single-strain run
# ---------------------------------------------------------------------------

import os as _os
import subprocess as _sub
import sys as _sys
import time as _time
import signal as _signal

# --- audit P1: unbuffered, timestamped stage heartbeat (stderr) ----------------------------
# A long parse must look like progress, not a hang. These lines go to stderr with flush=True so
# they appear in real time even when stdout is captured by a calling harness. Silence with
# MAMEY_QUIET_STAGES=1.
_RUN_T0 = None


def _stage(msg: str) -> None:
    if _os.environ.get("MAMEY_QUIET_STAGES"):
        return
    global _RUN_T0
    now = _time.time()
    if _RUN_T0 is None:
        _RUN_T0 = now
    emit(f"[{_time.strftime('%H:%M:%S')}] (+{now - _RUN_T0:5.1f}s) {msg}", file=_sys.stderr, flush=True)


class _BoundedTimeout(Exception):
    pass


def _with_timeout(seconds: int, fn, *args, **kwargs):
    """Run fn under a wall-clock budget (SIGALRM, main thread, Unix). Raises _BoundedTimeout on
    overrun. Where SIGALRM is unavailable (Windows), runs without a guard (returns normally).
    Note: on Windows the render timebox is simply not applied — this is intentional; it is not a bug.
    """
    if seconds <= 0 or not hasattr(_signal, "SIGALRM"):
        return fn(*args, **kwargs)

    def _handler(signum, frame):
        raise _BoundedTimeout()

    old = _signal.signal(_signal.SIGALRM, _handler)
    _signal.alarm(int(seconds))
    try:
        return fn(*args, **kwargs)
    finally:
        _signal.alarm(0)
        _signal.signal(_signal.SIGALRM, old)


# audit v9.7.49: a strain-brief render failure or a matplotlib/font-manager STALL must NEVER block the
# package seal. The brief (and its figures) are a cosmetic extraction-layer add-on; gate_validation.json,
# gold_mode_receipt.json, checksums, and the Complete Package ZIP are the deliverable. Wall-clock budget,
# env-overridable; a slow first render (font-cache build) completes inside it, a true hang is killed.
MAMEY_BRIEF_TIMEOUT_S = int(_os.environ.get("MAMEY_BRIEF_TIMEOUT_S", "120"))
# v9.7.80 P0: subprocess render timeout (hard-kill; replaces unreliable in-process SIGALRM).
MAMEY_RENDER_TIMEOUT_S = int(_os.environ.get("MAMEY_RENDER_TIMEOUT_S", str(MAMEY_BRIEF_TIMEOUT_S)))
# v9.7.88 Finding L (Option A): seal the deterministic core FIRST, then render the brief as a
# separate post-seal phase. A scientific artifact must not depend on a cosmetic render step — they
# are different reliability classes. With seal-first ON (default), manifest/gate/checksums/ZIP are
# written before the brief, so a render hang costs figures, never the core. CONTRACT CHANGE: with
# seal-first ON the brief/figure files live OUTSIDE the core ZIP/checksum set (tracked separately).
# Set MAMEY_SEAL_FIRST=0 to restore the old render-before-seal behaviour (Option B / pre-v9.7.88).
MAMEY_SEAL_FIRST = _os.environ.get("MAMEY_SEAL_FIRST", "1") not in ("0", "false", "no", "")



def _parse_evidence_with_budget(input_zip, json_mode, budget, stage):
    """Preserve the requested mode and actual CLI budget outcome in the saved receipt.

    This guard wraps the status parser, including its separate record passes;
    it is not the main walker's matched-leaf cap. Return behavior is unchanged.
    """
    requested = json_mode
    budget_state = "DISABLED" if budget <= 0 else "NOT_APPLICABLE"
    if json_mode == "bounded" and budget > 0:
        try:
            evidence = _with_timeout(budget, parse_antismash_evidence_status,
                                     input_zip, json_mode="bounded")
            budget_state = ("RETURNED_GUARD_ARMED" if hasattr(_signal, "SIGALRM")
                            else "RETURNED_GUARD_UNAVAILABLE")
        except _BoundedTimeout:
            stage(f"[WARN] bounded json-evidence exceeded {budget}s — falling back to main JSON walker off; record paths are independent")
            json_mode = "off"
            evidence = parse_antismash_evidence_status(input_zip, json_mode="off")
            budget_state = "EXCEEDED_FALLBACK_OFF"
    else:
        evidence = parse_antismash_evidence_status(input_zip, json_mode=json_mode)
    evidence["json_mode_requested"] = requested
    evidence["json_parse_budget"] = {
        "seconds": budget, "state": budget_state,
        "scope": "CLI status parser including requested record passes; fallback outside budget",
    }
    return evidence, json_mode

def _phase_receipt(package_dir, phase: str, status: str, **kw) -> bool:
    """P0: Append one JSONL receipt row to run_phase_receipts.jsonl.
    Machine-readable phase log for ChatGPT sessions; never raises. Returns
    whether the row was written; an independent warning exposes write failure
    because the failed receipt cannot diagnose itself.
    v9.7.87 9.7.87-A: also carries a monotonic timestamp (mono_ns) so the timing
    breakdown can pair START/END and compute real per-phase deltas — the HH:MM:SS
    display field is fragile (no date, no sub-second, breaks across midnight)."""
    import json as _j
    _pkg = Path(package_dir).resolve()

    def _portable(value):
        if isinstance(value, dict):
            return {key: _portable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_portable(item) for item in value]
        if isinstance(value, (str, Path)):
            text = str(value)
            candidate = Path(text)
            if candidate.is_absolute():
                try:
                    return candidate.resolve().relative_to(_pkg).as_posix()
                except ValueError:
                    return candidate.name
        return value

    row = {"phase": phase, "status": status, "time": _time.strftime("%H:%M:%S"),
           "mono_ns": _time.monotonic_ns(), "version": __version__,
           **{key: _portable(value) for key, value in kw.items()}}
    try:
        with open(_os.path.join(str(package_dir), "run_phase_receipts.jsonl"), "a", encoding="utf-8") as _fh:
            _fh.write(_j.dumps(row) + "\n")
        return True
    except Exception as _receipt_exc:
        # The receipt cannot diagnose its own write failure. Logging is independent
        # of Python's warning filters (including ``-W error``); a hostile custom
        # logging handler also must not violate this helper's never-raises contract.
        with _suppress(Exception):
            _LOGGER.warning(
                "phase receipt write failed for %s: %s",
                phase,
                type(_receipt_exc).__name__,
            )
        return False



def _terminal_mamey_status(validator_status: str, issues: list[str] | tuple[str, ...] | None) -> str:
    """Canonical terminal status for console, receipts, and package_status.json.

    `package_status` keeps merge-safety semantics (MAMEY_COMPLETE vs recovery/partial),
    while `terminal_status` preserves issue-bearing completion for ChatGPT/audit readers.
    """
    validator_status = str(validator_status or "")
    issue_count = len(issues or [])
    if validator_status == "MAMEY_COMPLETE":
        return "MAMEY_COMPLETE_WITH_ISSUES" if issue_count else "MAMEY_COMPLETE"
    if validator_status == "PASS" and issue_count == 0:
        return "MAMEY_COMPLETE"
    if validator_status in {"PASS", "PASS_WITH_ISSUES", "MAMEY_COMPLETE_WITH_ISSUES"}:
        return "MAMEY_COMPLETE_WITH_ISSUES"
    if validator_status == "FAIL":
        return "VALIDATION_FAIL"
    return validator_status


def _stamp_terminal_status(package_dir: Path, *, validator_status: str, issues: list[str] | tuple[str, ...]) -> str:
    """Persist terminal_status/issue_count before final manifest/checksum/ZIP seal.

    BCHERRY-374: manifest.json's "issues"/"issue_count" are refreshed here because
    _write_package() (cli.py ~1634) snapshots `run.issues` BEFORE the package_addons
    phase (~1677) can still append to it (e.g. OVER_MERGE_CANDIDATES) -- this function
    is the existing, deliberate fix for that staleness, applied to manifest.json only.
    commit_receipt.json and issue_log.md are written by that SAME early _write_package()
    snapshot and suffer the identical staleness (confirmed live on AS-XXX: both files
    stopped at 4 issues while manifest.json correctly shows all 5 once this function
    ran), but never received the equivalent refresh. Extending it here rather than
    filing a second, parallel mechanism.
    """
    machine_status = _terminal_mamey_status(validator_status, issues)
    try:
        _mp = Path(package_dir) / "manifest.json"
        _base = json.loads(_mp.read_text(encoding="utf-8")) if _mp.exists() else {}
        _base["terminal_status"] = machine_status
        _base["issue_count"] = len(issues or [])
        _base["issues"] = list(issues or [])
        _mp.write_text(json.dumps(_base, indent=2), encoding="utf-8")
    except Exception as _e:
        # A package sealing WITHOUT its terminal status must be visible, not silent:
        # the phase log is the never-raises channel built for exactly this.
        _phase_receipt(package_dir, "stamp_terminal_status", "FAIL", error=repr(_e))
    # BCHERRY-374: refresh the two sibling issue surfaces from the same up-to-date
    # `issues` list, same fail-open pattern as the manifest.json refresh above.
    try:
        _crp = Path(package_dir) / "commit_receipt.json"
        if _crp.exists():
            _cr = json.loads(_crp.read_text(encoding="utf-8"))
            _cr["issues"] = list(issues or [])
            _cr["status"] = "PASS_WITH_ISSUES" if issues else "PASS"
            _crp.write_text(json.dumps(_cr, indent=2), encoding="utf-8")
    except Exception as _e:
        _phase_receipt(package_dir, "stamp_terminal_status_commit_receipt", "FAIL", error=repr(_e))
    try:
        _ilp = Path(package_dir) / "issue_log.md"
        if issues:
            _issue_text = "# Issue Log\n\n" + "\n".join(f"- {i}" for i in issues)
        else:
            _issue_text = "# Issue Log\n\n- No blocking issues recorded.\n"
        _ilp.write_text(_issue_text, encoding="utf-8")
    except Exception as _e:
        _phase_receipt(package_dir, "stamp_terminal_status_issue_log", "FAIL", error=repr(_e))
    try:
        from .recovery_status import write_package_status_receipt as _wpsr
        _wpsr(package_dir, validator_status=validator_status,
              terminal_status=machine_status, issue_count=len(issues or []))
    except Exception as _status_exc:
        _phase_receipt(
            package_dir,
            "stamp_terminal_status_package_status",
            "FAIL",
            error_type=type(_status_exc).__name__,
        )
        with _suppress(Exception):
            _LOGGER.warning(
                "terminal package-status receipt write failed: %s",
                type(_status_exc).__name__,
            )
    return machine_status


def _render_brief_nonblocking(package_dir, tier, on_issue, timeout_s=None):
    """P0 patch: run render_brief in a subprocess with hard kill on timeout.

    Falls back to in-process SIGALRM if subprocess spawn fails.
    On any failure writes BRIEF_SKIPPED_TIMEOUT.md and a phase receipt, then
    returns SKIPPED so the caller seals the core ZIP regardless.
    """
    from pathlib import Path as _Path
    pdir = _Path(package_dir).resolve()  # resolve: subprocess below runs with a different cwd
    if timeout_s is None:
        timeout_s = MAMEY_RENDER_TIMEOUT_S

    _phase_receipt(pdir, "brief_render", "START", tier=tier, timeout_s=timeout_s)

    # MAMEY_BRIEF_FORCE_INPROCESS=1: skip subprocess, use in-process path (for unit tests with mocks)
    if _os.environ.get("MAMEY_BRIEF_FORCE_INPROCESS"):
        try:
            r = _with_timeout(timeout_s, render_brief, str(pdir), tier=tier, logger=on_issue)
            _phase_receipt(pdir, "brief_render", "END", note="forced in-process")
            return r
        except _BoundedTimeout:
            reason = f"in-process timed out (> {timeout_s}s)"
            on_issue(f"[WARN] strain brief skipped (non-fatal): {reason}; package seals without it")
            _phase_receipt(pdir, "brief_render", "TIMEOUT", reason=reason)
            return {"status": "SKIPPED", "reason": reason, "files": [], "tier": tier}
        except Exception as _ep:
            reason = f"render error: {_ep}"
            on_issue(f"[WARN] strain brief skipped (non-fatal): {reason}; package seals without it")
            _phase_receipt(pdir, "brief_render", "ERROR", reason=reason)
            return {"status": "SKIPPED", "reason": reason, "files": [], "tier": tier}

    cmd = [
        _sys.executable, "-c",
        (
            "import sys, os; "
            "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(sys.executable))));"
            "from mamey.render_brief import render_brief; import json;"
            "r = render_brief(sys.argv[1], tier=sys.argv[2]); print(json.dumps(r))"
        ),
        str(pdir), tier,
    ]
    timed_out = False
    try:
        proc = _sub.run(cmd, timeout=timeout_s, capture_output=True, text=True,
                        cwd=str(_Path(__file__).parent.parent))
        if proc.returncode == 0 and proc.stdout.strip():
            import json as _j2
            result = _j2.loads(proc.stdout.strip().splitlines()[-1])
            _phase_receipt(pdir, "brief_render", "END", n_files=len(result.get("files", [])))
            return result
        reason = f"subprocess exit {proc.returncode}: {(proc.stderr or '')[:200]}"
    except _sub.TimeoutExpired:
        timed_out = True
        reason = f"subprocess timed out (> {timeout_s}s)"
    except Exception as _e:
        # Fallback: in-process
        try:
            r = _with_timeout(timeout_s, render_brief, str(pdir), tier=tier, logger=on_issue)
            _phase_receipt(pdir, "brief_render", "END", note="in-process fallback")
            return r
        except _BoundedTimeout:
            timed_out = True
            reason = f"in-process timed out (> {timeout_s}s)"
        except Exception as _e2:
            reason = f"render error: {_e2}"

    on_issue(f"[WARN] strain brief skipped (non-fatal): {reason}; package seals without it")
    skip_marker = "BRIEF_SKIPPED_TIMEOUT.md" if timed_out else "BRIEF_SKIPPED_ERROR.md"
    try:
        (pdir / skip_marker).write_text(
            "# Brief render skipped\n\n"
            f"Reason: {reason}\n\n"
            "The core Mamey package is complete and valid.\n"
            "Re-render: python -m mamey render-figures --package <pkg_dir>\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    try:
        with (pdir / "issue_log.md").open("a") as _il:
            _il.write(f"\n- [WARN] strain brief skipped: {reason}\n")
    except Exception:
        pass
    _phase_receipt(pdir, "brief_render", "TIMEOUT" if timed_out else "ERROR",
                   reason=reason, skip_marker=skip_marker)
    return {"status": "SKIPPED", "reason": reason, "files": [], "tier": tier}


def _write_batch_plan(package_dir, strain_id: str, mode: str, source: str,
                      issues: list[str] | None = None) -> bool:
    """audit P1: drop a ready-to-run projected next-batch plan so a single run always hands the
    operator a concrete continuation, per the intake-first/batch directive."""
    txt = (
        f"# Projected batch plan — after {strain_id}\n\n"
        f"`{strain_id}` is complete (mode={mode}). To process the rest of the cohort as one managed,\n"
        f"timeout-safe batch (NOT one strain at a time by hand), point the intake harness at the folder\n"
        f"of antiSMASH zips:\n\n"
        f"```\n"
        f"python tools/intake_harness.py --inputs <dir-of-zips> --outdir runs --registry runs/intake_registry.csv \\\n"
        f"  --metrics runs/intake_metrics.csv --batch-report runs/batch_report.md --resume \\\n"
        f"  --source \"{source}\" --release PUBLIC   # PRIVATE override always honored (e.g. AJS-/PENDING- strains)\n"
        f"```\n\n"
        f"- `--resume` skips strains already in the registry, so a timeout is safe to re-run.\n"
        f"- Per-strain wall-time/RSS are captured; a strain exceeding budget is an input/parse issue —\n"
        f"  checkpoint and continue (do not loop one strain). See prompts/RUN_DIAGNOSIS_PROMPT.md.\n"
    )
    target = package_dir / f"{strain_id}_BATCH_PLAN.md"
    try:
        target.write_text(txt, encoding="utf-8")
    except Exception as exc:
        message = f"BATCH_PLAN_WRITE_FAILED: {type(exc).__name__}: {exc}"
        if issues is not None:
            issues.append(message)
        _phase_receipt(package_dir, "batch_plan", "ERROR", reason=message)
        return False
    _phase_receipt(package_dir, "batch_plan", "END", path=target.name)
    return True


def _write_start_here(package_dir, strain_id, mode, status, raw, interior, edge, fc,
                      corrected, tier, issues: list[str] | None = None) -> bool:
    """audit W4/W14/W16/W30: one loud user-facing entrypoint. A PASS package with many files can feel
    'complete' when only deterministic EXTRACTION is done and the interpretive judgment is still pending."""
    # v9.7.161: smoke removed — gold is the only analysis mode, so the header is unconditional.
    # (v9.7.160 briefly branched here for a smoke NOT-ANALYZABLE banner; that path is gone.)
    _header = "## ✅ EXTRACTION COMPLETE  ·  ⏳ JUDGMENT PENDING"
    _lead = (
        f"This is a **Mamey deterministic-extraction** package (mode={mode}, validation={status}). It is the\n"
        f"skeleton — inventory, scans, scores, evidence. The **interpretive deliverables** (BGC-by-BGC Mode B,\n"
        f"DAPR, claim-safe ecology, bench/layperson guides, literature) are **NOT in this package**: they are\n"
        f"the separate **Sapote judgment** step. A rich PASS package is not a finished analysis.\n\n"
    )
    txt = (
        f"# START HERE — {strain_id}\n\n"
        f"{_header}\n\n"
        f"{_lead}"
        f"## Headline\n"
        f"- **{raw} raw BGCs** — {interior} Interior / {edge} Edge / {fc} Full-contig · **corrected {corrected} (effective estimate; Interior + ½·Edge + ¼·Full-contig)**\n"
        f"- **Assembly tier: {tier}**\n\n"
        f"## Start here (in order)\n"
        f"1. `{strain_id}_ANALYSIS_FORWARD.md` — the ranked leads to judge first.\n"
        f"   - Antibacterial lead board: `{strain_id}_4c_AB_lead_board.csv` · Antifungal: `{strain_id}_4c_AF_lead_board.csv`\n"
        f"     (pre-sorted; standing-rule-downgraded rows are marked in `Downgrade` and sink to the bottom).\n"
        f"2. Trigger the judgment layer: **`Run full Sapote analysis on {strain_id}`**.\n"
        f"3. To process the rest of the cohort: `{strain_id}_BATCH_PLAN.md` (one managed, timeout-safe batch).\n\n"
        f"## Optional: domain-level HMM scan (not run automatically)\n"
        f"The pyHMMER scanner registry is a separate pass, not part of `run`. For motif-level evidence\n"
        f"run **`python -m mamey hmm-adjudicate`** against this package once the science stack is\n"
        f"installed. It complements the source-derived domain architecture; not required for the boards.\n\n"
        f"## Which tier to run\n"
        f"Use the **CODE** tier for analysis; **SID-public** to share; never distribute **MERGED-PRIVATE**\n"
        f"(it contains unpublished identifiers). The four zips are the same engine — they differ only in\n"
        f"what's stripped for release.\n\n"
        f"## Ecology note (source-independent)\n"
        f"Interpretation is genome-grounded; unknown/`not supplied` isolation source does NOT block or defer\n"
        f"any deliverable, and a known source is provenance only — never read into a functional claim.\n"
        f"Check `source_provenance` in `manifest.json` before putting the host on a figure: `accession` /\n"
        f"`table` trace to a record; `filename` / `asserted` do NOT, and must not be captioned as this\n"
        f"strain's host until traced (`source_provenance_note` carries the sentence to use).\n\n"
        f"## RG-GMCI split-cluster pairs — how to read `{strain_id}_4A_RGGMCI_ranked_pairs.csv`\n"
        f"This file is shipped in every package and is easy to skip. Do not skip it. The ranked-pairs\n"
        f"table is mostly LOW background; the signal is a small number of HIGH/MODERATE pairs. For any\n"
        f"BGC you are judging:\n"
        f"1. Select every row where this BGC is `bgc_a` or `bgc_b`.\n"
        f"2. Filter by `rggmci_confidence`: report `HIGH_RG_GMCI_RESCUE` and `MODERATE_RG_GMCI_CANDIDATE`\n"
        f"   in detail; summarize the count of `LOW_SHARED_REFERENCE_SIGNAL` as background — do NOT enumerate.\n"
        f"3. For each reported pair give: partner BGC (with its node/contig), `rggmci_score`,\n"
        f"   `functional_rescue_class`, and the actionable interpretation.\n"
        f"4. `functional_rescue_class`, strongest evidence first:\n"
        f"   **COMPLEMENTARY** (strongest — one fragment carries the core biosynthetic machinery, the\n"
        f"   other the accessory genes; what a real split looks like) > **BOTH_CORE** (both fragments\n"
        f"   carry a near-complete core — corroborates PARALOGY, not a split) > **ACCESSORY_ONLY**\n"
        f"   (shared accessory genes only) > **AMBIGUOUS**.\n"
        f"5. Caution: high pair-count is NOT high confidence. A fragment that matches many reference\n"
        f"   clusters is usually promiscuous, not multiply-split — filter to HIGH/MODERATE and read\n"
        f"   `functional_rescue_class` before calling any link.\n"
        f"6. Always quote the claim-safety rail verbatim:\n"
        f"   *\"Homology-guided shared-reference linkage; not nucleotide-level joining.\"*\n"
        f"   A COMPLEMENTARY pair at HIGH confidence is a split-assembly HYPOTHESIS testable by genome\n"
        f"   closure — state it as a hypothesis, never as a physical contig merge. BOTH_CORE corroborates\n"
        f"   PARALOGY instead (an OVERLAPPING_PARALOG subject-tiling verdict), not a split.\n"
    )
    target = package_dir / "START_HERE.md"
    try:
        target.write_text(txt, encoding="utf-8")
    except Exception as exc:
        message = f"START_HERE_WRITE_FAILED: {type(exc).__name__}: {exc}"
        if issues is not None:
            issues.append(message)
        _phase_receipt(package_dir, "start_here", "ERROR", reason=message)
        return False
    _phase_receipt(package_dir, "start_here", "END", path=target.name)
    return True


# Strain-label policy: prefer a real strain name; an NCBI assembly accession used as the label is a
# FALLBACK only. Detect the common accession shapes so the run can flag "supply a strain name if you have
# one" rather than silently propagating an accession through every deliverable.
import re as _re
_ACCESSION_RE = _re.compile(
    r"^(?:NC_|NZ_|NW_|NT_|NG_)\d{6,}(?:\.\d+)?$"      # RefSeq chromosome, e.g. NC_003888.3
    r"|^(?:NZ_)?[A-Z]{4,6}\d{6,}(?:\.\d+)?$"          # WGS, e.g. NZ_QHHY00000000.1 / QHHY00000000
    r"|^GC[AF]_\d{9}(?:\.\d+)?$")                      # assembly, e.g. GCA_009862675.1


def _label_is_accession(strain_id: str) -> bool:
    # v9.7.372 (VGP): delegated so the accession pattern has ONE definition. The module also covers
    # the 2-letter INSDC prefixes (CP025018.1) this regex never matched, and the sanitised form
    # ("CP025018_1") that a cleaned filename actually produces.
    from .strain_identity import looks_like_accession
    return looks_like_accession(strain_id)


def _input_zip_sha256(path) -> str | None:
    """SHA-256 of the source antiSMASH ZIP, for self-contained manifest provenance.

    GOLDENROD .384: the manifest already records ``input_zip`` (the path) but not its
    content digest, so dedup / "which bytes went in" could not be answered from the
    manifest alone. Returns the 64-char hex digest, or ``None`` if the path is empty,
    missing, or unreadable (backward-compatible: old packages simply carry ``null``).
    Streamed in 1 MiB chunks; one pass over the ZIP, once per strain (not per BGC).
    """
    p = str(path) if path else ""
    if not p or not _os.path.exists(p):
        return None
    import hashlib as _hashlib
    h = _hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _emit_bgc_bank(package_dir, manifest: dict,
                   issues: list[str] | None = None) -> bool:
    """W6: write a single-strain bgc_data.json into the package, matching the cohort-bank schema
    (strains{sid:meta} + bgcs[]). This unblocks build_modeb_deepdive on ONE strain's package without the
    full cohort ingest (the 100-file-limit path). length_kb is read from the manifest (now materialised)."""
    try:
        sid = manifest.get("strain_id")
        tax = manifest.get("taxonomy") or manifest.get("display_name") or ""
        a = manifest.get("assembly") or {}
        bc = manifest.get("bgc_counts") or {}
        from mamey.cohort_resolver import resolve_cohort
        _coh = resolve_cohort(sid, tax)
        # CGAD (chitin/glycan ecology): derive from source_scans.chitinase if present.
        # cgad_active=True means ≥1 chitin-family gene detected genome-wide — used by
        # build_lead_tiers.py to resolve the nucleoside-antifungal chitin-context gate (H4 fix).
        _ss = manifest.get("source_scans") or {}
        _chitin_counts = (_ss.get("chitinase") or {}).get("counts") or {}
        _n_chitin = sum(v for v in _chitin_counts.values() if isinstance(v, (int, float)))
        cgad_active = _n_chitin > 0
        strains = {sid: {
            "organism": tax, "cohort": _coh["cohort"],
            # v9.7.402 (W402-35 round 3): persist the routing-vs-membership distinction into the
            # bank itself, not just the in-memory resolver result -- a reader of bgc_data.json
            # (e.g. build_modeb_deepdive, cross-strain synthesis) must not treat a persisted
            # cohort="OTHER" row as confirmed scientific cohort membership.
            "membership_authority": _coh.get("membership_authority"),
            "actino_status": _coh["actino_status"], "resolved_sid": _coh["resolved_sid"],
            "contigs": a.get("contigs"), "n50": a.get("n50"), "genome_bp": a.get("genome_bp"),
            "gc_pct": a.get("gc_pct"), "largest_contig": a.get("largest_contig"),
            "raw_bgcs": bc.get("raw"), "corrected_bgcs": bc.get("corrected"),
            "edge_dist": {"Interior": bc.get("interior"), "Full-contig": bc.get("full_contig"),
                          "Edge": bc.get("edge")},
            "cgad_active": cgad_active,  # H4: genome-level chitin context for nucleoside axis gate
        }}
        bgcs = []
        for b in manifest.get("bgcs", []):
            bgcs.append({
                "sid": sid, "organism": tax, "bgc_id": b.get("bgc_id"),
                "region": f"region{int(b.get('region_number') or 0):03d}", "contig": b.get("contig"),
                "products": ";".join(b.get("products") or []),
                "edge_status": b.get("edge_status"),
                "length_kb": b.get("length_kb"),
                "kcb_top": b.get("kcb_top"), "kcb_cumulative": b.get("kcb_cumulative"),
                "closest_kcb_product": b.get("closest_candidate_kcb_product"),
                "closest_mibig": b.get("closest_mibig_accession"),
                "cctt_triggers": b.get("cctt_triggers", ""),
                "release": b.get("release", ""),
                "riq": b.get("riq_label") or "",
                # AUDIT_374 fix: propagate the lead-exclusion flags scoring.py::triage_bgcs
                # already computed (standing_rule_flag / primary_metabolism_flag / mobile_element_flag)
                # so a downstream bgc_data.json consumer (e.g. figures_extra.py's deterministic figure
                # pack) can tell a rule-excluded/guard-suppressed BGC from a real lead. Previously these
                # three fields were dropped entirely here, so every consumer of bgc_data.json had no way
                # to filter them even if it wanted to -- 5th instance of the "excluded-BGC leak" pattern
                # (see AUDIT_374_META_excluded_bgc_leak_pattern/META_NOTE.md); depends on
                # AUDIT_374_manifest_bgc_downgrade_flags_missing also landing, since that is the
                # card that gets these flags into manifest_data["bgcs"] (this function's `b`) in the
                # first place -- until then these read as absent/empty here too, same as today.
                "standing_rule_flag": b.get("standing_rule_flag") or "",
                "primary_metabolism_flag": bool(b.get("primary_metabolism_flag")),
                "mobile_element_flag": b.get("mobile_element_flag") or "",
            })
        import json as _json
        (package_dir / "bgc_data.json").write_text(
            _json.dumps({"strains": strains, "bgcs": bgcs}, indent=2), encoding="utf-8")
    except Exception as exc:
        message = f"BGC_BANK_WRITE_FAILED: {type(exc).__name__}: {exc}"
        if issues is not None:
            issues.append(message)
        _phase_receipt(package_dir, "bgc_bank", "ERROR", reason=message)
        return False
    _phase_receipt(package_dir, "bgc_bank", "END", path="bgc_data.json")
    return True


class _LocusMapsSkipped(Exception):
    """P0 (v9.7.101): internal sentinel — locus-map render skipped by policy, not an error."""


def _emit_gold_figures(package_dir: Path, strain_id: str, mode: str) -> None:
    """Auto-emit single-strain gold figures (v9.7.148 PATCH-AUTO-FIGURES).

    Extracted verbatim from run_one_strain (v9.7.155 cli decomposition) so the
    strain-run orchestrator reads as a phase sequence. Requires gold mode
    (deep_data.json must exist). Non-blocking — figure failure never affects the
    package seal or validation result. In smoke/standard mode, writes a note
    explaining how to get figures instead.
    """
    if mode == "gold":
        _gold_fig_out = package_dir / "gold_figures"
        try:
            from .cohort_figures import generate as _gen_single_figs
            # runs_dir: conventionally two levels up from package_dir
            # (<outdir>/<strain>/package → <outdir>). Validate the STANDARD
            # layout holds — package_dir's own name is literally "package" and
            # its parent.parent exists as a directory — rather than requiring
            # a sibling strain (which a genuine single-strain run never has;
            # the earlier version of this check regressed the common case).
            _inferred_runs = package_dir.parent.parent
            _direct_parent = package_dir.parent
            _standard_layout = (package_dir.name == "package" and _inferred_runs.is_dir())
            if _standard_layout:
                _runs_dir = str(_inferred_runs)
            else:
                # Non-standard layout (package_dir doesn't end in .../<strain>/package)
                # — use immediate parent and emit a note so the gap is visible.
                _runs_dir = str(_direct_parent)
                try:
                    _gold_fig_out.mkdir(parents=True, exist_ok=True)
                    (_gold_fig_out / "RUNS_DIR_NOTE.md").write_text(
                        f"# Non-standard package path\n\n"
                        f"Expected layout: <runs_dir>/<strain_id>/package/ — "
                        f"package_dir.name was {package_dir.name!r}, not 'package'.\n"
                        f"Used the package directory's immediate parent as runs_dir; "
                        f"figures may be incomplete or missing.\n",
                        encoding="utf-8")
                except Exception as _note_exc:
                    _phase_receipt(
                        package_dir, "gold_figures_layout_note", "ERROR",
                        reason=f"{type(_note_exc).__name__}: {_note_exc}",
                    )
            _fig_res = _gen_single_figs(
                runs_dir=_runs_dir,
                out=str(_gold_fig_out),
                strains=[strain_id],
                series="all",   # v9.7.252 (P8): default was series="F" -> 2 panels, not 21
            )
            _nfig = _fig_res.get("figures", 0)
            if _nfig:
                emit(f"  Gold figures: {_nfig} figure(s) + sidecar CSVs → {_gold_fig_out.name}/")
            else:
                emit(f"  Gold figures: SKIPPED (no data available or matplotlib not installed)")
        except Exception as _fig_exc:
            # Write a note so the user knows figures were skipped but nothing is broken
            try:
                _gold_fig_out.mkdir(parents=True, exist_ok=True)
                (_gold_fig_out / "GOLD_FIGURES_SKIPPED.md").write_text(
                    f"# Gold figures skipped\n\n"
                    f"Error: {type(_fig_exc).__name__}: {_fig_exc}\n\n"
                    # CLAUDE_409: this note ships in the package; keep the re-render hint
                    # a placeholder path, never the operator's absolute <home>/<user>/...
                    # gold_figures path (DEEP_AUDIT3 F2). The error string above is retained.
                    f"Re-render: python -m mamey cohort-figures --runs-dir <runs_dir> "
                    f"--out <package_dir>/gold_figures --strains {strain_id}\n",
                    encoding="utf-8",
                )
            except Exception:
                pass
            emit(f"  Gold figures: SKIPPED ({type(_fig_exc).__name__}: {_fig_exc})")
    else:
        # Smoke/standard mode — write a note explaining how to get figures
        _gold_fig_out = package_dir / "gold_figures"
        _gold_fig_out.mkdir(parents=True, exist_ok=True)
        (_gold_fig_out / "GOLD_FIGURES_REQUIRE_GOLD_MODE.md").write_text(
            "# Gold figures require --mode gold\n\n"
            "This package was run in smoke or standard mode.\n"
            "Re-run with --mode gold to get the per-BGC domain heatmap and figure suite.\n",
            encoding="utf-8",
        )


def _emit_deep_data(package_dir: Path, strain_id: str, mode: str, issues: list | None = None) -> None:
    """Emit the gene-level deep_data.json + gene_data.json (gold mode only).

    Extracted verbatim from run_one_strain (v9.7.155 cli decomposition). B-9/F-10:
    in gold mode, build the per-gene deep-data from the package's own snapshot +
    evidence parse so tools/build_modeb_deepdive.py runs from the package instead
    of degrading to verdict-less cards. Written before the final manifest/checksum
    seal so they are tracked, and before _emit_gold_figures which reads deep_data.json.
    Never fails the package over the enrichment layer.

    BCHERRY-374: also append to the run-level `issues` list (when passed), not just the
    direct issue_log.md append below. issue_log.md is fully REWRITTEN from `issues` by
    _stamp_terminal_status() before the seal (fixing the "issues appended after
    _write_package's early snapshot" staleness bug) -- a warning that only reached the
    file via this function's direct .open("a") append, and never reached the `issues`
    list, would be silently dropped by that rewrite. Routing through `issues` too keeps
    both channels honest instead of only patching the rewrite side.
    """
    if mode == "gold":
        try:
            from .deep_data import build_deep_data_files
            build_deep_data_files(package_dir, strain_id)
        except Exception as _e:  # never fail the package over the enrichment layer
            _msg = f"[WARN] deep_data emit skipped: {_e}"
            with (package_dir / "issue_log.md").open("a", encoding="utf-8") as _ilf:
                _ilf.write(f"\n- {_msg}\n")
            if issues is not None:
                issues.append(_msg)


def _emit_cohort_sources(package_dir: Path, strain_id: str, mode: str, input_zip: str,
                          issues: list | None = None) -> None:
    """Bake the cross-strain cohort-source CSVs into package/cohort_source/ (gold mode only).

    v9.7.277 (engine 1.9.110): makes the sealed package standalone and portable for cross-strain
    work. cohort-precompute reads these directly, so a folder of shared packages assembles the
    cohort tables with no re-derivation and no original antiSMASH zips. Reuses the run's input zip
    for full module detail, falling back to the sealed gene context if the zip is unavailable.
    Written before the final seal so the files are tracked. Never fails the package.

    BCHERRY-374: also append to the run-level `issues` list (when passed) -- see the identical
    note on _emit_deep_data() above; same issue_log.md-rewrite staleness risk otherwise.
    """
    if mode != "gold":
        return
    try:
        from .domain_level import run_domain_level
        _src = input_zip if (input_zip and _os.path.exists(str(input_zip))) else None
        _rec = run_domain_level(package_dir, source_antismash=_src,
                                outdir=Path(package_dir) / "cohort_source")
        _n = len(_rec.get("files", []))
        emit(f"    Cohort sources: {_n} file(s) baked into cohort_source/ "
              f"({_rec.get('mode', '?')}) \u2014 package is cross-strain-portable")
    except Exception as _e:  # never fail the package over the portability layer
        _msg = f"[WARN] cohort_source emit skipped: {_e}"
        if issues is not None:
            issues.append(_msg)
        with (package_dir / "issue_log.md").open("a", encoding="utf-8") as _ilf:
            _ilf.write(f"\n- {_msg}\n")


def _phase_environment(
    package_dir: Path,
    strain_id: str,
    mode: str,
    json_mode: str,
    token_budget: str,
    input_zip: str,
    brief: str,
    display_name: str,
    taxonomy: str,
    source: str,
    bioactivity: object | None,
    master_path: str | None,
    run_dir: Path,
    source_provenance: str = "asserted",   # AMBER-03-2
) -> tuple:
    """Environment setup: timing recorder, accession-label check, taxonomy
    normalization, display-name cleanup, and RunContext construction.

    Extracted verbatim from run_one_strain (v9.7.155 cli decomposition). Returns
    (timer, label_accession, taxonomy, display_name, context) — all four of the
    non-timer values are read much later in the pipeline (taxonomy by
    run_source_scans/run_external_scan_pack/_resolve_cohort, label_accession by
    the cohort-resolution log line, context by manifest construction), so every
    one must round-trip through the return tuple rather than being dropped.
    """
    _phase_receipt(package_dir, "environment", "START", strain_id=strain_id,
                   mode=mode, json_evidence=json_mode, token_budget=token_budget,
                   pid=_os.getpid(), version=__version__)
    # v9.7.81: timing recorder — tracks phase durations and emits breakdown files
    from . import __version__ as _mv
    _timer = TimingRecorder(
        strain_id=strain_id, mode=mode, mamey_version=_mv,
        workflow_version=__version__, chatgpt_safe=(brief == "none"),
        input_zip_bytes=(_os.path.getsize(input_zip) if input_zip and _os.path.exists(str(input_zip)) else None),
    )
    _phase_receipt(package_dir, "environment", "END",
                   chatgpt_safe=(brief == "none"), input_zip_bytes=(_os.path.getsize(input_zip) if input_zip and _os.path.exists(str(input_zip)) else None))
    _label_accession = _label_is_accession(strain_id)
    if _label_accession:
        # v9.7.229 naming convention: derive Genus_species_Designation from the organism record rather
        # than keep an accession/LLM label. Sourced from ORGANISM (or filename tokens); never invented.
        from .cohort_resolver import derive_strain_id as _derive_sid
        _derived, _sid_note = _derive_sid(strain_id, organism=taxonomy,
                                          filename=(_os.path.basename(str(input_zip)) if input_zip else ""))
        if _derived and _derived != strain_id:
            _stage(f"[NOTE] {_sid_note}")
            strain_id = _derived
        else:
            _stage(f"[NOTE] label '{strain_id}' looks like an NCBI accession — strain names are preferred; "
                   f"supply --strain <Genus_species_Designation> when available (accession is a fallback label)")

    # F-6: the AS GBKs deposit `ORGANISM  .` (genus missing), so an organism string extracted from them is the
    # literal ".". Normalize a taxonomy with no alphabetic genus to a safe "sp." placeholder so "." never
    # propagates into organism / genus / cohort / display; clean a display name whose genus slot is the dot too.
    from .cohort_resolver import normalize_taxonomy as _norm_tax
    from .source_provenance import normalize_source_provenance as _norm_src_prov
    taxonomy = _norm_tax(taxonomy)
    if display_name and not (display_name.strip()[:1].isalpha()):
        _rest = display_name.strip().lstrip(". ").strip()
        display_name = (f"{taxonomy} {_rest}".strip() if _rest else f"{taxonomy} strain {strain_id}")

    # --- Parse antiSMASH ZIP ---
    context = RunContext(
        strain_id=strain_id,
        display_name=display_name,
        version=__version__,
        analysis_mode=mode,
        input_zip=str(input_zip),
        outdir=str(run_dir),
        taxonomy=taxonomy,
        source=source,
        source_provenance=_norm_src_prov(source_provenance),
        bioactivity=normalize_bioactivity(bioactivity),
        master_path=master_path,
    )

    return _timer, _label_accession, taxonomy, display_name, context


def _phase_citation_compact(
    package_dir: Path,
    strain_id: str,
    token_budget: str,
    brief: str,
    heartbeat_seconds: int,
    issues: list,
) -> None:
    """Emit citation-compact ledger + compact Markdown supplements, when the
    run's token_budget is 'citation-compact'. No-op otherwise.

    Extracted verbatim from run_one_strain (v9.7.155 cli decomposition). `issues`
    is the shared run-level issue list; this phase appends warnings to it in
    place (mutation, not a return) exactly as the inline block did, so callers
    do not need to reassign it.
    """
    if token_budget == "citation-compact":
        _phase_receipt(package_dir, "citation_compact", "START")
        try:
            from .citation_compact import emit_citation_compact_outputs as _emit_cc
            with heartbeat_context("citation_compact", enabled=(brief == "none"), seconds=heartbeat_seconds):
                _cc_res = _emit_cc(package_dir, strain_id=strain_id, bundle_version=BUNDLE_VERSION)
            _stage(f"citation-compact outputs: {_cc_res.get('citation_count', 0)} citation(s), "
                   f"{len(_cc_res.get('outputs', []))} file(s)")
            _phase_receipt(package_dir, "citation_compact", "END",
                           compact_status=_cc_res.get("status"),
                           lead_count=_cc_res.get("lead_count"),
                           citation_count=_cc_res.get("citation_count"),
                           literature_task_count=_cc_res.get("literature_task_count"),
                           output_count=len(_cc_res.get("outputs", [])))
        except Exception as _cc_err:
            issues.append(f"[WARN] citation-compact outputs skipped: {_cc_err}")
            _phase_receipt(package_dir, "citation_compact", "ERROR", reason=str(_cc_err))


def _verify_sealed_receipt(zip_path: Path, external_path: Path) -> bool:
    """F04 (v9.7.354): confirm the gate_validation.json sealed INSIDE the ZIP is byte-identical to
    the EXTERNAL on-disk receipt. Returns True on match; False on mismatch, a missing entry, or an
    unreadable ZIP. Because _phase_package_seal now finalizes the receipt before writing the ZIP, a
    False result signals a genuine seal/validation ordering regression (the F04 defect class)."""
    import zipfile
    try:
        external = external_path.read_bytes()
    except OSError:
        return False
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in regular_file_names(zf)
                     if n == "gate_validation.json" or n.endswith("/gate_validation.json")]
            if not names:
                return False
            internal = zf.read(names[0])
    except (OSError, zipfile.BadZipFile):
        return False
    return internal == external


def _phase_package_seal(
    package_dir: Path,
    run_dir: Path,
    strain_id: str,
    brief: str,
    heartbeat_seconds: int,
    validate_result: dict,
    issues: list,
    antismash_profile: str = "unknown",
) -> tuple:
    """Write the manifest + checksums, zip the package, and compute the final
    validator status. Returns (zip_path, status).

    Extracted verbatim from run_one_strain (v9.7.155 cli decomposition). `issues`
    is the shared run-level issue list; mutated in place (append), same as the
    inline block. `status` and `zip_path` are both read again later in
    run_one_strain (terminal-status computation and the returned summary dict),
    so both must round-trip through the return tuple.
    """
    _phase_receipt(package_dir, "package_seal", "START")
    _stage("writing manifest + checksums")
    # v9.7.367 CANDIDATE (Indigo2 §1+§2, the review lane-ruled 2026-08-15): drain silent-degradation
    # breadcrumbs into the phase receipt (MUTABLE_RECEIPT_NAMES; outside DETERMINISM_WHITELIST).
    # v9.7.370 swallow triage: the receipt drain is best-effort by contract — a failure
    # of the recorder cannot be recorded by the recorder. Suppression deliberate + named.
    with _contextlib.suppress(Exception):
        from . import degradation as _degradation
        _deg_events = _degradation.drain()
        if _deg_events:
            _phase_receipt(package_dir, "degradation_events", "WARN",
                           n=len(_deg_events), events=_deg_events[:50])
    _phase_receipt(package_dir, "manifest_write", "START")
    with heartbeat_context("manifest_and_checksums", enabled=(brief == "none"), seconds=heartbeat_seconds):
        write_manifest(package_dir)
    _phase_receipt(package_dir, "manifest_write", "END",
                   manifest_bytes=(package_dir / "manifest.json").stat().st_size,
                   checksums_bytes=(package_dir / "checksums_sha256.txt").stat().st_size
                   if (package_dir / "checksums_sha256.txt").exists() else 0)

    # F04 (v9.7.354): FINALIZE the validation receipt BEFORE sealing the ZIP, so the
    # gate_validation.json captured inside the ZIP is byte-identical to the external on-disk one.
    #
    # CRITICAL ORDERING — why this differs from the .353 AMBER attempt that was REVERTED: that
    # version ran this enrichment-aware validation as the FIRST step of the phase, BEFORE
    # write_manifest, so it validated an INCOMPLETE package (no manifest.json / checksums yet) →
    # the status fell to a non-terminal value → the [BLOCKING] issue fired on legitimate
    # smoke/minimal/chatgpt-safe packages and regressed 13 seal/package/deliverable tests. Here the
    # validation runs immediately AFTER write_manifest — the exact package state the base validated
    # (zip_package writes to run_dir, never mutates package_dir, so pre-zip and post-zip validation
    # are identical) — so the computed status is unchanged from the base and NO new gold-path
    # blocking is introduced. The only real change is that the receipt is now written before the ZIP.
    _enrich_result = validate_package(package_dir, enrichment_check=True)
    _enrich_missing = _enrich_result.get("missing_required_suffixes", [])
    _enrich_only_missing = [s for s in _enrich_missing if s in ("OPEN_ME_FIRST.html", "manifest_short.json")]
    if _enrich_only_missing:
        issues.append(f"[WARN] enrichment files missing before seal: {_enrich_only_missing} — package still valid")

    # P0 (ChatGPT audit): a gold run seals as terminal status MAMEY_COMPLETE, but the old
    # receipt recorded validator_is_pass = status.startswith("PASS") → False for a fully
    # successful gold package, which misleads ChatGPT/audit automation into reading a
    # completed run as a failure. Keep validator_is_pass (PASS-only) for back-compat, but
    # add validator_is_terminal_success that recognizes every terminal-success status.
    _TERMINAL_SUCCESS = {"PASS", "PASS_WITH_ISSUES", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"}
    # SEAL-02 (v9.7.338 verdict-changing): the final enrichment-aware re-validation (_enrich_result)
    # re-runs every gate on the FINAL package — after gene tables, the Two_Model_Flag triage
    # patch, manifest_short.json, and the compiled report exist. Honor the final result, rewrite the
    # on-disk gate from it (gate_validation.json is a MUTABLE_RECEIPT in packaging.py, so rewriting
    # it after write_manifest does not violate the checksum set — same as the base), and block on
    # non-terminal-success. This preserves the .352/.353 blocking semantics exactly; F04 only moves
    # WHEN the receipt is written (before the ZIP) so the sealed-internal copy equals the external.
    status = _enrich_result["status"]
    (package_dir / "gate_validation.json").write_text(
        json.dumps(_enrich_result, indent=2), encoding="utf-8"
    )
    if status not in _TERMINAL_SUCCESS:
        issues.append(f"[BLOCKING] final post-seal validation status {status!r} is not a "
                      f"terminal success {sorted(_TERMINAL_SUCCESS)}; sealed package regressed")

    # Enrichment validation above can itself add issues after write_manifest. Refresh every
    # mutable status surface once more before zip_package captures the authoritative bytes.
    _stamp_terminal_status(package_dir, validator_status=status, issues=issues)

    # v9.7.84 naming fix: name the package after the SAPOTE BUNDLE version (the user-facing release
    # line), with the engine version retained as a provenance suffix. Previously this used only the
    # engine __version__ (e.g. "Mamey_v1.9.84"), which made it impossible to tell which bundle cut
    # produced a package from its filename alone.
    # v9.7.398 (review lane): stamp the antiSMASH detection strictness (loose/relaxed/strict)
    # into the package filename. Regions from different strictness are NOT comparable, and the
    # flavor was previously recoverable only from the manifest's `antismash_profile` — the filename
    # alone could not tell a loose package from a relaxed one, so a loose and relaxed run of the
    # same strain collided by name in a shared home. The token is inserted BEFORE `_Complete_Package`
    # so the `_v{X.Y.Z}_` version regex and every `*Complete_Package.zip` glob still match.
    _flavor = antismash_profile if antismash_profile in ("strict", "relaxed", "loose") else "unknown"
    zip_path = run_dir / f"{strain_id}_SapoteMamey_v{BUNDLE_VERSION}_engine{__version__}_{_flavor}_Complete_Package.zip"
    _stage(f"sealing package → {zip_path.name}")
    _phase_receipt(package_dir, "zip_package", "START", zip=str(zip_path))
    with heartbeat_context("zip_package", enabled=(brief == "none"), seconds=heartbeat_seconds):
        zip_package(package_dir, zip_path)
    _phase_receipt(package_dir, "zip_package", "END", zip=str(zip_path), bytes=zip_path.stat().st_size)

    # F04 (v9.7.354): prove the sealed-internal receipt equals the external one (byte-compare).
    # Because the receipt was finalized before the ZIP was written, these MUST match — a mismatch is
    # a real ordering regression, not an expected transient, so it is a blocking issue.
    receipt_match = _verify_sealed_receipt(zip_path, package_dir / "gate_validation.json")
    if not receipt_match:
        issues.append("[BLOCKING] sealed-internal gate_validation.json differs from the external "
                      "final receipt (seal/validation ordering regression)")

    emit(f"  Package: {status}  →  {zip_path}")
    _stage(f"done {strain_id} — {status}")
    _phase_receipt(package_dir, "package_seal", "END",
                   validator=status, zip=str(zip_path),
                   validator_is_pass=(status in {"PASS", "PASS_WITH_ISSUES"}),
                   validator_is_terminal_success=(status in _TERMINAL_SUCCESS),
                   receipt_internal_equals_external=receipt_match)

    return zip_path, status


def _acquire_master_workbook_lock(master_path):
    """v9.7.409 (CLAUDE_409 C1): serialize concurrent writers to ONE shared --master workbook.

    Two runs into different --outdir but the SAME --master are a read-modify-write on a resource
    shared across run dirs, which H13's per-run-dir lock does not cover. A BLOCKING advisory flock on
    ``<master>.lock`` makes the second writer WAIT (not refuse — both strains must survive) until the
    first has published, so its own read sees the first writer's appended rows. Blocking (LOCK_EX,
    no LOCK_NB) is intentional: refusing would drop a legitimate strain; serializing preserves both.

    Returns the open lock handle (kept until _release_master_workbook_lock) or None when locking is
    unavailable (non-POSIX, or an OSError such as a read-only filesystem). The caller treats None as
    a structured failure and refuses the shared-master mutation so loss-prone unlocked writes cannot
    masquerade as a successful update."""
    if not master_path:
        return None
    try:
        import fcntl as _fcntl
    except ImportError:  # non-POSIX: no advisory locks available
        return None
    _fh = None
    try:
        _fh = open(str(master_path) + ".lock", "a+")
        _fcntl.flock(_fh.fileno(), _fcntl.LOCK_EX)  # blocking: wait, don't refuse
        return _fh
    except OSError:
        if _fh is not None:
            with _suppress(Exception):
                _fh.close()
        return None  # cannot lock (e.g. read-only fs): do not block the run


def _release_master_workbook_lock(handle) -> None:
    """Release the shared-master advisory lock by closing the handle (drops the flock). Best-effort."""
    if handle is None:
        return
    with _suppress(Exception):  # v9.7.409: best-effort cleanup, intent explicit (was except: pass)
        handle.close()


def _atomic_publish_master(src_path, dest_path) -> None:
    """v9.7.409 (CLAUDE_409 C1): publish the freshly-written master to the SHARED --master path
    atomically. The old ``shutil.copy2(master_out, master_path_p)`` streamed bytes in place, so a
    concurrent reader (a cohort command, or the other run) doing ``load_workbook(master_path)``
    mid-copy could read a truncated .xlsx (BadZipFile), and two interleaving copies could leave a
    mixed zip. Copy to a UNIQUE same-directory temp, then os.replace onto the destination (atomic on
    the same filesystem): a reader sees either the whole old file or the whole new file, never a
    half-written one."""
    import shutil as _shutil, tempfile as _tempfile
    dest_path = Path(dest_path)
    _fd, _tmpname = _tempfile.mkstemp(prefix="." + dest_path.name + ".", suffix=".tmp",
                                      dir=str(dest_path.parent))
    os.close(_fd)
    try:
        _shutil.copy2(src_path, _tmpname)
        os.replace(_tmpname, dest_path)
    except BaseException:
        with _suppress(OSError):  # v9.7.409: best-effort cleanup, intent explicit (was except: pass)
            if os.path.exists(_tmpname):
                os.remove(_tmpname)
        raise


def run_one_strain(
    strain_id: str,
    display_name: str,
    input_zip: str,
    outdir: str,
    mode: str,
    taxonomy: str,
    source: str,
    bioactivity: object | None = None,
    master_path: str | None = None,
    source_provenance: str = "asserted",  # AMBER-03-2: accession|table|filename|asserted
    json_mode: str = "bounded",   # v9.3.2: bounded when ijson present; falls back gracefully to off
    antismash_profile: str = "auto",  # "auto" = read strictness from the ZIP; else supplied (comparability)
    brief: str = "standard",      # render deterministic strain brief: none|minimal|standard
    release: str | None = None,   # operator release override (PUBLIC|PRIVATE); None = fail-safe derivation
    privacy_profile: str | None = None,  # optional exact-ID user-owned named-tier policy
    project_registry: str | None = None,  # explicit user-declared privacy/genome/assay registry
    metadata_csv: str | None = None,  # path to strain metadata CSV for collection figures
    require_workbook: bool = False,    # if True, raise on workbook failure instead of continuing
    locus_maps: str = "auto",          # P0 (v9.7.101): auto|off|on locus-map render policy
    token_budget: str = "standard",    # v9.7.136: standard|citation-compact output profile
    heartbeat_seconds: int = 20,            # ChatGPT-safe heartbeat interval for quiet finalization stages
    hmm_scan: bool = False,
) -> dict:
    """Run Mamey extraction for one strain. Returns summary dict."""

    # v9.7.371 hardening: ClusterBlast staging dir, set during package add-ons. Initialized here so
    # downstream consumers reference it directly rather than via locals() introspection (the same
    # incident class as the validate.py `"mdata" in locals()` bug).
    _cb_dir = None

    # Admit metadata before creating a run directory or package artifact.  A
    # malformed object is a workflow hold, never a biological conclusion.
    try:
        bioactivity = normalize_bioactivity(bioactivity)
    except BioactivityMetadataError as exc:
        emit(f"ERROR: {exc.code}: {exc.detail}", file=_sys.stderr, flush=True)
        return {"status": exc.code, "written": False}

    out_root   = Path(outdir)
    run_dir    = out_root / strain_id
    package_dir = run_dir / "package"
    package_dir.mkdir(parents=True, exist_ok=True)
    # v9.7.409 (H13): taken here, AFTER every pre-write refusal above, so a refused run creates nothing.
    _pkg_lock = _acquire_package_lock(outdir, strain_id)
    if _pkg_lock is None:
        return {"status": "PACKAGE_LOCKED", "written": False}

    emit(f"\n{'='*60}", f"Mamey v{__version__} — {strain_id}", f"Mode: {mode}  |  {input_zip}", RUN_STATEMENT, '='*60, _dependency_banner(), sep="\n")
    global _RUN_T0
    _RUN_T0 = None
    _stage(f"start {strain_id} (mode={mode}, json-evidence={json_mode}, token-budget={token_budget})")
    _timer, _label_accession, taxonomy, display_name, context = _phase_environment(
        package_dir, strain_id, mode, json_mode, token_budget, input_zip, brief,
        display_name, taxonomy, source, bioactivity, master_path, run_dir,
        source_provenance=source_provenance,
    )

    # BR6-406-REBASE (originally Codex, engine-facing half): project-level privacy and
    # data-availability registry. Generic architecture: privacy is declared by the user, not
    # guessed from strain-ID prefixes. Genome and bioassay availability remain independent axes.
    # Recorded on RunContext / the manifest only in this rebase -- it does NOT yet drive
    # release/BGCRecord.privacy_tier derivation, which the landed --privacy-profile mechanism
    # (resolve_profile_privacy(), below) already owns. See BR6_REBASE_MAP.md for why that
    # reconciliation was deliberately left to the composing lane rather than merged here.
    _project_registry_obj = None
    _project_snapshot = None
    if project_registry and privacy_profile:
        # Engine 1.9.146 (owner ruling 2026-09-03): two privacy authorities on one run is a typed refusal,
        # not a precedence rule. --privacy-profile drives release/BGCRecord.privacy_tier; --project-registry
        # is recorded on RunContext/manifest only. Which one wins when both exist is deferred (.407).
        raise SystemExit(
            f"PRIVACY_AUTHORITY_CONFLICT: --project-registry and --privacy-profile were both supplied for "
            f"'{strain_id}'. Supply one. The project registry is recorded but does not drive release in "
            f"this engine; the privacy profile does."
        )
    if project_registry:
        from .project_registry import load_project_registry, write_strain_registry_surfaces
        _project_registry_obj = load_project_registry(project_registry)
        _project_record = _project_registry_obj.require_strain(strain_id)
        _project_snapshot = write_strain_registry_surfaces(
            package_dir, _project_registry_obj, strain_id
        )
        context.project_privacy_tier = _project_snapshot["privacy_tier"]
        context.project_privacy_tier_source = "USER_DECLARED_PROJECT_REGISTRY"
        context.publication_status = _project_record.publication_status
        context.genome_state = _project_record.genome_state
        context.project_registry_sha256 = _project_registry_obj.source_sha256
        context.assay_summary = _project_registry_obj.assay_summary(strain_id)
    else:
        _atomic_write_manifest_text(
            package_dir / "project_registry_status.json",
            json.dumps({
                "schema_version": "sapote_project_registry_status_v1",
                "status": "NOT_PROVIDED_PRIVACY_HOLD",
                "privacy_tier": "UNDECLARED",
                "genome_state": "NOT_PROVIDED",
                "assay_data_state": "NOT_PROVIDED",
                "export_rule": "No public export is authorized without an explicit project registry declaration.",
                "legacy_compatibility": "Existing release behavior remains available for analysis compatibility; it is not a generic privacy declaration.",
            }, indent=2),
        )

    # v9.7.374 (audit lane intake audit): identify_antismash_input() is a purpose-built,
    # never-raises recognizer ("Nothing raises on a bad archive... Callers decide policy" —
    # antismash_input.py) that already distinguishes a missing file / a corrupt ZIP / a valid
    # ZIP with no antiSMASH content, each with its own accurate warning. It was previously called
    # AFTER assembly_metrics_from_zip below and its is_antismash/warnings/n_regions fields were
    # never consulted, so: (a) a missing or non-ZIP --input-zip crashed run_one_strain with a raw
    # unhandled FileNotFoundError/BadZipFile traceback instead of a clean refusal, because
    # assembly_metrics_from_zip (which does not catch those) ran first; and (b) a valid ZIP with
    # no antiSMASH content ran the ENTIRE pipeline (source scans, RG-GMCI, ClusterBlast/MIBiG
    # per-gene maps, KS-clade channel) on empty data before failing downstream with a generic,
    # sometimes-inaccurate "looks like a bare assembly" guess instead of this module's own,
    # already-computed, more specific diagnosis. Move the call first and act on it.
    _as_input = identify_antismash_input(input_zip)
    if not _as_input.is_antismash:
        _reason = "; ".join(_as_input.warnings) or "not recognised as an antiSMASH results archive"
        emit(f'  [FAIL] INPUT_NOT_ANTISMASH: {_reason}', f"         ({Path(input_zip).name}) — supply the strain's antiSMASH output ZIP, not a raw genome download or an unrelated file.", sep="\n")
        return {
            "strain_id": strain_id, "status": "MAMEY_FAILED",
            "raw_bgcs": 0, "corrected_bgcs": 0, "assembly_tier": "NONE",
            "package_zip": None, "master_updated": False,
            "issues": [f"INPUT_NOT_ANTISMASH: {_reason} — no package written."],
        }
    try:
        assembly = assembly_metrics_from_zip(input_zip)
    except GbkSizeGuardRefusal as exc:
        # A non-empty FASTA subset is not an assembly. Refuse at intake before
        # parsing, scans, package sealing, or master-workbook publication.
        _issue = (
            f"FASTA_INPUT_REFUSED: {exc}. The archive's FASTA set was rejected as "
            "incomplete; no package was written. Remove the unsafe member only if "
            "the resulting archive is intentionally complete, or supply a complete "
            "antiSMASH output archive."
        )
        return {
            "strain_id": strain_id, "status": "MAMEY_FAILED",
            "raw_bgcs": 0, "corrected_bgcs": 0, "assembly_tier": "NONE",
            "package_zip": None, "master_updated": False,
            "issues": [_issue],
        }
    antismash_ver     = extract_antismash_version(input_zip)
    # v9.7.372 (VGP): the detection strictness is recorded INSIDE the archive, so it need not be
    # taken on trust. "auto" reads it; an explicit value is honoured but a disagreement is surfaced
    # rather than silently accepted. Regions from different strictness are not comparable, and a
    # wrong profile is harder to detect downstream than a missing one.
    _profile_issue = None
    if antismash_profile == "auto":
        antismash_profile = _as_input.strictness          # "unknown" only if truly unreadable
        if antismash_profile == "unknown":
            _profile_issue = ("ANTISMASH_PROFILE_UNREADABLE: detection strictness could not be read "
                              f"from {Path(input_zip).name}; this package must NOT be pooled with "
                              "another profile until it is established.")
    elif _as_input.strictness not in ("unknown", antismash_profile):
        _profile_issue = (f"PROFILE_MISMATCH: --antismash-profile={antismash_profile} but the archive "
                          f"records strictness={_as_input.strictness} "
                          f"({_as_input.strictness_evidence}). The archive wins on evidence; the run "
                          "continues under the supplied value at the operator's risk.")
    if _profile_issue:
        emit(f"  [profile] {_profile_issue}")
    # audit P1: bounded json-evidence streams large JSONs (ijson) and is the one step that can stall on a
    # big strain. Run it under a wall-clock budget; on overrun, fall back to off (TXT-only) instead of
    # hanging. Budget via MAMEY_BOUNDED_BUDGET_S (default 300s); 0 disables the guard.
    _budget = int(_os.environ.get("MAMEY_BOUNDED_BUDGET_S", "300"))
    _phase_receipt(package_dir, "antismash_parse", "START")
    _stage("parsing antiSMASH KCB/RiQ evidence")
    antismash_evidence, json_mode = _parse_evidence_with_budget(
        input_zip, json_mode, _budget, _stage)
    _phase_receipt(package_dir, "antismash_parse", "END",
                   json_evidence=json_mode,
                   evidence_status=antismash_evidence.get("status") if isinstance(antismash_evidence, dict) else "")
    # Reuse the evidence just parsed for the status dict instead of parsing the records a second
    # time inside parse_bgcs_from_zip (apply_evidence_to_bgcs reads only by_region, so this is
    # identical to the prior two-parse path — one record parse per run instead of two).
    _phase_receipt(package_dir, "inventory", "START")
    _stage("parsing BGC regions")
    bgcs              = parse_bgcs_from_zip(input_zip, json_mode=json_mode, evidence=antismash_evidence)
    # Apply the same evidence object that will be written to disk, so
    # AntiSMASH_Evidence_Parse.json contains the KCB assignment audit.
    apply_evidence_to_bgcs(bgcs, antismash_evidence)

    # v9.7.86: deterministic compound-class annotation. Reads antiSMASH's own
    # t2pks/terpene product_classes (primary, machinery-based), with own-evidence
    # MIBiG-name fallback. Annotation-only for most chemotypes; the three scored families
    # (polyene_macrolide/anthracycline/ionophore) carry a consequence applied in the triage
    # scoring step. No-op when JSON evidence is off (falls back to the resolved product line).
    # v9.7.87 P-10: predictions are matched to each BGC by genomic-coordinate OVERLAP within
    # the same contig, not broadcast to every BGC on the contig. On a complete single-contig
    # genome the old contig key collapsed to one bucket and broadcast the chromosome's aromatic
    # -PKS prediction to all BGCs (73/75 Actinomadura BGCs mislabelled "angucycline").
    try:
        from .compound_class import annotate_bgc as _annotate_bgc
        from collections import defaultdict as _dd
        _by_contig = _dd(list)
        for _r in (antismash_evidence.get("product_class_predictions") or []):
            _by_contig[_r.get("record_id") or ""].append(_r)

        def _preds_for_bgc(_b):
            cands = _by_contig.get(_b.contig or "", [])
            if not cands:
                return None
            bs, be = (_b.start or 0), (_b.end or 0)
            # keep only predictions whose coordinates overlap this BGC's span. If a prediction
            # lacks coordinates (older extractor / missing field), fall back to contig-level so
            # behaviour is no worse than v9.7.86 rather than dropping the signal silently.
            overlap, uncoorded = [], []
            for _r in cands:
                ps, pe = _r.get("start"), _r.get("end")
                if ps is None or pe is None:
                    uncoorded.append(_r)
                elif not (pe < bs or ps > be):   # genomic-span overlap
                    overlap.append(_r)
            picked = overlap or uncoorded
            return picked or None

        for _b in bgcs:
            _ann = _annotate_bgc(_b, _preds_for_bgc(_b))
            _b.compound_class_annotation = _ann.as_dict()
    except Exception as _e:
        _stage(f"compound-class annotation skipped: {_e}")

    # R1: stamp each BGC with its release tag (AS -> PUBLIC per the v9.7.236 PI decision;
    # AJS/PENDING/unknown shapes fail safe to PRIVATE), so the
    # row-level release flag is present from extraction onward and a downstream merge/leak-audit can filter on it.
    if privacy_profile:
        from .privacy_profile import load_privacy_profile, resolve_profile_privacy
        _privacy = resolve_profile_privacy(
            strain_id, load_privacy_profile(privacy_profile), override=release,
        )
        _rel = _privacy.release
        _refused = _privacy.reason == "public_override_refused_by_profile"
        _privacy_tier, _privacy_state = _privacy.tier_id, _privacy.assignment_state
    else:
        from .dedup_and_guard import resolve_release as _resolve_release
        _rel, _refused = _resolve_release(strain_id, release)
        _privacy_tier, _privacy_state = "LEGACY_DERIVATION", "LEGACY_DERIVATION"
    if _refused:
        emit(f"  [release] --release PUBLIC REFUSED for '{strain_id}': trips the private-identifier guard "
              f"(AJS/PENDING/private-registry) — tagged PRIVATE. The leak guard is not operator-overridable.")
    for _b in bgcs:
        _b.release = _rel
        _b.privacy_tier = _privacy_tier
        _b.privacy_assignment_state = _privacy_state

    # Extract sec_met_domain Pfam hits from GBK region files.
    # antiSMASH runs HMMER internally; these are its pre-computed domain hits
    # surfaced without any additional external tool invocation.
    gbk_pfam_hits = {}
    try:
        gbk_pfam_hits = extract_gbk_pfam_hits(input_zip)
        # v9.4.1-tigrfix: merge JSON TIGRFAM diagnostics (AHBA_synth_RP, ene_KS,
        # TIGR03604, NikJ-family) that are NOT in GBK sec_met_domain and were
        # previously dropped — caused false-negative ansamycin/enediyne/
        # thiopeptide/nucleoside class calls.
        try:
            # tigrfam diagnostics were already extracted in the single record pass during
            # parse_antismash_evidence_status (all json modes). Read AND remove them here: the
            # data flows into gbk_pfam_hits via the merge below (exactly as before), so the
            # standalone key is dropped to keep the persisted evidence byte-identical to the
            # pre-fold artifact (no new field in AntiSMASH_Evidence_Parse.json).
            tigrfam_hits = antismash_evidence.pop("tigrfam_hits", {})
            gbk_pfam_hits = merge_tigrfam_into_pfam_hits(gbk_pfam_hits, tigrfam_hits)
            n_tigrfam = sum(len(v) for v in tigrfam_hits.values())
            if n_tigrfam:
                emit(f"  TIGRFAM diagnostics merged: {n_tigrfam} hit(s)")
        except Exception as _tf_exc:
            antismash_evidence.setdefault("warnings", []).append(
                f"tigrfam merge failed: {_tf_exc}")
        antismash_evidence["gbk_pfam_hits"] = gbk_pfam_hits
        n_regions_with_hits = len(gbk_pfam_hits)
        n_tier1 = sum(1 for hits in gbk_pfam_hits.values()
                      for h in hits if h.get("tier1_diagnostic"))
        emit(f"  GBK Pfam extraction: {n_regions_with_hits} regions, {n_tier1} tier-1 diagnostic hits")
    except Exception as _pfam_exc:
        antismash_evidence.setdefault("warnings", []).append(
            f"GBK Pfam extraction failed: {_pfam_exc}")

    _stage("extracting CDS/contig/domain features")
    cds               = extract_cds_features(input_zip)
    contigs           = extract_contig_sequences(input_zip)
    domains           = extract_domain_features(input_zip)

    if hmm_scan:
        from .registry_detector import run_hmm_scan as _run_registry_hmm_scan
        _hmm_receipt = _run_registry_hmm_scan(input_zip, bgcs, strain_id)
        _atomic_write_manifest_text(
            package_dir / f"{strain_id}_HMM_Scan.json",
            json.dumps(_hmm_receipt, indent=2),
        )
        _stage(f"HMM scan: {_hmm_receipt.get('status', 'HMM_SCAN_UNAVAILABLE')}")

    _stage(f"parsed {len(bgcs)} BGCs from antiSMASH {antismash_ver} (json-evidence: {json_mode})")
    emit(f"  Parsed: {len(bgcs)} BGCs from antiSMASH {antismash_ver}  (json-evidence: {json_mode})")

    # PARSE-COMPLETENESS: the ZIP states how many region GBKs it offers; the parser states how
    # many BGCs it produced. Nothing compared the two, so a region GBK that errored OR parsed to
    # zero records (read_genbank_records warns, but a warning is not a gate) silently shortened
    # every downstream denominator — triage totals, governed counts, "all N BGCs accounted for" —
    # and the package stayed internally consistent, so validate_package still returned
    # MAMEY_COMPLETE. Report the source count next to the parsed count, and say so loudly on a
    # shortfall. Strict inequality only: a legitimately higher BGC count (a region GBK carrying
    # more than one record) is not a defect, and 0 means "no region GBKs, nothing to check".
    _source_region_gbks = _count_antismash_region_gbks(input_zip)
    if _source_region_gbks and len(bgcs) < _source_region_gbks:
        _missing = _source_region_gbks - len(bgcs)
        emit(f"  !! PARSE SHORTFALL: {_source_region_gbks} region GBK(s) in the ZIP but only "
              f"{len(bgcs)} BGC(s) parsed — {_missing} yielded no record (corrupt/truncated GBK). "
              f"Every downstream count is short by {_missing}; re-export the antiSMASH output.")
        _stage(f"PARSE SHORTFALL: {_missing} region GBK(s) yielded no record")

    # --- Source-derived scans ---
    _phase_receipt(package_dir, "inventory", "END",
                   raw_bgcs=len(bgcs), source_region_gbks=_source_region_gbks,
                   cds_count=len(cds), contig_count=len(contigs), domain_count=len(domains))
    _phase_receipt(package_dir, "source_scans", "START")
    _stage("running source scans (CCTT/CGAD/EFLS/resistance/TFBS/…)")
    try:
        with heartbeat_context("source_scans", enabled=(brief == "none"), seconds=heartbeat_seconds):
            source_scans = run_source_scans(bgcs, cds, contigs, domains, organism=taxonomy)
        _phase_receipt(package_dir, "source_scans", "END",
                       raw_bgcs=len(bgcs),
                       efls_pairs=(source_scans.efls or {}).get("candidate_pair_count") if source_scans else None,
                       tfbs_total=(source_scans.tfbs or {}).get("total_hits") if source_scans else None)
    except Exception as _ss_err:
        _phase_receipt(package_dir, "source_scans", "ERROR", reason=str(_ss_err))
        raise
    _stage("source scans complete; writing gene context and optional add-ons")

    # Shared issue channel must exist before optional renderers run. Their degradations are
    # carried into MameyRun and determine the final terminal status later in this function.
    issues: list[str] = []

    # v9.7.88 roadmap #1 / AS-XXX finding E: serialize a normalized per-CDS gene context into the
    # package NOW, while the parsed CDS/domain objects are in hand. This is the durable, sealed
    # source the gene-by-gene builder (and Mode B) read post-seal — so they no longer fall back to
    # NOLOCUS placeholder rows when the original antiSMASH ZIP is gone.
    _phase_receipt(package_dir, "gene_context", "START")
    try:
        from .gene_context import write_gene_context as _write_gene_context
        with heartbeat_context("gene_context", enabled=(brief == "none"), seconds=heartbeat_seconds):
            _gc_res = _write_gene_context(package_dir, strain_id, bgcs, cds, domains)
        _stage("gene context written; evaluating locus-map policy")
        _phase_receipt(package_dir, "gene_context", "END",
                       n_cds=_gc_res.get("n_cds"), n_bgcs=_gc_res.get("n_bgcs_with_cds"),
                       status_detail=_gc_res.get("status"))
    except Exception as _gc_err:
        _phase_receipt(package_dir, "gene_context", "ERROR", reason=str(_gc_err))

    # v9.7.90 (AS-XXX finding): deterministic gene-arrow locus maps. Rendered IN-RUN from each
    # BGC's region GBK (already inside input_zip), so no K0 dependency. Three triggers: top AB/AF
    # leads, every Mode B BGC, and each RG-GMCI HIGH pair (paired panel). Post-seal, non-blocking:
    # a render failure is logged and the core package stays valid.
    #
    # P0 (v9.7.101): locus-map render policy. The phase is expensive on large strains — a 65-BGC
    # genome under --chatgpt-safe did not finish in a wall-clock-capped session. Policy:
    #   off : never render (default for --chatgpt-safe, which sets brief="none")
    #   on  : always render (log expected count)
    #   auto: render, but skip when raw BGC count > 20 in a capped (brief="none") run
    _raw_bgc_n = len(bgcs)
    if locus_maps == "off":
        _run_locus_maps, _skip_reason = False, "locus_maps=off"
    elif locus_maps == "on":
        _run_locus_maps, _skip_reason = True, ""
    else:  # auto
        if brief == "none" and _raw_bgc_n > 20:
            _run_locus_maps, _skip_reason = False, f"auto: capped run with {_raw_bgc_n} BGCs (>20)"
        else:
            _run_locus_maps, _skip_reason = True, ""
    if not _run_locus_maps:
        _phase_receipt(package_dir, "locus_maps", "SKIP", reason=_skip_reason)
        _stage(f"locus maps skipped ({_skip_reason})")
    else:
        _phase_receipt(package_dir, "locus_maps", "START")
        _stage("rendering locus maps")
    try:
        if not _run_locus_maps:
            raise _LocusMapsSkipped()
        import zipfile as _zf_lm, tempfile as _tf_lm
        from .locus_map import cds_rows_from_gbk as _cds_from_gbk, render_locus_map as _render_lm
        from .locus_map_v8 import render_bgc_v8 as _render_lm_v8
        import shutil as _shutil_lm
        _lm_dir = package_dir / "locus_maps"
        _lm_dir.mkdir(exist_ok=True)
        _release = (getattr(bgcs[0], "release", "") if bgcs else "") or "PRIVATE"
        _bgc_by_id = {b.bgc_id: b for b in bgcs}

        # cache: extract each needed region GBK from the zip once, render rows
        _rows_cache: dict[str, list] = {}

        def _rows_for(_bid):
            if _bid in _rows_cache:
                return _rows_cache[_bid]
            b = _bgc_by_id.get(_bid)
            if not b or not getattr(b, "source_gbk", ""):
                _rows_cache[_bid] = []
                return []
            member = b.source_gbk
            try:
                with _zf_lm.ZipFile(input_zip) as _z:
                    # source_gbk may be a full path inside the zip or a bare name
                    _name = next((n for n in regular_file_names(_z)
                                  if n == member or n.endswith("/" + member)
                                  or n.endswith(member.split("/")[-1])), None)
                    if not _name:
                        _rows_cache[_bid] = []
                        return []
                    with _tf_lm.NamedTemporaryFile(suffix=".gbk", delete=False) as _tmp:
                        _tmp.write(_z.read(_name))
                        _tmp_path = _tmp.name
                _rows, _ = _cds_from_gbk(_tmp_path)
                _os.unlink(_tmp_path)
            except Exception:
                _rows = []
            _rows_cache[_bid] = _rows
            return _rows

        def _title_lm(_bid):
            b = _bgc_by_id.get(_bid)
            if not b:
                return _bid
            prods = "; ".join(b.products[:3]) if getattr(b, "products", None) else ""
            return (f"{_bid} · {getattr(b, 'node_id', '') or b.contig} · "
                    f"{getattr(b, 'antismash_region', '') or ''} — {prods} · "
                    f"{getattr(b, 'edge_status', '') or ''}")

        def _one_lm(_bid, _tag):
            b = _bgc_by_id.get(_bid)
            _node = getattr(b, "node_id", "") or (b.contig if b else "")
            _region = getattr(b, "antismash_region", "") if b else ""
            _png = _lm_dir / f"{_bid}_{_node}_locus.png"
            _csv = _lm_dir / f"{_bid}_{_node}_locus_data.csv"
            try:
                # v9.7.405: locus map v8 is the default renderer.
                _render_lm_v8(
                    package_dir, _bid, out_dir=_lm_dir, strain_id=strain_id, node=_node,
                    region=_region,
                    products="; ".join((getattr(b, "products", None) or [])[:3]))
                # Historical filenames are preserved for downstream consumers; these aliases
                # hold the v8 bytes, not a second legacy render.
                _shutil_lm.copyfile(_lm_dir / f"{_bid}_locus_map.png", _png)
                _shutil_lm.copyfile(_lm_dir / f"{_bid}_locus_map_data.csv", _csv)
                return
            except Exception as _lm_exc:
                # A post-seal figure cannot fail the core run, but the degradation is named:
                # fall through to the legacy map rather than emitting nothing silently.
                import sys as _sys_lm
                _sys_lm.stderr.write(
                    f"  locus map v8 unavailable for {_bid} "
                    f"({type(_lm_exc).__name__}: {_lm_exc}); using legacy renderer\n")
            _rows = _rows_for(_bid)
            if not _rows:
                return
            _render_lm([(_title_lm(_bid), _rows)], _png, _csv,
                       suptitle=f"{strain_id} — {_bid} locus ({_tag})", claim_prefix=_release)

        # (1) top AB + top AF lead BGCs
        _ranked_ab = sorted(bgcs, key=lambda b: getattr(b, "ab_score", 0) or 0, reverse=True)
        _ranked_af = sorted(bgcs, key=lambda b: getattr(b, "af_score", 0) or 0, reverse=True)
        if _ranked_ab:
            _one_lm(_ranked_ab[0].bgc_id, "top antibacterial lead")
        if _ranked_af and _ranked_af[0].bgc_id != (_ranked_ab[0].bgc_id if _ranked_ab else None):
            _one_lm(_ranked_af[0].bgc_id, "top antifungal lead")

        # (2) every Mode B BGC (depth-floor set)
        _mb_ids = [b.bgc_id for b in bgcs
                   if _depth_floor(b, (source_scans.cctt or {}) if source_scans else {}, mode) == "full_mode_b"]
        for _bid in _mb_ids:
            _one_lm(_bid, "Mode B")

        # (3) each RG-GMCI HIGH pair (paired panel) — startswith("HIGH") per item H
        _rg = (source_scans.rggmci or {}) if source_scans else {}
        _n_pairs = 0
        for _pr in _rg.get("ranked_pairs", []):
            if not str(_pr.get("rggmci_confidence", "")).startswith("HIGH"):
                continue
            _a, _b = _pr.get("bgc_a"), _pr.get("bgc_b")
            _ra, _rb = _rows_for(_a), _rows_for(_b)
            if not _ra or not _rb:
                continue
            _png = _lm_dir / f"{_a}__{_b}_pair_locus.png"
            _csv = _lm_dir / f"{_a}__{_b}_pair_locus_data.csv"
            _render_lm([(_title_lm(_a), _ra), (_title_lm(_b), _rb)], _png, _csv,
                       suptitle=f"{strain_id} — RG-GMCI HIGH pair {_a} ↔ {_b} (split / homology candidate)",
                       claim_prefix=_release)
            _n_pairs += 1

        _n_maps = len(list(_lm_dir.glob("*_locus.png")))
        # catalog the maps (filename, data_csv, kind) like every other figure deliverable
        try:
            import csv as _csv_lm
            with open(_lm_dir / "locus_map_manifest.csv", "w", newline="", encoding="utf-8") as _mf:
                _w = _SafeWriter(_mf)
                _w.writerow(["filename", "data_csv", "kind"])
                for _p in sorted(_lm_dir.glob("*_locus.png")):
                    if _p.name.endswith("_pair_locus.png"):
                        _w.writerow([_p.name, _p.name.replace("_pair_locus.png", "_pair_locus_data.csv"), "pair"])
                    else:
                        _w.writerow([_p.name, _p.name.replace("_locus.png", "_locus_data.csv"), "single"])
        except Exception as _catalog_exc:
            message = (
                f"LOCUS_MAP_CATALOG_WRITE_FAILED: {type(_catalog_exc).__name__}: "
                f"{_catalog_exc}"
            )
            issues.append(message)
            _phase_receipt(package_dir, "locus_map_catalog", "ERROR", reason=message)
        _phase_receipt(package_dir, "locus_maps", "END", n_maps=_n_maps, n_high_pairs=_n_pairs)
    except _LocusMapsSkipped:
        pass  # SKIP receipt already emitted above; no render performed
    except Exception as _lm_err:
        _phase_receipt(package_dir, "locus_maps", "ERROR", reason=str(_lm_err))

    # R-A: write per-BGC CCTT T43 triggers back onto each BGC record (they were computed in source_scans but
    # never persisted on the BGC, so the manifest/B1 cctt_triggers field came out blank).
    # AUDIT_371 (silent_swallow triage, same class as the v9.7.370 recorder-guard campaign
    # elsewhere in this function): this used to be a bare `except Exception: pass` -- a partial
    # failure mid-loop would silently blank cctt_triggers/cctt_uncorroborated (claim-relevant
    # fields feeding the triage board and manifest) for that BGC and every subsequent one, with
    # zero visibility, and the package would still seal MAMEY_COMPLETE. Named + recorded instead,
    # matching the established _degradation.record pattern used elsewhere in this file.
    try:
        _cctt = (source_scans.cctt or {}) if source_scans else {}
        _cctt_map = _cctt.get("per_bgc") or _cctt.get("bgc_coupling") or {}
        _uncorr_map = _cctt.get("context_uncorroborated_by_bgc") or {}
        for _b in bgcs:
            _trigs = _cctt_map.get(_b.bgc_id) or []
            _b.cctt_triggers = ";".join(sorted({str(t) for t in _trigs})) if _trigs else ""
            _unc = _uncorr_map.get(_b.bgc_id) or []
            _b.cctt_uncorroborated = ";".join(sorted({str(t) for t in _unc})) if _unc else ""
    except Exception as _cctt_persist_exc:
        from . import degradation as _deg_cctt
        _deg_cctt.record("cli.run_one_strain.cctt_trigger_persist", _cctt_persist_exc,
                         strain=strain_id)

    # --- Full RG-GMCI pre-triage gate ---
    # RG-GMCI is the core split-pathway/fragment-rescue feature.  It must run
    # before scan-status, triage, workbook writing, and package validation so
    # antibiotic/antifungal lead ranking can account for rescued BGC pairs.
    _phase_receipt(package_dir, "rggmci", "START")
    _stage("running RG-GMCI (multi-contig reconstruction)")
    try:
        source_scans.rggmci = run_rggmci(input_zip, bgcs, contigs=contigs)
    except Exception as _rg_err:
        _phase_receipt(package_dir, "rggmci", "ERROR", reason=str(_rg_err))
        raise
    if source_scans.rggmci.get("summary_line"):
        _stage(source_scans.rggmci["summary_line"])
    # P-CBG (v9.7.100): retain the FULL ClusterBlast per-gene correspondence (query gene -> reference gene,
    # %id, %coverage, blast score). RG-GMCI keeps only subject+identity for its adjacency math; this layer
    # is what lets a locus be characterised gene-by-gene against its reference cluster.
    from .clusterblast_genes import parse_clusterblast_gene_map
    try:
        source_scans.clusterblast_genes = parse_clusterblast_gene_map(input_zip, bgcs)
        _cbg = source_scans.clusterblast_genes
        _stage(f"ClusterBlast per-gene map: {_cbg.get('status')} "
               f"({_cbg.get('bgc_count', 0)} BGCs, {_cbg.get('parse_error_count', 0)} parse errors)")
    except Exception as _cbg_exc:  # pragma: no cover - defensive
        source_scans.clusterblast_genes = {"status": f"ERROR_{type(_cbg_exc).__name__}", "per_gene_best_hit": {}}
    # P-MPG: MIBiG/knownclusterblast-only, rank-uncapped per-gene evidence.
    try:
        from .mibig_per_gene import (
            parse_mibig_gene_map,
            build_bgc_mibig_profile,
            build_mibig_convergence,
        )
        _mpg = parse_mibig_gene_map(input_zip, bgcs)
        _bgc_mpg_context = {
            b.bgc_id: {
                "kcb_top": getattr(b, "kcb_top", None),
                "products": list(getattr(b, "products", []) or []),
                "edge_status": getattr(b, "edge_status", ""),
            }
            for b in bgcs
        }
        _mpg["mibig_convergence"] = build_mibig_convergence(
            _mpg.get("per_gene_mibig", {}),
            _mpg.get("query_gene_counts", {}),
            _bgc_mpg_context,
            _mpg.get("recognizable_query_gene_counts", {}),
        )
        _mpg["bgc_mibig_profile"] = build_bgc_mibig_profile(
            _mpg.get("per_gene_mibig", {}), _mpg.get("query_gene_counts", {}),
            _bgc_mpg_context, _mpg.get("mibig_convergence", []))
        source_scans.mibig_per_gene = _mpg
        _stage(
            f"MIBiG per-gene map: {_mpg.get('status')} "
            f"({_mpg.get('bgc_count', 0)} BGCs; "
            f"{len(_mpg.get('mibig_convergence', []))} convergence rows)"
        )
    except Exception as _mpg_exc:  # pragma: no cover - defensive
        source_scans.mibig_per_gene = {"status": f"ERROR_{type(_mpg_exc).__name__}", "per_gene_mibig": {}}
    # P-AS-TABLES: preserve structured antiSMASH JSON/GBK evidence as tables.
    try:
        from .antismash_tables import build_structured_tables
        source_scans.antismash_structured = build_structured_tables(input_zip, antismash_evidence, bgcs)
        _stage("structured antiSMASH module/RiPP/motif tables collected")
    except Exception as _ast_exc:  # pragma: no cover - defensive
        source_scans.antismash_structured = {"status": f"ERROR_{type(_ast_exc).__name__}"}
    # P-CBDB v9.7.100: functional-complementarity for rescue. Profile each BGC's gene roles (core /
    # tailoring / transport / regulatory) from the sealed gene context, then tag every RG-GMCI pair with a
    # functional_rescue_class (COMPLEMENTARY / BOTH_CORE / ACCESSORY_ONLY). A homology rescue is only
    # credible when the fragments are functionally complementary; BOTH_CORE corroborates a paralog verdict.
    try:
        from .clusterblast_genes import (functional_profile_from_gene_context,
                                          rescue_functional_complementarity)
        from .gene_context import load_gene_context as _load_gc
        _gctx = _load_gc(package_dir, strain_id)
        _fprof = functional_profile_from_gene_context(_gctx)
        source_scans.functional_profiles = _fprof
        _rk = source_scans.rggmci.get("ranked_pairs", []) if source_scans.rggmci else []
        for _p in _rk:
            _fc = rescue_functional_complementarity(_fprof.get(_p.get("bgc_a")), _fprof.get(_p.get("bgc_b")))
            _p["functional_rescue_class"] = _fc.get("functional_rescue_class", "UNKNOWN_NO_PROFILE")
            _p["a_core_fraction"] = _fc.get("a_core_fraction")
            _p["b_core_fraction"] = _fc.get("b_core_fraction")
            _p["a_functional_roles"] = "; ".join(_fc.get("a_roles", []))
            _p["b_functional_roles"] = "; ".join(_fc.get("b_roles", []))
        _stage(f"functional-complementarity annotated on {len(_rk)} RG-GMCI pairs")
    except Exception as _fp_exc:  # pragma: no cover - defensive
        source_scans.functional_profiles = {"status": f"ERROR_{type(_fp_exc).__name__}"}
    _phase_receipt(package_dir, "rggmci", "END",
                   pairs_total=source_scans.rggmci.get("pairs_total") if source_scans.rggmci else None,
                   high_pairs=source_scans.rggmci.get("high_pairs") if source_scans.rggmci else None,
                   ranked_pairs=len(source_scans.rggmci.get("ranked_pairs", [])) if source_scans.rggmci else 0,
                   functional_profiles_status=(source_scans.functional_profiles or {}).get("status", "OK"))
    # --- _4B PKS-KS intrinsic clade channel (.359, phylogenomics-lane P358): deterministic, offline; complements
    # RG-GMCI with reference-FREE cross-contig KS homology. Never fails the core run. The _4D two-proof
    # join that consumes this is emitted later, in _write_package, once _4A_RGGMCI_ranked_pairs.csv exists.
    _phase_receipt(package_dir, "pks_ks_scan", "START")
    try:
        _ksscan = run_pks_ks_scan(input_zip, bgcs)
        source_scans.pks_ks_scan = _ksscan
        write_pks_ks_csv(_ksscan, _os.path.join(package_dir, f"{strain_id}_4B_pks_ks_fragment_scan.csv"), strain_id)
        if _ksscan.get("summary_line"):
            _stage(_ksscan["summary_line"])
        _phase_receipt(package_dir, "pks_ks_scan", "END",
                       n_ks=_ksscan.get("n_ks"),
                       cross_contig_clades=len(_ksscan.get("cross_contig_clades", [])),
                       iterative_candidates=_ksscan.get("iterative_candidates"))
    except Exception as _ks_exc:  # never fail the core run
        _phase_receipt(package_dir, "pks_ks_scan", "ERROR", reason=str(_ks_exc))
    _stage("scan pack + triage")

    scan_status  = run_external_scan_pack(source_scans, antismash_evidence, taxonomy,
                                           gbk_pfam_hits=gbk_pfam_hits)

    # --- Issues ---
    from .assembly import corrected_bgc_count, assembly_tier
    from collections import Counter
    c = Counter(b.edge_status for b in bgcs)
    raw = len(bgcs)
    interior = c.get("Interior", 0)
    edge     = c.get("Edge", 0)
    fc       = c.get("Full-contig", 0)
    interior_pct = round(interior / raw * 100, 1) if raw else 0
    # CUT B (v9.7.223): publish this strain's assembly tier so _apply_boundary_adjustment can skip
    # the Edge penalty on POOR/VERY_POOR assemblies (Edge is expected there, not a quality signal).
    # v9.7.374 doc-currency fix (AUDIT audit): _apply_boundary_adjustment lives on
    # architecture_first.py's assess_architecture() path, which — per card_verdicts.py's own
    # v9.7.371 doc-fix note — is a separate, currently-unwired KCB-concordance engine; the live
    # architecture-capacity call is class_architecture.py::annotate_architecture(), called from
    # source_scans.py, which has no equivalent assembly-tier-aware boundary adjustment. This call
    # is therefore inert in production (only tests exercise the reader) and CUT B's Edge-penalty
    # skip does not currently affect any real run's output; it is ALSO moot even if re-wired,
    # since scoring.py::edge_penalty() has returned a hardcoded 0.0 since v9.7.84 (the boundary
    # penalty CUT B would skip no longer exists). Left in place (dead but harmless) rather than
    # deleted so a future re-wiring of architecture_first.py has this state ready; flagged here so
    # the next reader does not mistake it for live boundary-adjustment behavior.
    try:
        from .architecture_first import set_run_assembly_tier
        set_run_assembly_tier(assembly_tier(interior_pct))
    except Exception:
        pass

    # F1: a bare assembly (NO antiSMASH regions parsed) must NOT pass as a 0-BGC strain — that
    # silently banks an empty strain. Fail closed and write no package.
    # A missing antiSMASH VERSION string is NOT a bare assembly when regions were parsed (raw > 0):
    # the parsed regions prove this is antiSMASH output; only the version probe failed (e.g. a
    # GBK structured-comment variant). Discarding a real, region-bearing strain on a failed version
    # probe is the F1 mis-fire — guard on region count alone, and record the missing version below.
    if raw == 0:
        emit(f"  [FAIL] No antiSMASH regions parsed (antiSMASH version: {antismash_ver or 'None'}).", '         This looks like a bare assembly. Run antiSMASH 8 on the genome first, then re-run mamey on the antiSMASH output ZIP — not the raw NCBI/.fna download.', sep="\n")
        return {
            "strain_id": strain_id, "status": "MAMEY_FAILED",
            "raw_bgcs": 0, "corrected_bgcs": 0, "assembly_tier": "NONE",
            "package_zip": None, "master_updated": False,
            "issues": ["No antiSMASH regions found in input — bare assembly; no package written. "
                       "Run antiSMASH 8 first."],
        }

    # v9.7.374 fix: _profile_issue (PROFILE_MISMATCH / ANTISMASH_PROFILE_UNREADABLE, set ~475 lines
    # above) was computed and printed to the console but never persisted anywhere durable. A sealed
    # package could carry an operator-supplied --antismash-profile that the archive's own embedded
    # record actively disagreed with, with zero trace once the run's console log is gone -- exactly
    # the "pooling them silently corrupts cross-strain work such as BiG-SCAPE GCF clustering" risk
    # the surrounding code's own comments describe. Folding it into `issues` here is sufficient to
    # reach manifest.json too: `run = MameyRun(..., issues=issues, ...)` a few dozen lines below
    # feeds this same list into MameyRun.to_dict()'s "issues" field, which _write_package() uses
    # verbatim as manifest_data["issues"] -- so this single edit closes both gaps.
    if _profile_issue:
        issues.append(_profile_issue)
    if _label_accession:
        issues.append(f"Strain label '{strain_id}' is an NCBI accession (fallback). Prefer a strain name "
                      f"via --strain when one is available; accessions are a label of last resort.")
    # AMBER-03-2: a host that does not trace to a record must say so in the run's own issue
    # list, not only in a manifest field nobody opens. Sign-off gate item 7 ("flag PI-word-only
    # provenance"). Non-blocking, and silent when no source was supplied at all.
    from .source_provenance import (source_is_traced as _src_traced,
                                    describe_source_provenance as _src_desc,
                                    NOT_SUPPLIED as _SRC_NOT_SUPPLIED)
    _src_prov = context.source_provenance
    if str(source or "").strip().lower() not in _SRC_NOT_SUPPLIED and not _src_traced(_src_prov):
        emit(f"  [WARN] isolation source '{source}' is {_src_desc(_src_prov)} — untraced provenance.")
        issues.append(
            f"SOURCE_PROVENANCE: isolation source '{source}' is {_src_desc(_src_prov)}. Do NOT "
            f"present it as this strain's host in a figure, caption or table until it is traced "
            f"to the authoritative strain table or a GenBank accession "
            f"(re-run with --source-provenance accession|table once it is). Provenance only — "
            f"never read into a functional claim."
        )
    from mamey.cohort_resolver import resolve_cohort as _resolve_cohort
    _coh = _resolve_cohort(strain_id, taxonomy)
    if _coh["resolved_sid"] and _coh["note"]:
        issues.append(f"COHORT: {_coh['note']} — cohort set to SID (was OTHER under ID-prefix-only "
                      f"classification).")
    if _coh["actino_status"] == "non_actinomycete":
        issues.append(f"*** NON-ACTINOMYCETE: {_coh['note']}. This strain is OUTSIDE the project's "
                      f"actinomycete scope; do not merge it into an actinomycete cross-strain comparison "
                      f"without explicit intent.")
    if not antismash_ver:
        issues.append("antiSMASH version string not detected, but {n} region(s) were parsed; "
                      "proceeding and treating the input as antiSMASH output.".format(n=raw))
    if not bgcs:
        issues.append("No BGC GenBank region records parsed from antiSMASH archive.")
    if antismash_evidence.get("status") == "NO_KCB_SOURCE_FOUND":
        issues.append("KCB/RiQ parser found no antiSMASH JSON/TXT evidence; KCB fields may be blank.")
    # AUDIT_374: _kcb_recycling_audit() (antismash_evidence.py) computes a real structural
    # sanity check on KCB assignment right after apply_evidence_to_bgcs() above, and its own
    # docstring says a FAIL "should block manuscript/comparative use until inspected" — but the
    # verdict was previously only ever written into {strain}_AntiSMASH_Evidence_Parse.json, never
    # consulted here. It never reached `issues`, commit_receipt.json's PASS/PASS_WITH_ISSUES
    # status, issue_log.md, or the console. Surface it the same way every sibling check in this
    # block already is.
    _kcb_audit = antismash_evidence.get("kcb_assignment_audit") or {}
    if _kcb_audit.get("status") not in (None, "PASS"):
        issues.append(
            f"KCB_ASSIGNMENT_AUDIT: {_kcb_audit['status']} — {_kcb_audit.get('assigned_bgcs', 0)} "
            f"BGCs assigned KCB evidence, only {_kcb_audit.get('distinct_score_protein_pairs', 0)} "
            f"distinct (score, protein_hits) pairs among them"
            + (f"; {len(_kcb_audit.get('accession_tail_score_bgcs', []))} BGC(s) with a KCB score "
               f"matching their own contig accession's numeric tail"
               if _kcb_audit.get("accession_tail_score_bgcs") else "")
            + ". Check region keying before using KCB-derived novelty or comparisons for this "
              "strain; see kcb_assignment_audit in the AntiSMASH_Evidence_Parse.json for detail."
        )
    # A2: use needs_multibatch() for the definitive per-strain batch-split decision.
    # Replaces the former ad-hoc `raw > 40` check (which used a different threshold and ignored
    # edge/FC counts and rescue state). rescue_triggered = any HIGH RG-GMCI pairs (judgment must
    # address split clusters, adding to the review load even when raw count is modest).
    from .scoring import needs_multibatch as _nmb
    _rggmci_high = source_scans.rggmci.get("high_pairs", 0) if source_scans.rggmci else 0
    _needs_mb, _mb_reason = _nmb(bgcs, rescue_triggered=bool(_rggmci_high))
    if _needs_mb:
        import math as _math
        _batches = _math.ceil(raw / 20)
        issues.append(
            f"MULTIBATCH: {_mb_reason} — judgment will need ~{_batches} LLM batches "
            f"(~20 BGCs each). Use the batch plan to sequence them."
            + (f" RG-GMCI HIGH pairs: {_rggmci_high} (include split-cluster review in each batch)."
               if _rggmci_high else "")
        )
    if assembly_tier(interior_pct) == "VERY_POOR":
        issues.append(f"VERY_POOR assembly ({interior_pct}% interior BGCs). Most leads are edge/FC fragments; RG-GMCI must be used before lead ranking.")
    # PC-A2 (v9.7.101): non-blocking assembly-sanity / contamination check. Two VERY_POOR drafts
    # previously passed as MAMEY_COMPLETE with no flag despite bimodal-GC / foreign-content pathology.
    try:
        from .parsers import read_fasta_sequences_from_zip, read_genbank_records
        from .assembly import assembly_sanity_check
        _seqs = read_fasta_sequences_from_zip(input_zip)
        if not _seqs:
            _seqs = {}
            for _, _rec in read_genbank_records(input_zip, region_only=False):
                _cid = getattr(_rec, "name", "") if str(getattr(_rec, "name", "")).startswith("NODE_") else _rec.id
                if _cid not in _seqs or len(_rec.seq) > len(_seqs[_cid]):
                    _seqs[_cid] = str(_rec.seq)
        _sanity = assembly_sanity_check(_seqs)
        # AMBER-03-3: the size flags and the GC flags mean different things, so they must not
        # share one sentence. The old message said "possible contamination or co-assembly" for
        # every flag — wrong, and misleading, for a partial GenBank submission.
        _size_flags = [f for f in _sanity["flags"] if f.startswith("PARTIAL_")]
        _gc_flags = [f for f in _sanity["flags"] if not f.startswith("PARTIAL_")]
        if _size_flags:
            _floor = _sanity.get("min_genome_bp") or 0
            _what = ("looks like a PARTIAL GenBank submission (one or a few records), not a small "
                     "genome" if _sanity.get("partial_submission_suspect")
                     else "is far below the actinomycete floor")
            emit(f"  [WARN] {'/'.join(_size_flags)}: {_sanity['genome_bp']:,} bp in "
                  f"{_sanity['n_contigs']} record(s) — {_what}.")
            issues.append(
                f"{'/'.join(_size_flags)}: {_sanity['genome_bp']:,} bp in "
                f"{_sanity['n_contigs']} record(s) — below the ~{_floor:,} bp actinomycete floor; "
                f"{_what}. The BGC count for this input is a property of the submitted sequence, "
                f"NOT a measurement of the organism, and must not be compared with whole-genome "
                f"counts or plotted on a per-strain BGC figure without that caveat. Re-download "
                f"the full assembly (all records / the GCF_ assembly, not a single accession) "
                f"before using it as a comparator."
            )
        if _gc_flags:
            issues.append(
                f"{'/'.join(_gc_flags)}: per-contig GC sd={_sanity['per_contig_gc_sd']}% "
                f"(clean genomes ~1-2%), overall GC={_sanity['overall_gc']}%, "
                f"{_sanity['n_contigs']} contigs / {_sanity['genome_bp']:,} bp. "
                f"Possible contamination or co-assembly — non-blocking; analyst to review."
            )
    except Exception as _sanity_exc:
        _sanity_issue = (
            "ASSEMBLY_SANITY_PROBE_FAILED: assembly completeness and contamination "
            f"status are UNVERIFIED ({type(_sanity_exc).__name__})."
        )
        issues.append(_sanity_issue)
        _phase_receipt(
            package_dir, "assembly_sanity_probe", "ERROR", reason=_sanity_issue
        )
    # v9.7.187: antiSMASH --limit record-cap detection. A truncated run scans only the largest
    # N records; BGCs on skipped records are silently missing while the GC/contamination stats
    # above still cover the whole assembly. Surface it so MAMEY_COMPLETE is not read as "whole
    # genome scanned".
    try:
        from .parsers import antismash_record_limit_truncation as _artl
        _trunc = _artl(input_zip)
        if _trunc.get("truncated"):
            _an = _trunc.get("analysed")
            _sk = _trunc.get("skipped_count")
            _eg = (f", first {_trunc['first_skipped']}" if _trunc.get("first_skipped") else "")
            _sktxt = (f"{_sk} eligible records were skipped ({_eg.lstrip(', ')})"
                      if _sk else f"records beyond the cap were skipped{_eg}")
            issues.append(
                f"RECORD_LIMIT_TRUNCATION: antiSMASH analysed only the largest {_an} records "
                f"(--limit); {_sktxt} and were NOT scanned for BGCs, so the region count is a "
                f"FLOOR, not the whole assembly. The contamination/GC stats above cover the full "
                f"FASTA and are not comparable to the BGC coverage. Re-run antiSMASH with a higher "
                f"--limit for complete coverage."
            )
    except Exception as _limit_exc:
        _limit_issue = (
            "RECORD_LIMIT_PROBE_FAILED: antiSMASH record-limit coverage status is "
            f"UNVERIFIED ({type(_limit_exc).__name__})."
        )
        issues.append(_limit_issue)
        _phase_receipt(
            package_dir, "record_limit_probe", "ERROR", reason=_limit_issue
        )
    if source_scans.rggmci.get("status") not in {"PASS", "NULL_NO_RGGMCI_PAIRS"}:
        issues.append(f"RG-GMCI did not complete cleanly: {source_scans.rggmci.get('status')}")
    # PHO-CLUSTER: flag a strong phosphonate signal. counts = HIT count (gene-level); bgc_counts = how many
    # DISTINCT BGCs carry T43-PHO. The two answer different questions, so report both and let the BGC spread
    # drive the interpretation (one locus vs. a phosphonate-rich strain) instead of the raw hit count.
    pho_hits = source_scans.cctt.get("counts", {}).get("T43-PHO_phosphonate", 0)
    pho_bgcs = source_scans.cctt.get("trigger_bgc_counts", {}).get("T43-PHO_phosphonate", 0)
    if pho_hits >= 5:
        # AUDIT_371 (claim-safety): "phosphonate-rich strain" was a flat descriptor derived
        # purely from source-derived gene-hit density, with no genomic-capacity hedge (unlike the
        # single-locus branch, which already said "not a phosphonate-rich strain" -- implying the
        # multi-BGC branch's phrase was read as a positive claim, not just a routing label). Hedged
        # to match this project's diagnostic-gene-capacity-not-identity convention.
        _spread = (f"a single dedicated phosphonate locus ({pho_hits} hits in 1 BGC) — not a "
                   "phosphonate-rich genomic profile" if pho_bgcs <= 1
                   else f"phosphonate signal spread across {pho_bgcs} BGCs ({pho_hits} hits total) "
                        "— phosphonate-rich genomic profile (gene-hit density only; capacity, not "
                        "a compound-class or production claim)")
        issues.append(
            f"PHO_CLUSTER: T43-PHO {pho_hits} hits / {pho_bgcs} BGC(s) — {_spread}. "
            "Recommend: 31P-NMR metabolomics screen; FomA/FomB BLASTP on the PHO-carrying BGC(s); "
            "PepM-like domain confirmation before compound-class claims."
        )

    run = MameyRun(
        context=context,
        assembly=assembly,
        bgcs=bgcs,
        scan_status=scan_status,
        source_scans=source_scans,
        issues=issues,
    )

    # --- Write output files ---
    _phase_receipt(package_dir, "workbook", "START")
    _stage("writing output files (inventory, triage, workbook)…")
    _phase_receipt(package_dir, "write_package", "START")
    try:
        with heartbeat_context("write_package", enabled=(brief == "none"), seconds=heartbeat_seconds):
            _write_package(run, package_dir, antismash_evidence, antismash_profile)
        _phase_receipt(package_dir, "write_package", "END",
                       file_count=sum(1 for _p in package_dir.rglob("*") if _p.is_file()))
    except Exception as _wp_err:
        _phase_receipt(package_dir, "write_package", "ERROR", reason=str(_wp_err))
        raise

    # --- Per-strain workbook (MMW-1: non-blocking, always reported) ----
    _per_wb_path = package_dir / f"{strain_id}_5_workbook.xlsx"
    _per_wb_status: dict = {}
    _phase_receipt(package_dir, "per_strain_workbook", "START")
    try:
        from .workbook import write_per_strain_workbook
        with heartbeat_context("per_strain_workbook", enabled=(brief == "none"), seconds=heartbeat_seconds):
            write_per_strain_workbook(run, _per_wb_path)
        import hashlib as _hl
        _per_wb_cs = _hl.sha256(_per_wb_path.read_bytes()).hexdigest()[:16]
        _per_wb_status = {"state": "PRODUCED", "path": str(_per_wb_path),
                          "checksum_sha256_head16": _per_wb_cs}
        _phase_receipt(package_dir, "per_strain_workbook", "END",
                       workbook=str(_per_wb_path), bytes=_per_wb_path.stat().st_size)
    except Exception as _per_wb_err:
        _per_wb_status = {"state": "FAILED", "reason": str(_per_wb_err)[:200]}
        issues.append(f"per_strain_workbook FAILED: {_per_wb_err}")
        _phase_receipt(package_dir, "per_strain_workbook", "ERROR", reason=str(_per_wb_err))
        if require_workbook:
            raise RuntimeError(f"--require-workbook: per-strain workbook failed: {_per_wb_err}") from _per_wb_err
    _write_batch_plan(package_dir, strain_id, mode, source, issues=issues)

    # --- P01/P02 addons: Diagnostic Rescue 4B + analysis-forward directive (before seal) ---
    # Emitted here so the new files are tracked in manifest.files, checksummed, and zipped.
    _phase_receipt(package_dir, "package_addons", "START")
    try:
        import tempfile as _tf
        import zipfile as _zf
        from . import package_addons as _addons
        # Patch G (v9.7.196): recover antiSMASH NRPS/PKS predictions the pipeline otherwise drops
        # (per-A-domain Stachelhaus substrate + PKS-AT extender + assembled polymer/SMILES +
        # over-merge kind). Reads the run JSON straight from the ZIP, independent of --json-evidence.
        try:
            from .nrps_predictions import write_nrps_prediction_csvs
            _npred = write_nrps_prediction_csvs(input_zip, package_dir, strain_id)
            if _npred.get("over_merged_regions"):
                run.issues.append(
                    f"OVER_MERGE_CANDIDATES: {_npred['over_merged_regions']} region(s) carry >=2 "
                    f"protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own "
                    f"'region = >=2 BGCs' signal. See {strain_id}_predicted_polymers.csv.")
        except Exception as _npe:  # fail-open: never break the package over an add-on
            _phase_receipt(package_dir, "nrps_predictions", "ERROR", reason=str(_npe))
        _cb_dir = None
        with _zf.ZipFile(input_zip) as _z:
            _cb = [n for n in regular_file_names(_z)
                   if "clusterblast" in n.split("/") and n.endswith(".txt")]
            if _cb:
                _cb_dir = _os.path.join(_tf.mkdtemp(prefix="mamey_cb_"), "clusterblast")
                _os.makedirs(_cb_dir, exist_ok=True)
                for _n in _cb:
                    with _z.open(_n) as _s, open(_os.path.join(_cb_dir, _os.path.basename(_n)), "wb") as _o:
                        _o.write(_s.read())
        with heartbeat_context("package_addons", enabled=(brief == "none"), seconds=heartbeat_seconds):
            _leads = _addons.emit_rescue_4b(str(package_dir), clusterblast_dir=_cb_dir)
            _addons.add_d4_sheet(str(package_dir / f"{strain_id}_5_workbook.xlsx"), _leads)
            _addons.write_analysis_forward(str(package_dir))
        _stage("package add-ons written; preparing package entry points")
        # v9.7.67: initialise judgment register — creates the write path for Sapote Mode B persistence.
        # Idempotent: preserves any prior Sapote progress if the package is re-extracted.
        try:
            from .judgment_store import init_register as _init_reg
            import csv as _csv2
            _inv = next((str(p) for p in package_dir.iterdir()
                         if p.name.endswith("_2_inventory.csv")), None)
            _bgc_ids = []
            if _inv:
                with open(_inv, newline="", encoding="utf-8") as _f:
                    _bgc_ids = [r.get("BGC_ID","") for r in _csv2.DictReader(_f) if r.get("BGC_ID","")]
            _init_reg(str(package_dir), strain_id, _bgc_ids)
        except Exception as _je:
            issues.append(f"judgment_store.init_register skipped: {_je}")
        _hi = sum(1 for _l in _leads if _l["rescue_tier"] == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE")
        _phase_receipt(package_dir, "package_addons", "END",
                       rescue_leads=len(_leads), high_rescue_leads=_hi)
        emit(f"  Diagnostic Rescue: {len(_leads)} lead(s), {_hi} HIGH  |  ANALYSIS_FORWARD.md written")
    except Exception as _e:  # never block a run on an addon
        issues.append(f"Diagnostic Rescue / analysis-forward addon skipped: {_e}")
        _phase_receipt(package_dir, "package_addons", "ERROR", reason=str(_e))

    # --- Update master workbook ---
    # GUARD: the canonical master_workbook.py writer (coded A1-H3, snake_case) must not be pointed at a
    # legacy *descriptive*/"v1.2 session" workbook (built by tools/build_master.py + add_xstrain_sheets.py),
    # where header-keyed appends silently miss every core sheet and the resave then drops sheets. Detect
    # that workbook ONLY by its distinctive descriptive sheets (Fragment_Rescue_Tiers / TIGRFAM_Check).
    # NB: do NOT trigger on A2_Strain_Registry — it is shared with the canonical coded scheme, so including
    # it here would (wrongly) block appending strain #2+ onto a correct canonical master.
    _master_wb_status: dict = {}
    if master_path and Path(master_path).exists():
        try:
            import openpyxl as _oxl
            _wb = _oxl.load_workbook(master_path, read_only=True)
            _v12 = {"Fragment_Rescue_Tiers", "TIGRFAM_Check"} & set(_wb.sheetnames)
            _wb.close()
            if _v12:
                emit(f"  [BLOCKED] --master target is a Schema-v1.2 workbook ({', '.join(sorted(_v12))} present).", "            The canonical --master writer is incompatible with v1.2 and would drop core sheets.", "            Bank this strain into the cohort instead, then rebuild:", "              python tools/ingest_package.py --package <pkg_dir> --ww <WWxxxx> --merge --banked-dir cohort", "              python tools/build_workbook.py --build-master tools/build_master.py \\", "                  --add-xstrain tools/add_xstrain_sheets.py --workbook <out.xlsx>", sep="\n")
                master_path = None  # skip the destructive canonical write
        except Exception as _schema_exc:
            message = (
                f"MASTER_WORKBOOK_SCHEMA_PROBE_FAILED: {type(_schema_exc).__name__}: "
                f"{_schema_exc}; refusing master mutation"
            )
            issues.append(message)
            _phase_receipt(package_dir, "master_workbook_schema_probe", "ERROR", reason=message)
            _master_wb_status = {"state": "FAILED", "reason": message[:200]}
            master_path = None

    master_out = None
    if not master_path:
        if not _master_wb_status:
            _master_wb_status = {"state": "NOT_REQUESTED"}
    else:
        # v9.7.409 (CLAUDE_409 C1): the shared --master workbook is a read-modify-write PUBLISHED
        # to a resource shared across run dirs. H13's per-run-dir lock does NOT cover it (two runs
        # into different --outdir share one --master but take different .mamey.lock). Two such runs
        # both read master [..N], append their own strain, and copy2 back -> last writer wins and one
        # strain's rows are silently lost (reproduced: 4 concurrent appends kept 1). Fixes: (a) hold a
        # BLOCKING advisory lock on <master>.lock across the whole read-append-publish so a second
        # writer serializes and appends onto the FIRST writer's result (no lost update), and (b)
        # publish with a unique-temp + os.replace instead of the non-atomic shutil.copy2 (a concurrent
        # reader can no longer see a half-written/interleaved .xlsx). The .lock sits beside the master,
        # never inside a package, so it is not swept into any checksum set.
        _master_lock = None
        try:
            _master_lock = _acquire_master_workbook_lock(master_path)
            if _master_lock is None:
                raise RuntimeError(
                    "MASTER_WORKBOOK_LOCK_UNAVAILABLE: refusing shared-master mutation "
                    "because an exclusive advisory lock could not be acquired"
                )
            master_path_p = Path(master_path)
            master_out = out_root / f"Mamey_v{__version__}_Master_After_{strain_id}_{date.today()}.xlsx"
            from .master_workbook import update_master_workbook  # v9.7.409 A1: lazy (openpyxl)
            update_master_workbook(run, master_path_p, master_out)
            # v9.7.367 CANDIDATE (Indigo2 §2 surface 2): drain merge-side coverage
            # breadcrumbs into the phase receipt (runs post-seal receipt append; the
            # receipt file is MUTABLE_RECEIPT_NAMES, outside all gated surfaces).
            # v9.7.370 swallow triage: same recorder-guard pattern — deliberate, named.
            with _contextlib.suppress(Exception):
                from . import degradation as _deg_m
                _mdeg = _deg_m.drain()
                if _mdeg:
                    _phase_receipt(package_dir, "master_coverage", "WARN",
                                   n=len(_mdeg), events=_mdeg[:20])
            shutil.copy2(master_out, package_dir / master_out.name)
            _atomic_publish_master(master_out, master_path_p)  # C1: was shutil.copy2 (non-atomic)
            import hashlib as _hl2
            _mcs = _hl2.sha256(master_path_p.read_bytes()).hexdigest()[:16]
            import openpyxl as _oxl2
            _mwb = _oxl2.load_workbook(master_path_p, read_only=True)
            _sheets = _mwb.sheetnames; _mwb.close()
            _master_wb_status = {"state": "PRODUCED", "path": str(master_path_p),
                                 "checksum_sha256_head16": _mcs,
                                 "sheets": _sheets}
            emit(f"  Master workbook updated: {master_path_p}")

            # Enrich manifest with cross-strain context
            from .master_workbook import cross_strain_context  # v9.7.409 A1: lazy (openpyxl)
            ctx = cross_strain_context(master_path_p, strain_id, source)
            manifest_path = package_dir / "manifest.json"
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_data["cross_strain_context"] = ctx
            _atomic_write_manifest_text(manifest_path, json.dumps(manifest_data, indent=2))
        except Exception as _mwb_err:
            _master_wb_status = {"state": "FAILED", "reason": str(_mwb_err)[:200],
                                 "recovery_command": "python tools/ingest_package.py --package <pkg_dir> --master <path>"}
            issues.append(f"master_workbook FAILED: {_mwb_err}")
            emit(f"  [WARN] Master workbook FAILED: {_mwb_err}")
            if require_workbook:
                raise RuntimeError(f"--require-workbook: master workbook failed: {_mwb_err}") from _mwb_err
        finally:
            # v9.7.409 (CLAUDE_409 C1): release the shared-master advisory lock (closing the handle
            # drops the flock). Runs on both the success and failure paths, including the
            # --require-workbook re-raise above.
            _release_master_workbook_lock(_master_lock)

    # --- Render deterministic strain brief (extraction-layer; GENUINELY non-blocking) ---
    # v9.7.88 Finding L: with seal-first ON (default), the brief render is DEFERRED to after the
    # core is sealed (see the post-seal block below). The old path (render here, before the seal,
    # so brief files are inside the checksum set) runs only when MAMEY_SEAL_FIRST=0.
    if not MAMEY_SEAL_FIRST and brief != "none":
        brief_res = _render_brief_nonblocking(package_dir, brief, issues.append)
        if brief_res.get("status") == "COMPLETE":
            emit(f"  Strain brief: {brief_res['tier']} ({len(brief_res['files'])} files)")
        elif brief_res.get("status") == "SKIPPED":
            emit(f"  Strain brief: SKIPPED ({brief_res.get('reason','')})")
    elif brief == "none":
        # v9.7.185 P10: only write the marker when figures are truly absent; the old text falsely
        # claimed "intentionally skipped" even when the gold figure suite rendered on a separate path.
        _phase_receipt(package_dir, "brief_render", "SKIP", reason="--brief none")
        _fig_dirs = ("smoke_figures", "locus_maps", "gold_figures")
        _have_figs = any(
            (package_dir / d).is_dir() and any((package_dir / d).iterdir())
            for d in _fig_dirs
        )
        if not _have_figs:
            _nfr = (
                "# No figures rendered\n\n"
                "Built with --brief none (or --chatgpt-safe); the strain-brief figure step was "
                "skipped for safe batch operation.\n\n"
                "Re-render: python -m mamey render-all-figures --package <this_dir>\n"
            )
            try:
                (package_dir / "NO_FIGURES_RENDERED.md").write_text(_nfr, encoding="utf-8")
            except Exception as _marker_exc:
                message = (
                    f"NO_FIGURES_MARKER_WRITE_FAILED: {type(_marker_exc).__name__}: "
                    f"{_marker_exc}"
                )
                issues.append(message)
                _phase_receipt(package_dir, "no_figures_marker", "ERROR", reason=message)

    # --- Collection figures (metadata-gated, non-blocking) ---
    _meta_csv_path = metadata_csv
    try:
        from .collection_figures import render_collection_figures as _rcf
        import csv as _csv_mod
        _meta_rows = None
        if _meta_csv_path and Path(_meta_csv_path).exists():
            with open(_meta_csv_path, newline="", encoding="utf-8") as _mf:
                _meta_rows = list(_csv_mod.DictReader(_mf))
        _fig_out = package_dir / "figures"
        _cf_result = _rcf(
            _meta_rows, _fig_out,
            source_file=str(_meta_csv_path) if _meta_csv_path else "",
        )
        if _cf_result["n_generated"] > 0:
            emit(f"  Collection figures: {_cf_result['n_generated']} generated, "
                  f"{_cf_result['n_skipped']} skipped — see figures/FIGURE_AVAILABILITY.md")
        else:
            emit(f"  Collection figures: 0 generated (no metadata or no eligible fields) "
                  f"— see figures/FIGURE_AVAILABILITY.md")
        for _w in _cf_result.get("warnings", []):
            issues.append(f"collection_figures: {_w}")
    except Exception as _cfe:
        issues.append(f"collection_figures skipped: {_cfe}")

    # --- Validate and seal package ---
    # Backward-compatible alias for earlier HOW_TO_USE/kernel language.
    # manifest.json remains the authoritative handoff object.
    # v9.7.400 de-bloat: the alias used to be a VERBATIM re-dump of manifest.json, duplicating
    # the entire source_scans blob (~21 MB on a measured 96-BGC strain, whose manifest and
    # snapshot each carried a byte-identical 20,882,853-byte source_scans — ~40% of the package).
    # The alias is now a tiny stub pointing at the manifest; in-bundle readers follow `alias_of`
    # (see mamey/snapshot_alias.py). The file still exists, so validate.py's presence gate and
    # every `*Project_Memory_Snapshot.json` glob keep working.
    _alias_stub = {
        "schema": "project_memory_snapshot_alias_v1",
        "alias_of": "manifest.json",
        "strain_id": strain_id,
        "note": ("Alias stub: the full snapshot content lives in manifest.json in this "
                 "directory (the pre-v9.7.400 snapshot was a verbatim copy of it). "
                 "Load via mamey.snapshot_alias.load_snapshot() or follow alias_of."),
    }
    (package_dir / f"{strain_id}_Project_Memory_Snapshot.json").write_text(
        json.dumps(_alias_stub, indent=2), encoding="utf-8"
    )

    # B-9/F-10: emit gene-level deep_data.json + gene_data.json (gold mode only),
    # before the seal so they're tracked and before gold figures which read them.
    _emit_deep_data(package_dir, strain_id, mode, issues=issues)

    # Auto-emit single-strain gold figures (gold mode only; non-blocking).
    _emit_gold_figures(package_dir, strain_id, mode)

    # A-05 (WAC/DSM audit): the --brief none step writes NO_FIGURES_RENDERED.md EARLY, before the
    # collection/gold figure paths run. Nothing cleared it, so a sealed package could carry the
    # "no figures" marker beside rendered PNGs/SVGs (observed on WAC-01375: 21 PNG + 5 SVG present,
    # marker still there). Reconcile now that every figure step has run: if figures exist, the marker
    # is stale — remove it so the package state is not self-contradictory.
    with _contextlib.suppress(Exception):
        _marker = package_dir / "NO_FIGURES_RENDERED.md"
        if _marker.exists():
            _figdirs = ("figures", "gold_figures", "locus_maps", "smoke_figures")
            _rendered = any(
                (package_dir / _d).is_dir()
                and any(p.suffix.lower() in (".png", ".svg") for p in (package_dir / _d).rglob("*"))
                for _d in _figdirs
            )
            if _rendered:
                _marker.unlink()

    # v9.7.277: bake the cross-strain cohort-source CSVs into package/cohort_source/ so the
    # sealed package is standalone/portable for cohort assembly (gold mode only; non-blocking).
    _emit_cohort_sources(package_dir, strain_id, mode, input_zip, issues=issues)

    # Create a provisional package inventory so validation can check checksums.
    # A final inventory is written again after gate/receipt files are added.
    write_manifest(package_dir)

    # Write validation outputs before the final manifest/checksum seal so no
    # tracked gate files appear as untracked extras inside the ZIP.
    _stage("validating package")
    validate_result = validate_package(package_dir)
    _phase_receipt(package_dir, "validator", "END",
                   validator_status=validate_result.get("status"),
                   file_presence=validate_result.get("file_presence"),
                   rggmci_gate=validate_result.get("rggmci_gate"))
    (package_dir / "gate_validation.json").write_text(
        json.dumps(validate_result, indent=2), encoding="utf-8"
    )
    (package_dir / "gold_mode_receipt.json").write_text(
        json.dumps({
            "strain_id": strain_id,
            "mode": mode,
            "status": validate_result.get("status"),
            "gold_completeness": validate_result.get("gold_completeness"),
            "depth_floor_breakdown": validate_result.get("depth_floor_breakdown"),
            "note": validate_result.get("gold_note", "Non-gold run or no gold-specific gate."),
        }, indent=2),
        encoding="utf-8",
    )

    # Refresh the user-visible checklist after manifest/gate/checksum files exist,
    # then regenerate the final manifest and checksums so the checklist itself is tracked.
    write_output_checklist(run, package_dir)

    # audit W4/W14/W16/W30: loud single entrypoint (written before the final manifest/zip so it ships in-package)
    _write_start_here(package_dir, strain_id, mode, validate_result["status"], raw, interior, edge, fc,
                      corrected_bgc_count(interior, edge, fc), assembly_tier(interior_pct),
                      issues=issues)

    # Final package manifest also writes checksums_sha256.txt.
    # v9.7.81: gene-by-gene table for top Mode B leads
    _phase_receipt(package_dir, "gene_by_gene", "START")
    try:
        _gbg_top_n = 10
        _gbg_result = build_gene_by_gene_table(package_dir, top_n=_gbg_top_n, strain_id=strain_id)
        _stage(f"gene-by-gene table: {_gbg_result['row_count']} rows, "
               f"{_gbg_result['bgcs_covered']} BGCs, GBK={_gbg_result['has_gbk_data']}")
        _phase_receipt(package_dir, "gene_by_gene", "END",
                       row_count=_gbg_result["row_count"],
                       bgcs_covered=_gbg_result["bgcs_covered"],
                       csv=_gbg_result["csv_path"],
                       xlsx=_gbg_result["xlsx_path"])
    except Exception as _gbg_err:
        issues.append(f"[WARN] gene-by-gene table skipped: {_gbg_err}")
        _phase_receipt(package_dir, "gene_by_gene", "ERROR", reason=str(_gbg_err))

    # v9.7.93: uniform all-BGC gene-by-gene coverage (every BGC, not just top leads) —
    # makes gold's uniform full Mode B visible at the artifact level.
    _phase_receipt(package_dir, "gene_by_gene_all", "START")
    try:
        _gbga_result = build_gene_by_gene_table(package_dir, strain_id=strain_id, scope="all_bgcs")
        _stage(f"gene-by-gene (all BGCs): {_gbga_result['row_count']} rows, "
               f"{_gbga_result['bgcs_covered']} BGCs")
        _phase_receipt(package_dir, "gene_by_gene_all", "END",
                       row_count=_gbga_result["row_count"],
                       bgcs_covered=_gbga_result["bgcs_covered"],
                       csv=_gbga_result["csv_path"],
                       xlsx=_gbga_result["xlsx_path"])
    except Exception as _gbga_err:
        issues.append(f"[WARN] gene-by-gene all-BGCs table skipped: {_gbga_err}")
        _phase_receipt(package_dir, "gene_by_gene_all", "ERROR", reason=str(_gbga_err))

    # v9.7.191: seal-time independent CDS recount sidecar (AS-XXX upstream-omission hardening).
    # Reads region GBKs from the input zip (a different code path than the CSV above), so
    # guide_quality_gate can catch genes silently dropped upstream. Best-effort; never blocks a run.
    try:
        from .gene_by_gene import write_gene_count_crosscheck
        _xc = write_gene_count_crosscheck(package_dir, input_zip=input_zip)
        _stage(f"gene-count cross-check: {len(_xc['per_bgc'])} BGCs -> gene_count_crosscheck.json")
    except Exception as _xc_err:
        issues.append(f"[WARN] gene-count cross-check sidecar skipped: {_xc_err}")

    # AUDIT_371: Two_Pathway_Flag patch-in-place, mirroring the Two_Model_Flag mechanism
    # immediately below (same file-ordering hazard, same fix shape). two_pathway_by_bgc() is also
    # called inside _write_package() (called earlier, at line ~1584) -- but _write_package runs
    # BEFORE *_gene_by_gene_all_bgcs.csv is written here (just above), so that first call always
    # sees no table and _two_pathway is always {} at write time: every Two_Pathway_Flag cell comes
    # out blank in every normal run. Confirmed empirically against 2,807 sealed triage boards /
    # 147,859 rows on disk: only 11 non-blank rows, all traced to 2 strains in test-harness re-run
    # directories that happened to already have a *_gene_by_gene_all_bgcs.csv sitting in
    # package_dir from a PRIOR invocation -- i.e. the only times this ever "worked" it was reading
    # stale data, not this run's data. tools/bgc_reconcile.py consumes this column as a
    # cross-channel contradiction signal for Mode-B card authors, so this has been a silently-dead
    # safety check with real downstream reach. Recomputed here now that the real gene table
    # exists, and patched into the already-written triage board -- unconditionally per BGC (not
    # only when non-empty), so a stale leftover value from a prior run in the same package_dir is
    # also correctly overwritten by this run's own computation, not left in place.
    _phase_receipt(package_dir, "two_pathway_patch", "START")
    try:
        from .two_pathway import (two_pathway_by_bgc as _two_pathway_by_bgc,
                                  two_pathway_flag_cell as _two_pathway_flag_cell)
        _two_pathway_patched = _two_pathway_by_bgc(package_dir)
        _triage_csv_tp = package_dir / f"{strain_id}_4_triage_board.csv"
        _tp_flagged = 0
        if _two_pathway_patched and _triage_csv_tp.exists():
            import csv as _csv_tp
            with open(_triage_csv_tp, newline="", encoding="utf-8") as _tf:
                _reader = _csv_tp.DictReader(_tf)
                _rows = list(_reader)
                _fields = list(_reader.fieldnames or [])
            if "Two_Pathway_Flag" in _fields:
                for _r in _rows:
                    _bid = _r.get("BGC_ID") or _r.get("bgc_id") or ""
                    _verdict = _two_pathway_patched.get(_bid)
                    _cell = _two_pathway_flag_cell(_verdict)
                    _r["Two_Pathway_Flag"] = _cell
                    if _cell:
                        _tp_flagged += 1
                with open(_triage_csv_tp, "w", newline="", encoding="utf-8") as _tf:
                    _w = _SafeDictWriter(_tf, fieldnames=_fields, extrasaction="ignore")
                    _w.writeheader()
                    _w.writerows(_rows)
        _phase_receipt(package_dir, "two_pathway_patch", "END",
                       bgcs_evaluated=len(_two_pathway_patched), flagged_count=_tp_flagged)
    except Exception as _tp_err:
        issues.append(f"[WARN] two-pathway patch skipped: {_tp_err}")
        _phase_receipt(package_dir, "two_pathway_patch", "ERROR", reason=str(_tp_err))

    # v9.7.129: BGC two-model decomposition after all-BGC gene table exists.
    # This is deliberately post-gene_by_gene_all: the fitter needs real per-CDS
    # sec_met_domain rows. The initial triage board is written earlier, so this
    # block writes the 4B CSV and patches the Two_Model_Flag column in place
    # before the final manifest/checksum seal.
    _phase_receipt(package_dir, "bgc_two_model", "START")
    from .exact_identity import ExactLocusIdentityError
    try:
        _gene_csv = next(package_dir.glob("*_gene_by_gene_all_bgcs.csv"), None)
        _decomp = run_bgc_decomp(run.bgcs, _gene_csv, kcb_dir=_cb_dir, strain=strain_id)
        if _decomp.get("summary_line"):
            _stage(_decomp["summary_line"])
        # SCHEMA-P01: a two-model pass that never saw the gene table is not a clean negative — surface it.
        if _decomp.get("gene_table_status", "OK") != "OK":
            issues.append(
                f"[WARN] two-model decomposition ran without gene data "
                f"(gene_table_status={_decomp.get('gene_table_status')}); TWO_MODEL results are not "
                f"a clean negative — verify {strain_id}_gene_by_gene_all_bgcs.csv was written before this stage.")

        if _decomp and _decomp.get("rows"):
            _dm_path = package_dir / f"{strain_id}_4B_two_model_decomp.csv"
            _dm_cols = list(TWO_MODEL_DECOMP_HEADERS)
            import csv as _csv_mod
            with open(_dm_path, "w", newline="", encoding="utf-8") as _fh:
                _w = _SafeDictWriter(_fh, fieldnames=_dm_cols, extrasaction="ignore")
                _w.writeheader()
                _w.writerows(_decomp["rows"])

            # Patch the already-written triage board column in place.
            _triage_csv = package_dir / f"{strain_id}_4_triage_board.csv"
            if _triage_csv.exists():
                with open(_triage_csv, newline="", encoding="utf-8") as _tf:
                    _reader = _csv_mod.DictReader(_tf)
                    _rows = list(_reader)
                    _fields = list(_reader.fieldnames or [])
                if "Two_Model_Flag" not in _fields:
                    try:
                        _idx = _fields.index("Two_Pathway_Flag") + 1
                    except ValueError:
                        _idx = len(_fields)
                    _fields.insert(_idx, "Two_Model_Flag")
                for _r in _rows:
                    _bid = _r.get("BGC_ID") or _r.get("bgc_id") or ""
                    _r["Two_Model_Flag"] = _two_model_flag_cell(_bid, _decomp)
                with open(_triage_csv, "w", newline="", encoding="utf-8") as _tf:
                    _w = _SafeDictWriter(_tf, fieldnames=_fields, extrasaction="ignore")
                    _w.writeheader()
                    _w.writerows(_rows)

        _phase_receipt(package_dir, "bgc_two_model", "END",
                       strong_count=_decomp.get("strong_count", 0),
                       candidate_count=_decomp.get("candidate_count", 0),
                       row_count=len(_decomp.get("rows", [])))
    except ExactLocusIdentityError:
        (package_dir / f"{strain_id}_4B_two_model_decomp.csv").unlink(missing_ok=True)
        issues.append(
            "EXACT_LOCUS_IDENTITY_UNAVAILABLE: two-model sidecar omitted; "
            "complete source locus identity is required."
        )
        _phase_receipt(package_dir, "bgc_two_model", "SKIP",
                       reason="EXACT_LOCUS_IDENTITY_UNAVAILABLE")
    except Exception as _de:
        issues.append(f"[WARN] BGC two-model decomposition skipped: {_de}")
        _phase_receipt(package_dir, "bgc_two_model", "ERROR", reason=str(_de))

    # v9.7.81: manifest_short.json — compact LLM-consumable summary
    # F1/F2 fix: triage_records was undefined here (triage lives inside _write_package).
    # Read the already-written triage_board.csv instead — deterministic, no re-computation.
    try:
        import csv as _csv_ms
        from .dedup_and_guard import resolve_release as _resolve_release_ms
        _triage_csv = package_dir / f"{strain_id}_4_triage_board.csv"
        _triage_rows = []
        if _triage_csv.exists():
            with open(_triage_csv, newline="", encoding="utf-8") as _tf:
                _triage_rows = list(_csv_ms.DictReader(_tf))
        _eligible = [r for r in _triage_rows
                     if not r.get("Primary_metab_flag") and not r.get("Standing_rule")]
        def _fscore(r, col):
            try: return float(r.get(col) or 0)
            except (ValueError, TypeError): return 0.0
        _ms_ab = sorted(_eligible, key=lambda r: _fscore(r, "AB_auto"), reverse=True)[:3]
        _ms_af = sorted(_eligible, key=lambda r: _fscore(r, "AF_auto"), reverse=True)[:3]
        _ms = {
            "strain_id": strain_id,
            "mamey_version": __version__,
            # v9.7.87 9.7.87-B: surface the release class on the compact dashboard. The full
            # manifest/bgc_data/intake all carry it, but manifest_short — the artifact whose
            # whole purpose is fast triage without loading the 5.7 MB manifest — was silent on
            # it. For a hard guard the compact surface must be the MOST explicit about release.
            "release": (next((b.release for b in run.bgcs if getattr(b, "release", None)), None)
                        or _resolve_release_ms(strain_id, release)[0]),
            "status": validate_result.get("status"),
            "assembly_tier": assembly_tier(interior_pct),
            "raw_bgcs": raw,
            "corrected_bgcs": corrected_bgc_count(interior, edge, fc),
            "interior_pct": round(interior_pct, 1) if interior_pct is not None else None,
            "top_3_ab": [{"bgc_id": r.get("BGC_ID",""), "contig": r.get("Contig",""),
                          "ab_score": _fscore(r, "AB_auto")} for r in _ms_ab],
            "top_3_af": [{"bgc_id": r.get("BGC_ID",""), "contig": r.get("Contig",""),
                          "af_score": _fscore(r, "AF_auto")} for r in _ms_af],
            "phase_receipts_path": "run_phase_receipts.jsonl",
            "timing_json": f"{strain_id}_timing_breakdown.json",
            "gene_by_gene_csv": f"{strain_id}_gene_by_gene_top_leads.csv",
            "gene_by_gene_all_bgcs_csv": f"{strain_id}_gene_by_gene_all_bgcs.csv",
            # v9.7.88: the normalized sealed gene context — the durable per-CDS source for true
            # gene-by-gene Mode B walkthroughs (one JSON line per BGC: locus_tag, coords, strand,
            # aa_length, sec_met_domains, tta_codons). Read via mamey.gene_context.load_gene_context.
            "gene_context_jsonl": f"{strain_id}_gene_context.jsonl",
        }
        (package_dir / "manifest_short.json").write_text(
            json.dumps(_ms, indent=2), encoding="utf-8"
        )
    except Exception as _ms_err:
        issues.append(f"[WARN] manifest_short.json skipped: {_ms_err}")

    # C1: OPEN_ME_FIRST.html — collaborator-facing package entry point
    try:
        from .package_addons import write_open_me_first as _womf
        _womf(package_dir)
        _stage("OPEN_ME_FIRST.html written")
    except Exception as _omf_err:
        issues.append(f"[WARN] OPEN_ME_FIRST.html skipped: {_omf_err}")

    # v9.7.81: write timing breakdown files BEFORE manifest/checksum so they are sealed
    try:
        _timer.write(package_dir,
                     raw_bgcs=raw,
                     corrected_bgcs=corrected_bgc_count(interior, edge, fc))
    except Exception as _t_err:
        issues.append(f"[WARN] timing breakdown skipped: {_t_err}")

    # v9.7.136: citation-compact output budget.  Emit the citation ledger and
    # compact Markdown report supplements before final manifest/checksum/ZIP so
    # they are sealed into the package.  Scoring and triage are unchanged.
    _phase_citation_compact(package_dir, strain_id, token_budget, brief, heartbeat_seconds, issues)

    _phase_receipt(package_dir, "workbook", "END",
                   per_strain=_per_wb_status.get("state"),
                   master=_master_wb_status.get("state"))

    # SEAL-04: the mandatory compiled report and PACKAGE_MAP.json are emitted HERE, just
    # BEFORE the seal, so they are inside the sealed ZIP and its checksum set. They were
    # previously written after the seal and were therefore absent from the ZIP. They are
    # still emitted best-effort (try/except) and never block the seal; only the post-seal
    # brief figures remain deliberately outside the core ZIP.
    # v9.7.157 (mandatory-deliverable gate): the design promise is that a user need not know
    # which deliverables to ask for — a completed run must hand them something human-readable.
    # Prior behaviour: smoke is triage-only and --capped-session forces --brief none, so a
    # correct run could seal MAMEY_COMPLETE and emit ZERO user-facing deliverables (only the
    # sealed package CSV/JSON). output_checklist.py already marks a compiled report REQUIRED;
    # this gate honours that by AUTO-EMITTING the minimum viable deterministic deliverable
    # (the compiled report) from the package, in every mode, if it is not already present.
    # Non-blocking: a failure here costs the convenience report, never the sealed core.
    # Sapote narrative slots remain honestly marked "to fill".
    try:
        _report_path = package_dir / f"{strain_id}_compiled_report.md"
        _report_withheld_claim_safety = False  # LEAK-4: set when an overclaiming report is withheld
        if not _report_path.exists():
            _stage("auto-emitting compiled report (mandatory-deliverable gate)")
            from .compile_report import build_report as _build_report
            # generate_figures=False keeps the gate fast and non-blocking on capped sessions;
            # the deterministic narrative + triage/decision tables are what the user needs handed to them.
            _md = _build_report(str(package_dir), generate_figures=False)
            # LEAK-4 (CLAUDE_409_claimsafety_coverage): lint the report body BEFORE it is written.
            # Prior behaviour wrote the report first, then appended a soft `[WARN] claim_safety` to
            # `issues` and SHIPPED the overclaiming report anyway -- the flagship deliverable of nearly
            # every run kept a warn-and-ship default here, even though the compile-report COMMAND
            # (CLAUDE_409_narrative_gates) now REFUSES by default (rc 3, writes nothing). This path is
            # documented as "never block the seal", and that invariant is preserved: the deterministic
            # core still seals. What changes is that we no longer SHIP an overclaiming report as a
            # clean deliverable -- on a finding we WITHHOLD it (write nothing, mirroring the command
            # path) and raise a loud TYPED refusal into `issues`, which flips the terminal status to
            # MAMEY_COMPLETE_WITH_ISSUES (the documented non-zero advisory). See PATCH_CARD.md for the
            # conservative-choice rationale (seal preserved; report refused, not silently shipped).
            from .claim_safety_gate import lint_text as _cs_lint_text
            _cs_findings = _cs_lint_text(_md)
            if _cs_findings:
                _report_withheld_claim_safety = True
                issues.append(
                    f"[CLAIM-SAFETY REFUSAL] auto-emitted compiled report WITHHELD: "
                    f"{len(_cs_findings)} possible overclaim(s) in the report body "
                    f"({_report_path.name}): " + "; ".join(_cs_findings)
                    + f" -- revise to class-level capacity language and run "
                      "`mamey compile-report .` from this package directory "
                      "(blocks by default) to regenerate."
                )
            else:
                _report_path.write_text(_md, encoding="utf-8")
        if _report_path.exists():
            emit(f"  DELIVERABLE (auto-emitted): {_report_path.name}")
        elif not _report_withheld_claim_safety:
            issues.append("[WARN] mandatory-deliverable gate: compiled report not produced; "
                          "run `mamey compile-report .` from this package directory to generate it")
    except Exception as _dl_err:
        issues.append(f"[WARN] mandatory-deliverable gate skipped (non-fatal): {_dl_err}; "
                      "run `mamey compile-report .` from this package directory to generate the report")

    # PACKAGE_MAP.json gate (non-blocking): the semantic file->purpose->section
    # map the flat manifest["files"] checksum inventory lacks. Lets an author (and the read-gate)
    # know which artifacts to open before writing each Mode B section, instead of authoring a
    # section off a summary while the deep evidence sits unread. Mirrors the mandatory-deliverable
    # gate: never blocks, never un-seals; degrades to a [WARN] naming the manual command.
    try:
        _pmap_path = package_dir / "PACKAGE_MAP.json"
        if not _pmap_path.exists():
            _stage("writing PACKAGE_MAP.json (package discovery map)")
            from .package_map import write_package_map as _write_pmap
            _write_pmap(package_dir)  # uses bundled default spec
        if _pmap_path.exists():
            emit(f"  DELIVERABLE (auto-emitted): {_pmap_path.name}")
        else:
            issues.append("[WARN] PACKAGE_MAP gate: map not produced; "
                          f"run `python -m mamey.package_map --package {package_dir}` to generate it")
    except Exception as _pm_err:
        issues.append(f"[WARN] PACKAGE_MAP gate skipped (non-fatal): {_pm_err}; "
                      f"run `python -m mamey.package_map --package {package_dir}` to generate it")

    # This is the authoritative pre-seal stamp. Every issue-producing phase that ships inside
    # the core ZIP has completed, so manifest.json and commit_receipt.json cannot miss a late
    # mandatory-deliverable or package-map warning.
    _preseal_validator_status = validate_result["status"]
    _preseal_terminal_status = _stamp_terminal_status(
        package_dir, validator_status=_preseal_validator_status, issues=issues)
    _phase_receipt(package_dir, "terminal_status_preseal", "END",
                   terminal_status=_preseal_terminal_status, issue_count=len(issues),
                   validator_status=_preseal_validator_status)

    zip_path, status = _phase_package_seal(
        package_dir, run_dir, strain_id, brief, heartbeat_seconds, validate_result, issues,
        antismash_profile=antismash_profile)

    # v9.7.88 Finding L (Option A): the deterministic core (manifest/gate/checksums/ZIP) is now
    # sealed above. Render the brief HERE, as a separate post-seal phase that cannot block or
    # un-seal the core. Its figures are supplementary artifacts in the package DIRECTORY but live
    # outside the core ZIP/checksum set (the ZIP was already written). This resolves Finding F too:
    # the brief is genuinely non-blocking now — a render hang costs figures, never the sealed core.
    if MAMEY_SEAL_FIRST and brief != "none":
        _stage("rendering strain brief (post-seal; supplementary)")
        brief_res = _render_brief_nonblocking(package_dir, brief, issues.append)
        if brief_res.get("status") == "COMPLETE":
            emit(f"  Strain brief (post-seal): {brief_res['tier']} ({len(brief_res['files'])} files)")
        elif brief_res.get("status") == "SKIPPED":
            emit(f"  Strain brief (post-seal): SKIPPED ({brief_res.get('reason','')}) — core already sealed")
        # mark the post-seal figures as supplementary (not in the core checksum set)
        try:
            (package_dir / "FIGURES_SUPPLEMENTARY.md").write_text(
                "# Figures are supplementary (post-seal)\n\n"
                "v9.7.88 seal-first (Finding L, Option A): the deterministic core package "
                "(manifest.json, gate_validation.json, checksums_sha256.txt, and the Complete "
                "Package ZIP) was sealed BEFORE these figures were rendered. The figures in this "
                "directory are therefore supplementary and are NOT inside the core ZIP or its "
                "checksum set. The reproducible scientific artifact does not depend on them.\n",
                encoding="utf-8")
        except Exception as _supp_exc:
            _supp_issue = (
                "FIGURES_SUPPLEMENTARY_MARKER_WRITE_FAILED: "
                f"{type(_supp_exc).__name__}: {_supp_exc}"
            )
            issues.append(_supp_issue)
            _phase_receipt(
                package_dir, "figures_supplementary_marker", "ERROR",
                reason=_supp_issue
            )

    # SEAL-04: the mandatory compiled report and PACKAGE_MAP.json auto-emit that previously
    # lived here (post-seal, absent from the sealed ZIP) now runs just BEFORE
    # _phase_package_seal so they are inside the sealed ZIP + checksum set.

    # v9.7.149c (W2 Part B): smoke-mode figure stub. Three CSV-driven figures
    # (BGC ranking by length, class composition, assembly-tier composition)
    # that require only the triage + inventory CSVs — which exist in every
    # mode including smoke. Non-blocking: failures here never affect the run
    # status.
    try:
        from . import figures_smoke as _figures_smoke
        _smoke_res = _figures_smoke.generate(package_dir)
        if _smoke_res.get("figures"):
            emit(f"  smoke_figures: {_smoke_res['figures']} png(s) "
                  f"-> {_smoke_res['out']}")
        elif _smoke_res.get("skipped_reason"):
            emit(f"  smoke_figures: skipped ({_smoke_res['skipped_reason']})")
    except Exception as _e:
        emit(f"  smoke_figures: non-blocking error ({type(_e).__name__})",
              file=_sys.stderr, flush=True)

    # Auto-emit the Figure Factory as an expected post-seal deliverable (v9.7.409).
    # Same contract as the cohort-figures bridge: extraction-only and best-effort, it
    # renders the manifest-governed aggregate-evidence figures into
    # <package>/figure_factory when a Figure Factory Next config is present, and
    # returns a typed skip (never a crash) when its config or declared inputs are
    # absent. The sealed core is already written above and is untouched.
    _auto_emit_figure_factory(package_dir, source_dir=package_dir)

    # v9.7.409 (CLAUDE post_seal_checksums lane): fold the checksum-exempt post-seal deliverables into a
    # tracked post_seal_checksums.txt so a later `validate` catches injection/swap/delete there. Non-blocking.
    try:
        _psc = write_post_seal_checksums(package_dir)
        _stage(f"post-seal integrity manifest: {_psc['n_files']} files -> post_seal_checksums.txt")
        _phase_receipt(package_dir, "post_seal_checksums", "END", n_files=_psc["n_files"])
    except Exception as _psc_err:
        issues.append(f"[WARN] post_seal_checksums skipped: {_psc_err}")
        _phase_receipt(package_dir, "post_seal_checksums", "ERROR", reason=str(_psc_err))

    # Post-seal integrity is the last issue-producing phase. Only now render the issue list,
    # compute the returned status, and refresh the mutable external receipts. A failure here
    # does not rewrite the already sealed core ZIP; it marks the external package directory
    # MAMEY_COMPLETE_WITH_ISSUES and preserves the exact late issue for audit and recovery.
    if issues:
        for issue in issues:
            emit(f"  [ISSUE] {issue}")

    # MMW-1: WORKBOOK_STATUS — always printed, never silent
    emit(f"  WORKBOOK_STATUS:", f"    per_strain_workbook: {_per_wb_status.get('state', 'UNKNOWN')}", sep="\n")
    if _per_wb_status.get('state') == 'PRODUCED':
        emit(f"      path: {_per_wb_status['path']}", f"      checksum: {_per_wb_status['checksum_sha256_head16']}", sep="\n")
    elif _per_wb_status.get('reason'):
        emit(f"      reason: {_per_wb_status['reason']}")
    emit(f"    cumulative_master_workbook: {_master_wb_status.get('state', 'UNKNOWN')}")
    if _master_wb_status.get('state') == 'PRODUCED':
        emit(f"      path: {_master_wb_status['path']}", f"      checksum: {_master_wb_status['checksum_sha256_head16']}", f"      sheets: {len(_master_wb_status.get('sheets', []))}", sep="\n")
    elif _master_wb_status.get('reason'):
        emit(f"      reason: {_master_wb_status['reason']}")
        if _master_wb_status.get('recovery_command'):
            emit(f"      recovery: {_master_wb_status['recovery_command']}")

    # B11: canonical machine-readable terminal status codes
    machine_status = _terminal_mamey_status(status, issues)
    emit(f"  MAMEY_STATUS: {machine_status}")
    _stage(f"terminal status: {machine_status}")
    _phase_receipt(package_dir, "terminal", machine_status,
                   validator_status=status, issue_count=len(issues),
                   core_zip_unchanged=True)
    _stamp_terminal_status(package_dir, validator_status=status, issues=issues)

    return {
        "strain_id": strain_id,
        "status": machine_status,
        "validator_status": status,
        "raw_bgcs": raw,
        "corrected_bgcs": corrected_bgc_count(interior, edge, fc),
        "assembly_tier": assembly_tier(interior_pct),
        "package_zip": str(zip_path),
        "master_updated": bool(master_path and _master_wb_status.get("state") == "PRODUCED"),
        "workbook_status": {
            "per_strain": _per_wb_status,
            "cumulative_master": _master_wb_status,
        },
        "token_budget": token_budget,
        "issues": issues,
    }


def _auto_emit_cohort_figures_extended(results, outdir, logger=None):
    """Auto-emit the extended cross-strain figure suite for a multi-strain batch (v9.7.410).

    ``mamey/cohort_figures_extended.py`` documents itself as the auto-emit companion to
    ``cohort_figures.generate`` (fused there in v9.7.279), but through v9.7.409 it was only
    reached from the manual ``cohort-figures`` subcommand: the ``run_batch`` multi-strain
    block called ``build_cohort_figures`` and the gold F-series and nothing else. This is
    the missing bridge. Same contract as the sibling bridges: extraction-only, best-effort,
    never blocks or un-seals a package. It renders the 11 extended figures (census, PKS
    bars, size-vs-richness, locus map, archetype, KCB novelty, CCTT triggers, boundary,
    domain co-occurrence, resistance, TTA/bldA) into ``<outdir>/cohort_figures_extended``
    from the per-strain package CSVs alone and prints one line
    ``[cohort-figures-extended] N figures -> <dir>``.

    Strains are taken from ``results`` in batch order and restricted to those whose
    package carries ``<sid>_2_inventory.csv`` (the suite's only required input), so the
    strain list is deterministic and never wider than the batch itself. Fewer than two
    such strains, or any failure, returns a *typed skip* dict rather than raising.

    Returns ``{"status": "PASS", "figure_count": N, "out": <dir>, ...}`` on success, else
    ``{"status": "SKIPPED_...", "figure_count": 0}``.
    """
    if logger is None:
        logger = emit
    log = logger or (lambda *a, **k: None)
    try:
        root = Path(outdir)
        sids = []
        for r in results or []:
            sid = str((r or {}).get("strain_id", "") or "")
            if sid and (root / sid / "package" / f"{sid}_2_inventory.csv").is_file():
                sids.append(sid)
        if len(sids) < 2:
            log(f"[cohort-figures-extended] SKIPPED — {len(sids)} of {len(results or [])} "
                f"strain(s) carry an inventory (needs >= 2)")
            return {"status": "SKIPPED_INSUFFICIENT_INVENTORIES", "figure_count": 0}
        from .cohort_figures_extended import generate_extended
        out_dir = root / "cohort_figures_extended"
        ext = generate_extended(runs_dir=str(root), out=str(out_dir), strains=sids)
        nfig = int(ext.get("figures", 0) or 0)
        for _e in ext.get("errors", []):
            log(f"  [cohort-figures-extended WARN] {_e}")
        # Same caption sheet the manual ``cohort-figures`` subcommand ships alongside the suite.
        _cap = Path(__file__).resolve().parent.parent / "docs" / "COHORT_FIGURE_CAPTIONS.md"
        if nfig and _cap.is_file():
            import shutil as _sh
            _sh.copy(_cap, out_dir / "COHORT_FIGURE_CAPTIONS.md")
        log(f"[cohort-figures-extended] {nfig} figures -> {out_dir}")
        status = "PASS" if nfig else "SKIPPED_NO_FIGURES"
        return {"status": status, "figure_count": nfig, "out": str(out_dir),
                "strains": list(sids), "errors": list(ext.get("errors", []))}
    except Exception as _cx_exc:
        log(f"[cohort-figures-extended] SKIPPED ({type(_cx_exc).__name__}: {_cx_exc})")
        return {"status": f"SKIPPED_{type(_cx_exc).__name__}", "figure_count": 0}


def _auto_emit_figure_factory(target_dir, logger=None, source_dir=None):
    """Auto-run the Figure Factory as an expected post-seal deliverable (v9.7.409).

    Mirrors the ``build_cohort_figures`` bridge: extraction-only, best-effort, and it
    NEVER blocks or un-seals a package. It discovers a Figure Factory Next config,
    renders the manifest-governed aggregate-evidence figure set into
    ``<target_dir>/figure_factory``, and prints one line
    ``[figure-factory] N figures -> <dir>``. When no config is present, or the config
    or its declared inputs cannot be honoured, it returns a *typed skip* dict rather
    than raising — so a run without a Figure Factory config is a silent no-op by design.

    target_dir : run/package/cohort output directory to receive the figure set.
    source_dir : optional extra directory searched for the config (e.g. a sealed
                 package dir when target_dir is the run root).
    Returns the build receipt (with ``figure_count`` added) on success, else a small
    typed status dict ``{"status": "SKIPPED_...", "figure_count": 0}``.
    """
    if logger is None:  # v9.7.409: resolve the package emitter here (no injected callable at call sites)
        logger = emit
    log = logger or (lambda *a, **k: None)
    try:
        import os as _os
        import tempfile as _tempfile

        target_dir = Path(target_dir)
        config_name = "figure_factory_next_config.json"
        candidates = []
        env_cfg = _os.environ.get("MAMEY_FIGURE_FACTORY_CONFIG", "").strip()
        if env_cfg:
            candidates.append(Path(env_cfg).expanduser())
        if source_dir:
            candidates.append(Path(source_dir) / config_name)
        candidates.append(target_dir / config_name)
        config_path = next((c for c in candidates if c.is_file()), None)
        if config_path is None:
            # Feature not in use for this run: silent, typed no-op.
            return {"status": "SKIPPED_NO_CONFIG", "figure_count": 0}

        config = json.loads(config_path.read_text(encoding="utf-8"))
        # Emit into a deterministic, conventional subdir of the run/cohort output.
        out_dir = (target_dir / "figure_factory").resolve()
        if out_dir.exists():
            # Deterministic re-emit: replace only our own conventional subdir.
            shutil.rmtree(out_dir, ignore_errors=True)
        config["output_dir"] = str(out_dir)
        # Resolve a relative external_data_root against the config's own directory so
        # the config is portable regardless of where target_dir sits.
        root = config.get("external_data_root")
        if root and not Path(root).expanduser().is_absolute():
            config["external_data_root"] = str((config_path.parent / root).resolve())

        target_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_cfg = _tempfile.mkstemp(
            prefix=".figure_factory_cfg.", suffix=".json", dir=str(target_dir))
        _os.close(fd)
        try:
            Path(tmp_cfg).write_text(
                json.dumps(config, sort_keys=True) + "\n", encoding="utf-8")
            from .figure_factory_next import build as _ff_build
            receipt = _ff_build(Path(tmp_cfg))
        finally:
            with _suppress(OSError):  # v9.7.409: best-effort cleanup, intent explicit (was except: pass)
                _os.unlink(tmp_cfg)

        outputs = receipt.get("outputs", []) if isinstance(receipt, dict) else []
        nfig = sum(
            1 for o in outputs
            if str(o.get("logical_locator", "")).lower().endswith((".svg", ".png")))
        log(f"[figure-factory] {nfig} figures -> {out_dir}")
        if isinstance(receipt, dict):
            receipt.setdefault("figure_count", nfig)
            return receipt
        return {"status": "PASS", "figure_count": nfig}
    except Exception as _ff_exc:
        # Fail-closed: a missing/invalid config or absent inputs degrades to a typed
        # skip, never a crash. Announced (unlike the no-config no-op) because a config
        # was found but could not be honoured.
        log(f"[figure-factory] SKIPPED ({type(_ff_exc).__name__}: {_ff_exc})")
        return {"status": f"SKIPPED_{type(_ff_exc).__name__}", "figure_count": 0}


def _package_source_locator_evidence(run: MameyRun, package_dir: Path) -> None:
    """Copy concrete knownclusterblast source files cited by provenance rows.

    Mutates bgc.source_kcb_file so packaged CSV/workbook locators resolve
    from inside the Complete_Package rather than only from the original ZIP.
    """
    cited = [b for b in run.bgcs
             if getattr(b, "closest_product_provenance", "") == "MIBIG_REFERENCE_LINE"
             and getattr(b, "source_kcb_file", "UNRESOLVED") not in ("", "UNRESOLVED")]
    if not cited:
        return
    evidence_root = package_dir / "source_locator_evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    import zipfile
    with zipfile.ZipFile(run.context.input_zip) as zf:
        names = set(regular_file_names(zf))
        for bgc in cited:
            original = str(getattr(bgc, "source_kcb_file"))
            if original not in names:
                bgc.needs_manual_kcb_check = "yes"
                bgc.parse_confidence = "LOW"
                bgc.product_claim_ceiling = "locator unresolved in package; do not use product name"
                continue
            dest = evidence_root / original
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(original) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            packaged = str(dest.relative_to(package_dir))
            old_locator = getattr(bgc, "source_kcb_locator", "")
            bgc.source_kcb_file = packaged
            bgc.source_kcb_locator = old_locator.replace(original, packaged) if old_locator else old_locator

def _write_axis_lead_boards(package_dir, strain, triage, bgc_by_id, issues):
    """Write both optional boards only after complete native identity admission."""
    from .exact_identity import ExactLocusIdentityError
    from .lead_board import axis_lead_board_rows, AXIS_LEAD_BOARD_HEADERS

    targets = [(axis, package_dir / f"{strain}_4c_{axis.upper()}_lead_board.csv")
               for axis in ("ab", "af")]
    try:
        rows_by_axis = {
            axis: axis_lead_board_rows(triage, bgc_by_id, axis, strain=strain)
            for axis, _ in targets
        }
    except ExactLocusIdentityError:
        # Retire stale generated boards as well: an earlier successful run must
        # not masquerade as this run's unavailable auxiliary output.
        for _, path in targets:
            path.unlink(missing_ok=True)
        issues.append(
            "EXACT_LOCUS_IDENTITY_UNAVAILABLE: axis lead boards omitted; "
            "complete source locus identity is required."
        )
        _phase_receipt(package_dir, "axis_lead_boards", "SKIP",
                       reason="EXACT_LOCUS_IDENTITY_UNAVAILABLE")
        return
    try:
        for axis, path in targets:
            with _atomic_open_pkg(path, "w", newline="") as handle:
                writer = _SafeWriter(handle)
                writer.writerow([("AB_score" if axis == "ab" else "AF_score") if h == "Score" else h
                                 for h in AXIS_LEAD_BOARD_HEADERS])
                writer.writerows([[row[h] for h in AXIS_LEAD_BOARD_HEADERS]
                                  for row in rows_by_axis[axis]])
    except Exception:
        # A failed paired write must not leave one fresh board beside stale data.
        # Only exact generated file targets are retired; directories are preserved.
        for _, path in targets:
            if path.is_file() or path.is_symlink():
                path.unlink()
        raise
    _phase_receipt(package_dir, "axis_lead_boards", "END")


def _write_package(run: MameyRun, package_dir: Path,
                   antismash_evidence: dict,
                   antismash_profile: str = "auto") -> None:
    """Write all numbered output files to package_dir."""
    from .scoring import triage_bgcs
    from collections import Counter

    strain    = run.context.strain_id
    ss        = run.source_scans
    triage    = triage_bgcs(run.bgcs, run.source_scans.rggmci if run.source_scans else None, run.source_scans if run.source_scans else None)
    triage_by = {t.bgc_id: t for t in triage}

    # v9.7.409 (CLAUDE_409 provenance anchors): every per-BGC delivery CSV must be traceable to a
    # durable locus (BGC### is a non-portable internal id; strain + node/contig + region is the
    # durable anchor). Build a bgc_id -> {strain, assembly_locator, contig, region} crosswalk once
    # — the same four-part anchor master_workbook.py leads every Excel sheet with — and prepend it
    # to the per-gene / per-detail CSVs that historically shipped a bare `bgc_id`.
    _ANCHOR_COLS = ["strain", "assembly_locator", "contig", "region"]
    _anchor_by_id = {b.bgc_id: b for b in run.bgcs}
    def _bgc_anchor(bgc_id) -> dict:
        b = _anchor_by_id.get(bgc_id)
        if b is None:
            return {"strain": strain, "assembly_locator": "", "contig": "", "region": ""}
        return {
            "strain": strain,
            "assembly_locator": assembly_locator(b),
            "contig": (getattr(b, "node_id", "") or getattr(b, "contig", "") or ""),
            "region": (getattr(b, "antismash_region", "") or ""),
        }
    def _anchor_vals(bgc_id) -> list:
        _a = _bgc_anchor(bgc_id)
        return [_a[c] for c in _ANCHOR_COLS]

    # --- W4/W23: emit the deterministic<->judgment boundary payloads and self-audit ---
    # records.json (BGCRecord side) + verdicts.json (TriageRecord side), then diff them
    # by bgc_id. A failure here is the AS-XXX silent-omission class (or a downgrade that
    # was recorded but not honoured). Instrumentation is wrapped so it can never break a
    # package build; the receipt is written for verify_tiers/CI to gate on.
    try:
        from .serialize import write_boundary_payloads
        from .boundary_audit import audit_files
        _rec_path, _ver_path = write_boundary_payloads(package_dir, strain, run.bgcs, triage)
        _brc, _bproblems = audit_files(str(_rec_path), str(_ver_path))
        _atomic_write_manifest_text(package_dir / f"{strain}_boundary_audit.json",
            json.dumps({"ok": _brc == 0, "problems": _bproblems}, indent=2))
        if _brc != 0:
            emit(f"  [WARN] boundary audit found {len(_bproblems)} issue(s) — see {strain}_boundary_audit.json")
    except Exception as _e:  # never let boundary instrumentation break a package build
        emit(f"  [WARN] boundary audit skipped: {_e}")
    cctt_coupling = ss.cctt.get("bgc_coupling", {}) if ss else {}
    rt_per_bgc    = ss.resistance_tiers.get("per_bgc", {}) if ss else {}
    dss_per_bgc   = ss.per_bgc_dss.get("per_bgc", {}) if ss else {}
    tta_per_bgc   = ss.blda_tta.get("per_bgc", {}) if ss else {}
    qs_ids        = set(ss.qs_signals.get("qs_signal_bgc_ids", [])) if ss else set()
    napaa_ids     = set(ss.qs_signals.get("napaa_bgc_ids", [])) if ss else set()
    rggmci_pairs  = ss.rggmci.get("ranked_pairs", []) if ss else []
    rggmci_support = {}
    for p in rggmci_pairs:
        if p.get("rggmci_confidence") in {"HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"}:
            for bid in (p.get("bgc_a"), p.get("bgc_b")):
                if bid:
                    rggmci_support.setdefault(bid, []).append(p.get("pair"))

    _package_source_locator_evidence(run, package_dir)

    # 1 — intake.json
    # B-2: stamp the strain-level release into intake.json (it was present in manifest/snapshot/bgc_data but
    # absent here, so a tool reading only intake could not tell PUBLIC from PRIVATE). All BGCs carry the same
    # resolved tag; fall back to a fresh resolution if the inventory is empty.
    from .dedup_and_guard import resolve_release as _resolve_release_intake
    _strain_release = next((b.release for b in run.bgcs if getattr(b, "release", None)), None) \
        or _resolve_release_intake(run.context.strain_id, None)[0]
    intake = {
        "strain_id":       run.context.strain_id,
        "display_name":    run.context.display_name,
        "taxonomy":        run.context.taxonomy,
        "source":          run.context.source,
        # AMBER-03-2: intake is what the redaction/figure tooling reads; the host's evidence
        # strength must travel with the host, not be reconstructable only from the run command.
        "source_provenance": run.context.source_provenance,
        "release":         _strain_release,
        "antismash_version": extract_antismash_version(run.context.input_zip),
        "antismash_profile": antismash_profile,
        "assembly":        {
            "genome_bp":  run.assembly.genome_bp,
            "contigs":    run.assembly.contigs,
            "n50":        run.assembly.n50,
            "gc_pct":     run.assembly.gc_pct,
        },
        "bgc_count":       len(run.bgcs),
        "locked_bgc_ids":  [b.bgc_id for b in run.bgcs],
    }
    _atomic_write_manifest_text(package_dir / f"{strain}_1_intake.json",
        json.dumps(intake, indent=2))

    # 2 — inventory.csv
    inv_headers = [
        # v9.7.87 9.7.87-C: Release is the row-level key the documented "filter rows -> public
        # cut" workflow filters on (and the leak audit asserts on). It lived only in the JSON
        # layers; the canonical row-level table now carries it too, second column for prominence.
        "BGC_ID", "Release", "Assembly_Locator", "User_Label", "Contig", "Node_ID", "antiSMASH_Region", "Source_GBK", "Region", "Start", "End", "Length_kb",
        "Boundary", "Products", "Arch", "Arch_rationale",
        "KCB_top", "KCB_score", "KCB_evidence_state", "KCB_proteins", "RiQ_score", "RiQ_label",
        "TTA_tier", "CCTT_triggers", "Resistance_tier", "DSS",
        "QS_routing", "NAPAA_flag", "Depth_floor",
        "closest_product_provenance", "source_kcb_file", "source_kcb_locator",
        "kcb_hit_rank", "denominator_type", "parse_confidence",
        "needs_manual_kcb_check", "product_claim_ceiling",
        "efls_status", "flank_census_tier1", "flank_census_tier2_todo",
        "cross_contig_candidate_set", "efls_claim_ceiling",
        "dkp_rank", "dkp_cdps_evidence", "dkp_oxidase_homology",
        "dkp_provenance", "dkp_claim_ceiling",
        "diagnostic_signal_score", "evidence_weight_tier", "claim_confidence",
        "claim_ceiling", "safe_claim",
        # v9.7.409 (CLAUDE_409 provenance anchors): the flat CSV lacked a `strain` column though the
        # locus is present via Assembly_Locator/Contig/Node_ID/Region. Appended (not inserted) so no
        # positional reader of the existing columns is disturbed; consumers read this board by name.
        "Strain",
    ]
    from .compat_v941 import compatibility_fields_for_bgc
    with _atomic_open_pkg(package_dir / f"{strain}_2_inventory.csv", "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(inv_headers)
        for bgc in run.bgcs:
            compat = compatibility_fields_for_bgc(bgc, triage_by.get(bgc.bgc_id), ss)
            tta  = tta_per_bgc.get(bgc.bgc_id, {})
            rt   = rt_per_bgc.get(bgc.bgc_id, {})
            dss  = dss_per_bgc.get(bgc.bgc_id, {})
            w.writerow([
                bgc.bgc_id, getattr(bgc, "release", "") or "PRIVATE", assembly_locator(bgc), bgc.user_label, bgc.contig, bgc.node_id, bgc.antismash_region, bgc.source_gbk, bgc.region_number,
                bgc.start, bgc.end, bgc.length_kb,
                bgc.edge_status, "; ".join(bgc.products),
                bgc.architecture_confidence, bgc.architecture_rationale,
                bgc.kcb_top or "", bgc.kcb_cumulative or "",
                getattr(bgc, "kcb_evidence_state", "UNKNOWN_KCB"),
                bgc.kcb_protein_hits or "", bgc.riq_score or "", bgc.riq_label or "",
                tta.get("bldA_tier", ""),
                ", ".join(cctt_coupling.get(bgc.bgc_id, [])),
                rt.get("tier", ""),
                dss.get("dss", ""),
                "QS_ECOLOGY_ONLY" if bgc.bgc_id in qs_ids else "",
                "NAPAA" if bgc.bgc_id in napaa_ids else "",
                _depth_floor(bgc, cctt_coupling, run.context.analysis_mode, rt_per_bgc),
                getattr(bgc, "closest_product_provenance", "UNRESOLVED"),
                getattr(bgc, "source_kcb_file", "UNRESOLVED"),
                getattr(bgc, "source_kcb_locator", "UNRESOLVED"),
                getattr(bgc, "kcb_hit_rank", "UNRESOLVED"),
                getattr(bgc, "denominator_type", "UNRESOLVED"),
                getattr(bgc, "parse_confidence", "LOW"),
                getattr(bgc, "needs_manual_kcb_check", "yes"),
                getattr(bgc, "product_claim_ceiling", "unresolved; do not use product name"),
                compat.get("efls_status", ""),
                compat.get("flank_census_tier1", ""),
                compat.get("flank_census_tier2_todo", ""),
                compat.get("cross_contig_candidate_set", ""),
                compat.get("efls_claim_ceiling", ""),
                compat.get("dkp_rank", ""),
                compat.get("dkp_cdps_evidence", ""),
                compat.get("dkp_oxidase_homology", ""),
                compat.get("dkp_provenance", ""),
                compat.get("dkp_claim_ceiling", ""),
                compat.get("diagnostic_signal_score", ""),
                compat.get("evidence_weight_tier", ""),
                compat.get("claim_confidence", ""),
                compat.get("claim_ceiling", ""),
                compat.get("safe_claim", ""),
                strain,  # v9.7.409: Strain anchor column
            ])

    # 2b — BGC crosswalk: mandatory map from Mamey BGC IDs to user-facing antiSMASH identifiers
    with _atomic_open_pkg(package_dir / f"{strain}_2b_bgc_crosswalk.csv", "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=[
            # v9.7.409: lead with `strain` (was absent) so the crosswalk itself is strain-traceable.
            "strain",
            "bgc_id", "assembly_locator", "user_label", "contig", "node_id", "antismash_region",
            "region_number", "source_gbk", "start", "end", "contig_length",
            "edge_status", "products"
        ], extrasaction="ignore")
        w.writeheader()
        for row in build_bgc_crosswalk(run.bgcs):
            row = dict(row)
            row["strain"] = strain
            row["assembly_locator"] = assembly_locator(row)
            row["products"] = "; ".join(row.get("products") or [])
            w.writerow(row)

    # 3 — scan_states.json
    _atomic_write_manifest_text(package_dir / f"{strain}_3_scan_states.json",
        json.dumps(run.scan_status, indent=2))

    # 4A — full RG-GMCI outputs (must exist before lead ranking)
    rggmci = ss.rggmci if ss else {}
    _atomic_write_manifest_text(package_dir / f"{strain}_4A_RGGMCI_full.json",
        json.dumps(rggmci, indent=2))
    rg_headers = [
        "pair", "bgc_a", "contig_a", "products_a", "edge_a",
        "bgc_b", "contig_b", "products_b", "edge_b",
        "rggmci_score", "rggmci_confidence", "supporting_references",
        "strong_supporting_references", "complete_or_chromosome_references",
        "good_geometry_references", "avg_min_identity", "max_protein_sum",
        "rescue_evidence_base", "knownclusterblast_refs", "clusterblast_refs",
        "functional_rescue_class", "a_core_fraction", "b_core_fraction",
        "a_functional_roles", "b_functional_roles",
        "subject_tiling_verdict", "terminus_truncation_rescue", "terminus_override_note",
        "shared_class_tokens", "complementary_disjoint_refs", "overlapping_subject_refs",
        "n_a_only_subjects", "n_b_only_subjects", "n_shared_subjects",
        "a_only_subjects", "b_only_subjects", "shared_subjects",
        "shared_reference_type_tokens", "shared_product_tokens", "best_sources",
        "interpretation_guard",
    ]
    with _atomic_open_pkg(package_dir / f"{strain}_4A_RGGMCI_ranked_pairs.csv", "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(rg_headers)
        for row in rggmci.get("ranked_pairs", []):
            w.writerow([row.get(h, "") for h in rg_headers])
    # --- _4D two-proof rescue verdict (.359, phylogenomics-lane P358): join RG-GMCI _4A (reference-based, just written
    # above) x KS-clade _4B (reference-free, computed in the pks_ks_scan phase). Placed HERE — not beside the
    # _4B scan — because two_proof_join reads the _4A CSV from disk, which only exists after this write.
    # Advisory: never a merge, never fails packaging; verdicts are candidates for the review lane's C06 adjudication.
    try:
        from .rescue_two_proof import two_proof_join, write_4d_csv
        _ksscan_4d = getattr(ss, "pks_ks_scan", None) if ss else None
        if _ksscan_4d:
            _rows_4d, _sum_4d, _cnt_4d = two_proof_join(
                str(package_dir / f"{strain}_4A_RGGMCI_ranked_pairs.csv"), _ksscan_4d)
            write_4d_csv(_rows_4d, str(package_dir / f"{strain}_4D_two_proof_rescue.csv"), strain)
    except Exception as _two_proof_exc:  # advisory join; never fail packaging
        _two_proof_issue = (
            "TWO_PROOF_RESCUE_WRITE_FAILED: "
            f"{type(_two_proof_exc).__name__}: {_two_proof_exc}"
        )
        run.issues.append(_two_proof_issue)
        _phase_receipt(
            package_dir, "two_proof_rescue", "ERROR", reason=_two_proof_issue
        )
    ev_headers = [
        "pair", "bgc_a", "bgc_b", "ref", "db_kind", "source", "reference_type",
        "rank_a", "rank_b", "nprot_a", "nprot_b",
        "mean_identity_a", "mean_identity_b", "avg_min_identity", "interval_a", "interval_b",
        "adjacency_class", "adjacency_basis", "adjacency_gap", "adjacency_span",
        "gap_locus_suffix", "overlap_locus_suffix",
        "subject_tiling_class", "n_shared_subjects", "n_a_only_subjects", "n_b_only_subjects",
        "shared_reference_type_tokens", "shared_product_tokens",
    ]
    with _atomic_open_pkg(package_dir / f"{strain}_4A_RGGMCI_evidence.csv", "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(ev_headers)
        for row in rggmci.get("evidence_rows", []):
            w.writerow([row.get(h, "") for h in ev_headers])

    # P-CBG (v9.7.100): persist the ClusterBlast per-gene correspondence layer.
    cbg = (ss.clusterblast_genes if ss else {}) or {}
    _atomic_write_manifest_text(package_dir / f"{strain}_4A2_ClusterBlast_gene_map.json",
        json.dumps(cbg, indent=2))
    cbg_headers = ["bgc_id", "query_gene", "subject_gene", "pct_identity", "pct_coverage",
                   "blast_score", "evalue", "reference", "reference_source", "reference_rank"]
    with _atomic_open_pkg(package_dir / f"{strain}_4A2_ClusterBlast_per_gene.csv", "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(_ANCHOR_COLS + cbg_headers)  # v9.7.409: prepend strain/assembly_locator/contig/region
        for bgc_id, hits in sorted((cbg.get("per_gene_best_hit") or {}).items()):
            _a = _anchor_vals(bgc_id)
            for h in hits:
                w.writerow(_a + [bgc_id] + [h.get(k, "") for k in cbg_headers[1:]])

    # P-MPG: rank-uncapped MIBiG per-gene table and BGC interpretation profile.
    mpg = (ss.mibig_per_gene if ss else {}) or {}
    _atomic_write_manifest_text(package_dir / f"{strain}_3_mibig_per_gene.json", json.dumps(mpg, indent=2))
    mpg_headers = ["bgc_id", "query_gene", "subject_gene", "mibig_accession", "mibig_compound",
                   "reference_type", "pct_identity", "pct_coverage",
                   "pct_coverage_interpretation", "coverage_qc_flag",
                   "blast_score", "evalue",
                   "reference_rank", "reference", "source_file"]
    with _atomic_open_pkg(package_dir / f"{strain}_3_mibig_per_gene.csv", "w", newline="") as f:
        w = _SafeWriter(f); w.writerow(_ANCHOR_COLS + mpg_headers)  # v9.7.409: prepend anchor
        for bid, hits in sorted((mpg.get("per_gene_mibig") or {}).items()):
            _a = _anchor_vals(bid)
            for h in hits:
                w.writerow(_a + [h.get(k, "") if k != "bgc_id" else bid for k in mpg_headers])
    convergence_rows = mpg.get("mibig_convergence") or []
    _atomic_write_manifest_text(package_dir / f"{strain}_3_mibig_convergence.json",
        json.dumps({
            "schema": "mibig_pathway_convergence_v2",
            "rows": convergence_rows,
            "claim_safety": (
                "Multi-gene convergence is pathway-family sequence evidence, not proof of "
                "exact product identity, expression, production, activity, or novelty."
            ),
        }, indent=2))
    convergence_headers = [
        "bgc_id", "products", "boundary", "mibig_accession", "mibig_compound",
        "reference_type", "distinct_query_genes", "distinct_subject_genes",
        "query_gene_count_total", "recognizable_query_gene_count",
        "query_gene_share", "recognizable_gene_share", "median_pct_identity",
        "median_pct_coverage", "median_pct_coverage_interpretation",
        "coverage_qc_flag", "minimum_pct_identity", "best_reference_rank",
        "source_row_count", "class_concordance", "convergence_tier",
        "convergence_tier_basis", "convergence_rank", "dominant_reference",
        "dominance_status", "runner_up_mibig_accession",
        "runner_up_mibig_compound", "runner_up_distinct_query_genes",
        "dominance_gene_margin", "claim_safety",
    ]
    with _atomic_open_pkg(package_dir / f"{strain}_3_mibig_convergence.csv", "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=_ANCHOR_COLS + convergence_headers, extrasaction="ignore")  # v9.7.409
        w.writeheader()
        for _row in convergence_rows:
            w.writerow({**_bgc_anchor(_row.get("bgc_id", "")), **_row})
    mpg_profile_headers = ["bgc_id", "query_gene_count", "recognizable_gene_count",
                           "recognizable_gene_fraction", "recognizable_min_pct_identity",
                           "median_pct_identity", "distinct_mibig_refs", "interpretation_class",
                           "dominant_mibig_accession", "dominant_mibig_compound",
                           "dominant_distinct_query_genes", "dominant_convergence_tier",
                           "report_only_contract"]
    with _atomic_open_pkg(package_dir / f"{strain}_3_mibig_profile.csv", "w", newline="") as f:
        w = _SafeWriter(f); w.writerow(_ANCHOR_COLS + mpg_profile_headers)  # v9.7.409: prepend anchor
        for bid, row in sorted((mpg.get("bgc_mibig_profile") or {}).items()):
            w.writerow(_anchor_vals(bid) + [row.get(k, "") for k in mpg_profile_headers])

    # P-AS-TABLES: stable JSON plus CSV tables for Claude/Excel consumers.
    ast = (ss.antismash_structured if ss else {}) or {}
    _atomic_write_manifest_text(package_dir / f"{strain}_3_antismash_structured.json", json.dumps(ast, indent=2))
    from .antismash_tables import TABLE_COLUMNS
    for key, filename in [
        ("modules", "antismash_modules"),
        ("ripp_motifs", "antismash_ripp_motifs"),
        ("motifs", "antismash_motifs"),
        ("rrefinder", "antismash_rrefinder"),
        ("hmm", "antismash_hmm"),
    ]:
        rows = ast.get(key) or []
        columns = TABLE_COLUMNS[key]
        # v9.7.409: add only the anchor columns this table lacks (most carry `contig`; `hmm` carries
        # `region_key` instead), so no column is duplicated. strain/region are always missing.
        _extra = [c for c in _ANCHOR_COLS if c not in columns]
        with _atomic_open_pkg(package_dir / f"{strain}_3_{filename}.csv", "w", newline="") as f:
            w = _SafeDictWriter(f, fieldnames=_extra + columns, extrasaction="ignore"); w.writeheader()
            for row in rows:
                _base = {k: (json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v) for k, v in row.items()}
                _a = _bgc_anchor(row.get("bgc_id", ""))
                for c in _extra:
                    _base[c] = _a[c]
                w.writerow(_base)

    # P-LWC trial metric: additive, explicitly not the corrected headline count.
    try:
        from .length_weighted import length_weighted_profile, summary as lwc_summary
        _lwc_rows = length_weighted_profile(run.bgcs)
        _lwc_manifest_summary = lwc_summary(_lwc_rows)
        # v9.7.409: prepend the anchor columns the per-BGC metric table lacks (contig is present).
        _lwc_fields = list(_lwc_rows[0]) if _lwc_rows else ["bgc_id"]
        _lwc_extra = [c for c in _ANCHOR_COLS if c not in _lwc_fields]
        with _atomic_open_pkg(package_dir / f"{strain}_3_length_weighted_capacity.csv", "w", newline="") as f:
            _w = _SafeDictWriter(f, fieldnames=_lwc_extra + _lwc_fields); _w.writeheader()
            for _lr in _lwc_rows:
                _lrow = dict(_lr)
                _la = _bgc_anchor(_lr.get("bgc_id", ""))
                for c in _lwc_extra:
                    _lrow[c] = _la[c]
                _w.writerow(_lrow)
        _atomic_write_manifest_text(package_dir / f"{strain}_3_length_weighted_summary.json", json.dumps(_lwc_manifest_summary, indent=2))
    except Exception as _lwc_exc:
        _lwc_manifest_summary = {"status": f"ERROR_{type(_lwc_exc).__name__}"}
        _atomic_write_manifest_text(package_dir / f"{strain}_3_length_weighted_summary.json", json.dumps(_lwc_manifest_summary, indent=2))
        _stage(f"[WARN] P-LWC length-weighted trial metric failed ({type(_lwc_exc).__name__}) — "
               f"summary JSON tagged ERROR (propagates to manifest), CSV omitted")

    # 4 — triage_board.csv
    # Three independent axes are reported here; they are NOT the same measurement and may disagree without
    # contradiction:
    #   * Arch            = architecture_confidence (A-E): STRUCTURAL completeness grade of the locus.
    #   * Arch_Capacity   = architecture_capacity: the claim-safe class-CAPACITY CALL (a class name).
    #   * Class_Conf      = architecture_class_confidence (HIGH/MOD/LOW): confidence IN THAT CLASS CALL.
    #   (B1's separate `claim_confidence` is the overall lead-CLAIM confidence from scoring.)
    # e.g. "Arch=A, Class_Conf=LOW" is coherent: a structurally clean locus whose product-class call is
    # uncertain. (W9: was "Arch_Conf", which dropped "class" and read as architecture-grade confidence.)
    triage_headers = [
        "Rank", "Assembly_Locator", "BGC_ID", "User_Label", "Contig", "Node_ID", "antiSMASH_Region", "Products", "Boundary", "Arch",
        "Arch_Capacity", "Class_Conf",
        "AB_auto", "AF_auto", "Novelty_auto", "Lead_tier_auto",
        "KCB_top", "KCB_clusterblast", "ClusterBlast_organism", "MIBiG_ranked_n", "SubCluster_hits", "KCB_score", "CCTT_triggers", "RGGMCI_support", "Depth_floor", "Primary_metab_flag",
        "Standing_rule", "Corrected_rank", "Composite_region",
        # v9.7.350 (BB_03): the region-merge structure the engine already resolves at parse time but
        # never wrote to a package. Composite_region only fires at single_protocluster_count>=3, so a
        # TWO-protocluster merge was indistinguishable from a clean single-protocluster region — blank
        # meant both "not composite" and "composite with exactly 2". These three are written for EVERY
        # region, unconditionally, so a consumer can tell those apart without re-parsing the GBK.
        # Structural/capacity descriptors only: how many protoclusters antiSMASH resolved here and
        # whether it called them fused. Never a product, activity, or novelty claim.
        "Protocluster_count", "Single_protocluster_count", "Chemical_hybrid", "Overmerge_state",
        "Misanchor_Flag", "Two_Pathway_Flag", "Two_Model_Flag", "Concordance", "UMED_gap",
        "AB_recall", "AF_recall", "Recall_family",
        # AUDIT_378 (wave 17): mobile_element_flag is a real, computed TriageRecord field
        # (models.py:206, populated scoring.py:746, gates corrected_rank alongside
        # standing_rule_flag/primary_metabolism_flag at scoring.py:752) that was already plumbed
        # into the manifest/verdicts.json handoff (serialize.py:68, per the v9.7.374 comment there)
        # but never into this CSV — the one artifact render_brief.py::load_facts() and
        # lead_pages.py::build() actually read (render_brief.py's own docstring: "Reads ONLY
        # artifacts the sealed package already produced (manifest.json + *_4_triage_board.csv)").
        # Both consumers can already detect SOME exclusion via a blank Corrected_rank
        # (compile_report.py's v9.7.377 fix generalizes to all three gating flags), but neither
        # can attribute a mobile-element-only exclusion to the specific ICE/transposon family
        # scoring.py identified — that attribution existed only in memory and in verdicts.json,
        # never on this board. Appended at the end (not inserted alongside Primary_metab_flag) so
        # no positional/index-based reader of this list is disturbed; every real consumer found in
        # this codebase reads the board by column name (csv.DictReader / dict-style row access).
        "Mobile_element_flag",
        # v9.7.409 (CLAUDE_409 provenance anchors): add the `Strain` anchor (locus already present
        # via Assembly_Locator/Contig/Node_ID/antiSMASH_Region). Appended for the same
        # positional-reader safety reason as Mobile_element_flag above.
        "Strain",
    ]
    # v9.7.127: gene-only two-pathway detection — flag windows where a single-class product label
    # may hide a second pathway. KCB-independent; reads the gene-by-gene table written above.
    # AUDIT_384: this early pass (inside _write_package, run BEFORE the fresh
    # *_gene_by_gene_all_bgcs.csv is written later in run_one_strain -- see the AUDIT_371 comment
    # a few hundred lines below) normally sees no table and _two_pathway_by_bgc() legitimately
    # returns {}. But when a STALE *_gene_by_gene_all_bgcs.csv from a prior invocation is already
    # sitting in package_dir (the exact scenario AUDIT_371 documents empirically: 2 strains found
    # with leftover tables from a prior run), a genuine read/parse failure on that stale file now
    # correctly propagates out of two_pathway_by_bgc() (v9.7.384 narrowed its own bare except) --
    # but this caller's bare `except Exception: _two_pathway = {}` re-swallowed it with NO
    # _phase_receipt and NO issues.append, silently converting a real parse failure into an empty
    # dict with zero trace on disk (worse than the pre-.384 bug, which at least wrote a
    # bgcs_evaluated=0 receipt). Match the sibling early-pass pattern used elsewhere in this same
    # function (e.g. the gene_by_gene_all/_gbga_err handler just above) so the failure is recorded.
    try:
        from .two_pathway import two_pathway_by_bgc, two_pathway_flag_cell
        _two_pathway = two_pathway_by_bgc(package_dir)
    except Exception as _tp_wp_err:
        run.issues.append(f"[WARN] two-pathway (early pass) skipped: {_tp_wp_err}")
        _phase_receipt(package_dir, "two_pathway_early", "ERROR", reason=str(_tp_wp_err))
        _two_pathway = {}
        two_pathway_flag_cell = lambda v: ""  # noqa: E731

    # v9.7.129: populated after gene_by_gene_all exists; the triage column is
    # patched in place later during run_command before final sealing.
    _decomp = None

    # v9.7.367 CANDIDATE (Indigo2 §2, the review lane-ruled 2026-08-15; smoke premise corrected by
    # Indigo #1 the same day): BeeCohort-class coverage guard, WARN-ONLY (raise_on_fail=False).
    # The analysis_mode gate matches the engine's existing idiom (cli.py:2617) and is currently
    # ALWAYS TRUE: gold is the only analysis mode ("standard" is rewritten to gold pre-context
    # at run_command; "smoke" was removed v9.7.161 and argparse rejects it). It stays as a
    # guard for any future non-gold mode, not as a live exemption. Warning goes to console +
    # phase receipt; promotion to raising is a future bump decision, not .367.
    try:
        if getattr(getattr(run, "context", None), "analysis_mode", "") == "gold":
            from .scoring import assert_full_scoring_coverage
            _cov_msg = assert_full_scoring_coverage(run.bgcs, triage, strain=strain, raise_on_fail=False)
            if _cov_msg:
                emit(f"[mamey] WARNING {_cov_msg}")
                _phase_receipt(package_dir, "scoring_coverage", "WARN", reason=_cov_msg)
    except Exception as _cov_exc:
        _phase_receipt(package_dir, "scoring_coverage", "ERROR", reason=repr(_cov_exc))

    with _atomic_open_pkg(package_dir / f"{strain}_4_triage_board.csv", "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(triage_headers)
        # v9.7.230 (audit #3): distinguish parsed-zero from not-parsed for SubClusterBlast. If ANY BGC in
        # the run carries subcluster hits, the tab was parsed, so an empty list is a real 0 ("NO_HITS")
        # rather than a missing parse (blank). Lets Sapote treat absent submodule support as NEGATIVE evidence.
        _subcluster_parsed = any(getattr(b, "subcluster_hits", None) for b in run.bgcs)
        for rank, t in enumerate(triage, 1):
            bgc = next((b for b in run.bgcs if b.bgc_id == t.bgc_id), None)
            if not bgc:
                continue
            w.writerow([
                rank, assembly_locator(bgc), bgc.bgc_id, bgc.user_label, bgc.contig, bgc.node_id, bgc.antismash_region, "; ".join(bgc.products),
                bgc.edge_status, bgc.architecture_confidence,
                getattr(t, "architecture_capacity", "") or getattr(bgc, "architecture_capacity", "") or "",
                getattr(t, "architecture_class_confidence", "") or getattr(bgc, "architecture_class_confidence", "") or "",
                t.ab_score, t.af_score, t.novelty_score, t.lead_tier,
                bgc.kcb_top or "", getattr(bgc, "clusterblast_top", "") or "", (bgc.clusterblast_ranked[0]["label"] if getattr(bgc, "clusterblast_ranked", None) else ""), len(getattr(bgc, "mibig_ranked", []) or ""), (("; ".join(f"{h['ref']}({h['mean_identity']})" for h in (getattr(bgc, "subcluster_hits", []) or [])[:3])) or ("NO_HITS" if _subcluster_parsed else "")), bgc.kcb_cumulative or "",
                ", ".join(cctt_coupling.get(bgc.bgc_id, [])),
                "; ".join((rggmci_support.get(bgc.bgc_id) or [])[:10]),
                _depth_floor(bgc, cctt_coupling, run.context.analysis_mode, rt_per_bgc),
                "YES" if getattr(t, "primary_metabolism_flag", False) else "",
                getattr(t, "standing_rule_flag", "") or "",
                getattr(t, "corrected_rank", None) if getattr(t, "corrected_rank", None) is not None else "",
                f"{bgc.single_protocluster_count}x single" if getattr(bgc, "composite_region", False) else "",
                # v9.7.350 (BB_03): unconditional structural counts. `protocluster_count` is the TRUE
                # antiSMASH protocluster-feature count (models.py: "Consumers that mean 'how many
                # protoclusters did antiSMASH resolve here' must read this field") — it is NOT
                # interchangeable with single_protocluster_count, which counts /kind="single"
                # cand_clusters. A chemical_hybrid region can have >=2 protoclusters but exactly 1
                # single-kind cand_cluster. Chemical_hybrid marks a FUSED cross-class pathway, whose
                # merged product string is correct and must NOT be de-inflated.
                getattr(bgc, "protocluster_count", 0),
                getattr(bgc, "single_protocluster_count", 0),
                "YES" if getattr(bgc, "has_chemical_hybrid", False) else "",
                getattr(bgc, "overmerge_state", "NOT_VERIFIABLE"),
                _misanchor_cell(t, (ss.misanchor_guards.get("per_bgc", {}).get(bgc.bgc_id, {})
                                    if ss and getattr(ss, "misanchor_guards", None) else {})),
                two_pathway_flag_cell(_two_pathway.get(bgc.bgc_id)),  # v9.7.127 gene-only two-pathway signal
                _two_model_flag_cell(bgc.bgc_id, _decomp),  # v9.7.129, patched after all-BGC gene table exists
                _concordance_cell(ss, bgc.bgc_id),  # C1
                getattr(t, "umed_gap_flag", "") or "",  # v9.7.62: MATURATION_GAP when no nearby maturation genes
                getattr(t, "ab_recall", "") if getattr(t, "ab_recall", 0) else "",   # v9.7.120 boost-only antimicrobial-recall AB
                getattr(t, "af_recall", "") if getattr(t, "af_recall", 0) else "",   # v9.7.120 boost-only antimicrobial-recall AF
                getattr(t, "recall_family", "") or "",                               # v9.7.120 family that drove the boost
                getattr(t, "mobile_element_flag", "") or "",  # AUDIT_378 wave 17: corrected_rank-gating flag, was manifest-only
                strain,  # v9.7.409: Strain anchor column
            ])

    # 4c — dedicated AB / AF lead boards (B-8/F-9): pre-sorted single-axis views so the antibacterial and
    # antifungal lead boards are directly locatable, not just AB_auto/AF_auto columns inside the triage board.
    _write_axis_lead_boards(package_dir, strain, triage,
                            {b.bgc_id: b for b in run.bgcs}, run.issues)

    # 4d — Mode B verdict scaffold (B-9/F-10, gold mode): deterministic first-pass CONFIRM/DOWNGRADE/DROP
    # per BGC that the Sapote gene-by-gene layer refines. Together with deep_data.json (emitted at package
    # seal) this lets tools/build_modeb_deepdive.py run from the package instead of degrading to verdict-less
    # placeholder cards.
    if run.context.analysis_mode == "gold":
        from .deep_data import modeb_verdict_rows, MODEB_VERDICT_HEADERS
        _misanchored = {t.bgc_id for t in triage if getattr(t, "misanchor_flag", "")}
        _vrows = modeb_verdict_rows(strain, triage, _misanchored)
        with _atomic_open_pkg(package_dir / "modeb_verdicts.csv", "w", newline="") as f:
            w = _SafeDictWriter(f, fieldnames=MODEB_VERDICT_HEADERS)
            w.writeheader()
            for r in _vrows:
                w.writerow(r)

    # 5 — workbook.xlsx (per-strain): written in run_one_strain with status tracking

    # 5b — manual BLASTP spot-check worklist (metadata only; does not claim BLASTP was run)
    cds_for_blastp = []
    try:
        cds_for_blastp = extract_cds_features(run.context.input_zip)
    except Exception:
        cds_for_blastp = []
    blast_rows = candidate_blastp_rows(run.bgcs, cds_for_blastp, strain=strain)
    blast_fields = [
        "bgc_id", "assembly_locator", "user_label", "user_blastp_label", "contig", "node_id",
        "antismash_region", "source_gbk", "protein_id", "kcb_closest_gene", "kcb_bitscore",
        "protein_start", "protein_end", "product_annotation",
        "manual_blastp_status", "reason_for_blastp", "sequence_available",
    ]
    with _atomic_open_pkg(package_dir / f"{strain}_5b_manual_blastp_worklist.csv", "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=blast_fields)
        w.writeheader()
        for row in blast_rows:
            row = dict(row)
            row["assembly_locator"] = assembly_locator(row)
            w.writerow({k: row.get(k, "") for k in blast_fields})

    # 5c — ChatGPT-safe iterative BLASTP FASTA panel: first-pass + one-best + curated
    # representative batches. This is a deliverable, not a claim: it lets the user
    # verify representative proteins outside Mamey without blasting whole contigs.
    try:
        _panel_dir = package_dir / "bgc_blastp_panel"
        _panel_summary = write_bgc_blastp_panel(
            _panel_dir, strain, run.bgcs, cds_for_blastp,
            genes_per_bgc=2, proteins_per_file=20, max_residues=90000, first_pass_size=30,
        )
        emit(f"  BGC BLASTP panel: first-pass {_panel_summary.get('first_pass_unique_proteins', 0)}; "
              f"curated {_panel_summary.get('curated_unique_proteins', 0)} proteins "
              f"in {_panel_summary.get('round_count', 0)} FASTA file(s) -> {_panel_dir.name}/")
    except Exception as _panel_exc:
        # Non-blocking: absence of the panel must not invalidate extraction, but the failure is visible.
        emit(f"  [WARN] BGC BLASTP panel skipped: {_panel_exc}")

    # 6 — user-visible output progress checklist is written after gate files
    # are added, so Packaging rows reflect the sealed state.

    # 7 — transparent cell provenance and missing-data worklist
    write_cell_provenance(run, package_dir)

    # manifest.json (full JSON snapshot — the handoff object)
    manifest_data = run.to_dict()
    manifest_data["antismash_profile"] = antismash_profile
    manifest_data["reporting_features"] = {
        "schema_version": "sapote_reporting_features_v2",
        "report_only_contract": "REPORT_ONLY_NO_SCORING",
        "p_mpg": {
            "schema_version": mpg.get("schema_version", ""),
            "status": mpg.get("status", ""),
            "per_gene_rows": sum(
                len(rows) for rows in (mpg.get("per_gene_mibig") or {}).values()
            ),
            "convergence_rows": len(mpg.get("mibig_convergence") or []),
            "profile_rows": len(mpg.get("bgc_mibig_profile") or {}),
        },
        "antismash_structured": {
            "schema_version": ast.get("schema_version", ""),
            "status": ast.get("status", ""),
            "counts": ast.get("counts", {}),
        },
        "p_lwc": _lwc_manifest_summary,
    }
    # F3 (v9.7.198): record the source antiSMASH ZIP path so post-seal automated paths
    # (render-all-figures -> domain-level) can re-open it for aSModule_count detail; the sealed
    # gene-context alone has no aSModule features and yields 0. Path dependency, not embedded data.
    manifest_data["input_zip"] = Path(run.context.input_zip).name
    # GOLDENROD .384: record the source ZIP's SHA-256 next to its path so dedup and
    # provenance are self-contained from the manifest (path proves which file; digest
    # proves which bytes). None if the ZIP is unavailable at seal time.
    _input_digest = _input_zip_sha256(run.context.input_zip)
    manifest_data["input_zip_sha256"] = _input_digest
    if _input_digest is None:
        _digest_issue = (
            "INPUT_ZIP_SHA256_UNAVAILABLE: source bytes could not be hashed at package "
            "write time; manifest provenance is incomplete."
        )
        run.issues.append(_digest_issue)
        _phase_receipt(
            package_dir, "input_zip_sha256", "ERROR", reason=_digest_issue
        )
    # v9.7.400 channel de-dup: four source_scans sub-objects are ALREADY written verbatim as
    # standalone package files above (measured byte-identical; together ~83-90% of source_scans,
    # e.g. 18.8 MB of 20.9 MB on a 96-BGC strain). Embed tiny alias stubs instead of second
    # copies; readers materialize them via mamey.snapshot_alias.resolve_scan_channel. The stub
    # is only written when the standalone file really exists — otherwise the full object stays
    # embedded (fail-safe: never a dangling pointer).
    _ss_md = manifest_data.get("source_scans") or {}
    for _ck, _cfn in (("rggmci", f"{strain}_4A_RGGMCI_full.json"),
                      ("mibig_per_gene", f"{strain}_3_mibig_per_gene.json"),
                      ("antismash_structured", f"{strain}_3_antismash_structured.json"),
                      ("clusterblast_genes", f"{strain}_4A2_ClusterBlast_gene_map.json")):
        if _ck in _ss_md and _ss_md[_ck] is not None and (package_dir / _cfn).is_file():
            _ss_md[_ck] = {"schema": "source_scan_channel_alias_v1", "alias_of": _cfn}
    _atomic_write_manifest_text(package_dir / "manifest.json", json.dumps(manifest_data, indent=2))
    _emit_bgc_bank(  # W6: per-strain bgc_data.json for build_modeb_deepdive
        package_dir, manifest_data, issues=run.issues
    )

    # W7: node_citation_map.json — pre-built BGC→node lookup for Sapote judgment layer.
    # Eliminates the need for Sapote to derive node strings from the triage board CSV.
    # Format: {"BGC007": "NODE_1_length_406707_cov_83 region001", ...}
    # AUDIT_374 (bcherry, AS-XXX runtime-output audit, 2026-08-22): this read
    # "bgc_records", a key manifest_data (run.to_dict()) never sets -- the per-BGC list
    # is written under "bgcs" (models.py:410). manifest_data.get("bgc_records", []) has
    # always silently returned [], so _ncm has always been empty and the `if _ncm:` guard
    # below has always skipped the write: node_citation_map.json has never once been
    # emitted since this W7 block was introduced. mamey/data/mode_b/package_map_spec.json
    # already documents this as a permanent non-artifact ("does NOT exist ... this engine
    # version does not emit") and routes Mode B authors to the triage board instead, so no
    # live consumer depends on this file -- but the feature itself, and its own inline
    # comment above, have been dead code the whole time. Fixed to the real key so the
    # documented W7 deliverable actually ships.
    try:
        _ncm = {}
        for _b in manifest_data.get("bgcs", []) or []:
            _bid = str(_b.get("bgc_id") or "").strip()
            _node = str(_b.get("node_id") or _b.get("contig") or "").strip()
            _region = str(_b.get("antismash_region") or "").strip()
            if _bid and _node:
                _ncm[_bid] = f"{_node} {_region}".strip() if _region else _node
        if _ncm:
            _atomic_write_manifest_text(package_dir / "node_citation_map.json",
                json.dumps(_ncm, indent=2, sort_keys=True))
    except Exception as _ncm_exc:
        _ncm_issue = (
            "NODE_CITATION_MAP_WRITE_FAILED: triage board CSV remains the fallback "
            f"({type(_ncm_exc).__name__}: {_ncm_exc})"
        )
        run.issues.append(_ncm_issue)
        _phase_receipt(
            package_dir, "node_citation_map", "ERROR", reason=_ncm_issue
        )

    # commit_receipt.json
    receipt = {
        "strain": strain, "mamey_version": __version__,
        "mode": run.context.analysis_mode,
        "input_zip": Path(run.context.input_zip).name,
        "antismash_version": extract_antismash_version(run.context.input_zip),
        "raw_bgcs": len(run.bgcs),
        "issues": run.issues,
        "status": "PASS_WITH_ISSUES" if run.issues else "PASS",
    }
    _atomic_write_manifest_text(package_dir / "commit_receipt.json", json.dumps(receipt, indent=2))

    # issue_log.md
    if run.issues:
        issue_text = "# Issue Log\n\n" + "\n".join(f"- {i}" for i in run.issues)
    else:
        issue_text = "# Issue Log\n\n- No blocking issues recorded.\n"
    _atomic_write_manifest_text(package_dir / "issue_log.md", issue_text)

    # AntiSMASH evidence parse
    _atomic_write_manifest_text(package_dir / f"{strain}_AntiSMASH_Evidence_Parse.json",
        json.dumps(antismash_evidence, indent=2))


# ---------------------------------------------------------------------------
# Batch run
# ---------------------------------------------------------------------------

def _auto_emit_cohort_leads_ledger(outdir, logger=None):
    """Auto-emit COHORT_PRIORITY_LEADS.csv for a multi-strain run (v9.7.410).

    Mirrors the ``build_cohort_figures`` / ``_auto_emit_figure_factory`` bridges:
    extraction-only, best-effort, and it NEVER blocks or un-seals a package. It unions
    every sealed ``*_4_triage_board.csv`` under ``outdir`` into ONE ranked cross-strain
    worklist at ``<outdir>/COHORT_PRIORITY_LEADS.csv`` (sibling of ``cohort_figures/``)
    and prints one line ``[cohort-leads-ledger] N leads across M strain(s) -> <csv>``.

    Claim-safety: the ledger is a prioritization surface only. It re-projects rows the
    per-strain triage boards already carry (capacity tier, AB/AF routing scores); it
    does not recompute scores and it never asserts product identity, production, or
    bioactivity. When the cohort spans engine versions the CSV header and the console
    carry the MIXED-ENGINE comparability caution.

    Returns the ledger meta dict (with ``status`` and ``out_path`` added) on success,
    else a typed skip dict ``{"status": "SKIPPED_...", "n_leads": 0}``. Fewer than two
    triage boards is a silent typed no-op (no file is written).
    """
    if logger is None:
        logger = emit
    log = logger or (lambda *a, **k: None)
    try:
        from .cohort_leads_ledger import build_ledger, find_triage_boards, write_ledger

        outdir = Path(outdir)
        boards = find_triage_boards(str(outdir))
        if len(boards) < 2:
            return {"status": "SKIPPED_SINGLE_BOARD" if boards else "SKIPPED_NO_BOARDS",
                    "n_leads": 0}
        rows, meta = build_ledger(str(outdir))
        out_path = outdir / "COHORT_PRIORITY_LEADS.csv"
        write_ledger(rows, meta, str(out_path))
        meta = dict(meta)
        meta["out_path"] = str(out_path)
        meta["status"] = "EMITTED"
        log(f"  [cohort-leads-ledger] {meta['n_leads']} Exceptional+High lead(s) across "
            f"{meta['n_strains']} strain(s) → {out_path}")
        if meta.get("mixed_engine"):
            log(f"  [cohort-leads-ledger] [CLAIM-SAFETY] MIXED engine versions "
                f"{meta['engine_versions']}; cross-strain rank is a routing prior only, "
                f"not a confident call.")
        return meta
    except Exception as e:
        log(f"  [cohort-leads-ledger] SKIPPED ({type(e).__name__}: {e})")
        return {"status": f"SKIPPED_{type(e).__name__}", "n_leads": 0}


def run_batch(
    input_zips: list[str],
    outdir: str,
    mode: str,
    master_path: str | None,
    taxonomy_list: list[str],
    source_list: list[str],
    bioactivity: object | None = None,
    source_provenance_list: list[str] | None = None,  # AMBER-03-2; pipe-separated on the CLI
    json_mode: str = "bounded",   # v9.3.2: bounded when ijson present; falls back to off
    brief: str = "standard",
    release: str | None = None,   # batch-level operator release override (PUBLIC|PRIVATE)
    privacy_profile: str | None = None,  # exact-ID user-owned named-tier policy shared across batch
    project_registry: str | None = None,  # one project registry may cover all batch strains
    locus_maps: str = "auto",     # P0 (v9.7.101): auto|off|on locus-map policy
    require_workbook: bool = False,  # P0 (v9.7.128): propagate --chatgpt-safe into batch runs
    token_budget: str = "standard",  # v9.7.136: standard|citation-compact output profile
    heartbeat_seconds: int = 20,      # v9.7.141: propagate ChatGPT-safe heartbeat into batch strains
    hmm_scan: bool = False,
    allow_accession_strain_id: bool = False,  # v9.7.374 fix: was declared on the shared `run`
        # subparser (so it reads as available for --strains batches too) but never threaded into
        # run_batch() -- the batch resolve_strain_id("auto", ...) call always used the default
        # allow_accession=False, so --allow-accession-strain-id had zero effect in a batch invocation
        # despite being a documented, unscoped flag.
) -> list[dict]:
    """Run up to N strains in sequence. Returns list of summary dicts."""
    results = []
    # v9.7.372 (VGP): two archives of the same organism resolve to the SAME id (e.g. two assemblies
    # of Actinophytocola sp. NPDC049390). Without uniquification the second run would write into the
    # first strain's package directory — silent overwrite. Track and suffix instead.
    _seen_sids: set[str] = set()
    for i, input_zip in enumerate(input_zips):
        # v9.7.372 (VGP): batch has no operator to re-prompt, so an accession-shaped id is UPGRADED
        # to the organism name from the archive rather than refused. This is the path that produced
        # CP025018_1 / CP108695_1 style packages on 2026-08-20.
        from .strain_identity import resolve_strain_id as _resolve_sid
        _sid_res     = _resolve_sid("auto", input_zip, allow_accession=allow_accession_strain_id)
        strain_id    = _sid_res.strain_id or _chatgpt_safe_strain_guess(input_zip)
        if _refuse_unsafe_strain_id(strain_id) or _refuse_outdir_inside_bundle(outdir):
            return 2
        if strain_id in _seen_sids:
            _n = 2
            while f"{strain_id}_{_n}" in _seen_sids:
                _n += 1
            emit(f"  [strain] id collision on '{strain_id}' -> '{strain_id}_{_n}' "
                  f"(distinct archive: {input_zip})")
            strain_id = f"{strain_id}_{_n}"
        _seen_sids.add(strain_id)
        if _sid_res.source == "archive":
            emit(f"  [strain] {input_zip}: id resolved to {strain_id} ({_sid_res.organism})")
        elif _sid_res.message:
            emit(f"  [strain] {_sid_res.message}")
        display_name = strain_id.replace("_", " ")
        taxonomy     = taxonomy_list[i] if i < len(taxonomy_list) else "not verified"
        source       = source_list[i]   if i < len(source_list)   else "not supplied"
        _spl         = source_provenance_list or []
        source_prov  = _spl[i] if i < len(_spl) else (_spl[0] if len(_spl) == 1 else "asserted")

        result = run_one_strain(
            strain_id=strain_id,
            display_name=display_name,
            input_zip=input_zip,
            outdir=outdir,
            mode=mode,
            taxonomy=taxonomy,
            source=source,
            source_provenance=source_prov,
            bioactivity=bioactivity,
            master_path=master_path,
            json_mode=json_mode,
            brief=brief,
            release=release,
            privacy_profile=privacy_profile,
            project_registry=project_registry,
            locus_maps=locus_maps,
            require_workbook=require_workbook,
            token_budget=token_budget,
            heartbeat_seconds=heartbeat_seconds,
            hmm_scan=hmm_scan,
        )
        results.append(result)

    emit(f"\n{'='*60}", f"Batch complete — {len(results)} strain(s)", sep="\n")
    for r in results:
        emit(f"  {r['strain_id']}: {r['status']} | {r['raw_bgcs']} BGCs | {r['assembly_tier']}")
    emit("="*60)

    # Auto-emit cross-strain figures — ONLY when more than one strain was analysed.
    # Extraction-only and best-effort: aggregates the per-strain packages into cohort
    # tables and renders the cross-strain figure pack. Never blocks or alters the
    # per-strain package seals; a single-strain batch is a no-op by design.
    if len(results) > 1:
        try:
            from .cohort_figures import build_cohort_figures
            cohort_res = build_cohort_figures(results, outdir, logger=emit)
            nfig = cohort_res.get("figure_count", 0)
            if nfig:
                emit(f"  Cross-strain figures: {nfig} emitted → {outdir}/cohort_figures/")
            else:
                emit(f"  Cross-strain figures: none ({cohort_res.get('status', 'no data')})")
        except Exception as e:
            emit(f"  Cross-strain figures: SKIPPED ({type(e).__name__}: {e})")

        # v9.7.410: the cohort class-capacity heatmap (strain x biosynthetic class) had no
        # auto-emit path — it existed only behind manual --workbook routes. Same best-effort,
        # typed-skip contract as the bridge above; writes into the same cohort_figures/ dir.
        _auto_emit_cohort_class_heatmap(results, Path(outdir))

        # PATCH-AUTO-FIGURES multi-strain (v9.7.148): also emit F01-F15 gold gene/domain
        # figure suite when >=2 gold packages are present. The bridge above emits
        # RGGMCI-focused figures; this emits the domain heatmaps, PCA, and clustermap.
        # Requires deep_data.json (gold mode). Non-blocking.
        try:
            _gold_pkgs = [
                r for r in results
                if (Path(outdir) / r.get("strain_id", "") / "package" / "deep_data.json").exists()
            ]
            if len(_gold_pkgs) >= 2:
                from .cohort_figures import generate as _gen_multi_figs
                _multi_res = _gen_multi_figs(
                    runs_dir=str(outdir),
                    out=str(Path(outdir) / "cohort_figures_gold"),
                )
                _mfig = _multi_res.get("figures", 0)
                if _mfig:
                    emit(f"  Gold domain figures: {_mfig} F-series figure(s) "
                          f"→ {Path(outdir)/'cohort_figures_gold'}/")
                else:
                    emit(f"  Gold domain figures: SKIPPED (no gold packages or no data)")
            elif len(_gold_pkgs) == 1 and len(results) > 1:
                emit(f"  Gold domain figures: SKIPPED — only 1 of {len(results)} strains is gold mode")
        except Exception as _mf_exc:
            emit(f"  Gold domain figures: SKIPPED ({type(_mf_exc).__name__}: {_mf_exc})")

        # Auto-emit the extended cross-strain suite (v9.7.410). Through v9.7.409 the
        # module's own docstring called it the auto-emit companion, yet only the manual
        # ``cohort-figures`` subcommand ever reached it. Same contract as the bridges
        # above: extraction-only, best-effort, typed skip on failure, never blocks.
        _auto_emit_cohort_figures_extended(results, outdir)

        # Auto-emit the Figure Factory across the cohort (v9.7.409). Same contract as
        # the cohort-figures bridge above: extraction-only, best-effort, and a typed
        # skip (never a crash) when no Figure Factory Next config is present for the
        # run. Emits into <outdir>/figure_factory as an expected cohort deliverable.
        _auto_emit_figure_factory(Path(outdir), source_dir=Path(outdir))

        # v9.7.410: auto-emit the cross-strain priority-leads ledger. The .408 runtime-
        # traced audit found `mamey/cohort_leads_ledger.py` was reachable ONLY through the
        # manual `cohort-leads` subcommand, so every multi-strain run silently shipped
        # without its ranked COHORT_PRIORITY_LEADS.csv. Same contract as the bridges
        # above: reads the sealed triage boards (never re-scores), best-effort, typed skip.
        _auto_emit_cohort_leads_ledger(Path(outdir))

    return results


def _auto_emit_cohort_class_heatmap(results, outdir, logger=None):
    """Auto-emit the cohort class-capacity heatmap for a multi-strain run (v9.7.410).

    Same contract as the ``build_cohort_figures`` bridge: extraction-only, best-effort, and it
    NEVER blocks or un-seals a package. Until v9.7.410 ``mamey/cohort_class_heatmap.py`` was
    reachable only by hand (``figures --figure-set cohort-class --workbook`` or
    ``render-all-figures --sets cohort-class --workbook``), both of which need a cohort
    workbook; a plain multi-strain run never emitted it. This helper rebuilds the
    B2_Product_Class_Matrix rows for THIS run from each sealed package's
    ``<strain>_2_inventory.csv`` (``Products`` column) with the master workbook's own bucketing
    (``master_workbook._b2_product_class_counts``), so the counts equal the master B2 row for
    the same strain, and renders into ``<outdir>/cohort_figures/cohort_class_capacity_heatmap.png``
    + ``_data.csv`` — the same names the manual routes write.

    Returns a small typed dict: ``{"status": "OK"|"SKIPPED_*", "figure_count": 0|1, ...}``.
    """
    if logger is None:
        logger = emit
    log = logger or (lambda *a, **k: None)
    try:
        ok = [r for r in results if isinstance(r, dict) and r.get("strain_id")]
        if len(ok) < 2:
            return {"status": "SKIPPED_SINGLE_STRAIN", "figure_count": 0}
        run_dir = Path(outdir)
        try:
            from .master_workbook import _b2_product_class_counts
        except Exception as imp_exc:  # openpyxl-less core install: typed skip, not a crash
            log(f"  Cohort class heatmap: SKIPPED (import: {type(imp_exc).__name__}: {imp_exc})")
            return {"status": "SKIPPED_IMPORT", "figure_count": 0,
                    "reason": f"{type(imp_exc).__name__}: {imp_exc}"}
        rows = []
        for r in ok:
            sid = r["strain_id"]
            # locate the package dir: <outdir>/<strain_id>/package  (matches run layout)
            pkg_dir = None
            zip_path = r.get("package_zip", "")
            if zip_path:
                cand = Path(zip_path).parent / "package"
                if cand.is_dir():
                    pkg_dir = cand
            if pkg_dir is None:
                cand = run_dir / sid / "package"
                pkg_dir = cand if cand.is_dir() else None
            inv = sorted(pkg_dir.glob("*_2_inventory.csv")) if pkg_dir else []
            if not inv:
                log(f"  Cohort class heatmap: no *_2_inventory.csv for {sid}; row skipped")
                continue
            products = []
            with open(inv[0], newline="", encoding="utf-8") as fh:
                for rec in csv.DictReader(fh):
                    products.extend(c.strip() for c in (rec.get("Products") or "").split(";")
                                    if c.strip())
            row = {"strain": sid}
            row.update(_b2_product_class_counts(products))
            row["label_provenance"] = "RAW_ANTISMASH"
            row["counts_reliability"] = r.get("assembly_tier", "") or ""
            rows.append(row)
        if len(rows) < 2:
            log(f"  Cohort class heatmap: SKIPPED (inventories found for {len(rows)} of {len(ok)} strains)")
            return {"status": "SKIPPED_INSUFFICIENT_DATA", "figure_count": 0, "n_rows": len(rows)}
        from .cohort_class_heatmap import render_cohort_class_heatmap
        out = run_dir / "cohort_figures"
        png = out / "cohort_class_capacity_heatmap.png"
        res = render_cohort_class_heatmap(
            None, png, out / "cohort_class_capacity_heatmap_data.csv",
            claim_prefix="PRIVATE", label_provenance="RAW_ANTISMASH", rows=rows)
        if str(res.get("status", "")).upper() != "OK":
            log(f"  Cohort class heatmap: SKIPPED ({res.get('reason', 'renderer skip')})")
            return {"status": "SKIPPED_RENDER", "figure_count": 0, "detail": res}
        log(f"  Cohort class heatmap: {res.get('n_strains', 0)} strains x "
            f"{res.get('n_classes', 0)} classes → {png}")
        return {"status": "OK", "figure_count": 1, "png": str(png),
                "csv": str(out / "cohort_class_capacity_heatmap_data.csv"), "detail": res}
    except Exception as e:  # never break the batch
        log(f"  Cohort class heatmap: SKIPPED ({type(e).__name__}: {e})")
        return {"status": "SKIPPED_ERROR", "figure_count": 0, "reason": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def run_command(args) -> int:
    # v9.7.152: capped-session timeout profile (assistant-neutral). Keyed on the same
    # `chatgpt_safe` dest as before so all existing call sites and tests are unaffected;
    # only the operator-facing name and notice changed. --chatgpt-safe still works as a
    # deprecated alias.
    _used_deprecated_alias = any(
        a == "--chatgpt-safe" or a == "--chatgpt-followup" or a.startswith("--chatgpt-safe=")
        for a in _sys.argv
    )
    if _used_deprecated_alias:
        emit("[deprecated] --chatgpt-safe/--chatgpt-followup are renamed to "
              "--capped-session/--capped-followup (v9.7.152). The old flags still work as "
              "aliases but will be removed in a future release.", flush=True)
    # P0: capped-session profile
    if getattr(args, "chatgpt_safe", False):
        args.brief = "none"
        args.json_evidence = "off"
        args.require_workbook = True
        if getattr(args, "locus_maps", "auto") == "auto":
            args.locus_maps = "off"   # P0: capped LLM sessions skip the expensive locus-map phase
        # Capped sessions are wall-clock capped; store-only ZIPs avoid spending the last
        # seconds compressing an already-complete package. Operators can override explicitly.
        _os.environ.setdefault("MAMEY_ZIP_COMPRESSION", "stored")
        if getattr(args, "heartbeat_seconds", None) is None:
            args.heartbeat_seconds = 20
        emit(f"[capped-session] --brief none --json-evidence off --require-workbook --locus-maps {args.locus_maps} --heartbeat-seconds {args.heartbeat_seconds}")
        # v9.7.160: capped sessions run gold DIRECTLY (the old forced smoke-first FATAL is gone).
        # v9.7.161: smoke removed entirely — gold is the only analysis mode, reachable in one
        # capped run. There is no longer a triage-only path to strand a session on.
    # v9.7.92: Standard mode retired — gold is the engine (uniform full Mode B for
    # every BGC, edge/FC included). Aliased to gold for back-compat; emits a notice.
    if getattr(args, "mode", "gold") == "standard":
        emit("[deprecated] --mode standard is retired (v9.7.92); running gold "
              "(uniform full Mode B, the only analysis mode).", flush=True)
        args.mode = "gold"
    bioactivity_input = args.bioactivity
    if getattr(args, "bioactivity_json", None):
        if args.bioactivity is not None:
            emit("ERROR: BIOACTIVITY_LEGACY_SHAPE_HOLD: supply one bioactivity input form", file=_sys.stderr, flush=True)
            return 2
        try:
            bioactivity_input = json.loads(args.bioactivity_json)
        except json.JSONDecodeError:
            emit("ERROR: BIOACTIVITY_LEGACY_SHAPE_HOLD: --bioactivity-json is not valid JSON", file=_sys.stderr, flush=True)
            return 2
    if args.strains:
        if getattr(args, "chatgpt_safe", False):
            _too_large, _detail = _chatgpt_safe_batch_too_large(args.strains)
            if _too_large:
                emit(
                    "FATAL: --capped-session multi-strain batch is too large for a capped LLM tool session. "
                    f"Split into one gold run per strain ({_detail}).",
                    file=_sys.stderr, flush=True,
                )
                for _zip in args.strains:
                    _sid = _chatgpt_safe_strain_guess(_zip)
                    emit(
                        f"  python -m mamey run --strain {_sid} --input-zip \"{_zip}\" "
                        "--mode gold --capped-session --json-evidence off --brief none",
                        file=_sys.stderr, flush=True,
                    )
                return 2
        # Multi-strain batch
        results = run_batch(
            input_zips=args.strains,
            outdir=args.outdir,
            mode=args.mode,
            master_path=args.master,
            taxonomy_list=(args.taxonomy or "").split("|"),
            source_list=(args.source or "").split("|"),
            source_provenance_list=[p.strip() for p in
                                    (getattr(args, "source_provenance", "") or "").split("|") if p.strip()],
            bioactivity=bioactivity_input,
            json_mode=args.json_evidence,
            brief=args.brief,
            release=getattr(args, "release", None),
            privacy_profile=getattr(args, "privacy_profile", None),
            project_registry=getattr(args, "project_registry", None),
            locus_maps=getattr(args, "locus_maps", "auto"),
            require_workbook=getattr(args, "require_workbook", False),
            token_budget=getattr(args, "token_budget", "standard"),
            heartbeat_seconds=getattr(args, "heartbeat_seconds", 20),
            hmm_scan=getattr(args, "hmm_scan", False),
            allow_accession_strain_id=getattr(args, "allow_accession_strain_id", False),
        )
    else:
        # Single strain
        # v9.7.372 (VGP): an accession is a database pointer, not a strain identity. Refuse it
        # ONLY when the archive offers a real organism name, so the error is actionable.
        from .strain_identity import resolve_strain_id as _resolve_sid
        _sid_res = _resolve_sid(args.strain, args.input_zip,
                                allow_accession=getattr(args, "allow_accession_strain_id", False))
        if _sid_res.refused:
            emit(f"\nERROR: {_sid_res.message}\n")
            return 2
        if _sid_res.message:
            emit(f"  [strain] {_sid_res.message}")
        strain_id    = _sid_res.strain_id or _chatgpt_safe_strain_guess(args.input_zip)
        if _refuse_unsafe_strain_id(strain_id) or _refuse_outdir_inside_bundle(args.outdir):
            return 2
        display_name = (args.display_name or strain_id.replace("_", " "))
        result = run_one_strain(
            strain_id=strain_id,
            display_name=display_name,
            input_zip=args.input_zip,
            outdir=args.outdir,
            mode=args.mode,
            taxonomy=args.taxonomy or "not verified",
            source=args.source or "not supplied",
            source_provenance=getattr(args, "source_provenance", "asserted"),
            bioactivity=bioactivity_input,
            master_path=args.master,
            json_mode=args.json_evidence,
            # v9.7.374 fix: SSOT drift -- run_one_strain()'s own parameter default (line ~959)
            # and the --antismash-profile argparse default (line ~4308) were both deliberately
            # flipped from "unknown" to "auto" this cut (VGP's auto-recognizer), but this getattr
            # fallback was one of two remaining sites still hardcoding the pre-cut "unknown"
            # literal (the other is _write_package()'s own parameter default, fixed alongside
            # this one -- AUDIT_374 re-review batch1 caught the omission of that second
            # site from this card's original "only remaining site" claim). Currently unreachable
            # in practice at both sites (argparse always populates args.antismash_profile via its
            # own default="auto"; _write_package() is always called with the argument passed
            # explicitly), but would silently defeat the auto-recognizer entirely for any caller
            # constructing an args-like object, or calling _write_package() directly, without
            # this attribute/argument set.
            antismash_profile=getattr(args, "antismash_profile", "auto"),
            brief=getattr(args, "brief", "standard"),
            release=getattr(args, "release", None),
            privacy_profile=getattr(args, "privacy_profile", None),
            project_registry=getattr(args, "project_registry", None),
            metadata_csv=getattr(args, "metadata_csv", None),
            require_workbook=getattr(args, "require_workbook", False),
            locus_maps=getattr(args, "locus_maps", "auto"),
            token_budget=getattr(args, "token_budget", "standard"),
            heartbeat_seconds=getattr(args, "heartbeat_seconds", 20),
            hmm_scan=getattr(args, "hmm_scan", False),
        )
        results = [result]

    success_statuses = {"MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES", "PASS", "PASS_WITH_ISSUES"}
    all_pass = bool(results) and all(
        str(r.get("status", "")) in success_statuses
        or str(r.get("validator_status", "")) in success_statuses
        for r in results
    )

    # v9.7.279 (deliverable-surfacing gate): the sealed per-strain Complete_Package.zip IS the run
    # deliverable and the portable unit of exchange — but operators (human or LLM) kept missing it,
    # because its only pointer was one terse "Package: ... -> ...zip" line buried mid-run and the
    # instruction to surface it lived only in DELIVERABLE_CONTRACT.md / SESSION_START_MANIFEST. This
    # makes delivery instruction-independent for BOTH the single-strain and batch paths: an explicit
    # DELIVERABLES block is printed LAST (after the results JSON), and a machine-readable HANDBACK.json
    # is written to the outdir so agent operators can surface the zip paths without reading any prose.
    # Emission is best-effort and never changes the exit code.
    _deliverables = []
    for _r in results:
        _z = _r.get("package_zip")
        if _z and Path(_z).exists():
            _deliverables.append({
                "strain_id": _r.get("strain_id", "?"),
                "zip": str(_z),
                "bytes": Path(_z).stat().st_size,
                "status": _r.get("status", "?"),
            })

    emit(json.dumps(results, indent=2))

    if _deliverables:
        emit(f"\n{'='*60}", "DELIVERABLES — hand these sealed package zip(s) to the user:", sep="\n")
        for _d in _deliverables:
            emit(f"  \u2192 {_d['zip']}  ({_d['bytes']//1024} KB, {_d['status']})")
        emit("  Each is the sealed, portable Complete_Package (the unit of exchange).", "  Surface these files to the user AS the deliverable; do NOT substitute a", "  hand-rolled subset of package files.", sep="\n")
        try:
            _hb = Path(args.outdir) / "HANDBACK.json"
            _hb.write_text(json.dumps({
                "schema": "mamey_handback_v1",
                "bundle_version": BUNDLE_VERSION,
                "engine": __version__,
                "directive": "Surface each 'zip' path to the user as THE run deliverable. "
                             "Do not substitute hand-rolled artifact subsets.",
                "primary_deliverables": _deliverables,
            }, indent=2))
            emit(f"  handback pointer: {_hb}")
        except Exception as _hb_exc:  # pragma: no cover - never fatal
            emit(f"  handback pointer: SKIPPED ({type(_hb_exc).__name__}: {_hb_exc})")
        emit("=" * 60)

    return 0 if all_pass else 1


def ingest_blastp_trove_command(args) -> int:
    """v9.7.340: ingest a pre-organized per-BGC BLASTp trove into the package overlay (no workbook,
    no raw HitTable). Channel-tagged (nr > clustered_nr > ebi); reader-side, non-scoring."""
    from .blastp_ingest import ingest_blastp_trove
    import os as _os
    if not _os.path.isdir(args.package):
        emit(f"FATAL: package directory not found: {args.package}", file=_sys.stderr, flush=True)
        return 2
    if not _os.path.isdir(args.trove):
        emit(f"FATAL: trove directory not found: {args.trove}", file=_sys.stderr, flush=True)
        return 2
    res = ingest_blastp_trove(args.package, args.trove, args.channel, getattr(args, "strain", None))
    emit(f"[ingest-blastp-trove] channel={res['channel']} "
          f"{len(res['bgcs_written'])} BGCs, {res['genes']} genes -> {res['package']}/blastp_online/",
          flush=True)
    return 0


def blastp_status_command(args) -> int:
    """v9.7.340: per-BGC BLASTp overlay coverage audit (channels/genes); flags ClusterBlast fallback."""
    from .blastp_ingest import blastp_status
    rows = blastp_status(args.package)
    if not rows:
        emit("  (no blastp_online overlays present — all BGCs on ClusterBlast fallback)", flush=True)
    for r in rows:
        flag = "" if r["armed"] else "  DISARMED -> ClusterBlast fallback"
        emit(f"  {r['bgc']:<8} channels={r['channels']:<24} genes={r['genes']:<4}{flag}", flush=True)
    return 0


def ingest_blastp_command(args) -> int:
    """v9.7.163: ingest NCBI BLASTp output into B5_BLASTp_Hits. Deliverable-first: writes the
    updated workbook, reports the row/query/BGC counts, and points at the file."""
    from .blastp_ingest import BlastpAlignmentKeyConflictError, BlastpHitTableError, ingest_blastp
    import os as _os
    if not _os.path.exists(args.master):
        emit(f"FATAL: master workbook not found: {args.master}", file=_sys.stderr, flush=True)
        return 2
    if not _os.path.exists(args.hit_table):
        emit(f"FATAL: HitTable CSV not found: {args.hit_table}", file=_sys.stderr, flush=True)
        return 2
    pkg = getattr(args, "package", None)
    if pkg and not _os.path.isdir(pkg):
        emit(f"FATAL: package directory not found: {pkg}", file=_sys.stderr, flush=True)
        return 2
    try:
        res = ingest_blastp(args.master, args.strain, args.hit_table,
                            getattr(args, "xml", None), top_n=getattr(args, "top_n", 10),
                            package=pkg, source=getattr(args, "source", None) or "NCBI web-BLASTp")
    except (BlastpAlignmentKeyConflictError, BlastpHitTableError) as exc:
        # SystemExit bypasses the post-seal refresh wrapper: a rejected ingest must not
        # mutate either the workbook or package integrity metadata.
        raise SystemExit(f"ingest-blastp: {exc}") from exc
    emit(f"[ingest-blastp] {res['rows']} hit rows across {res['queries']} query genes / "
          f"{res['bgcs']} BGC(s) appended to B5_BLASTp_Hits "
          f"(enriched from XML: {res['enriched']}) -> {args.master}"
          + (f"; binding guard: {res['binding_guard']['admitted']} admitted, {res['binding_guard']['quarantined']} quarantined"
             + (f" -> {res['binding_guard']['quarantine']}" if res['binding_guard'].get('quarantine') else "")
             if res.get('binding_guard', {}).get('binding_validated') else "; binding guard: no sealed context (not validated)"),
          flush=True)  # v9.7.412: guard summary folded into the existing emission (no new site)
    # v9.7.410 (CLAUDE_410_blastp_bgc_recovery_409): fail loud on a 0-BGC bind. Rows landed in B5
    # but none carries a BGC_ID, so write_nr_overlay writes 0 genes / 0 files and the
    # conservation_median_id / NOVELTY_CONTRADICTION guard stays silently disarmed. Likely cause:
    # the query FASTA was a raw `proteins.faa` subset with a space-delimited defline
    # (`>ctg107_3 gene=... BGC=BGC003 ...`) -- NCBI truncates the HitTable query_id at the first
    # space and drops the BGC token -- instead of the NCBI-safe pipe-delimited `bgc_blastp_panel/`
    # FASTA. The BGC survives in the Alignment XML <query-title>; --xml recovers it.
    _parsed = int(res.get("rows_parsed", res["rows"]) or 0)
    if _parsed > 0 and int(res.get("bgcs", 0) or 0) == 0:
        emit(f"[ingest-blastp] WARNING: {_parsed} hit row(s) parsed but 0 BGC(s) bound -- every "
              f"row has an empty BGC_ID, so no nr overlay gene was written and the "
              f"conservation_median_id / NOVELTY_CONTRADICTION guard stays disarmed. Likely cause: "
              f"the BLASTp query FASTA was a raw proteins.faa subset with a space-delimited defline "
              f"(NCBI truncates the HitTable query id at the first space, dropping `BGC=`), not the "
              f"NCBI-safe FASTA under bgc_blastp_panel/. Rescue: re-run with --xml <Alignment XML> "
              f"(the <query-title> still carries the BGC token), or re-submit from the "
              f"bgc_blastp_panel/ FASTA.", file=_sys.stderr, flush=True)
    ov = res.get("overlay")
    if ov:
        emit(f"[ingest-blastp] nr overlay: {ov['genes']} gene(s) across {ov['bgcs']} BGC(s) "
              f"-> {ov['outdir']} (arms conservation_median_id / NOVELTY_CONTRADICTION)", flush=True)
    else:
        emit("[ingest-blastp] NOTE: no --package given, so no nr overlay was written. "
              "conservation_median_id will fall back to ClusterBlast and the "
              "NOVELTY_CONTRADICTION lint stays disarmed for these genes.", flush=True)
    return 0


def verify_citations_command(args) -> int:
    """Fail-closed node·region citation gate for a Mode B report/deliverable (WAC-01375 fatal-error class).

    A node-less `strain + BGC-number` citation merged two distinct AS-XXX loci and mis-attributed an AB
    prior. This refuses any deliverable that cites a strain+BGC without a locating token (NODE_/ctg/region).
    """
    import sys as _sys
    from .bgc_citation_gate import gate_text
    p = Path(args.path)
    if p.is_dir():
        files = sorted(p.rglob("*.md"))
    elif p.is_file():
        files = [p]
    else:
        _sys.stderr.write(f"verify-citations: no such path: {p}\n")
        return 2
    total = 0
    for f in files:
        try:
            findings = gate_text(f.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:  # noqa: BLE001 - a bad file is reported, not fatal to the scan
            _sys.stderr.write(f"  [skip] {f}: {e}\n")
            continue
        if findings:
            total += len(findings)
            _sys.stdout.write(f"NODE-LESS CITATIONS in {f}:\n")
            for m in findings:
                _sys.stdout.write(f"  {m}\n")
    if total:
        _sys.stdout.write(
            f"\nverify-citations: FAIL — {total} node-less BGC citation(s) across {len(files)} file(s). "
            "Cite by node·region (NODE_n_length_L_cov_C / regionNNN), never a bare BGC number.\n"
        )
        return 1
    _sys.stdout.write(f"verify-citations: PASS — {len(files)} file(s), no node-less BGC citations.\n")
    return 0


def validate_command(args) -> int:
    result = validate_package(
        args.package_dir,
        enrichment_check=True,
        manifest_contract_check=getattr(args, "manifest_contract", False),
    )
    emit(json.dumps(result, indent=2))
    status = str(result.get("status", ""))
    base_exit = 0 if status.startswith("PASS") or status == "MAMEY_COMPLETE" else 1

    # v9.7.123 (SM-P1-008): workbook populated-sheet gate.
    # WARN-first: the check ALWAYS runs and prints WORKBOOK_CONTENT for observability;
    # it only changes the exit code when --workbook-strict is passed.
    from pathlib import Path as _Path
    from .validate import validate_workbook_content
    pkg = _Path(args.package_dir)
    xlsx_candidates = sorted(pkg.glob("*_5_workbook.xlsx"))
    if not xlsx_candidates:
        emit("WORKBOOK_CONTENT:", json.dumps({"status": "SKIP", "reason": "no *_5_workbook.xlsx found"}))
        wb_blocks = False
    else:
        wb_result = validate_workbook_content(xlsx_candidates[0])
        emit("WORKBOOK_CONTENT:", json.dumps(wb_result, indent=2))
        wb_blocks = getattr(args, "workbook_strict", False) and wb_result["status"] != "PASS"

    return 1 if (base_exit == 1 or wb_blocks) else 0


def seal_package_command(args) -> int:
    """mamey seal-package — run all QC gates and emit a seal receipt (v9.7.125)."""
    from .seal_package import seal_package, write_receipts
    result = seal_package(args.package_dir,
                          strict=getattr(args, "strict", False),
                          advisory=getattr(args, "advisory", False))
    out_dir = args.out or args.package_dir
    paths = write_receipts(result, out_dir)
    # H3/v9.7.352: loud banner when a non-strict seal is hiding a blocking FAIL behind exit 0.
    if result.get("non_strict_warning"):
        emit(f"!!! {result['non_strict_warning']}", file=_sys.stderr, flush=True)
    emit(json.dumps({
        "overall": result["overall"],
        "strict": result["strict"],
        "non_strict_warning": result.get("non_strict_warning"),
        "exit_code": result["exit_code"],
        "receipt": str(paths["receipt"]),
        "gates": {g["name"]: g["status"] for g in result["gates"]},
    }, indent=2))
    return result["exit_code"]



def _concordance_cell(ss, bgc_id: str) -> str:
    """Triage-board Concordance cell: CONCORDANT/PARTIAL/DISCORDANT/NO_REFERENCE + matched compound.
    C1 v9.7.58 — wired from concordance_per_bgc in SourceScanBundle."""
    if not ss or not getattr(ss, "concordance_per_bgc", None):
        return ""
    c = ss.concordance_per_bgc.get(bgc_id, {})
    if not c:
        return ""
    verdict = c.get("verdict", "")
    if not verdict or verdict == "NO_REFERENCE":
        return ""
    compound = c.get("matched_compound", "") or ""
    frac = c.get("marker_frac")
    frac_str = f" ({int(frac*100)}% markers)" if frac is not None else ""
    return f"{verdict}: {compound}{frac_str}" if compound else verdict


def _misanchor_cell(t, mg):
    """Triage-board Misanchor cell: the negative mis-anchor flag PLUS the positive enediyne verdict and the
    matched anchor compound, so a reviewer can audit a gate firing without re-parsing (Doc 8 rec#3)."""
    parts = []
    base = getattr(t, "misanchor_flag", "") or ""
    if base:
        parts.append(base)
    ev = mg.get("enediyne_verdict", "") if isinstance(mg, dict) else ""
    if ev in ("GENUINE_E_SIGNAL", "E_SIGNAL_UNRESOLVED") and ev not in base:
        parts.append(f"ENE:{ev}")
    matched = mg.get("matched_anchor", {}) if isinstance(mg, dict) else {}
    if matched:
        parts.append("[" + "; ".join(f"{k}={v}" for k, v in matched.items()) + "]")
    return " ".join(parts)


def chatgpt_init_command(args) -> int:
    """Assistant discoverability: surface the shared assistant operating contract so the assistant
    can prove it located and read the current instruction file before doing work.

    Prints, reading live values straight from AGENTS.md (never from memory):
      - the path + SHA256 of AGENTS.md
      - the current bundle / engine / build string (the version-freshness probe: these
        change every cut, so emitting the *current* values demonstrates the *current*
        file was read, not a remembered older one)
      - the current known-gotcha line(s)
      - the recommended workflow
      - the inventory of shared instruction files that exist in this bundle
      - the contract's read-marker phrase, if defined, surfaced as a DOCUMENTED FIELD for
        the human to eyeball (a human-facing "did it read the file" marker — reported as
        data, not an instruction to act on)

    This command reads and reports; it changes no files.
    """
    import hashlib, re as _re
    from pathlib import Path

    root = Path(__file__).parent.parent
    start_here = root / "AGENTS.md"
    if not start_here.exists():
        emit("✗ AGENTS.md not found in this bundle — cannot confirm the "
              "shared assistant operating contract is present.")
        return 1

    text = start_here.read_text(encoding="utf-8")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

    be = _re.search(r"bundle / engine\s*:\s*(.+)", text)
    bundle_engine = be.group(1).strip() if be else f"v{BUNDLE_VERSION} / {__version__}"

    def _extract_chatgpt_gotcha(txt: str) -> str:
        lines = txt.splitlines()
        out: list[str] = []
        capture = False
        for line in lines:
            if "known gotcha (this build)" in line.lower():
                capture = True
                _, _, rest = line.partition(":")
                if rest.strip():
                    out.append(rest.strip())
                continue
            if capture:
                stripped = line.strip()
                if stripped.lower().startswith("workflow"):
                    break
                if stripped:
                    out.append(stripped)
        return " ".join(out).strip() or "(see AGENTS.md §3)"

    gotcha_line = _extract_chatgpt_gotcha(text)
    cp = _re.search(r"challenge[ _]phrase\s*[:=]\s*(.+)", text, _re.I)
    challenge_phrase = cp.group(1).strip().strip('">') if cp else None

    candidates = [
        "AGENTS.md", "CLAUDE.md", "README.md", "bootstrap_contract.yml",
    ]
    present = [c for c in candidates if (root / c).exists()]

    emit("◆ SAPOTE–MAMEY · SHARED ASSISTANT — contract surface")
    # v9.7.371: these two lines used to hardcode "✓ present"; a proof-of-read surface must not
    # assert presence it did not check. Route through the same existence test as the list below.
    def _mark(_rel):
        return "✓ present" if (root / _rel).exists() else "✗ absent in this bundle"
    emit(f"   instruction file : AGENTS.md  {_mark('AGENTS.md')}  (root bootstrap: AGENTS.md)", f"   bootstrap contract: bootstrap_contract.yml  {_mark('bootstrap_contract.yml')}", f"   sha256           : {sha}", f"   bundle / engine  : {bundle_engine}", f"   known gotcha     : {gotcha_line}", sep="\n")
    emit(f'   workflow         : doctor → inspect → run(gold + --capped-session) → validate → list-bgcs → mode-b → guide → render-figures → ingest-receipts', f'   instruction files present ({len(present)}/{len(candidates)}):', sep="\n")
    for c in present:
        emit(f"     ✓ {c}")
    for c in [c for c in candidates if c not in present]:
        emit(f"     ✗ {c}  (absent in this bundle)")
    if challenge_phrase:
        emit(f'   contract read-marker (human-facing, documented): {challenge_phrase!r}', '     ↳ a documented proof-of-read marker for the operator to check; reported here as data, not an instruction to act on.', sep="\n")
    emit("\n   The authoritative version-freshness proof is the bundle/engine/build + gotcha "
          "line above: they change every cut, so the CURRENT values demonstrate the CURRENT "
          "file was read. Read them from this file at emit time, never from memory.")
    return 0


def doctor_command(args) -> int:
    """B5: mamey doctor — pre-flight environment check for new users.

    Checks Python version, required/optional dependencies, write permissions,
    antiSMASH ZIP detection, and bundle integrity. Prints a clear PASS/WARN/FAIL
    per item so a new user can diagnose their environment in under 60 seconds.
    """
    import importlib.util, sys, os, platform
    from pathlib import Path

    BUNDLE_ROOT = Path(__file__).parent.parent
    ok, warn, fail = [], [], []

    def _have(mod):
        try: return importlib.util.find_spec(mod) is not None
        except Exception: return False

    # Python version
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        ok.append(f"Python {major}.{minor} ✓")
    elif (major, minor) >= (3, 8):
        warn.append(f"Python {major}.{minor} — 3.10+ recommended (3.8+ works)")
    else:
        fail.append(f"Python {major}.{minor} — 3.8+ required")

    # Required deps
    for mod, label in [("openpyxl", "openpyxl (workbooks)"), ("zipfile", "zipfile (stdlib)")]:
        if _have(mod):
            ok.append(f"{label} ✓")
        else:
            fail.append(f"{label} MISSING — required for workbooks (pip install openpyxl; "
                        f"project https://openpyxl.readthedocs.io, MIT licence; not redistributed in this bundle — "
                        f"installing it is the user's responsibility; re-run `mamey doctor` to confirm)")

    # Core render dependency (NC-009): reportlab is CORE for Mode-B PDF/DOCX export — surfaced
    # DISTINCTLY from the optional figure extras below so a 'PDF-ready' claim is never silent.
    from mamey.modeb_export import core_render_dependency_status as _crds
    _rd = _crds()
    if _rd["present"]:
        ok.append("reportlab (Mode-B PDF/DOCX export) ✓")
    else:
        warn.append(f"{_rd['state']}: reportlab — {_rd['detail']}")

    # Optional deps
    for mod, label, hint in [
        ("Bio", "biopython", "optional for core (GBK shim in use if absent) — but REQUIRED for `mamey triage-raw` AND `blastp-online` (parses NCBI BLAST XML). The bundled wheel is cp312/manylinux x86_64 only, so on macOS/arm64 or other Pythons it will NOT install offline — `pip install biopython` (needs network)"),
        ("ijson", "ijson", "optional; bounded JSON streaming (pip install ijson; https://github.com/ICRAR/ijson, BSD; a pure-Python copy is vendored at mamey/_vendor/ijson so this is a speed-up)"),
        ("numpy", "numpy", "optional; required for figures (pip install numpy; https://numpy.org, BSD)"),
        ("matplotlib", "matplotlib", "optional; required for figures (pip install matplotlib; https://matplotlib.org, PSF-based licence)"),
        ("pytest", "pytest", "optional; required to run the test suite (pip install pytest; https://pytest.org, MIT)"),
    ]:
        # v9.7.405 (WAC-01375 item 11): every add-on line names the package, the official project
        # URL and licence family, and the fact that the bundle does NOT redistribute it — the
        # user installs and accepts the third-party terms; `mamey doctor` only verifies presence.
        # Tested versions live in docs/EXTERNAL_TOOL_INVENTORY.md / the offline wheelhouse, not here.
        if _have(mod):
            ok.append(f"{label} ✓")
        else:
            warn.append(f"{label} absent — {hint}; not shipped in the bundle — install it yourself and re-run `mamey doctor`")

    # Write permissions
    # BC2-398: mkdir(parents=True) created BOTH runs/ and runs/_doctor_probe/, but only the
    # leaf was ever rmdir()'d — every `mamey doctor` invocation left an empty runs/ directory
    # behind permanently. That litter trips tools/public_release_audit.py's `runs*` glob check
    # (PUBLIC RELEASE AUDIT: FAIL), which is a required, non-continue-on-error step in
    # .github/workflows/ci.yml's release-gates job — reproduced live against the sealed .397
    # candidate before this fix. Only remove runs/ here if the probe itself created it (never
    # touch a pre-existing runs/ that may hold real `mamey run` output); rmdir() only succeeds
    # on an empty directory regardless, as a second safety margin.
    _runs_root = BUNDLE_ROOT / "runs"
    _runs_preexisted = _runs_root.exists()
    test_dir = _runs_root / "_doctor_probe"
    try:
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "probe.txt").write_text("ok", encoding="utf-8")
        (test_dir / "probe.txt").unlink()
        test_dir.rmdir()
        if not _runs_preexisted:
            try:
                _runs_root.rmdir()
            except OSError:
                pass  # not empty (a concurrent run populated it) or already gone — never force it
        ok.append("write permissions ✓ (./runs/ writable)")
    except Exception as e:
        fail.append(f"write permissions FAIL — cannot write to ./runs/: {e}")

    # Bundle integrity: key files present
    for rel in ["mamey_run.py", "mamey/__init__.py", "mamey/cli.py",
                "docs/START_HERE.md", "CITATION.cff", "TAG"]:
        if (BUNDLE_ROOT / rel).exists():
            ok.append(f"bundle file {rel} ✓")
        else:
            warn.append(f"bundle file {rel} missing (non-fatal if not using that feature)")

    # antiSMASH ZIP detection in current dir
    zips = list(Path(".").glob("*.zip"))
    as_zips = []
    if zips:
        import zipfile
        for z in zips[:5]:
            try:
                with zipfile.ZipFile(z) as zf:
                    names = regular_file_names(zf)
                    if any(n.endswith(".gbk") or n.endswith(".json") for n in names):
                        as_zips.append(z.name)
            except Exception as _zip_exc:
                warn.append(
                    f"antiSMASH ZIP unreadable: {z.name} ({type(_zip_exc).__name__})"
                )
    if as_zips:
        ok.append(f"antiSMASH ZIP(s) detected in current dir: {', '.join(as_zips[:3])}")
    else:
        warn.append("no antiSMASH ZIPs found in current directory (run from the dir containing your ZIPs, or supply --input-zip <path>)")

    # Platform note
    plat = platform.system()
    if plat == "Windows":
        warn.append("Windows detected — SIGALRM timeout guard unavailable (non-fatal; timeouts simply not enforced)")

    # Sapote add-ons: comparative-genomics stack (optional; installable offline from the bundle)
    gem_stack = [("pyrodigal", "S1 gene prediction"), ("pyfastani", "S2 ANI"),
                 ("pyswrd", "S4/S5 alignment"), ("Bio", "parsing/alignment")]
    gem_have = [lbl for mod, lbl in gem_stack if _have(mod)]
    if len(gem_have) == len(gem_stack):
        ok.append("Sapote add-ons ✓ (two-strain comparison ready: mamey compare)")
    elif gem_have:
        warn.append(f"Sapote add-ons partial ({len(gem_have)}/{len(gem_stack)}) — "
                    "run bundle_support/install_sapote_addons.sh to enable `mamey compare`")
    else:
        warn.append("Sapote add-ons not installed — run bundle_support/install_sapote_addons.sh "
                    "(offline, from bundled wheels) to enable two-strain comparison")
    # External reference datasets (v9.7.362: user-provisioned, never redistributed — licences and
    # release cadence belong to upstream). Report each so an operator knows exactly what to fetch
    # before a run degrades, rather than discovering it mid-analysis as a NOT MEASURED section.
    try:
        from . import external_data as _xd
        _st = _xd.status()
        _have_ds = [k for k, v in _st.items() if v["provisioned"]]
        _miss_ds = [k for k, v in _st.items() if not v["provisioned"]]
        if _have_ds:
            ok.append(f"External datasets provisioned ✓ ({len(_have_ds)}/{len(_st)}): {', '.join(sorted(_have_ds))}")
        for _k in sorted(_miss_ds):
            _d = _st[_k]
            warn.append(f"External dataset '{_k}' not provisioned ({_d['what']}) — "
                        f"set ${_d['env_var']} or $MAMEY_DATA_ROOT/<subdir>; "
                        f"get it from {_d['upstream']} (see docs/EXTERNAL_DATA.md)")
        if _miss_ds:
            warn.append("Sections depending on an absent dataset render NOT MEASURED — never an empty "
                        "result. Absence of a comparator is not evidence of novelty.")
        # CUT-10B: the governed denominator depends on a specific exclusions.json. Print its exact
        # resolved path when source-bound, and make fallback use a warning rather than an all-clear.
        # Merely seeing `official_data` in the external registry is not enough unless exclusions.py
        # resolves that same root.
        try:
            from . import exclusions as _excl
            _den = _excl.governed_denominator()
            _official_root = _xd.resolve("official_data")
            # v9.7.395: governed_denominator() returns {} on a genuinely code-only tree (no
            # OFFICIAL_DATA reachable at all -- exactly the case the warn branch below exists to
            # report). A bare _den['strains'] KeyErrors on that empty dict, and the outer
            # `except Exception: pass` then silently swallows it -- so the intended warning could
            # never actually print; the doctor probe just silently skipped this check instead.
            # .get(..., "?") keeps this check reporting something in every case, matching what
            # the surrounding ok/warn branches already intend.
            _denom = f"{_den.get('strains', '?')} strains / {_den.get('regions', '?')} regions"
            if _official_root is not None:
                ok.append(
                    f"Governed denominator source-bound ✓ ({_denom}; "
                    f"{_official_root / 'exclusions.json'})"
                )
            else:
                warn.append(
                    f"Governed denominator uses in-module _DEFAULT ({_denom}); set "
                    "$MAMEY_OFFICIAL_DATA or place "
                    "$MAMEY_DATA_ROOT/OFFICIAL_DATA/exclusions.json to bind the governed source"
                )
        except Exception as _den_exc:
            warn.append(
                f"governed denominator status unavailable ({type(_den_exc).__name__})"
            )
    except Exception as _e:  # never let a doctor probe break doctor
        warn.append(f"external-data status unavailable ({_e.__class__.__name__})")
    # CUT-05 (v9.7.364): companion BINARIES and reference DATASETS answered the same operator
    # question -- "what do I still need to install?" -- through two unrelated registries, so
    # `doctor` reported a missing MIBiG index but stayed silent on a missing phylogenomics
    # environment. GToTree is GPL-3 and external by design (the bundle plans and ingests; the
    # operator executes), so it will never be vendored -- which is exactly why its absence has to
    # be VISIBLE rather than discovered halfway through a tree run.
    import shutil as _sh_phylo
    _phylo = [("GToTree", "core-genome tree (138 SCG)"),
              ("iqtree3", "ML inference"), ("iqtree2", "ML inference"), ("iqtree", "ML inference"),
              ("fastANI", "whole-genome ANI — the rank-delimiting measurement")]
    _have_iq = any(_sh_phylo.which(b) for b in ("iqtree3", "iqtree2", "iqtree"))
    _missing_phylo = []
    if not _sh_phylo.which("GToTree"):
        _missing_phylo.append("GToTree")
    if not _have_iq:
        _missing_phylo.append("IQ-TREE (iqtree3/iqtree2/iqtree)")
    if not _sh_phylo.which("fastANI"):
        _missing_phylo.append("fastANI")
    if not _missing_phylo:
        ok.append("Phylogenomics companions ✓ (GToTree + IQ-TREE + fastANI on PATH)")
    else:
        warn.append(
            "Phylogenomics companions not on PATH: " + ", ".join(_missing_phylo)
            + " — install them in your own environment (GPL-3, never vendored; see "
              "docs/GTOTREE_WORKFLOW.md). Without them `plan_gtotree_iqtree.py` correctly refuses "
              "to authorize a run (HOLD_TOOL_MISSING); trees are NOT MEASURED, not absent.")
    # DIAMOND fast-path is optional and NOT vendored
    import shutil as _sh
    if _sh.which("diamond"):
        ok.append("DIAMOND binary on PATH ✓ (compare fast-path available)")
    else:
        warn.append("DIAMOND binary not on PATH — compare uses the proven pyswrd backend "
                    "(fine for a strain pair); see sapote_addons/DIAMOND_STATUS.md")
    # Science stack (optional; vendored in sapote_addons/wheels/) — pyhmmer covers most of
    # the DIAMOND gap (offline profile-HMM search); pyskani is a fragmentation-robust ANI backend.
    sci = [("pyhmmer", "offline HMMER3 profile search"), ("pyskani", "fragmentation-robust ANI"),
           ("pyfamsa", "MSA"), ("gb_io", "fast GenBank I/O"), ("pyrodigal_gv", "phage/giant-virus gene calling")]
    sci_have = [lbl for mod, lbl in sci if _have(mod)]
    if sci_have:
        ok.append(f"Science stack: {len(sci_have)}/{len(sci)} available "
                  f"({', '.join(sci_have)}) — bundle_support/install_sapote_addons.sh for the rest")
    else:
        warn.append("Science stack (pyhmmer/pyskani/pyfamsa/gb-io) not installed — "
                    "run bundle_support/install_sapote_addons.sh to enable offline HMM search + skani ANI")
    # Companion-files reminder — the anti-'assumed unavailable' guard
    if (BUNDLE_ROOT / "docs/COMPANION_FILES.md").exists():
        ok.append("docs/COMPANION_FILES.md present — companion inputs (antiSMASH ZIPs, genome "
                  "FASTAs, MIBiG refs) attach separately; ask the user if one is missing "
                  "rather than assuming a feature is unavailable")

    # Transport probe (v9.7.216, spec §6.6): report which BLASTp transport is live, so a run knows
    # before it burns a submission which channel to use. Opt-in (--probe-transports) + offline-safe:
    # short timeout, any error downgrades to WARN, never hangs the check.
    if getattr(args, "probe_transports", False):
        import urllib.request

        def _probe(url, timeout=6):
            try:
                body = urllib.request.urlopen(url, timeout=timeout).read(400).decode("utf-8", "replace")
                return True, body
            except Exception as exc:
                return False, f"{type(exc).__name__}"

        ncbi_up, ncbi_body = _probe("https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Web&PAGE_TYPE=BlastHome")
        if ncbi_up and "Temporarily unavailable" not in ncbi_body and len(ncbi_body) > 100:
            ok.append("NCBI BLAST transport LIVE — `blastp-online` (nr) available")
        else:
            reason = "Temporarily unavailable" if (ncbi_up and "Temporarily unavailable" in ncbi_body) else ("unreachable: " + ncbi_body)
            warn.append(f"NCBI BLAST transport DOWN ({reason}) — use `mamey blastp-ebi` fallback (EBI, no nr, DB-tagged)")
        ebi_up, ebi_body = _probe("https://www.ebi.ac.uk/Tools/services/rest/ncbiblast/parameters")
        if ebi_up:
            ok.append("EBI BLAST transport LIVE — `blastp-ebi` fallback available (uniprotkb_bacteria/trembl; no nr)")
        else:
            warn.append(f"EBI BLAST transport unreachable ({ebi_body}) — no online BLASTp channel available right now")

    # Companion tools (AMBER v9.7.331): external analysis tools are DETECTED, NOT BUNDLED.
    # They live downstream of a sealed Mamey package (BiG-SCAPE/clinker/GECCO/phylogenomics/…)
    # and are all OPTIONAL — a missing companion NEVER changes doctor's PASS/FAIL (they are not
    # appended to ok/warn/fail). Opt-in with `--companions` so the default doctor stays fast and
    # offline. antiSMASH is the one REQUIRED-upstream input (it produces the run's input ZIP).
    if getattr(args, "companions", False):
        try:
            from .companion_tools import probe_tools
            probes = probe_tools()
        except Exception as e:
            probes = None
            emit(f"\nCompanion tools: registry unavailable ({type(e).__name__}: {e}) — core unaffected.")
        if probes:
            by_cat: dict[str, list] = {}
            for pr in probes:
                by_cat.setdefault(pr.tool.category, []).append(pr)
            n_present = sum(1 for pr in probes if pr.present)
            emit(f'\nCompanion tools — DETECTED, not bundled (offline core unaffected): {n_present}/{len(probes)} present', '  These are OPTIONAL downstream analysis tools; missing ones do not affect the run.\n', sep="\n")
            for cat in sorted(by_cat):
                emit(f"  [{cat}]")
                for pr in by_cat[cat]:
                    t = pr.tool
                    tag = {"REQUIRED-upstream": " (REQUIRED-upstream)",
                           "on-request": " (on request / heavy)"}.get(t.requirement, "")
                    if pr.present:
                        ver = pr.detected_version or "version unknown"
                        emit(f"    ✅  {t.name}{tag}: {ver}")
                    else:
                        emit(f"    ⬚   {t.name}{tag}: not found — {t.detection_command}", f"         install: {pr.install_hint}", sep="\n")
                emit()
            emit("  Full purpose + per-OS install + usage recipes: docs/companion_tools.md")

    # Summary
    emit(f"\nMamey doctor — bundle {BUNDLE_ROOT.name}", f"Platform: {plat} | Python {sys.version.split()[0]}\n", sep="\n")
    for line in ok:   emit(f"  ✅  {line}")
    for line in warn: emit(f"  ⚠️   {line}")
    for line in fail: emit(f"  ❌  {line}")
    emit()
    if fail:
        emit(f"DOCTOR: {len(fail)} blocking issue(s) — fix the ❌ items before running mamey.")
        return 1
    elif warn:
        emit(f"DOCTOR: PASS with {len(warn)} warning(s) — optional items only; mamey will run.")
        return 0
    else:
        emit("DOCTOR: ALL CLEAR — environment looks good.")
        return 0


def cohort_command(args) -> int:
    """`mamey cohort` -- the cross-strain front-door. Produces a cohort deliverable bundle
    (cross-strain synthesis report + cohort figures) and enforces a mandatory-deliverable
    gate: a completed cohort run must hand back at least one human-readable deliverable."""
    from .cohort_deliverable import run_cohort_deliverable
    strains = args.strains.split(",") if getattr(args, "strains", None) else None
    res = run_cohort_deliverable(
        runs_dir=args.runs_dir, out=args.out, strains=strains,
        master_path=getattr(args, "master_path", None),
        novelty_basis=getattr(args, "novelty_basis", "fully_dark"),
        with_figures=not getattr(args, "no_figures", False),
        figure_series=getattr(args, "series", "all"),
        public_only=getattr(args, "public_only", False),
    )
    for w in res.warnings:
        emit(f"  [WARN] cohort: {w}")
    if res.synthesis_report:
        emit(f"  DELIVERABLE: {res.synthesis_report}")
    if res.figures_dir and res.figure_count:
        emit(f"  cohort figures: {res.figure_count} -> {res.figures_dir}")
    if not res.ok:
        # mandatory-deliverable gate failed: no human-readable deliverable produced
        emit("  [FAIL] cohort mandatory-deliverable gate: no deliverable emitted. "
              "Most likely no verified cohort master workbook was found -- build the "
              "master first or pass --master-path.")
        return 1
    emit(f"cohort: deliverable bundle -> {res.out_dir} "
          f"({len(res.deliverables)} deliverable(s), {len(res.strains)} strain(s))")
    return 0


def cohort_leads_command(args) -> int:
    """FA1: emit COHORT_PRIORITY_LEADS.csv -- the cross-strain union of Exceptional+High
    triage leads, ranked by (lead tier, AF, AB). Non-scoring re-projection; carries a
    MIXED-ENGINE comparability caution when strains span engine versions."""
    from .cohort_leads_ledger import run as _leads_run
    meta = _leads_run(args.runs_dir, args.out)
    emit(f"cohort-leads: {meta['n_leads']} Exceptional+High leads across "
          f"{meta['n_strains']} strain(s) -> {meta['out_path']}")
    if meta["mixed_engine"]:
        emit(f"  [CLAIM-SAFETY] MIXED engine versions {meta['engine_versions']}; "
              f"cross-strain rank is a routing prior only, not a confident call.")
    return 0 if meta["n_leads"] else 1


def activity_leads_command(args) -> int:
    """Emit exact-locus top-N AF/AB routing boards for every sealed strain."""
    from .activity_lead_report import run as _activity_leads_run
    meta = _activity_leads_run(
        args.runs_dir,
        args.out,
        top_n=args.top_n,
        canonical_crosswalk=getattr(args, "canonical_crosswalk", None),
        require_crosswalk=getattr(args, "require_crosswalk", False),
    )
    emit(
        f"activity-leads: {meta['n_rows']} board position(s) across "
        f"{meta['n_strains']} strain(s) -> {meta['paths']['report_md']}"
    )
    if meta["mixed_engine"]:
        emit(
            f"  [CLAIM-SAFETY] MIXED engine versions {meta['engine_versions']}; "
            "cross-version score magnitudes are not strictly comparable."
        )
    if meta["unbound_rows"]:
        emit(
            f"  [HOLD] {meta['unbound_rows']} source-local row(s) were not admitted; "
            f"see {meta['paths']['unbound_csv']}"
        )
    if not meta["complete"]:
        emit(
            "  [FAIL] one or more strains had fewer than the requested top-N "
            "canonical-bound rows; outputs remain partial."
        )
        return 1
    return 0 if meta["n_strains"] else 1


def activity_lead_genes_command(args) -> int:
    """Add source-bound gene-level class foundations to an activity-lead board."""
    from .activity_lead_genes import run as _activity_lead_genes_run
    meta = _activity_lead_genes_run(
        args.leads_csv,
        args.out,
        top_n=args.top_n,
    )
    emit(
        f"activity-lead-genes: {meta['gene_anchor_rows']} gene anchor(s) across "
        f"{meta['loci_with_gene_profiles']} exact locus/loci -> {meta['paths']['loci_csv']}"
    )
    if meta["holds"]:
        emit(
            f"  [HOLD] {meta['holds']} exact locus/loci were not source-bound; "
            f"see {meta['paths']['holds_csv']}"
        )
    return 0 if meta["loci_with_gene_profiles"] and not meta["holds"] else 1


def cohort_assemble_command(args) -> int:
    """FA1: assemble sealed packages into COHORT_MASTER.csv (+ strain_summary /
    class_by_strain siblings, optional xlsx). Non-scoring re-projection of sealed
    capacity-level outputs; the figure-ready cohort substrate."""
    from .cohort_assemble import run as _assemble_run
    meta = _assemble_run(args.runs_dir, args.out, xlsx=getattr(args, "xlsx", False))
    emit(f"cohort-assemble: {meta['n_strains']} strain(s), {meta['n_bgcs']} BGC(s) -> "
          f"{meta['paths']['main']}")
    for k in ("strain_summary", "class_by_strain", "xlsx"):
        if meta["paths"].get(k):
            emit(f"  {meta['paths'][k]}")
    if meta["mixed_engine"]:
        emit(f"  [CLAIM-SAFETY] MIXED engine versions {meta['engine_versions']}; "
              f"cross-strain comparison is not strictly valid.")
    return 0 if meta["n_strains"] else 1


def comparator_coverage_command(args) -> int:
    """FA2: two-denominator comparator coverage for a sealed package (report-only, non-scoring).
    Consumes the sealed _3_mibig_* + CDS rows and re-expresses each named MIBiG comparator
    against both locus and defining-core denominators; emits _3b_comparator_coverage.csv."""
    from .mibig_comparator_coverage import run_for_package
    result = run_for_package(args.package, cohort_runs_dir=getattr(args, "cohort_runs_dir", None))
    # v9.7.371 fix: result has no n_rows/csv_path keys (run_for_package returns rows/_written,
    # confirmed against the module own main()) -- this always printed "0 comparator row(s)" and
    # the package dir instead of the real count/path, regardless of the actual result.
    _written = result.get("_written", {})
    emit(f"comparator-coverage: {len(result.get('rows', []))} comparator row(s) -> "
          f"{_written.get('csv', args.package)}")
    return 0


def signoff_command(args) -> int:
    """FA4: analysis sign-off QC gate (advisory; the "would a master's student sign off?"
    objective checks on Newick trees). Always exit 0 -- advisory only."""
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "tools"))
    import signoff_check
    argv = list(getattr(args, "files", None) or [])
    if getattr(args, "minutes", None) is not None:
        argv = ["--minutes", str(args.minutes)] + argv
    _saved = _sys.argv
    try:
        _sys.argv = ["signoff_check"] + argv
        return signoff_check.main()  # always returns 0 (advisory)
    finally:
        _sys.argv = _saved


def capabilities_command(args) -> int:
    """Delegate concept discovery to the canonical generated-inventory owner."""
    import importlib.util as _ilu
    import sys as _sys
    if args.top < 1:
        # composer note (.401): refusals write to stderr per the ratchet convention
        # (sealed .400 sits exactly at the 1635 ceiling; ceiling changes are Alex-signed only).
        _sys.stderr.write("capabilities: --top must be at least 1\n")
        return 2
    root = Path(__file__).resolve().parent.parent
    script = root / "tools" / "gen_tools_inventory.py"
    if not script.is_file():
        _sys.stderr.write(
            "capabilities: internal tool inventory owner is unavailable "
            f"({script})\n"
        )
        return 2
    spec = _ilu.spec_from_file_location("_mamey_gen_tools_inventory", script)
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.capabilities_command(args.keywords, root=root, top=args.top)


def _d3_tool_command(args) -> int:
    """FA/D3: dispatch a post-seal orphan-tier reporting tool (domain-reference /
    realistic-count / novelty-shortlist). Thin, non-blocking; never touches the run
    pipeline, gates, or any published tier."""
    # v9.7.409 (AUDIT_cli_code_bugs #4): the v9.7.405 positional-package alias assigns the bare
    # positional as a STR (main(): `args.package = _pos`), but these d3 verbs declare --package
    # with action="append", so a str here is iterated one CHARACTER at a time below — rebuilding
    # `--package w --package o ...` and crashing the sub-tool with `error: not a directory: w`.
    # Coerce a str to a single-element list so the positional spelling works like --package.
    _pkgs = args.package
    if isinstance(_pkgs, str):
        _pkgs = [_pkgs]
    argv = []
    for pkg in (_pkgs or []):
        argv += ["--package", pkg]
    if getattr(args, "out", None):
        argv += ["--out", args.out]
    if getattr(args, "top", None) is not None:
        argv += ["--top", str(args.top)]
    import importlib.util as _ilu, os as _os
    _script = {
        "domain-reference": "build_domain_reference.py",
        "realistic-count": "realistic_bgc_count.py",
        "novelty-shortlist": "build_novelty_shortlist.py",
    }[args._d3_tool]
    _path = _os.path.join(_os.path.dirname(__file__), "..", "tools", _script)
    _spec = _ilu.spec_from_file_location(_script[:-3], _path)
    _t = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_t)
    return _t.main(argv)


def cohort_figures_command(args) -> int:
    """Emit the gold gene/domain figure suite (data-only PNG + sidecar CSV) for one
    or more gold packages. 1 strain -> single-strain panels; >1 -> cross-strain set.
    PUBLIC (SID/WW) grouped first, PRIVATE (AJS-/PENDING-) last."""
    from .cohort_figures import generate
    strains = args.strains.split(",") if getattr(args, "strains", None) else None
    res = generate(runs_dir=args.runs_dir, out=args.out, strains=strains,
                   public_only=getattr(args, "public_only", False),
                   series=getattr(args, "series", "F"),
                   f13_cohort_manifest=getattr(args, "f13_cohort_manifest", None),
                   f13_cohort_manifest_sha256=getattr(args, "f13_cohort_manifest_sha256", None),
                   f13_denominator_registry=getattr(args, "f13_denominator_registry", None),
                   f13_denominator_registry_sha256=getattr(args, "f13_denominator_registry_sha256", None),
                   f13_profile=getattr(args, "f13_profile", "SINGLE_COLUMN"))
    if not res["figures"]:
        emit(f"cohort-figures: {res.get('note','no figures produced')}")
        return 1
    emit(f"cohort-figures: {res['figures']} figures for {len(res['strains'])} strain(s) "
          f"({', '.join(res['strains'])}) -> {res['out']}")
    for f in res.get("files", []):
        emit(f"  {f}")
    # v9.7.279: fuse the extended figure suite (11 cross-strain / per-BGC figures) into auto-emit.
    if getattr(args, "extended", True):
        try:
            from .cohort_figures_extended import generate_extended
            ext = generate_extended(runs_dir=args.runs_dir, out=args.out, strains=strains)
            emit(f"cohort-figures: +{ext['figures']} extended figures -> {args.out}")
            for _e in ext.get("errors", []):
                emit(f"  [extended WARN] {_e}")
            import shutil as _sh, os as _os
            _cap = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "docs", "COHORT_FIGURE_CAPTIONS.md")
            if _os.path.exists(_cap):
                _sh.copy(_cap, _os.path.join(args.out, "COHORT_FIGURE_CAPTIONS.md"))
                emit(f"  COHORT_FIGURE_CAPTIONS.md")
        except Exception as _e:  # never block the standard suite over the extended one
            emit(f"cohort-figures: extended suite skipped ({type(_e).__name__}: {_e})")
    return 0


def figure_factory_command(args) -> int:
    """Wire the standalone Figure Factory as a first-class subcommand (v9.7.409).

    Reads a hash-bound JSON config and renders the receipt-bound aggregate evidence
    figure suite via mamey/figure_factory_next.py::build; a phylogeny figure_kind is
    routed to mamey/phylogeny_figure_factory.py::build instead. Deterministic and
    offline: consumes only the config's own bound inputs, never touches scores, boards,
    or sealed packages, and does not alter the Factory's own logic. Emits the receipt
    status line plus each output's logical locator / size / SHA-256."""
    import sys as _sys
    from pathlib import Path as _Path
    from .figure_factory_next import build as _build_aggregate
    from .bioassay_figure_factory import (
        FIGURE_KIND as _BIOASSAY_KIND,
        PLAN_KIND as _BIOASSAY_PLAN_KIND,
        BioassayFigureHold as _BioassayFigureHold,
        build as _build_bioassay,
        build_plan as _build_bioassay_plan,
    )
    from .phylogeny_figure_factory import (
        CONCORDANCE_KIND as _CONCORDANCE_KIND,
        EVIDENCE_WIDGET_KIND as _EVIDENCE_WIDGET_KIND,
        TRACK_KIND as _TRACK_KIND,
        PhylogenyFigureHold as _PhylogenyFigureHold,
        build as _build_phylogeny,
    )
    config_path = _Path(args.config).expanduser()
    if not config_path.is_file():
        emit(f"figure-factory: config not found: {config_path}", file=_sys.stderr)
        return 1
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        emit(f"figure-factory: unreadable config ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    phylo_kinds = {_TRACK_KIND, _CONCORDANCE_KIND, _EVIDENCE_WIDGET_KIND}
    try:
        if config.get("figure_kind") in phylo_kinds:
            receipt = _build_phylogeny(config_path)
        elif config.get("figure_kind") == _BIOASSAY_KIND:
            receipt = _build_bioassay(config_path)
        elif config.get("figure_kind") == _BIOASSAY_PLAN_KIND:
            receipt = _build_bioassay_plan(config_path)
        else:
            receipt = _build_aggregate(config_path)
    except (_PhylogenyFigureHold, _BioassayFigureHold) as exc:  # typed Figure Factory refusal
        emit(f"figure-factory: REFUSED {exc}", file=_sys.stderr)
        return 2
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        emit(f"figure-factory: {type(exc).__name__}: {exc}", file=_sys.stderr)
        return 1
    emit(f"figure-factory: {receipt.get('status', 'OK')}")
    for out in receipt.get("outputs", []):
        emit(f"  {out['logical_locator']}  ({out['bytes']} bytes)  {out['sha256']}")
    return 0


def _load_deliverable_tool(name):
    """Import a single graduated widget/analysis generator from deliverable_tools/ by
    file path (the tools are source-tree readers, not shipped in the wheel). The
    deliverable_tools/ dir is put on sys.path first so the module can import its siblings
    (_widget_paths, etc.). Raises ImportError if the directory is absent."""
    import importlib.util as _ilu
    import os as _os
    import sys as _sys
    dt = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "deliverable_tools")
    if not _os.path.isdir(dt):
        raise ImportError(f"deliverable_tools/ not found next to the package ({dt})")
    if dt not in _sys.path:
        _sys.path.insert(0, dt)
    path = _os.path.join(dt, name + ".py")
    if not _os.path.exists(path):
        raise ImportError(f"deliverable_tools/{name}.py not found ({path})")
    spec = _ilu.spec_from_file_location(name, path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_WIDGET_CLAIM_SAFETY = (
    "  Widgets render class-level CAPACITY, not activity/structure; comparators (MIBiG/KCB/"
    "reference members) are similarity anchors, not identity; AB/AF are auto-floor routing "
    "priors, not measured activity. Judgment deferred.")


def overmerge_widgets_command(args) -> int:
    """Post-seal, non-blocking: emit the over-merge inspector widget set (one HTML per
    OVER_MERGED region + a ranked index) from the canonical over-merge register + region
    GBKs. Reads only those inputs; never touches scores, boards, or the sealed package."""
    import os as _os
    import sys as _sys
    try:
        mod = _load_deliverable_tool("overmerge_widget")
    except ImportError as exc:
        emit(f"overmerge-widgets: ERROR: {exc}", file=_sys.stderr)
        return 1
    register = args.register or getattr(mod, "DEFAULT_REGISTER", None)
    if not register or not _os.path.exists(register):
        emit(f"overmerge-widgets: over-merge register not found: {register}\n"
              f"  pass --register /path/to/OVERMERGE_REGISTER_GBK.tsv "
              f"(needs strain/node/region/verdict cols).", file=_sys.stderr)
        return 1
    try:
        res = mod.render_overmerge(register=register,
                                   root=args.root or mod.ROOT_DEFAULT, outdir=args.out)
    except Exception as exc:  # non-blocking
        emit(f"overmerge-widgets: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    emit(f"overmerge-widgets: {res['built']} over-merged region widget(s) across {res['n_strains']} strains ({res['skipped']} skipped) -> {res['index']}", _WIDGET_CLAIM_SAFETY, sep="\n")
    return 0

def _clade_deepdive_command(args) -> int:
    """Post-seal, non-blocking: run the genus/clade deep-dive apparatus (six tracks: ANI, BiG-SCAPE
    matrix, conserved-dark, nt-core-BGC clock, decontam-if-flagged, clinker) via the orchestrator
    in deliverable_tools/clade_deepdive.py, and write a <CLADE>_SYNTHESIS.md skeleton. Never blocks
    or raises into the seal; degrades gracefully (skips a track with a note when its input/tool is
    missing). Engine-neutral — reads genomes/GBKs/the cohort DB; never touches scores, tiers, boards,
    or the sealed package.

    Claim-safety: every track is class-level capacity/relatedness. ANI<95% = candidate distinct
    species (94-96% boundary/indeterminate; never AAI-as-ANI); BiG-SCAPE GCFs = sequence-similarity
    clustering, not compound identity; conserved-dark = conserved protein of unknown function.
    Judgment deferred."""
    import importlib.util as _ilu
    import os as _os
    import sys as _sys
    orch = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)),
                         "deliverable_tools", "clade_deepdive.py")
    if not _os.path.exists(orch):
        emit(f"clade-deepdive: orchestrator not found ({orch}); needs the source tree "
              f"(deliverable_tools/clade_deepdive.py).", file=_sys.stderr)
        return 1
    spec = _ilu.spec_from_file_location("clade_deepdive", orch)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    decontam = None
    if getattr(args, "decontam_assembly", None) and args.ref_target and args.ref_contaminant:
        decontam = (args.decontam_assembly, args.ref_target, args.ref_contaminant)
    try:
        results, synth = mod.run(
            args.clade, args.genomes, getattr(args, "db", None), args.strains,
            comparators=getattr(args, "comparators", None), out=args.out,
            proteomes=getattr(args, "proteomes", None), gbk_dir=getattr(args, "gbk_dir", None),
            decontam=decontam, fastani_bin=getattr(args, "fastani", None), cutoff=args.cutoff)
    except Exception as exc:  # never raise into the caller / seal
        emit(f"clade-deepdive: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    n_ok = sum(1 for r in results.values() if r.get("status") == "ok")
    if n_ok == 0:
        emit("clade-deepdive: no track produced output. Provide --genomes/--db (and optionally "
              "--gbk-dir/--proteomes) and re-run:\n"
              "  python deliverable_tools/clade_deepdive.py --clade <NAME> --genomes <DIR> "
              "--db <full_cohort.db> --strains id1,id2,... --out <DIR>", file=_sys.stderr)
    emit("  Class-level capacity/relatedness only; ANI 94-96% = boundary; GCFs = similarity, "
          "not identity. Judgment deferred.")
    return 0


def rggmci_widget_command(args) -> int:
    """Post-seal, non-blocking: emit the within-strain RG-GMCI split-pathway linkage widget
    (one HTML per strain) from each sealed package's *_4A_RGGMCI_ranked_pairs.csv. Reads
    only those CSVs; never touches scores, boards, or the sealed package."""
    import sys as _sys
    try:
        mod = _load_deliverable_tool("rggmci_widget")
    except ImportError as exc:
        emit(f"rggmci-widget: ERROR: {exc}", file=_sys.stderr)
        return 1
    if not args.strain and not args.all:
        emit("rggmci-widget: pass --strain AS-XXX or --all", file=_sys.stderr)
        return 1
    found = mod.discover(args.runs_root)
    if not found:
        emit(f"rggmci-widget: no *_4A_RGGMCI_ranked_pairs.csv found under "
              f"{args.runs_root or 'the documented runs root'} — nothing to render.",
              file=_sys.stderr)
        return 1
    try:
        res = mod.render(strain=args.strain, all_strains=args.all,
                         runs_root=args.runs_root, outdir=args.out)
    except (FileNotFoundError, ValueError) as exc:
        emit(f"rggmci-widget: {exc}", file=_sys.stderr)
        return 1
    except Exception as exc:  # non-blocking
        emit(f"rggmci-widget: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    for s, nn, ne, outp in res["built"]:
        emit(f"rggmci-widget: {s} · {nn} BGCs · {ne} pairs -> {outp}")
    emit(f"rggmci-widget: built {res['n']} strain widget(s)", _WIDGET_CLAIM_SAFETY, sep="\n")
    return 0


def _assembly_line_family_pdf(args, tool: str, label: str) -> int:
    """Shared driver for the two print companions (v9.7.413, BC2).

    `assembly-line-pdf`  -> assembly_line_pdf.py   (NRPS/PKS domain architecture, N per page)
    `bgc-gene-map`       -> bgc_gene_map.py        (EVERY gene in EVERY region, all classes)

    Post-seal and non-blocking, like the widget family: reads a sealed package's own tables and
    never touches scores, boards, tiers or the package itself. Both tools import their data layer
    from assembly_line_widget.py so a PDF and its interactive sibling cannot disagree.
    """
    import sys as _sys
    try:
        mod = _load_deliverable_tool(tool)
    except ImportError as exc:
        emit(f"{label}: ERROR: {exc}", file=_sys.stderr)
        return 1
    strains = list(args.strains) if getattr(args, "strains", None) else (
        [args.strain] if getattr(args, "strain", None) else [])
    if getattr(args, "all_strains", False):
        try:
            strains = sorted(_load_deliverable_tool("assembly_line_widget").discover(args.runs_root))
        except Exception as exc:
            emit(f"{label}: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
            return 1
    if not strains:
        emit(f"{label}: pass --strain AS-XXX, --strains A B C, or --all", file=_sys.stderr)
        return 1
    built = 0
    for st in strains:
        try:
            if mod.build_pdf(st, args.runs_root, args.out, getattr(args, "per_page", 6)):
                built += 1
        except Exception as exc:  # post-seal: never raise into the seal
            emit(f"  {label}: {st} skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
    if not built:
        emit(f"{label}: nothing rendered (inputs absent).", file=_sys.stderr)
        return 1
    emit(f"{label}: {built}/{len(strains)} strain PDF(s) -> {args.out}", _WIDGET_CLAIM_SAFETY, sep="\n")
    return 0


def assembly_line_pdf_command(args) -> int:
    return _assembly_line_family_pdf(args, "assembly_line_pdf", "assembly-line-pdf")


def bgc_gene_map_command(args) -> int:
    return _assembly_line_family_pdf(args, "bgc_gene_map", "bgc-gene-map")


def assembly_line_widget_command(args) -> int:
    """Post-seal, non-blocking: emit the NRPS/PKS assembly-line / domain-architecture reader
    (one HTML per strain) from a sealed package's antismash_modules.csv + gene_context.jsonl.
    Reads only those files; never touches scores, boards, or the sealed package."""
    import sys as _sys
    try:
        mod = _load_deliverable_tool("assembly_line_widget")
    except ImportError as exc:
        emit(f"assembly-line-widget: ERROR: {exc}", file=_sys.stderr)
        return 1
    all_strains = getattr(args, "all_strains", False)
    strains = None if (args.demo or all_strains) else ([args.strain] if args.strain else None)
    if not args.demo and not all_strains and not strains:
        emit("assembly-line-widget: pass --strain AS-XXX, --demo, or --all", file=_sys.stderr)
        return 1
    try:
        res = mod.render(strains=strains, demo=args.demo,
                         runs_root=args.runs_root, outdir=args.out,
                         all_strains=all_strains)
    except Exception as exc:  # non-blocking
        emit(f"assembly-line-widget: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    if res["n"] == 0:
        emit("assembly-line-widget: no strain had a readable package with NRPS/PKS "
              "assembly-line domains (inputs absent) — nothing rendered.", file=_sys.stderr)
        return 1
    emit(f"assembly-line-widget: {res['n']}/{res['requested']} strain reader(s) -> {res['outdir']}", _WIDGET_CLAIM_SAFETY, sep="\n")
    return 0


def af_leadboard_command(args) -> int:
    """Post-seal, non-blocking: emit the cohort ANTIFUNGAL (AF) capacity lead-board dashboard
    (single self-contained HTML) from the per-BGC master CSV + codex-judged cards. Reads only
    those inputs; never touches scores, boards, or the sealed package."""
    import os as _os
    import sys as _sys
    try:
        mod = _load_deliverable_tool("af_leadboard_widget")
    except ImportError as exc:
        emit(f"af-leadboard: ERROR: {exc}", file=_sys.stderr)
        return 1
    root = args.root or mod.ROOT_DEFAULT
    md = mod._master_dir(root)
    master_csv = args.master_csv or _os.path.join(md, "SAPOTE_PER_BGC_MASTER_all_AS.csv")
    if not master_csv or not _os.path.exists(master_csv):
        emit(f"af-leadboard: per-BGC master CSV not found: {master_csv}\n"
              f"  pass --master-csv /path/to/SAPOTE_PER_BGC_MASTER_all_AS.csv.",
              file=_sys.stderr)
        return 1
    outdir = args.out or mod.module_dir("_AF_LEADBOARD_MODULE", root)
    try:
        outp, leads, meta = mod.build(outdir, master_csv=master_csv, master_dir=md)
    except Exception as exc:  # non-blocking
        emit(f"af-leadboard: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    emit(f"af-leadboard: {meta['n_leads']} AF leads across {meta['n_strains']} strains -> {outp}", '  AF is a class-level CAPACITY prior (mechanism/domain content), NOT measured antifungal activity; non-inhibition never proves incapacity. ' + _WIDGET_CLAIM_SAFETY.strip(), sep="\n")
    return 0


def split_overmerge_cards_command(args) -> int:
    """Post-seal, non-blocking: run the deterministic per-protocluster SPLIT *_FULL.md card
    QC-fixer/generator over the cards named in the split manifest. Patches only the
    deterministic base of the cards (idempotent QCFIX blocks); never touches judgment verdict
    blocks, scores, boards, or the sealed package."""
    import os as _os
    import sys as _sys
    try:
        mod = _load_deliverable_tool("split_cards")
    except ImportError as exc:
        emit(f"split-overmerge-cards: ERROR: {exc}", file=_sys.stderr)
        return 1
    base = args.base or (mod.master_dir() if hasattr(mod, "master_dir") else None)
    brepo = args.blastp_repo or (mod.blastp_repo() if hasattr(mod, "blastp_repo") else None)
    manifest = args.manifest or (
        _os.path.join(mod.module_dir("_OVERMERGE_MODULE"), "SPLIT_FULL_CARDS_MANIFEST.tsv")
        if hasattr(mod, "module_dir") else None)
    if not manifest or not _os.path.exists(manifest):
        emit(f"split-overmerge-cards: split-card manifest not found: {manifest}\n"
              f"  pass --manifest /path/to/SPLIT_FULL_CARDS_MANIFEST.tsv.", file=_sys.stderr)
        return 1
    try:
        stats = mod.run_fixer(manifest, base, brepo, dry=args.dry_run,
                              only=args.only, limit=args.limit)
    except Exception as exc:  # non-blocking
        emit(f"split-overmerge-cards: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    emit(f"split-overmerge-cards: processed {stats['cards_processed']} card(s), changed {stats['cards_changed']} (D1 {stats['D1_localized_evidence']} / D2 {stats['D2_sec28']} / D3 {stats['D3_selfresist']} / D4 {stats['D4_boundary']} / D5 {stats['D5_classprose']}; {stats['missing']} missing, {stats['parse_fail']} parse-fail){(' [dry-run]' if args.dry_run else '')}", '  Injected QCFIX blocks are claim-safe: similarity is not identity; comparators are anchors, not identity; capacity is not production; boundaries are computational. Judgment deferred.', sep="\n")
    return 0




def _flagged_lead_command(args) -> int:
    """Post-seal, non-blocking: reader-side flagged-lead + Mode B compilation workflow (VGP v9.7.353).

    Dispatches three deliverable_tools loaded by path (same convention as _bigscape_command):
      majority-read  -> whole_bgc_majority_read.py   (whole-BGC MIBiG majority read + flags)
      surface-leads  -> surface_flagged_leads.py     (PROMISCUOUS_ONLY + coherent-LOW_ID groups)
      modeb-compile  -> build_modeb_compilation.py   (per-strain report+cards+overlay dossier)
    Engine-neutral: reads sealed per-gene tables / Mode B cards; never touches scores, tiers,
    boards, or the sealed package. Data root via MAMEY_DATA_ROOT. Class-level capacity only; a
    per-gene hit != product identity; judgment deferred."""
    import importlib.util as _ilu
    import os as _os
    import sys as _sys
    tool = {"majority-read": "whole_bgc_majority_read",
            "surface-leads": "surface_flagged_leads",
            "modeb-compile": "build_modeb_compilation"}[args.command]
    path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)),
                         "deliverable_tools", tool + ".py")
    if not _os.path.exists(path):
        emit(f"{args.command}: tool not found ({path}); needs deliverable_tools/{tool}.py",
              file=_sys.stderr)
        return 1
    argv = [tool]
    if args.command == "majority-read":
        if getattr(args, "cohort", False): argv.append("--cohort")
        if getattr(args, "strain", None): argv += ["--strain", args.strain]
        if getattr(args, "bgc", None): argv += ["--bgc", args.bgc]
        if getattr(args, "out", None): argv += ["--out", args.out]
        # v9.7.415: forward --force here too. surface-leads and modeb-compile got the
        # canonical-overwrite guard at .413; majority-read writes the same shape of canonical dated
        # deliverable and was missed, so without this its guard would be a one-way door.
        if getattr(args, "force", False): argv.append("--force")
    elif args.command == "surface-leads":
        # v9.7.412 (BC2): forward --out. Without it the tool could only ever write to the canonical
        # dated folder, so any exploratory run overwrote a real deliverable in place.
        if getattr(args, "out", None): argv += ["--out", args.out]
        # v9.7.413 (BC2): forward --force, or the canonical-overwrite guard is a one-way door.
        if getattr(args, "force", False): argv.append("--force")
    elif args.command == "modeb-compile":
        if getattr(args, "strain", None): argv += ["--strain", args.strain]
        if getattr(args, "strains", None): argv += ["--strains", *args.strains]
        if getattr(args, "no_docx", False): argv.append("--no-docx")
        # v9.7.413 (BC2): forward --out. Without it this command could only write into the two
        # canonical targets, so any exploratory run overwrote real deliverables in place.
        if getattr(args, "out", None): argv += ["--out", args.out]
        # v9.7.413 (BC2): forward --force, or the canonical-overwrite guard is a one-way door.
        if getattr(args, "force", False): argv.append("--force")
    spec = _ilu.spec_from_file_location(tool, path)
    mod = _ilu.module_from_spec(spec)
    old = _sys.argv
    # Post-seal failures leave the sealed package intact but must exit nonzero.
    from .canonical_write_guard import CanonicalOverwriteRefused
    try:
        spec.loader.exec_module(mod)
        _sys.argv = argv
        return int(mod.main() or 0)
    except CanonicalOverwriteRefused as exc:
        message, exit_code = str(exc), 3
    except SystemExit as se:
        if se.code is None:
            return 0
        if isinstance(se.code, int):
            return se.code
        message, exit_code = str(se.code), 1
    except Exception as exc:
        message, exit_code = f"skipped ({type(exc).__name__}: {exc})", 1
    finally:
        _sys.argv = old
    emit(f"{args.command}: {message}", file=_sys.stderr)
    return exit_code



def _bigscape_command(args) -> int:
    """Post-seal, non-blocking: RUN BiG-SCAPE 2.x on a sealed package / cohort / explicit GBK
    dir, produce the cohort SQLite DB, and chain the cohort widgets. Never blocks or raises into
    the seal; on any failure it prints a re-run hint and returns non-zero. Engine-neutral — reads
    region GBKs, runs the external binary, reads the produced DB; never touches scores, tiers,
    boards, or the sealed package.

    Claim-safety: BiG-SCAPE GCF families = sequence-similarity clustering, class-level only;
    comparators are similarity anchors, not compound identity. Judgment deferred."""
    import importlib.util as _ilu
    import os as _os
    import sys as _sys
    runner_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)),
                                "deliverable_tools", "bigscape_run.py")
    if not _os.path.exists(runner_path):
        emit(f"bigscape: runner not found ({runner_path}); needs the source tree "
              f"(deliverable_tools/bigscape_run.py).", file=_sys.stderr)
        return 1
    spec = _ilu.spec_from_file_location("bigscape_run", runner_path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        res = mod.run_pipeline(
            package=getattr(args, "package", None),
            runs_dir=getattr(args, "runs_dir", None),
            input_gbk_dir=getattr(args, "input_gbk_dir", None),
            out=args.out, bigscape_bin=args.bigscape_bin, pfam=args.pfam,
            cpus=args.cpus, cutoffs=args.cutoffs, record_type=args.record_type,
            classify=args.classify, work_dir=args.work_dir, dry_run=args.dry_run,
            run_widgets=args.run_widgets, widgets_out=args.widgets_out)
    except Exception as exc:  # never raise into the caller / seal
        emit(f"bigscape: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1
    if args.dry_run:
        return 0
    if not res.get("db"):
        emit("bigscape: no cohort DB produced. Re-run detached (no foreground timeout):\n"
              "  python deliverable_tools/bigscape_run.py --package <pkg> --out <dir> --cpus 4",
              file=_sys.stderr)
        return 1
    emit("  GCF = BiG-SCAPE sequence-similarity clustering, class-level only; comparators "
          "are similarity anchors, not identity. Judgment deferred.")
    return 0

def _phylo_run_command(args) -> int:
    """Post-seal, non-blocking: EXECUTE an APPROVED GToTree->IQ-TREE->sign-off->(fastANI) run via
    tools/run_planned_tree.py. Respects the project tree-approval gate (requires --approved); the
    planner (plan_gtotree_iqtree.py) stays the gate, this is the post-approval executor. Engine-neutral
    -- never touches scores/tiers/boards or the sealed package. Class-level phylogenomics; ANI is
    nucleotide identity only; judgment deferred."""
    import importlib.util as _ilu
    import os as _os
    import sys as _sys
    runner_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)),
                                "tools", "run_planned_tree.py")
    if not _os.path.exists(runner_path):
        emit(f"phylo-run: runner not found ({runner_path}); needs the source tree "
              f"(tools/run_planned_tree.py).", file=_sys.stderr)
        return 1
    spec = _ilu.spec_from_file_location("run_planned_tree", runner_path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    argv = ["--genome-list", args.genome_list, "--workdir", args.workdir,
            "--outgroup", args.outgroup, "--hmm", args.hmm,
            "--threads", str(args.threads), "--parallel", str(args.parallel)]
    if getattr(args, "ani_refs", None): argv += ["--ani-refs", args.ani_refs]
    if getattr(args, "ani_queries", None): argv += ["--ani-queries", args.ani_queries]
    if getattr(args, "signoff", None): argv += ["--signoff", args.signoff]
    if getattr(args, "approved", False): argv += ["--approved"]
    try:
        return mod.main(argv)
    except Exception as exc:  # never raise into the caller / seal
        emit(f"phylo-run: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1

def _refuse(reason: str) -> bool:
    """One typed stderr refusal line for the run-time input guards (H2 strain id, H10 outdir, H13 lock); one emission site."""
    emit(f"  REFUSED: {reason}", file=_sys.stderr)
    return True


def _refuse_unsafe_strain_id(strain_id: str) -> bool:
    """v9.7.409 (BC hostile audit H2): True (refused) if the id cannot be a safe path component."""
    from .strain_identity import validate_strain_id as _validate_sid, UnsafeStrainId as _UnsafeSid
    try:
        _validate_sid(strain_id)
        return False
    except _UnsafeSid as _exc:
        return _refuse(f"[strain] {_exc}")


_ENGINE_OWNED_TOP_DIRS = frozenset({
    "mamey", "tools", "tests", "docs", "wiki", "deliverable_tools", "examples", "prompts", "schemas",
    "Wheelhouse", "wheels", "hooks", "sapote_hooks", "debugging_modules", "bundle_support", "skills", "templates", "resources",
    "validation", "scripts", "deliverables", "SAPOTE_CONTROL", ".github",
})


def _refuse_outdir_inside_bundle(outdir) -> bool:
    """v9.7.409 (BC hostile audit H10/H6): refuse an output location that is the engine tree's ROOT itself
    (two empty cohort CSVs written there shipped in the .407 seal) or that lies inside an ENGINE-OWNED
    directory (`mamey/`, `tools/`, `tests/`, `docs/` …). A NEW top-level directory under the bundle
    (`out/`, `runs/`, `strains_out/`) is the documented first-run layout and stays allowed.
    Set MAMEY_ALLOW_BUNDLE_WRITES=1 to override."""
    import os as _os
    if _os.environ.get("MAMEY_ALLOW_BUNDLE_WRITES") == "1" or not outdir:
        return False
    bundle = Path(__file__).resolve().parent.parent
    target = Path(outdir).expanduser()
    refusal_reason = None
    try:
        full = target.resolve() if target.exists() else (target.parent.resolve() / target.name if target.parent.exists() else Path(_os.path.abspath(target)))
    except OSError as _exc:
        refusal_reason = (
            f"[outdir] could not resolve {outdir!s} safely "
            f"({type(_exc).__name__}: {_exc}); refusing output until the path can be resolved"
        )
    else:
        if full == bundle:
            refusal_reason = f"[outdir] {outdir!s} is the engine tree itself ({bundle}); write analysis outputs into a subdirectory or outside the bundle (MAMEY_ALLOW_BUNDLE_WRITES=1 to override)"
        elif bundle in full.parents and full.relative_to(bundle).parts[0] in _ENGINE_OWNED_TOP_DIRS:
            refusal_reason = f"[outdir] {outdir!s} resolves inside the engine-owned directory {full.relative_to(bundle).parts[0]}/ of the bundle; analysis outputs must not be written into engine directories (MAMEY_ALLOW_BUNDLE_WRITES=1 to override)"
    return _refuse(refusal_reason) if refusal_reason else False


def _acquire_package_lock(outdir, strain_id: str):
    """v9.7.409 (BC hostile audit H13): two `run` processes writing the same `<outdir>/<strain>/` raced on an
    atomic rename (`FileNotFoundError` in `os.replace`) and left one package built by two interleaved writers.
    A non-blocking advisory lock on `<outdir>/<strain>/.mamey.lock` makes the second process refuse with a
    typed line instead. Returns the open lock handle (kept for the process lifetime) or None when refused."""
    try:
        import fcntl as _fcntl
    except ImportError:  # non-POSIX: no advisory locks; keep behaviour unchanged
        return object()
    run_dir = Path(outdir) / str(strain_id)
    try:
        fh = open(run_dir / ".mamey.lock", "a+")
        _fcntl.flock(fh.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return fh
    except BlockingIOError:
        _refuse(f"[lock] another mamey run is writing {run_dir} right now (advisory lock held); wait for it or use a different --outdir")
        return None
    except OSError:
        return object()  # cannot lock (read-only fs etc.): do not block the run


def _start_command(args) -> int:
    """The single front door for a new session or agent: prints the five-command happy path with this
    bundle's real version, and runs `doctor` unless --no-doctor. Reads nothing from the user's project;
    changes nothing. Added v9.7.408 after ten root orientation files proved to be nine too many."""
    import os as _os
    import sys as _sys
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    try:
        lines = open(_os.path.join(root, "BUILD_STAMP.txt"), encoding="utf-8").read().splitlines()
    except OSError:
        lines = []
    stamp = {k.strip(): v.strip() for k, v in (ln.split("=", 1) for ln in lines if "=" in ln)}
    emit(f"Sapote-Mamey bundle {stamp.get('version', '?')} \u00b7 engine {__version__} "
         f"\u00b7 build {stamp.get('build', '?')}",
         "Deterministic extraction, judgment deferred. Outputs are class-level hypotheses.",
         "",
         "Happy path (run in order; do not skip validate):",
         "  python mamey_run.py doctor",
         "  python mamey_run.py inspect <antiSMASH.zip>",
         "  python mamey_run.py run --strain <ID> --input-zip <antiSMASH.zip> \\",
         "      --taxonomy '<Genus sp.>' --source '<isolation source>' --mode gold --capped-session",
         "  python mamey_run.py validate runs/<ID>/package",
         "  python mamey_run.py explain  runs/<ID>/package",
         "",
         "Then, on the sealed package: list-bgcs, mode-b, render-figures, ingest-receipts.",
         "Docs: CURRENT_DOCS_INDEX.md is the only authority on which documents are current.",
         "Agents: AGENTS.md is the shared contract; CLAUDE.md is its generated discovery alias.",
         "        Trees: docs/PHYLO_AUTOPILOT_WORKFLOW.md.",
         "",
         sep="\n")
    if getattr(args, "no_doctor", False):
        return 0
    try:
        return int(_doctor_via_start() or 0)
    except Exception as exc:  # start must never fail because doctor did
        emit(f"start: doctor could not run ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 0


def _doctor_via_start() -> int:
    parser = build_parser()
    ns = parser.parse_args(["doctor"])
    return ns.func(ns)


def _phylo_autopilot_command(args) -> int:
    """Post-seal, non-blocking: the 16S/genome upload front door (tools/phylo_autopilot.py, AMBER-408)
    reached through the one CLI, so there is a single phylogenetics entrance. Pass-through: everything
    after `phylo-autopilot` goes to the tool unchanged (`plan`, `route`, `run-16s`; see --help there).
    The tool refuses to spend CPU without --approved-by (tree-approval gate). Class-level neighbourhood,
    never a species or ANI call; judgment deferred."""
    import importlib.util as _ilu
    import os as _os
    import sys as _sys
    tool_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "tools", "phylo_autopilot.py")
    if not _os.path.exists(tool_path):
        emit(f"phylo-autopilot: tool not found ({tool_path}); needs the source tree.", file=_sys.stderr)
        return 1
    spec = _ilu.spec_from_file_location("phylo_autopilot", tool_path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    argv = list(getattr(args, "tool_args", []) or [])
    if argv[:1] == ["--"]:
        argv = argv[1:]
    try:
        rc = mod.main(argv)
        return int(rc or 0)
    except SystemExit as exc:
        return int(exc.code or 0) if not isinstance(exc.code, str) else 1
    except Exception as exc:  # never raise into the caller / seal
        emit(f"phylo-autopilot: skipped ({type(exc).__name__}: {exc})", file=_sys.stderr)
        return 1

def build_parser():
    import argparse
    p = argparse.ArgumentParser(
        prog="mamey",
        description=f"Mamey v{__version__} — BGC extraction, evidence review, comparative workflows, and validated packaging",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"Mamey {__version__} / Sapote-Mamey {BUNDLE_VERSION}",
    )
    sub = p.add_subparsers(dest="command")

    # --- run ---
    r = sub.add_parser("run", help="Run Mamey extraction on one or more antiSMASH ZIPs")
    # Single-strain arguments
    r.add_argument("--allow-accession-strain-id", action="store_true",
                   dest="allow_accession_strain_id",
                   help=("v9.7.372: permit a database accession (CP025018.1, GCA_000009765.1) to be "
                         "used as the strain identity. Off by default: the strain id becomes the name "
                         "of every output file, the manifest strain_id, the sealed package and every "
                         "downstream card and figure label."))
    r.add_argument("--strain", default=None,
                   help="Strain ID (single strain; derived from ZIP name if omitted)")
    r.add_argument("--display-name", default=None, dest="display_name",
                   help="Display name, e.g. 'Actinomadura rubrisoli H3C3'")
    r.add_argument("--input-zip", default=None,
                   help="Path to antiSMASH output ZIP (single strain)")
    r.add_argument("--accession", default=None,
                   help="NCBI accession placeholder. Accession-mode preprocessing is not bundled; supplying this without --input-zip exits with UNSUPPORTED_ACCESSION_MODE.")
    # Batch argument (alternative to --input-zip)
    r.add_argument("--strains", nargs="+", default=None,
                   help="Paths to ≥1 antiSMASH ZIPs for batch processing (up to ~3 recommended)")
    # Shared arguments
    r.add_argument("--outdir", default="./runs",
                   help="Output root directory (default: ./runs)")
    r.add_argument("--master", default=None,
                   help="Path to master workbook; created if absent; updated on every run")
    r.add_argument("--mode", default="gold",
                   choices=["standard", "gold"],
                   help=(
                       "gold = every BGC gets full Mode B (default and only analysis mode); "
                       "standard = DEPRECATED (retired v9.7.92) — aliased to gold. "
                       "(smoke removed v9.7.161: it produced a non-analyzable triage-only "
                       "package with no ranked board, DAPR, or comparison — a dead end.)"
                   ))
    r.add_argument("--taxonomy", default=None,
                   help="Taxonomy string. Batch: pipe-separated, e.g. 'Genus sp.|Streptomyces sp.'")
    r.add_argument("--source", default=None,
                   help="Host/habitat. Batch: pipe-separated.")
    # AMBER-03-2: --source is a free string, so a host read off a folder name and a host traced
    # to a GenBank record were indistinguishable downstream. Record the provenance STRENGTH so a
    # figure caption cannot inherit authority the datum does not have. Fail-safe default:
    # 'asserted' (an operator who says nothing has asserted, not traced).
    r.add_argument("--source-provenance", default="asserted", dest="source_provenance",
                   choices=["accession", "table", "filename", "asserted"],
                   help="Evidence strength for --source: accession (deposited record) | table "
                        "(authoritative strain table) | filename (inferred from a file/folder "
                        "label) | asserted (person-supplied, no on-disk trace; default). "
                        "Batch: pipe-separated. Descriptive only — never changes a score or gate.")
    r.add_argument("--release", default=None, choices=["PUBLIC", "PRIVATE"],
                   help="Operator release tag override. Default: derivation from the strain ID "
                        "(AS -> PUBLIC per the v9.7.236 PI decision; AJS/PENDING/unrecognized -> PRIVATE, "
                        "fail-safe). Use --release PUBLIC for a named reference genome / accession whose shape "
                        "the derivation does not recognize. A PUBLIC override is REFUSED on an AJS-/PENDING-/"
                        "registry-private strain (never operator-bypassable); it is honored on AS and on "
                        "unrecognized shapes.")
    r.add_argument("--privacy-profile", default=None,
                   help="Optional JSON profile of exact strain-to-named-tier assignments. A public override "
                        "is refused unless the exact strain is assigned to a profile tier with public_export=true. "
                        "Unassigned strains use the profile's required non-public default tier.")
    r.add_argument("--project-registry", default=None, dest="project_registry",
                   help="Path to a sapote_project_registry_v1 JSON file declaring user-defined "
                        "privacy tiers, per-strain publication/genome states, and optional bioassay "
                        "records. BR6-406-REBASE: does not yet drive release/privacy_tier derivation "
                        "-- see BR6_REBASE_MAP.md; currently only recorded on RunContext "
                        "(project_registry_sha256, assay_summary) and the manifest.")
    r.add_argument("--bioactivity", default=None,
                   help="Deprecated legacy scalar context. Omit it for NOT_SUPPLIED; it never creates a named assay default.")
    r.add_argument("--bioactivity-json", default=None, dest="bioactivity_json",
                   help="Typed bioactivity_metadata_v1 JSON object. Structural admission occurs before package creation.")
    r.add_argument("--metadata-csv", default=None, dest="metadata_csv",
                   help="Path to strain metadata CSV for cross-strain collection figures. "
                        "Optional: if absent, a figure availability report is written instead.")
    r.add_argument("--require-workbook", action="store_true", dest="require_workbook",
                   default=False,
                   help="Fail the run if workbook production fails (default: non-blocking).")
    r.add_argument("--brief", default="standard",
                   choices=["none", "minimal", "standard"],
                   help="Render deterministic extraction-layer strain brief (PDF+figures). "
                        "none = no brief (back-compat); minimal = ~2pp; standard = ~3pp (default)")
    r.add_argument("--token-budget", default="standard", dest="token_budget",
                   choices=["standard", "citation-compact"],
                   help="Output token budget/profile. citation-compact emits Citation_Ledger.csv/json "
                        "and compact technical/bench/layperson Markdown reports with one global caveat.")
    # v9.7.152: the capped-session timeout profile is assistant-neutral. --capped-session is the
    # canonical flag; --chatgpt-safe is a deprecated alias kept for back-compat (same dest, same
    # behavior, emits a one-line deprecation notice). Any wall-clock-capped LLM tool session
    # (ChatGPT, Claude, or otherwise) should use --capped-session.
    r.add_argument("--capped-session", "--chatgpt-safe", action="store_true", dest="chatgpt_safe", default=False,
                   help="P0: capped-session timeout profile: --brief none + --json-evidence off + "
                        "--require-workbook. Use inside any wall-clock-capped LLM tool session. "
                        "(--chatgpt-safe is a deprecated alias for this flag.)")
    r.add_argument("--capped-followup", "--chatgpt-followup", action="store_true", dest="chatgpt_followup", default=False,
                   help="Legacy no-op (v9.7.161): --capped-session now runs gold directly. "
                        "Previously required after a smoke+validate run to allow gold; smoke has "
                        "been removed, so this flag is retained only for back-compat and does nothing. "
                        "(--chatgpt-followup is a deprecated alias.)")
    r.add_argument("--heartbeat-seconds", type=int, default=20, dest="heartbeat_seconds",
                   help="Under --capped-session, emit heartbeat lines during quiet finalization stages at this interval (default: 20).")
    r.add_argument("--locus-maps", dest="locus_maps", default="auto",
                   choices=["auto", "off", "on"],
                   help="P0 (v9.7.101): locus-map render policy. auto = render unless a capped run "
                        "(brief=none) has >20 BGCs; off = never (default under --capped-session); "
                        "on = always. The phase is expensive on large strains.")
    r.add_argument("--antismash-profile", dest="antismash_profile", default="auto",
                   choices=["auto", "strict", "relaxed", "loose", "unknown"],
                   help=("antiSMASH hmmdetection strictness for THIS run; recorded in manifest.json/"
                         "commit_receipt for cross-strain comparability. Pooling strains run under "
                         "different profiles is unsafe (see tools/check_antismash_profile.py). "
                         "DEFAULT 'auto' reads the strictness recorded inside the ZIP; an explicit "
                         "value is honoured but a disagreement is reported as PROFILE_MISMATCH."))
    # NB: run defaults to "bounded" (stream+cap) by design; the blastp subcommand defaults
    # to "off" because it needs no antiSMASH-JSON evidence. capped-session overrides run to
    # "off". (Resolves the stale patch-14 audit note that expected run="off".)
    r.add_argument("--json-evidence", default="bounded", dest="json_evidence",
                   choices=["off", "bounded", "full"],
                   help=(
                       "antiSMASH JSON handling. bounded (default) = stream JSON "
                       "with ijson, capped; falls back to off if ijson is absent. "
                       "off = TXT clusterblast files only, never opens JSON, safe "
                       "for any genome size. "
                       "full = legacy full flatten, refuses files >20 MB (hangs on "
                       "large genomes like the 159 MB rubrisoli JSON). "
                       "GBK sec_met_domain Pfam extraction runs regardless of this flag."
                   ))
    r.add_argument("--hmm-scan", action="store_true", dest="hmm_scan",
                   help="Run the optional registry-backed pyHMMER domain pass; missing database or dependency is recorded as HMM_SCAN_UNAVAILABLE, never as a negative hit.")
    r.set_defaults(func=run_command)

    # --- validate ---
    v = sub.add_parser("validate", help="Validate an existing package directory")
    v.add_argument("package_dir", help="Path to unpacked Mamey package directory")
    v.add_argument("--workbook-strict", action="store_true",
                   help="(SM-P1-008) also validate workbook sheet content; exit 1 on any FAIL")
    v.add_argument("--manifest-contract", action="store_true",
                   help="run the manifest/package contract checker as an advisory; never changes validation status or exit code")
    v.set_defaults(func=validate_command)

    # --- seal-package (v9.7.125: one final sealing layer) ---
    sp = sub.add_parser("seal-package",
                        help="Run all QC gates on a package and emit a seal receipt")
    sp.add_argument("package_dir", help="Path to unpacked Mamey package directory")
    sp.add_argument("--strict", action="store_true",
                    help="always enforce: exit 1 if any blocking gate FAILs (overrides --advisory)")
    sp.add_argument("--advisory", action="store_true",
                    help="F05 opt-in: report-only — a blocking FAIL exits 0 (with a loud banner). "
                         "Default (neither flag) now ENFORCES: a blocking FAIL exits 1.")
    sp.add_argument("--out", default=None,
                    help="output dir for DEBUG_RECEIPT.md / seal_status.json / seal_findings.csv "
                         "(default: the package dir)")
    sp.set_defaults(func=seal_package_command)

    # --- render-figures (P1) ---
    rf = sub.add_parser("render-figures",
                        help="Render one selected figure set from a sealed Mamey package")
    rf.add_argument("--package", required=True,
                    help="Path to sealed package directory (containing manifest.json)")
    rf.add_argument("--outdir", default=None,
                    help="Output dir for figures (default: <package>/figures_rendered/)")
    rf.add_argument("--top-n", type=int, default=10, dest="top_n",
                    help="Top N leads in lead-board figures (default: 10)")
    rf.add_argument("--style", default="chatgpt-node-first",
                    choices=["chatgpt-node-first", "standard"],
                    help="Figure style: chatgpt-node-first uses node/contig label (default)")
    rf.add_argument("--figure-set", default="standard", dest="figure_set",
                    choices=["standard", "domain-level", "locus-maps", "cohort-class",
                             "mamey-native", "compiled-mamey"],
                    help="Which figure set: standard (default), domain-level, locus-maps, cohort-class, "
                         "mamey-native (alias: compiled-mamey)")
    rf.add_argument("--workbook", default=None, dest="workbook",
                    help="Cohort/master workbook path (required for --figure-set cohort-class, "
                         "mamey-native, and compiled-mamey)")
    rf.set_defaults(func=render_figures_command)

    # --- Wave A (v9.7.341) post-seal report/tooling subcommands (non-blocking, additive) ---
    # compound-families (roadmap #10)
    cfam = sub.add_parser("compound-families",
        help="Map a sealed package's anchored BGCs to compound families + related-known structures")
    cfam.add_argument("package"); cfam.add_argument("--out", default=None)
    cfam.add_argument("--no-structures", action="store_true")
    cfam.set_defaults(func=compound_families_command)

    # p450-tailoring (roadmap #11)
    p450 = sub.add_parser("p450-tailoring",
        help="Classify a sealed package's P450 genes (oxidative-tailoring vs crosslinker cassette)")
    p450.add_argument("package"); p450.add_argument("--out", default=None)
    p450.set_defaults(func=p450_tailoring_command)

    # assembly-line (roadmap #6, report half)
    asm = sub.add_parser("assembly-line",
        help="Predicted PKS/NRPS assembly line per BGC from the native _domains.csv")
    asm.add_argument("package"); asm.add_argument("--out", default=None)
    asm.set_defaults(func=assembly_line_command)

    # interactive-figures: emit the Codex widget-data aggregate FROM sealed
    # Mamey packages (so the interactive widgets + publication_bridge run on this
    # engine's output). Structural class-level counts only; judgment deferred.
    ifg = sub.add_parser("interactive-figures",
        help="Build cohort widget data from a directory of sealed packages")
    ifg.add_argument("--runs-dir", dest="runs_dir", required=True,
        help="Directory containing <STRAIN>/package/ sealed outputs")
    ifg.add_argument("--out", default="AS_All_Strains_Widget_Data.json",
        help="Output JSON path (default: AS_All_Strains_Widget_Data.json)")
    ifg.add_argument("--strains", nargs="*", default=None,
        help="Explicit strain list (default: discover all under --runs-dir)")
    ifg.add_argument("--emit-figures", action="store_true", dest="emit_figures",
        help="Also render publication figures via the vendored publication_bridge "
             "(needs reportlab; skipped if absent)")
    ifg.add_argument("--figures-out", dest="figures_out", default=None,
        help="Output dir for --emit-figures (default: <out>/figures_publication)")
    ifg.add_argument("--scope", default="GOVERNED",
        help="publication_bridge scope for --emit-figures (default: GOVERNED)")
    ifg.set_defaults(func=_interactive_figures_command)

    # codex-heatmaps: optional post-seal presentation pack for Figure Factory
    # matrix sidecars.  The explicit Codex name keeps this accessibility/widget
    # profile separate from deterministic extraction and every release/science
    # gate.  SVG/HTML generation is dependency-free and never edits a package.
    chm = sub.add_parser(
        "codex-heatmaps",
        help="Legacy-named Figure Factory command: convert matrix CSVs into SVG/HTML figure packs",
    )
    chm.add_argument("--input", nargs="+", required=True,
        help="One or more Figure Factory *_data.csv matrix sidecars")
    chm.add_argument("--outdir", required=True,
        help="Output directory (must remain outside sealed packages)")
    chm.add_argument("--title", default=None,
        help="Optional figure title override (best with one input)")
    chm.add_argument("--normalization", choices=["raw", "log1p"], default="log1p",
        help="Colour transform only; raw values remain in labels/tooltips (default: log1p)")
    chm.add_argument("--top-rows", type=int, default=40,
        help="Keep the highest raw-total rows; 0 keeps all (default: 40)")
    chm.add_argument("--rows-per-panel", type=int, default=30)
    chm.add_argument("--columns-per-panel", type=int, default=24)
    chm.add_argument("--annotate", choices=["auto", "all", "none"], default="auto")
    chm.add_argument("--citation", action="append", default=[],
        help="Citation note for caption/methods text; repeatable")
    chm.add_argument("--claim-prefix", default="",
        help="Optional PUBLIC/PRIVATE/governance prefix for the caption")
    chm.set_defaults(func=_codex_heatmaps_command)

    # codex-figure-catalog: registry-first expansion of Figure Factory. The
    # command emits 200 governed specifications (25 scientific families × 8
    # analytical lenses), explicitly including per-strain and cohort views.
    # Specifications declare readiness and do not pretend gated inputs exist.
    cfc = sub.add_parser(
        "codex-figure-catalog",
        help="Legacy-named Figure Factory command: emit the governed figure registry and caption/method catalog",
    )
    cfc.add_argument("--outdir", required=True,
        help="Output directory for JSON/CSV/HTML/caption-methods/QA artifacts")
    cfc.add_argument("--family", default=None,
        help="Optional three-letter family ID filter, e.g. MPG, BND, CLS")
    cfc.add_argument("--status", default=None,
        help="Optional exact readiness-status filter")
    cfc.set_defaults(func=_codex_figure_catalog_command)

    cfs = sub.add_parser(
        "codex-figure-sets",
        help="Legacy-named Figure Factory command: render implemented strain/cohort sets from the governed registry",
    )
    cfs.add_argument("--widget-data", required=True,
        help="AS_All_Strains_Widget_Data.json emitted from sealed Mamey packages")
    cfs.add_argument("--outdir", required=True,
        help="Output directory outside sealed packages")
    cfs.add_argument("--tranche", choices=("1", "2", "3", "4", "5", "6", "all"), default="1",
        help="Implemented tranche to render (default: 1)")
    cfs.add_argument("--source-bundle", default=None,
        help="Required for tranches 2-6/all; output of codex-figure-sources")
    cfs.add_argument("--lead-ledger", default=None,
        help="Required for tranche 6; optional for all (enables the 200-set atlas)")
    cfs.set_defaults(func=_codex_figure_sets_command)

    bgff = sub.add_parser(
        "codex-bigscape-figure-sets",
        help="Legacy-named Figure Factory command: render the optional BiG-SCAPE figure extension",
    )
    source = bgff.add_mutually_exclusive_group(required=True)
    source.add_argument("--bigscape-tsv")
    source.add_argument("--bigscape-db")
    bgff.add_argument("--bigscape-run", required=True,
        help="Exact run ID/label; never infer latest or largest")
    bgff.add_argument("--bigscape-cutoffs", required=True,
        help="Explicit comma-delimited cutoff list")
    bgff.add_argument("--run-manifest",
        help="Immutable run manifest; required for portable TSV input")
    bgff.add_argument("--bgc-bridge",
        help="Optional exact strain+bgc_id+locator bridge for boundary/host views")
    bgff.add_argument("--lead-ledger",
        help="Optional exact strain+bgc_id+locator declared-lead ledger")
    bgff.add_argument("--outdir", required=True,
        help="Per-job sibling output directory; sealed packages/databases are never mutated")
    bgff.set_defaults(func=_codex_bigscape_figure_sets_command)

    csrc = sub.add_parser(
        "codex-figure-sources",
        help="Legacy-named Figure Factory command: build a provenance-rich source bundle from sealed package ZIPs",
    )
    csrc.add_argument("--widget-data", required=True,
        help="Governed AS_All_Strains_Widget_Data.json")
    csrc.add_argument("--package-dir", required=True,
        help="Directory containing the sealed packages named by widget data")
    csrc.add_argument("--outdir", required=True,
        help="Output directory outside sealed packages")
    csrc.set_defaults(func=_codex_figure_sources_command)

    # dualpass (roadmap #8)
    dpl = sub.add_parser("dualpass",
        help="Merge two engine CLAIMS_LEDGER.tsv into a divergence table (claims_vocab enum)")
    dpl.add_argument("claude"); dpl.add_argument("codex"); dpl.add_argument("--out", default=None)
    dpl.add_argument("--no-normalize", action="store_true"); dpl.add_argument("--miscalls", default=None)
    dpl.set_defaults(func=dualpass_command)

    # lead-pages (Wave B: roadmap #4 dossier + #7 lead-§31–40, lead-only report layer)
    lp = sub.add_parser("lead-pages",
        help="Render lead-only §31-40 enrichment + related-genomes dossier pages from a sealed package")
    lp.add_argument("package"); lp.add_argument("--out", default=None)
    lp.add_argument("--bgc", default="ALL", help="a single BGC_ID, or ALL (default)")
    lp.add_argument("--all-tiers", action="store_true", dest="all_tiers",
                    help="lift the lead-only gate and render a page for every BGC (capacity read)")
    lp.set_defaults(func=lead_pages_command)

    # --- render-widgets (Group D, .344): dependency-free interactive post-seal reader deliverable ---
    rw = sub.add_parser(
        "render-widgets",
        help="Render portable interactive widgets + publication handoff from a sealed package/ZIP",
    )
    rw.add_argument(
        "--package", required=True,
        help="Path to a sealed package directory or Complete_Package.zip",
    )
    rw.add_argument(
        "--outdir", default=None,
        help="Sibling output directory (default: <source-name>_widgets; never inside the package)",
    )
    rw.set_defaults(func=render_widgets_command)

    # --- render-all-figures (Gap 3 / W9-N14, v9.7.150e+): post-seal aggregate
    # over every applicable figure module. Use this AFTER a --chatgpt-safe run
    # to populate the full figure suite without the wall-clock cap. Non-
    # blocking per-set: a failure in one module never affects the others.
    from .render_all_figures import render_all_figures_command, DEFAULT_SETS, ALL_SETS
    raf = sub.add_parser(
        "render-all-figures",
        help="Run every applicable figure module against a sealed package "
             "and record per-module outcomes without changing the sealed package",
    )
    raf.add_argument("--package", required=True,
                     help="Path to sealed package directory (containing manifest.json)")
    raf.add_argument("--include", default=None,
                     help=f"Comma-separated set names to run (default: {','.join(DEFAULT_SETS)}). "
                          f"Available: {','.join(ALL_SETS)}")
    raf.add_argument("--exclude", default=None,
                     help="Comma-separated set names to skip")
    raf.add_argument("--all", action="store_true", dest="all_sets", default=False,
                     help="Run every set including workbook-requiring ones "
                          "(needs --workbook for cohort-class / mamey-native)")
    raf.add_argument("--workbook", default=None,
                     help="Cohort or master workbook .xlsx (enables cohort-class + mamey-native)")
    raf.add_argument("--top-n", default=10, type=int, dest="top_n",
                     help="Top N for lead-board and locus-map figures (default: 10)")
    raf.add_argument("--fail-fast", action="store_true", dest="fail_fast",
                     default=False,
                     help="Stop on first error (default: continue, non-blocking per set)")
    raf.add_argument("--dry-run", action="store_true", dest="dry_run",
                     default=False,
                     help="Print which sets would run without running them")
    raf.set_defaults(func=render_all_figures_command)

    # --- cohort-figures (P-9x): gold gene/domain figure suite across packages ---
    cf = sub.add_parser("cohort-figures",
                        help="Emit the gold gene/domain figure suite (data-only PNG + sidecar CSV) "
                             "for one or more gold packages")
    cf.add_argument("--runs-dir", default="runs_gold",
                    help="Directory containing <ID>/package/ gold outputs (default: runs_gold)")
    cf.add_argument("--out", default="cohort_figures",
                    help="Output directory for figures (default: cohort_figures)")
    cf.add_argument("--strains", default=None,
                    help="Comma-separated explicit strain order/subset (default: all found)")
    cf.add_argument("--public-only", action="store_true", dest="public_only",
                    help="Drop PRIVATE (AJS-/PENDING-) strains -> shareable PUBLIC cut")
    cf.add_argument("--series", default="F", choices=["F", "G", "D", "all"],
                    help="Figure series: F=heatmaps (default), G=complementary, D=dot/bubble, all")
    cf.add_argument("--f13-cohort-manifest", default=None,
                    help="Hash-bound F13 cohort-manifest JSON; omit to emit an F13 HOLD receipt")
    cf.add_argument("--f13-cohort-manifest-sha256", default=None,
                    help="Exact SHA-256 digest for --f13-cohort-manifest")
    cf.add_argument("--f13-denominator-registry", default=None,
                    help="Independent F13 denominator-registry path; never inferred or defaulted")
    cf.add_argument("--f13-denominator-registry-sha256", default=None,
                    help="Exact SHA-256 digest for --f13-denominator-registry")
    cf.add_argument("--f13-profile", choices=["SINGLE_COLUMN", "DOUBLE_COLUMN"],
                    default="SINGLE_COLUMN",
                    help="Declared physical F13 source-artwork width profile")
    cf.add_argument("--no-extended", action="store_false", dest="extended", default=True,
                    help="Skip the 11-figure extended suite (census/PKS-bars/locus/archetype/KCB/"
                         "CCTT/boundary/co-occurrence/resistance/TTA); emit only the standard F-series.")
    cf.set_defaults(func=cohort_figures_command)

    # --- figure-factory (v9.7.409): wire the standalone Figure Factory as a first-class
    # subcommand. Renders the receipt-bound aggregate evidence figure suite from a hash-
    # bound JSON config (mamey/figure_factory_next.py::build); a phylogeny figure_kind is
    # routed to the phylogeny Figure Factory. Deterministic/offline reader — never touches
    # scores, boards, or sealed packages, and does not change the Factory's own logic. ---
    ff = sub.add_parser("figure-factory",
                        help="Render the receipt-bound Figure Factory evidence figure suite "
                             "from a hash-bound JSON config (aggregate, phylogeny, or bioassay kind)")
    ff.add_argument("--config", required=True,
                    help="Path to the hash-bound Figure Factory JSON config "
                         "(aggregate, phylogeny, or bioassay schema)")
    ff.set_defaults(func=figure_factory_command)

    # --- bigscape (v9.7.352): post-seal, non-blocking — RUN BiG-SCAPE 2.x on a package/cohort's
    # antiSMASH region GBKs, produce the cohort SQLite DB, and chain the cohort widgets (matrix +
    # clinker). Reuses tools/bigscape_prep.py for GBK staging + the .351 widget generators;
    # engine-neutral (no scores/tiers/sealed-package changes). ---
    bs = sub.add_parser("bigscape",
                        help="RUN BiG-SCAPE 2.x on a package/cohort's region GBKs -> cohort DB "
                             "(+ chained matrix/clinker widgets). Post-seal, non-blocking.")
    bs_src = bs.add_mutually_exclusive_group(required=True)
    bs_src.add_argument("--package", help="A single sealed Mamey Complete_Package dir/zip")
    bs_src.add_argument("--runs-dir", dest="runs_dir",
                        help="Cohort dir containing <ID>/package/ (or sealed zips)")
    bs_src.add_argument("--input-gbk-dir", dest="input_gbk_dir",
                        help="Explicit dir of already-extracted antiSMASH region GBKs")
    bs.add_argument("--out", default="bigscape_run", help="Output dir (default: bigscape_run)")
    bs.add_argument("--bigscape", dest="bigscape_bin",
                    default=str(workspace_root()) + "/miniconda3/envs/bigscape/bin/bigscape",
                    help="BiG-SCAPE 2.x binary (default: the conda bigscape env)")
    bs.add_argument("--pfam", default=str(workspace_root()) + "/BigSCAPE/Pfam-A.hmm",
                    help="Pfam-A.hmm (pressed)")
    bs.add_argument("--cpus", type=int, default=4, help="CPU cores (default: 4)")
    bs.add_argument("--cutoffs", default="0.3,0.5,0.7", help="GCF cutoffs (default: 0.3,0.5,0.7)")
    bs.add_argument("--record-type", dest="record_type", default="region",
                    help="BiG-SCAPE --record-type (default: region)")
    bs.add_argument("--classify", default="category",
                    help="BiG-SCAPE --classify (default: category)")
    bs.add_argument("--work-dir", dest="work_dir", default=None,
                    help="Space-free staging dir (default: a fresh system-temp dir)")
    bs.add_argument("--no-widgets", action="store_false", dest="run_widgets", default=True,
                    help="Skip chaining into the BiG-SCAPE cohort widgets")
    bs.add_argument("--widgets-out", dest="widgets_out", default=None,
                    help="Output dir for chained widgets (default: <out>/widgets)")
    bs.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Print the command + staging plan without running BiG-SCAPE")
    bs.set_defaults(func=_bigscape_command)
    # --- flagged-lead + Mode B compilation workflow (post-seal, non-blocking; VGP v9.7.353) ---
    mr = sub.add_parser("majority-read",
                        help="whole-BGC MIBiG majority read (minority/promiscuous-anchor flags)")
    mr.add_argument("--strain"); mr.add_argument("--bgc")
    mr.add_argument("--cohort", action="store_true"); mr.add_argument("--out")
    # v9.7.415: same flag spelling as surface-leads / modeb-compile, so the guard has an escape hatch.
    mr.add_argument("--force", "--in-place", dest="force", action="store_true",
                    help="allow overwriting an existing canonical dated deliverable")
    mr.set_defaults(func=_flagged_lead_command)
    slp = sub.add_parser("surface-leads",
                         help="surface PROMISCUOUS_ONLY + coherent-LOW_ID review groups")
    slp.add_argument("--out", help="output directory (default: the canonical dated "
                                   "flagged_lead_surfacing folder, which is overwritten in place)")
    slp.add_argument("--force", "--in-place", dest="force", action="store_true",
                     help="allow overwriting an existing canonical dated deliverable")
    slp.set_defaults(func=_flagged_lead_command)
    mbc = sub.add_parser("modeb-compile",
                         help="per-strain Mode B compilation (report+cards+majority-read overlay+figures)")
    mbc.add_argument("--strain"); mbc.add_argument("--strains", nargs="+")
    mbc.add_argument("--out", help="write here INSTEAD of the two canonical targets "
                                   "(default: the strain folder AND the dated compilation folder, "
                                   "both overwritten in place)")
    mbc.add_argument("--force", "--in-place", dest="force", action="store_true",
                     help="allow overwriting an existing canonical dated deliverable")
    mbc.add_argument("--no-docx", action="store_true")
    mbc.set_defaults(func=_flagged_lead_command)

    pr = sub.add_parser("phylo-run",
                        help="Run an approved GToTree and IQ-TREE genome workflow, with optional fastANI and tree sign-off")
    pr.add_argument("--genome-list", dest="genome_list", required=True,
                    help="File of absolute FASTA paths (one per line)")
    pr.add_argument("--workdir", required=True, help="Output workdir (MUST contain no spaces)")
    pr.add_argument("--outgroup", required=True,
                    help="Comma-separated outgroup tip label(s) = FASTA basename(s)")
    pr.add_argument("--hmm", default="Actinobacteria", help="GToTree HMM set (default: Actinobacteria)")
    pr.add_argument("--threads", type=int, default=4)
    pr.add_argument("--parallel", type=int, default=2)
    pr.add_argument("--ani-refs", dest="ani_refs", default=None,
                    help="Optional: reference FASTA paths file for a fastANI boundary table")
    pr.add_argument("--ani-queries", dest="ani_queries", default=None,
                    help="Optional: query FASTA paths for fastANI (default: --genome-list)")
    pr.add_argument("--signoff", default=None, help="Optional: path to signoff_check.py")
    pr.add_argument("--approved", action="store_true",
                    help="REQUIRED to run. Affirms a human approved this CPU run (tree-approval gate).")
    pr.set_defaults(func=_phylo_run_command)

    pa = sub.add_parser("phylo-autopilot",
                        help="Plan local 16S/genome inputs, route 16S references, or run an approved EPA-ng placement workflow")
    pa.add_argument("tool_args", nargs=argparse.REMAINDER,
                    help="passed through unchanged to tools/phylo_autopilot.py")
    pa.set_defaults(func=_phylo_autopilot_command)

    st = sub.add_parser("start",
                        help="Primary CLI starting point: show the five-command workflow and run the environment check")
    st.add_argument("--no-doctor", action="store_true", dest="no_doctor",
                    help="print the path only; skip the environment check")
    st.set_defaults(func=_start_command)

    # --- widget/analysis deliverable tools (BLIZZARD_BLUE_05, .353): five post-seal,
    # non-blocking reader generators graduated from strain_data ad-hoc modules. Each
    # reads its own inputs and writes self-contained HTML/cards; none touches scores, boards,
    # gates, or the sealed package, and each returns non-zero cleanly when its inputs are
    # absent. (Deferred AUG3_08/11 follow-up; rebased onto sealed .352.) ---
    omw = sub.add_parser("overmerge-widgets",
                         help="Emit the over-merge inspector widget set (per OVER_MERGED "
                              "region + ranked index) from the over-merge register + GBKs")
    omw.add_argument("--register", default=None,
                     help="Canonical over-merge register TSV (default: OVERMERGE_REGISTER_GBK.tsv)")
    omw.add_argument("--root", default=None,
                     help="Deliverables-workspace root (resolves strain_data GBKs)")
    omw.add_argument("--out", default=None,
                     help="Output directory (default: the register's _OVERMERGE_MODULE folder)")
    omw.set_defaults(func=overmerge_widgets_command)

    rgw = sub.add_parser("rggmci-widget",
                         help="Emit the within-strain RG-GMCI split-pathway linkage widget "
                              "from each package's *_4A_RGGMCI_ranked_pairs.csv")
    rgw.add_argument("--strain", default=None, help="One strain id (e.g. AS-XXX)")
    rgw.add_argument("--all", action="store_true", help="Every strain with a ranked-pairs CSV")
    rgw.add_argument("--runs-root", default=None, dest="runs_root",
                     help="Directory of sealed per-strain packages (default: documented location)")
    rgw.add_argument("--out", default=None,
                     help="Output directory (default: _RGGMCI_MODULE/widgets)")
    rgw.set_defaults(func=rggmci_widget_command)

    alw = sub.add_parser("assembly-line-widget",
                         help="Emit the NRPS/PKS assembly-line / domain-architecture reader "
                              "from a sealed package's antismash_modules.csv + gene_context.jsonl")
    alw.add_argument("--strain", default=None, help="One strain id (e.g. AS-XXX)")
    alw.add_argument("--demo", action="store_true", help="Render the flagship demo strains")
    alw.add_argument("--all", action="store_true", dest="all_strains",
                     help="Every strain with an antismash_modules.csv (mirrors rggmci-widget --all)")
    alw.add_argument("--runs-root", default=None, dest="runs_root",
                     help="Directory of sealed per-strain packages (default: documented location)")
    alw.add_argument("--out", default=None,
                     help="Output directory (default: _ASSEMBLY_LINE_MODULE/widgets)")
    alw.set_defaults(func=assembly_line_widget_command)

    # v9.7.413 (BC2): print companions to the interactive readers.
    for _name, _fn, _help in (
            ("assembly-line-pdf", assembly_line_pdf_command,
             "print-ready PDF of a strain's NRPS/PKS assembly lines, 4 or 6 per page"),
            ("bgc-gene-map", bgc_gene_map_command,
             "print-ready PDF gene map of EVERY region in a strain (all classes, not only NRPS/PKS)")):
        _p = sub.add_parser(_name, help=_help)
        _p.add_argument("--strain", default=None, help="One strain id (e.g. AS-XXX)")
        _p.add_argument("--strains", nargs="+", default=None, help="Several strain ids")
        _p.add_argument("--all", action="store_true", dest="all_strains",
                        help="Every strain with an antismash_modules.csv")
        _p.add_argument("--runs-root", default=None, dest="runs_root",
                        help="Directory of sealed per-strain packages")
        _p.add_argument("--out", required=True, help="Output directory")
        _p.add_argument("--per-page", type=int, default=6, choices=(4, 6), dest="per_page",
                        help="Panels per page (default 6)")
        _p.set_defaults(func=_fn)

    afb = sub.add_parser("af-leadboard",
                         help="Emit the cohort ANTIFUNGAL (AF) capacity lead-board dashboard "
                              "from the per-BGC master CSV + codex-judged cards")
    afb.add_argument("--master-csv", default=None, dest="master_csv",
                     help="SAPOTE_PER_BGC_MASTER_all_AS.csv (default: under strain_data)")
    afb.add_argument("--root", default=None, help="Deliverables-workspace root")
    afb.add_argument("--out", default=None,
                     help="Output directory (default: _AF_LEADBOARD_MODULE)")
    afb.set_defaults(func=af_leadboard_command)

    soc = sub.add_parser("split-overmerge-cards",
                         help="Run the deterministic per-protocluster SPLIT *_FULL.md card "
                              "QC-fixer/generator over the split-card manifest (idempotent)")
    soc.add_argument("--manifest", default=None,
                     help="SPLIT_FULL_CARDS_MANIFEST.tsv (default: in _OVERMERGE_MODULE)")
    soc.add_argument("--base", default=None, help="strain_data root")
    soc.add_argument("--blastp-repo", default=None, dest="blastp_repo",
                     help="BLASTp Repository root")
    soc.add_argument("--dry-run", action="store_true", dest="dry_run",
                     help="Report changes without writing the cards")
    soc.add_argument("--only", default=None, help="Substring filter on card path")
    soc.add_argument("--limit", type=int, default=0, help="Process at most N cards")
    soc.set_defaults(func=split_overmerge_cards_command)

    cdd = sub.add_parser("clade-deepdive",
                         help="Genus/clade deep-dive apparatus: six tracks (ANI, BiG-SCAPE matrix, "
                              "conserved-dark, nt-core-BGC clock, decontam-if-flagged, clinker) -> "
                              "<CLADE>_SYNTHESIS.md. Post-seal, non-blocking, degrades gracefully.")
    cdd.add_argument("--clade", required=True, help="clade name (output prefix)")
    cdd.add_argument("--genomes", required=True, help="dir of the clade's genome FASTAs")
    cdd.add_argument("--db", default=None, help="BiG-SCAPE cohort SQLite DB (full_cohort.db)")
    cdd.add_argument("--strains", default="", help="comma list of the clade's strain ids")
    cdd.add_argument("--comparators", default=None,
                     help="optional dir of comparator/type genome FASTAs (similarity anchors)")
    cdd.add_argument("--proteomes", default=None,
                     help="optional dir of <strain>.faa for the conserved reference-dark track")
    cdd.add_argument("--gbk-dir", dest="gbk_dir", default=None,
                     help="optional dir of region GBKs for the nucleotide core-BGC clock")
    cdd.add_argument("--decontam-assembly", dest="decontam_assembly", default=None,
                     help="assembly FASTA to decontaminate (only if the strain is flagged)")
    cdd.add_argument("--ref-target", dest="ref_target", default=None,
                     help="clean same-genus reference FASTA (decontam)")
    cdd.add_argument("--ref-contaminant", dest="ref_contaminant", default=None,
                     help="clean suspected-contaminant reference FASTA (decontam)")
    cdd.add_argument("--fastani", default=None, help="fastANI binary override (default: conda phylo env)")
    cdd.add_argument("--cutoff", type=float, default=0.3, help="BiG-SCAPE GCF cutoff (default: 0.3)")
    cdd.add_argument("--out", default=None, help="output dir (default: <clade>_deepdive)")
    cdd.set_defaults(func=_clade_deepdive_command)

    co = sub.add_parser("cohort",
                        help="Cross-strain front-door: emit a cohort deliverable bundle "
                             "(synthesis report + figures) with a mandatory-deliverable gate.")
    co.add_argument("--runs-dir", default="runs_gold",
                    help="Directory of sealed per-strain gold runs.")
    co.add_argument("--out", default="cohort_deliverable",
                    help="Output directory for the cohort deliverable bundle.")
    co.add_argument("--strains", default=None,
                    help="Optional comma-separated strain subset/order.")
    co.add_argument("--master-path", default=None, dest="master_path",
                    help="Explicit path to the verified cohort master workbook "
                         "(else auto-located under --runs-dir).")
    co.add_argument("--novelty-basis", default="fully_dark", dest="novelty_basis",
                    choices=["fully_dark", "dark_or_unresolved"],
                    help="Novelty basis passed to the synthesis writer.")
    co.add_argument("--series", default="all", choices=["F", "G", "D", "all"],
                    help="Cohort figure series (default: all).")
    co.add_argument("--public-only", action="store_true", dest="public_only",
                    help="Restrict figures to public-safe strain labels.")
    co.add_argument("--no-figures", action="store_true", dest="no_figures",
                    help="Emit the synthesis report only, skip the figure suite.")
    co.set_defaults(func=cohort_command)

    # --- cohort-leads (FA1): cross-strain union of Exceptional+High triage leads ---
    cl = sub.add_parser("cohort-leads",
                        help="Union every sealed package's triage board into ONE ranked "
                             "cross-strain priority-leads CSV (Exceptional+High leads). "
                             "Non-scoring, capacity-level re-projection.")
    cl.add_argument("--runs-dir", default="runs_gold",
                    help="Directory of sealed per-strain runs (<ID>/package/*_4_triage_board.csv).")
    cl.add_argument("--out", default="COHORT_PRIORITY_LEADS.csv",
                    help="Output CSV path (default: COHORT_PRIORITY_LEADS.csv).")
    cl.set_defaults(func=cohort_leads_command)

    # --- activity-leads: exact-locus top-N AF/AB routing boards per strain ---
    al = sub.add_parser(
        "activity-leads",
        help="Emit per-strain top-N antibacterial and antifungal routing boards "
             "from sealed triage packages (non-scoring; claim-safe).",
    )
    al.add_argument(
        "--runs-dir", default="runs_gold",
        help="Directory of sealed per-strain runs (<ID>/package/*_4_triage_board.csv).",
    )
    al.add_argument(
        "--out", default="activity_leads",
        help="Output directory for CSV, Markdown, metadata, and unbound-row ledger.",
    )
    al.add_argument(
        "--top-n", type=int, default=5, dest="top_n",
        help="Number of rows per strain and activity track (default: 5).",
    )
    al.add_argument(
        "--canonical-crosswalk", default=None, dest="canonical_crosswalk",
        help="Optional CSV with strain, full_node_or_contig, region, bgc_alias columns.",
    )
    al.add_argument(
        "--require-crosswalk", action="store_true", dest="require_crosswalk",
        help="Fail closed on rows absent from the canonical physical-key crosswalk.",
    )
    al.set_defaults(func=activity_leads_command)

    # --- activity-lead-genes: gene-level class foundations for routed leads ---
    alg = sub.add_parser(
        "activity-lead-genes",
        help="Bind per-package gene rows to an activity-leads CSV and select up to "
             "five genes that explain each source class label.",
    )
    alg.add_argument(
        "leads_csv",
        help="PER_STRAIN_ACTIVITY_LEADS.csv emitted by the activity-leads command.",
    )
    alg.add_argument(
        "--out", default="activity_lead_genes",
        help="Output directory for gene anchors, locus summaries, holds, and metadata.",
    )
    alg.add_argument(
        "--top-n", type=int, default=5, dest="top_n",
        help="Maximum source-bound genes selected per exact locus (default: 5).",
    )
    alg.set_defaults(func=activity_lead_genes_command)

    # --- cohort-assemble (FA1): assemble sealed packages into one cohort table ---
    ca = sub.add_parser("cohort-assemble",
                        help="Assemble many sealed packages into ONE cohort table "
                             "(strain_summary + bgc_inventory + class_by_strain) as "
                             "COHORT_MASTER.csv/xlsx, without the O(N^2) master rewrite.")
    ca.add_argument("--runs-dir", default="runs_gold",
                    help="Directory of sealed per-strain runs (<ID>/package/*_1_intake.json).")
    ca.add_argument("--out", default="COHORT_MASTER.csv",
                    help="Primary output CSV path; sibling _strain_summary.csv and "
                         "_class_by_strain.csv are written alongside (default: COHORT_MASTER.csv).")
    ca.add_argument("--xlsx", action="store_true", dest="xlsx",
                    help="Also emit a 3-sheet COHORT_MASTER.xlsx (requires openpyxl).")
    ca.set_defaults(func=cohort_assemble_command)

    # --- cohort-proteins: exact-locus within-project protein catalog/comparison ---
    # This is deliberately a separate evidence channel from nr, ClusteredNR,
    # Swiss-Prot, MIBiG and ClusterBlast.  It provides the measured AS/SID/TYPE
    # gene-comparison payload used by Mode B Section 45 and related sections.
    from .cohort_proteins import add_cli_parser as _add_cohort_protein_parser
    _add_cohort_protein_parser(sub)

    # --- comparator-coverage (FA2): two-denominator MIBiG comparator coverage (report-only) ---
    p_cc = sub.add_parser("comparator-coverage",
                          help="FA2 two-denominator comparator coverage (report-only, non-scoring)")
    p_cc.add_argument("package", help="Sealed package dir")
    p_cc.add_argument("--cohort-runs-dir", default=None, dest="cohort_runs_dir",
                      help="Optional runs dir for cohort comparator-prevalence de-weighting.")
    p_cc.set_defaults(func=comparator_coverage_command)

    # --- domain-reference / realistic-count / novelty-shortlist (D3 orphan-tier tools) ---
    p_domref = sub.add_parser("domain-reference",
                              help="emit the Mode-B domain functional-context dictionary from sealed package(s) (DOMREF-01)")
    p_domref.add_argument("--package", action="append", required=True)
    p_domref.add_argument("--out", default=None)
    p_domref.set_defaults(func=_d3_tool_command, _d3_tool="domain-reference", top=None)

    p_rcount = sub.add_parser("realistic-count",
                              help="corrected-denominator BGC count (marginal-drop + HIGH RG-GMCI merge); advisory")
    p_rcount.add_argument("--package", action="append", required=True)
    p_rcount.add_argument("--out", default=None)
    p_rcount.set_defaults(func=_d3_tool_command, _d3_tool="realistic-count", top=None)

    p_nov = sub.add_parser("novelty-shortlist",
                           help="composite multi-signal novelty shortlist (KCB-dark + low recognizability + RG-GMCI + cohort-unique domain); advisory")
    p_nov.add_argument("--package", action="append", required=True)
    p_nov.add_argument("--out", default=None)
    p_nov.add_argument("--top", type=int, default=30)
    p_nov.set_defaults(func=_d3_tool_command, _d3_tool="novelty-shortlist")

    # --- signoff (FA4): analysis sign-off QC gate (advisory; exit 0) ---
    sg = sub.add_parser("signoff",
                        help="Analysis sign-off QC gate: objective checks on Newick trees "
                             "(outgroup/contaminant/label-cruft/support/thin-tree). Advisory, exit 0.")
    sg.add_argument("files", nargs="*", help="tree file(s); default: scan cwd for recent *.treefile")
    sg.add_argument("--minutes", type=float, default=None, help="scan window when no files given")
    sg.set_defaults(func=signoff_command)

    # Read-only inspection is separate from catalog registration and ingestion.
    from .tool_database_reader import ADAPTERS, inspection_command
    tdi = sub.add_parser("tool-database-inspect", help="Inspect one explicit manifest-bound tool database read-only; no scientific admission")
    tdi.add_argument("--root", required=True, help="Explicit existing database root")
    tdi.add_argument("--manifest", required=True, help="Relative manifest locator beneath root")
    tdi.add_argument("--manifest-sha256", help="Optional externally expected manifest SHA-256")
    tdi.add_argument("--adapter", choices=ADAPTERS, default="manifest")
    tdi.add_argument("--locus", nargs=4, metavar=("STRAIN", "FULL_CONTIG", "REGION", "ALIAS"))
    tdi.add_argument("--limit", type=int, default=100)
    tdi.add_argument("--offset", type=int, default=0)
    tdi.add_argument("--view", choices=("genes", "searches", "hits", "hsps"), default="genes")
    tdi.add_argument("--gene-order", type=int, help="Exact gene order within the complete selected locus")
    tdi.add_argument("--search-id", type=int, help="Search selector bound to that gene; Swiss-Prot uses query-scoped selector 1")
    tdi.add_argument("--hit-rank", type=int, help="Source-retained hit rank within that search")
    tdi.set_defaults(func=inspection_command)

    # --- doctor (B5) ---
    doc = sub.add_parser("doctor",
                         help="Pre-flight environment check: Python, deps, write permissions, bundle integrity")
    doc.add_argument("--probe-transports", action="store_true", dest="probe_transports",
                     help="probe NCBI + EBI BLAST endpoints and report which transport is live (network; §6.6)")
    doc.add_argument("--companions", "--tools", action="store_true", dest="companions",
                     help="probe external companion tools (BiG-SCAPE/clinker/GECCO/phylogenomics/…) "
                          "and print a present/missing table with install hints. Optional & detected-not-bundled: "
                          "missing tools never fail the check. See docs/companion_tools.md")
    doc.set_defaults(func=doctor_command)

    # --- capabilities: active full-docstring discovery through the inventory owner ---
    cap = sub.add_parser(
        "capabilities",
        help="Search full docstrings for existing internal tools before writing a new one",
    )
    cap.add_argument("keywords", nargs="+", help="Concepts to find (for example: split fragment contig rescue)")
    cap.add_argument("--top", type=int, default=10, help="Maximum results (default: 10)")
    cap.set_defaults(func=capabilities_command)

    # --- chatgpt-init: surface the ChatGPT operating contract (read-only) ---
    cgi = sub.add_parser("chatgpt-init",
                         help="Legacy compatibility check for the shared assistant contract; new sessions use `start`")
    cgi.set_defaults(func=chatgpt_init_command)

    # --- inspect (B4) ---
    ins = sub.add_parser("inspect",
                         help="Preview what Mamey sees in an antiSMASH ZIP before running")
    ins.add_argument("zip", help="Path to antiSMASH output ZIP")
    ins.set_defaults(func=inspect_command)

    # --- ingest-blastp (v9.7.163): append NCBI BLASTp top-N hits to B5_BLASTp_Hits ---
    ib = sub.add_parser("ingest-blastp",
                        help="Ingest an NCBI BLASTp HitTable CSV (+ optional Alignment XML) into a master workbook's B5_BLASTp_Hits sheet")
    ib.add_argument("--master", required=True, help="Path to the master workbook (.xlsx) to append to")
    ib.add_argument("--strain", required=True, help="Strain ID these BLASTp hits belong to (e.g. AS-XXX)")
    ib.add_argument("--hit-table", required=True, dest="hit_table", help="NCBI -outfmt 10 HitTable CSV")
    ib.add_argument("--xml", default=None, help="Optional NCBI Alignment XML for enrichment (subject desc/sciname/node·contig)")
    ib.add_argument("--top-n", type=int, default=10, dest="top_n", help="Max hits per query gene (default 10)")
    ib.add_argument("--package", default=None,
                    help="Sealed Mamey package dir. When given, mirror the best nr hit per gene to "
                         "<package>/blastp_online/<BGC>_online_blastp.csv - the overlay that "
                         "authored_verify/genome_explore read to prefer nr over ClusterBlast for "
                         "conservation_median_id. Omit it and NOVELTY_CONTRADICTION stays disarmed.")
    ib.add_argument("--source", default=None,
                    help="Provenance stamped verbatim into B5_BLASTp_Hits' source column "
                         "(default 'NCBI web-BLASTp'). This command's HitTable format is shared by "
                         "the EBI fallback transport (blastp-ebi --to-outfmt10) - pass e.g. "
                         "--source \"EBI (uniprotkb_bacteria)\" when ingesting an EBI-derived "
                         "HitTable, or every such row is silently mislabeled NCBI.")
    ib.set_defaults(func=ingest_blastp_command)

    # v9.7.340: ingest a pre-organized per-BGC trove straight into the package overlay (no workbook)
    p_trove = sub.add_parser("ingest-blastp-trove",
        help="Ingest a pre-organized per-BGC BLASTp trove into the package overlay (no workbook).")
    p_trove.add_argument("--trove", required=True, help="Trove dir: <STRAIN>/<BGC>/<BGC>_top_hit_per_gene.csv")
    p_trove.add_argument("--package", required=True, help="Sealed Mamey package dir")
    p_trove.add_argument("--channel", required=True, choices=["nr", "clustered_nr", "swissprot", "ebi"])
    p_trove.add_argument("--strain", default=None, help="Restrict to one strain subdir")
    p_trove.set_defaults(func=ingest_blastp_trove_command)

    p_status = sub.add_parser("blastp-status",
        help="Report per-BGC BLASTp overlay coverage (channels/genes) or flag ClusterBlast fallback.")
    p_status.add_argument("--package", required=True)
    p_status.set_defaults(func=blastp_status_command)

    # --- explain (B6) ---
    exp = sub.add_parser("explain",
                         help="Human-readable summary of an existing result package")
    exp.add_argument("package_dir", help="Path to sealed Mamey package directory")
    exp.set_defaults(func=explain_command)

    # --- discover (workspace orientation: packages, coverage, next actions) ---
    dsc = sub.add_parser("discover", aliases=["discovery"],
                         help="Orient in a workspace: list packages, coverage, and next actions")
    dsc.add_argument("root", nargs="?", default=".",
                     help="workspace / runs / package dir to scan (default: current dir)")
    dsc.add_argument("--json", action="store_true", help="machine-readable output")
    dsc.add_argument("--emit-md", metavar="PATH", help="also write the report to a markdown file")
    dsc.add_argument("--depth", type=int, default=6, help="max recursion depth (default 6)")
    dsc.add_argument("--stale", action="store_true",
                     help="show only packages on an older engine than the newest run (re-run candidates)")
    dsc.add_argument("--current", metavar="VER",
                     help="engine version to treat as current (default: newest seen among packages)")
    dsc.add_argument("--source-collection-registry", metavar="PATH",
                     help="also run governed heterogeneous evidence discovery with this registry")
    dsc.add_argument("--expected-source-collection-registry-sha256", metavar="SHA256",
                     help="required exact registry hash for governed evidence discovery")
    dsc.add_argument("--source-root-id", metavar="ID",
                     help="logical evidence-root ID; absolute paths are not written to the catalog")
    dsc.add_argument("--emit-source-catalog-json", metavar="PATH",
                     help="write the governed source catalog as JSON (requires TSV output too)")
    dsc.add_argument("--emit-source-catalog-tsv", metavar="PATH",
                     help="write the governed source catalog as TSV (requires JSON output too)")
    dsc.add_argument("--source-depth", type=int, default=6,
                     help="maximum evidence-discovery recursion depth (default 6)")
    dsc.add_argument("--source-max-files", type=int, default=100_000,
                     help="fail-closed evidence-discovery file ceiling (default 100000)")
    dsc.add_argument("--source-max-apparent-bytes", type=int, default=20_000_000_000,
                     help="fail-closed apparent-byte ceiling (default 20000000000)")
    dsc.add_argument("--source-max-seconds", type=float, default=60.0,
                     help="fail-closed evidence-discovery time ceiling (default 60 seconds)")
    dsc.set_defaults(func=_discover.discover_command)

    # --- genus-appendix (AF/AB candidate appendices grouped by genus; report-only) ---
    gap = sub.add_parser("genus-appendix", aliases=["af-ab-appendix"],
                         help="Antifungal/antibacterial candidate appendices, grouped by genus (report-only)")
    gap.add_argument("root", nargs="?", default=".",
                     help="workspace / runs / package dir to scan (default: current dir)")
    gap.add_argument("--out", metavar="DIR", help="write GENUS_ANTIFUNGAL/ANTIBACTERIAL_APPENDIX.md here")
    gap.add_argument("--depth", type=int, default=3, help="max recursion depth (default 3)")
    gap.set_defaults(func=_genus_appendix.genus_appendix_command)

    # --- af-dossier (D2: Antifungal Lead Dossier: AF board x measured Candida activity) ---
    afd = sub.add_parser("af-dossier",
                         help="Antifungal (AF) Lead Dossier: AF lead board x measured "
                              "Candida activity (report-only)")
    afd.add_argument("root", nargs="?", default=".",
                     help="workspace / runs / package dir to scan (default: current dir)")
    afd.add_argument("--out", metavar="DIR", help="write AF_LEAD_DOSSIER.csv/.md here")
    afd.add_argument("--activity-table", dest="activity_table", metavar="CSV",
                     help="optional measured-bioactivity crosswalk CSV "
                          "(strain,anti_Candida,host,genus,...)")
    afd.add_argument("--depth", type=int, default=3, help="max recursion depth (default 3)")
    afd.set_defaults(func=_af_dossier.af_dossier_command)

    # --- good-guesses (FA7: claim-safe interpretive-priors report; report-only, non-scoring) ---
    ggp = sub.add_parser("good-guesses",
                         help="Good Guesses: single best claim-safe interpretive read per notable BGC (report-only)")
    ggp.add_argument("root", nargs="?", default=".",
                     help="workspace / runs / package dir to scan (default: current dir)")
    ggp.add_argument("--out", metavar="DIR", help="write GOOD_GUESSES.md/.csv/.docx/.pdf here")
    ggp.add_argument("--depth", type=int, default=3, help="max recursion depth (default 3)")
    ggp.add_argument("--pdf", action="store_true", help="also render GOOD_GUESSES.pdf")
    ggp.add_argument("--docx", action="store_true", help="also render GOOD_GUESSES.docx")
    ggp.set_defaults(func=_good_guesses.good_guesses_command)

    # --- reference-dark (v9.7.343: wire the orphaned reference-dark novelty prior into a
    #     real post-seal deliverable; report-only, non-ranking. Writes _3b_reference_dark_prior.csv
    #     as a NEW file per package — pre-existing sealed files stay byte-identical). ---
    rdp = sub.add_parser("reference-dark",
                         help="Write a non-ranking report of loci with limited admitted reference coverage")
    rdp.add_argument("root", nargs="?", default=".",
                     help="a sealed package/ dir, or a workspace/runs dir to scan (default: current dir)")
    rdp.add_argument("--out", metavar="DIR", help="write the *_3b_reference_dark_prior.csv here instead of into each package")
    rdp.add_argument("--depth", type=int, default=3, help="max recursion depth when scanning (default 3)")
    rdp.set_defaults(func=_reference_dark.reference_dark_command)

    # --- modeb-export (FA6: export an authored Mode B card .md / mode_b/ dir to .docx + .pdf) ---
    from .modeb_export import THEME_CHOICES as _MODEB_THEME_CHOICES
    from .modeb_export import main as _modeb_export_main
    mx = sub.add_parser("modeb-export",
                        help="Export an authored Mode B card .md (or a mode_b/ dir) to .docx + .pdf")
    mx.add_argument("input", help="A Mode B card .md OR a package mode_b/ directory (batch)")
    mx.add_argument("--outdir", default=None)
    mx.add_argument("--format", choices=["docx", "pdf", "both"], default="both")
    mx.add_argument("--theme", choices=_MODEB_THEME_CHOICES, default="evidence_dossier")
    mx.set_defaults(func=lambda a: _modeb_export_main(
        [a.input] + (["--outdir", a.outdir] if a.outdir else []) + ["--format", a.format, "--theme", a.theme]))

    # --- resume (session-state reducer) ---
    res = sub.add_parser("resume",
                         help="One-read session-resume briefing for a sealed package "
                              "(strain context + judgment progress + what's next)")
    res.add_argument("package_dir", help="Path to sealed Mamey package directory")
    res.add_argument("--json", action="store_true", default=False,
                     help="Emit the machine handoff object instead of the paste-ready markdown")
    res.add_argument("--ranked", default=None,
                     help="Comma-separated triage-rank BGC order (rank 1 first); "
                          "orders 'next up' by analytical priority")
    res.add_argument("--cross-strain-note", default=None, dest="cross_strain_note",
                     help="One-line cross-strain context to carry into the briefing")
    res.set_defaults(func=resume_command)

    # --- fingerprint (v9.7.199: cross-run/cross-chat determinism check) ---
    fpc = sub.add_parser("fingerprint",
                         help="Determinism fingerprint of a sealed package (score-bearing "
                              "outputs only) — same strain+bundle yields the same value in any chat")
    fpc.add_argument("package", help="Path to sealed Mamey package directory")
    fpc.add_argument("--compare", default=None,
                     help="Second package dir OR a raw fingerprint hex to diff against "
                          "(exit 0 = match, 1 = divergence)")
    fpc.add_argument("--json", action="store_true", default=False,
                     help="Machine-readable output")
    fpc.set_defaults(func=fingerprint_command)

    # --- handoff (v9.7.199: portable package + region-GBK bundle for another chat) ---
    hoc = sub.add_parser("handoff",
                         help="Pack a sealed package + region GBKs into one portable zip so "
                              "another chat can do the full workflow (incl. online BLASTp) "
                              "without the raw antiSMASH ZIP")
    hoc.add_argument("--package", required=True, help="Path to sealed Mamey package directory")
    hoc.add_argument("--input-zip", dest="input_zip", default=None,
                     help="Raw antiSMASH ZIP to pull region GBKs from (omit = package-only handoff)")
    hoc.add_argument("--top-n", dest="top_n", type=int, default=None,
                     help="Include only the top-N triage-ranked leads' region GBKs (default: all)")
    hoc.add_argument("--out", required=True, help="Output handoff zip path")
    hoc.set_defaults(func=handoff_command)

    # --- compile-report (deterministic §13 assembler) ---
    cr = sub.add_parser("compile-report",
                        help="Assemble the §13 compiled analysis report deterministically "
                             "(disk-backed sections filled; narrative sections left as Sapote slots)")
    cr.add_argument("package_dir", help="Path to sealed Mamey package directory")
    cr.add_argument("--out", default=None,
                    help="Output markdown path (default: <pkg>/<strain>_compiled_report.md)")
    cr.add_argument("--strict", action="store_true", default=False,
                    help="Compile gate: exit non-zero and write nothing if any narrative "
                         "SAPOTE slot is still unfilled (blocks a half-written master report)")
    cr.add_argument("--no-figures", action="store_true", default=False, dest="no_figures",
                    help="Skip compile-time figure generation (reference existing PNGs only)")
    cr.add_argument("--toc-depth", type=int, default=1, dest="toc_depth",
                    help="TOC depth (default 1; at 2 every BGC card heading appears in TOC, "
                         "which is unreadable for >20-BGC strains). W3 Gap 3.")
    cr.add_argument("--pdf", action="store_true", default=False,
                    help="Also render a printable Compiled Master PDF (the menu's Boss-Ready PDF / "
                         "\u00a715.8) via tools/md_to_pdf.sh (colorful reportlab renderer, pandoc+xelatex fallback). Refuses if narrative "
                         "slots are unfilled unless --allow-unfilled-pdf is given.")
    cr.add_argument("--allow-unfilled-pdf", action="store_true", default=False, dest="allow_unfilled_pdf",
                    help="Render the --pdf even if narrative slots are still unfilled (skeleton PDF).")
    cr.add_argument("--allow-claim-safety-warnings", action="store_true", default=False,
                    dest="allow_claim_safety_warnings",
                    help="v9.7.409: the assembled-report claim-safety scan (MB-03) now BLOCKS by "
                         "default (write nothing, exit 3) when it raises findings. This flag restores "
                         "the old warn-and-ship behaviour for a deliberate, explicitly-attested DRAFT; "
                         "it is NOT honoured under --strict.")
    cr.add_argument("--blastp-waiver", default=None, dest="blastp_waiver", metavar="REASON",
                    help="Override the v9.7.344 BLASTp-completeness HARD gate with a logged reason "
                         "(recorded to manifest provenance; the report ships BLASTP-INCOMPLETE by "
                         "attestation). Without this, the report is REFUSED when ingestable BLASTp "
                         "is available on disk but not ingested.")
    cr.set_defaults(func=compile_report_command)

    # --- write-narrative (W3 Gap 1, v9.7.149c) ---
    wn = sub.add_parser("write-narrative",
                        help="Write a pre-authored narrative section into the package "
                             "judgment/ dir, with claim-safety linting before write")
    wn.add_argument("package_dir", help="Path to sealed Mamey package directory")
    wn.add_argument("--section", required=True,
                    choices=["executive_summary", "layperson_guide",
                             "ecological_synthesis", "priority_deep_dives"],
                    help="Which compile-report narrative slot to fill")
    wn.add_argument("--file", required=True,
                    help="Path to the markdown file with the section content")
    wn.add_argument("--force", action="store_true", default=False,
                    help="v9.7.409: RESERVED for non-claim-safety warnings. A claim-safety linter "
                         "finding is ALWAYS refused (write nothing, exit 3) and can no longer be "
                         "forced past — revise to capacity-based language instead.")
    from .compile_report import write_narrative_command
    wn.set_defaults(func=write_narrative_command)

    # --- list-bgcs (B7) ---
    lb = sub.add_parser("list-bgcs",
                        help="Quick BGC inventory from a sealed package (table or JSON)")
    lb.add_argument("package_dir", help="Path to sealed Mamey package directory")
    lb.add_argument("--top",  "-n", type=int, default=None, dest="top_n",
                    help="Limit to top N BGCs")
    lb.add_argument("--axis", default="rank", choices=["rank", "ab", "af"],
                    help="Sort axis: rank (triage order), ab (antibacterial), af (antifungal)")
    lb.add_argument("--json", action="store_true", default=False,
                    help="Emit machine-readable JSON array instead of a table")
    lb.add_argument("--include-dropped", action="store_true", default=False, dest="include_dropped",
                    help="Include primary-metabolism and standing-rule-excluded BGCs")
    lb.set_defaults(func=list_bgcs_command)

    # --- cohort-precompute (v9.7.229): Part A as a first-class subcommand ---
    def _cohort_precompute_command(args):
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "tools"))
        import build_cohort_precompute as _bcp
        return _bcp.main(["--runs-dir", args.runs_dir, "--out", args.out])
    cp = sub.add_parser("cohort-precompute",
                        help="Consolidate per-strain precompute sources into the 7 cohort tables (+ VERSION.json/MANIFEST.csv)")
    cp.add_argument("--runs-dir", required=True, help="dir of <strain>/ source subdirs (cohort_sources)")
    cp.add_argument("--out", required=True, help="output dir for the cohort tables")
    cp.set_defaults(func=_cohort_precompute_command)

    # --- explore (v9.7.233): question-driven genome exploration ---
    from .genome_explore import explore_command
    ex = sub.add_parser("explore", help="question-driven genome exploration (divergence / co-capture / lead board)")
    ex.add_argument("package", help="sealed package directory")
    ex.add_argument("--top", type=int, default=8)
    ex.add_argument("--json", action="store_true")
    ex.set_defaults(func=explore_command)

    # --- mode-b (P1) ---
    mb = sub.add_parser("mode-b",
                        help="Emit a Mode B top-lead triage table and card scaffolds from a sealed package. "
                             "NOT a finished 48-section Mode B card: finished cards are authored per "
                             "wiki/Mode-B-Gene-First-and-48-Section-Manual.md and verified with `verify-modeb` (v9.7.405 wording).")
    mb.add_argument("--package", required=True,
                    help="Path to sealed package directory (containing manifest.json)")
    mb.add_argument("--top-n", type=int, default=10, dest="top_n",
                    help="Number of top leads to cover (default: 10)")
    mb.add_argument("--outdir", default=None,
                    help="Output directory (default: <package>/mode_b/)")
    mb.add_argument("--node-first", action="store_true", dest="node_first", default=True,
                    help="Label leads node/contig-first (always on: store_true over default=True has "
                         "no off switch; flag retained for invocation back-compat)")
    mb.add_argument("--strict-all", action="store_true", dest="strict_all", default=False,
                    help="Exit nonzero if --top-n requests full inventory coverage but native Mode B emits fewer cards")
    mb.set_defaults(func=mode_b_command)
    # --- modeb-availability (v9.7.370 candidate): evidence inventory before prose ---
    from .mode_b.availability import add_arguments as add_modeb_availability_arguments
    from .mode_b.availability import availability_command
    mba = sub.add_parser(
        "modeb-availability",
        help="Inventory and bind Mode B evidence streams before any card prose is authored",
    )
    add_modeb_availability_arguments(mba)
    mba.set_defaults(func=availability_command)
    # --- modeb-gene-first (v9.7.395 proposal): exact-locus offline composition ---
    from .mode_b.gene_first_explore import add_arguments as add_gene_first_arguments
    from .mode_b.gene_first_explore import gene_first_command
    mgf = sub.add_parser(
        "modeb-gene-first",
        help="Compose one exact-locus gene-first exploration without authoring a Mode B card",
    )
    add_gene_first_arguments(mgf)
    mgf.set_defaults(func=gene_first_command)
    # --- guide (BGC Guide deliverable; v9.7.186, sibling of mode-b) ---
    from .bgc_guide import guide_command
    gd = sub.add_parser("guide",
                        help="Layered per-gene BGC Guide (lay\u2192technical; Structure/Function/BLASTp per gene)")
    gd.add_argument("--package", required=True, help="Sealed package dir (manifest.json)")
    gd.add_argument("--bgc", default=None, help="BGC ID (omit to cover --top-n leads)")
    gd.add_argument("--format", choices=["md", "docx", "both"], default="both")
    gd.add_argument("--audience", choices=["lay", "technical", "both"], default="both")
    gd.add_argument("--blastp-store", default=None, dest="blastp_store",
                    help="BLASTp evidence store dir (default: auto-discover under package)")
    gd.add_argument("--top-n", type=int, default=10, dest="top_n")
    gd.add_argument("--outdir", default=None, help="Default: <package>/guide/")
    gd.add_argument("--with-diagram", action="store_true", default=False,
                    help="Embed figures-diagram PNG in Parts 3/4 if available")
    gd.set_defaults(func=guide_command)
    # --- layperson: Day-5-structure, package-only post-seal guide ---
    from .layperson_guide import layperson_command
    lp = sub.add_parser(
        "layperson",
        help="Render a claim-safe plain-language guide from one sealed package (post-seal)",
    )
    lp.add_argument("package", help="Path to a sealed Mamey package directory")
    lp.add_argument("--outdir", default=None,
                    help="Output directory (default: sibling layperson_guide directory)")
    lp.add_argument("--format", choices=["md", "docx", "both"], default="both",
                    help="Output format; DOCX is rendered from the same governed Markdown source")
    lp.add_argument("--top-n", type=int, default=5, dest="top_n",
                    help="Maximum package-ranked regions to explain (default: 5)")
    lp.set_defaults(func=layperson_command)
    # --- v9.7.192: authored-output verifiers (read the FINISHED file, not the skeleton) ---
    from .authored_verify import verify_guide_command, verify_modeb_command
    from .sapote_workflow import workflow_command
    vg = sub.add_parser("verify-guide",
                        help="Verify a FINISHED authored guide .md (no residual LAY slots; Parts authored; gene summaries present)")
    vg.add_argument("file", help="Path to the authored guide .md")
    vg.add_argument("--audience", choices=["lay", "technical", "both"], default="both")
    vg.set_defaults(func=verify_guide_command)
    vm = sub.add_parser("verify-modeb",
                        help="Verify a FINISHED authored Mode B card via lint_card (structure + strict depth)")
    vm.add_argument("file", help="Path to the authored Mode B card .md")
    vm.add_argument("--package", default=None, help="Sealed package dir (for BGC context predicates)")
    vm.add_argument("--bgc", default=None, help="BGC ID (for RiPP/novelty conditional-section predicates)")
    vm.add_argument("--no-strict-depth", action="store_true", default=False,
                    help="Depth findings WARN instead of ERROR (default: strict, thin card is refused)")
    vm.add_argument("--force", action="store_true", default=False,
                    help="v9.7.409: keep CLAIM_SAFETY findings at WARN on a FINISHED-profile card after "
                         "human review (default: blocking on the finished profile)")
    vm.add_argument("--interp", action="store_true", default=False,
                    help="Also run the Mode-B INTERPRETATION gate (judgment substance; advisory WARN, "
                         "non-blocking). --interp-strict requires the §4 #### SYNTHESIS/REFDARK anchors.")
    vm.add_argument("--interp-strict", action="store_true", default=False, dest="interp_strict",
                    help="With --interp: interpretation must live in the anchors (enforce on NEW cards).")
    vm.add_argument(
        "--substantive-quality-v2", action="store_true", default=False,
        dest="substantive_quality_v2",
        help=("Prospective finished-card gate for structured §26 OSMAC, §46 type/reference, "
              "and §47 host-matched comparison reasoning. Opt-in so legacy finished cards "
              "are not silently subjected to a new migration contract."),
    )
    vm.add_argument(
        "--semantic-sections-v3", action="store_true", default=False,
        dest="semantic_sections_v3",
        help=("Prospective finished-card gate for typed §10 boundary/co-capture, "
              "§12 ecological alternatives, §17 exact-target analytical decisions, "
              "and §24 receipt-bound novelty evidence. Separate opt-in so v2 remains stable."),
    )
    vm.add_argument(
        "--semantic-comparators-v4", action="store_true", default=False,
        dest="semantic_comparators_v4",
        help=("Prospective finished-card gate for evidence-opposed §6 tailoring and measured, "
              "bounded, decision-bearing §45-§47 comparisons. Separate opt-in so v2 and v3 "
              "remain stable."),
    )
    vm.add_argument(
        "--semantic-sections-v5", action="store_true", default=False,
        dest="semantic_sections_v5",
        help=("Prospective finished-card gate for receipt-bound missing-evidence ledgers, "
              "source-opposed final decisions, typed cross-cluster adjudication, exact region "
              "CDS census reconciliation, and RG-GMCI accounting in sections 15, 19, 29, 31, "
              "and 43. Separate opt-in so v2-v4 remain stable."),
    )
    vm.add_argument(
        "--semantic-decision-chains-v6", action="store_true", default=False,
        dest="semantic_decision_chains_v6",
        help=("Prospective finished-card gate applying one shared measured-or-terminal, "
              "alternative-or-limitation, bounded-inference and result-to-decision contract "
              "to sections 14, 16, 21, 22, 23, 25, 30 and 41. Separate opt-in so v2-v5 "
              "remain stable and inventory/presentation sections are not over-gated."),
    )
    vm.add_argument(
        "--semantic-claim-models-v7", action="store_true", default=False,
        dest="semantic_claim_models_v7",
        help=("Prospective finished-card gate for receipt-bound claim models in sections "
              "8, 11, 13 and 44. Separate opt-in so v2-v6 remain stable."),
    )
    vm.add_argument(
        "--inventory-reconciliation-v8", action="store_true", default=False,
        dest="inventory_reconciliation_v8",
        help=("Prospective finished-card observational reconciliation gate for exact-member "
              "or typed-zero inventories in sections 32-35, 37 and 38. Separate opt-in so "
              "v2-v7 remain stable."),
    )
    vm.add_argument(
        "--selection-process-v9", action="store_true", default=False,
        dest="selection_process_v9",
        help=("Prospective finished-card process-provenance gate for section 2: frozen "
              "candidate set, comparator or typed terminal, observed metrics, predeclared "
              "rule, bounded information gain and discriminating next action."),
    )
    vm.add_argument(
        "--figure-spec-v10", action="store_true", default=False,
        dest="figure_spec_v10",
        help=("Prospective finished-card section-18 bridge to the canonical locus-map-v8 "
              "receipt, rendered triple, exact roster and separate owner visual review."),
    )
    vm.add_argument(
        "--reconciliation-specificity-v11", action="store_true", default=False,
        dest="reconciliation_specificity_v11",
        help=("Prospective finished-card section-28 gate rejecting one normalized "
              "evidence/reconciliation pair reused across eight or more section rows. "
              "It does not score fixed claim-safety language or prose outside the matrix."),
    )
    vm.add_argument("--summary-only", action="store_true", default=False, dest="summary_only",
                    help="Print grouped finding-code counts instead of every finding instance. "
                         "Does not weaken the gate or change its exit code.")
    vm.add_argument("--report-json", default=None, dest="report_json", metavar="PATH",
                    help="Write a deterministic JSON receipt containing grouped categories and "
                         "all exact finding instances.")
    vm.set_defaults(func=verify_modeb_command)

    vc = sub.add_parser("verify-citations",
                        help="Fail-closed node·region citation gate: refuse a BGC deliverable that cites a "
                             "strain+BGC with no contig node (WAC-01375 fatal-error class)")
    vc.add_argument("path", help="A Mode B report/review/deliverable .md, or a directory scanned recursively")
    vc.set_defaults(func=verify_citations_command)

    # v9.7.236: `mamey workflow` — the Sapote-tier analogue of `mamey validate`.
    # Mamey enforces its phase order in engine code; the Sapote judgment layer had the same
    # ordered steps written down (FULL_RUN_PROFILE.md Section A) and a fleet of individually
    # callable gates, but no single driver that SEQUENCED them. This registers that driver so
    # the workflow ledger is reachable from the CLI like every other gate.
    # Contract: docs/SAPOTE_WORKFLOW_CONTRACT.md · Driver: tools/sapote_workflow.py
    wf = sub.add_parser("workflow",
                        help="Sapote workflow ledger for a sealed package: per-step "
                             "PASS/PENDING/BLOCKED with receipts (W0-W10). --strict fails closed.")
    wf.add_argument("--package", required=True, help="Sealed Mamey package directory")
    wf.add_argument("--deliverables", default=None,
                    help="Directory holding authored Sapote deliverables (guides, narratives)")
    wf.add_argument("--strict", action="store_true",
                    help="Exit 1 if any MANDATORY step is not PASS (release gate)")
    wf.add_argument("--json", action="store_true", dest="as_json",
                    help="Emit the ledger as JSON")
    wf.add_argument("--ledger-out", default=None, dest="ledger_out",
                    help="Write the markdown ledger here (default: inside the package)")
    wf.set_defaults(func=workflow_command)
    # v9.7.89: mode-b can consume domain-level evidence if present
    mb.add_argument("--with-domain-level", action="store_true", dest="with_domain_level",
                    default=False, help="Run/consume domain-level enrichment in Mode B cards")

    # v9.7.89: domain-level — native post-seal domain evidence review (non-blocking)
    dl = sub.add_parser("domain-level",
                        help="Post-seal domain-level Mode B enrichment from a sealed package "
                             "(role mapping, complexity, claim ceilings)")
    dl.add_argument("--package", required=True,
                    help="Path to sealed package directory (containing manifest.json)")
    dl.add_argument("--source-antismash", default=None, dest="source_antismash",
                    help="Optional antiSMASH ZIP for full per-domain detail (else uses sealed gene context)")
    dl.add_argument("--top-n", type=int, default=10, dest="top_n",
                    help="Number of top leads to analyse (default: 10)")
    dl.add_argument("--emit-figures", action="store_true", dest="emit_figures", default=False,
                    help="Also render domain-level figures into <outdir> (live: domain_figures.render_domain_figures)")
    dl.add_argument("--out", default=None, dest="outdir",
                    help="Output directory (default: <package>/domain_level/)")
    dl.set_defaults(func=_domain_level_command)

    # ingest-receipts: the P-D front door — persist Sapote Mode B judgment into the
    # store and reconcile the master workbook's E1 sheet from the updated register.
    ir = sub.add_parser("ingest-receipts",
                        help="Ingest Mode B judgment into the judgment store (+ optional --master E1 reconcile)")
    ir.add_argument("--package", required=True,
                    help="Path to the strain package directory (containing the judgment register)")
    ir.add_argument("--receipt", default=None,
                    help="Path to mode_b_receipt.json emitted by the Sapote session "
                         "(omit when using --auto-detect or --card)")
    ir.add_argument("--auto-detect", action="store_true", default=False,
                    dest="auto_detect",
                    help="Scan <pkg>/judgment/ for *_mode_b.md cards not yet in the "
                         "register and ingest them. Use at session start to recover "
                         "any chat-written cards. (W4 item 2, v9.7.149c)")
    ir.add_argument("--card", default=None,
                    help="Persist a single Mode B card file (one card = one CLI "
                         "call). Resolves BGC ID + session ID from the card's "
                         "<!-- MODE B: ... --> header, falls back to filename. "
                         "Mutually exclusive with --receipt and --auto-detect. "
                         "(N4 follow-up, v9.7.149c)")
    ir.add_argument("--master", default=None,
                    help="Optional master workbook .xlsx to reconcile E1_Mode_B_Index from the register")
    ir.add_argument("--force-structure", action="store_true", default=False,
                    dest="force_structure",
                    help="Record cards even when the structure gate finds "
                         "ERROR-severity §1–§48 contract violations. Use with "
                         "care — bypasses the firebreak that catches "
                         "wrong-scaffold cards. (W9, v9.7.150+)")
    ir.set_defaults(func=ingest_receipts_command)

    # Read-only gate between persisted candidate cards and external owner review.
    # This validates receipt/hash coupling but never mutates the package or owner index.
    frr = sub.add_parser(
        "validate-finished-review-request",
        help="Validate a hash-bound Mode B finished-review request without promotion",
    )
    frr.add_argument("--package", required=True,
                     help="Sealed package directory whose manifest binds the exact locus")
    frr.add_argument("--request", required=True,
                     help="Finished-review request JSON")
    frr.add_argument("--artifact-root", required=True, dest="artifact_root",
                     help="Root for portable relative card, roster, and receipt locators")
    frr.set_defaults(func=validate_finished_review_request_command)

    # class-believability (v9.7.330, LQ-PATH-01): committed-step believability engine. Non-blocking
    # post-seal subcommand — reads *_gene_context.jsonl + _2_inventory.csv, never touches the core
    # run. Emits per-BGC (local) and pooled-per-strain believability tiers with a named-FP guard.
    from . import class_believability as _class_believability
    _class_believability.register_subparser(sub)

    # emit-strain-modeb (v9.7.330, LQ-STRAIN-01/02): strain-level Mode B (Full Strain Sapote, S1–S8).
    # Non-blocking post-seal — emits the deterministic skeleton from a sealed package and runs a
    # strain-structure gate (sibling of modeb_structure_gate). Sapote authors S4/S5/S8 on top.
    from . import strain_modeb as _strain_modeb
    _strain_modeb.register_subparser(sub)

    # lab-quest (v9.7.390 candidate, B8/v9.7.405): optional local UI bound to this installed
    # engine. The launcher accepts a user-selected project root; it never searches personal
    # workspaces for an arbitrary Mamey source tree or treats interface progress as scientific
    # evidence. See mamey/lab_quest.py / lab_quest_registry.py / lab_quest_app.py / docs/LAB_QUEST.md.
    from . import lab_quest as _lab_quest
    _lab_quest.register_subparser(sub)

    # emit-modeb-cards (v9.7.330, Blue): compact auto-filled per-BGC Mode-B DATA cards (composition,
    # RG-GMCI split-pathway banner, auto-priors, architecture domain-counts). Complementary to
    # emit-modeb-template (the §1-§48 authoring scaffold) — a triage/quick-look card. Non-blocking.
    from . import modeb_cards as _modeb_cards
    _modeb_cards.register_subparser(sub)

    # resistance-dossier (Claude): post-seal per-BGC resistance-focused gene-by-gene dossiers —
    # resistance loci via domain_reference 'resistance' category + per-gene nr BLASTp + MIBiG
    # convergence, grouped by role, claim-safe. Non-blocking. Cross-BGC MIBiG join keyed exactly on
    # (bgc_id, query_gene); output is a sibling, never inside the sealed package.
    from . import resistance_dossier as _resistance_dossier
    _resistance_dossier.register_subparser(sub)

    # Gemini (v9.7.167): two-strain comparative layer. Consumes two strains' antiSMASH
    # ZIPs (and optionally genome FASTAs) and emits per-BGC gene-level similarity (S5) +
    # the recovered comparator layers (S6, already in Mamey as of v9.7.166). Alignment runs
    # on the pyswrd backend by default, auto-upgrading to DIAMOND if a `diamond` binary is on
    # PATH (see sapote_addons/DIAMOND_STATUS.md). Offline-installable via the vendored wheels.
    from .compare import compare_command
    gc = sub.add_parser(
        "compare",
        help="Compare two antiSMASH result sets gene by gene and retain ClusterBlast, "
             "SubClusterBlast, and KnownClusterBlast comparator evidence")
    gc.add_argument("--strain-a", required=True, dest="strain_a",
                    help="Strain A: antiSMASH output ZIP (needs GBK records/translations; a "
                         "sealed package dir does NOT store these — pass the ZIP)")
    gc.add_argument("--strain-b", required=True, dest="strain_b",
                    help="Strain B: antiSMASH output ZIP (the comparison reference; the more "
                         "contiguous assembly is the scaffold)")
    gc.add_argument("--genome-a", default=None, dest="genome_a",
                    help="Optional strain A whole-genome FASTA (enables S1/S2 ANI + proteome)")
    gc.add_argument("--genome-b", default=None, dest="genome_b",
                    help="Optional strain B whole-genome FASTA")
    gc.add_argument("--out", default="gemini_out", help="Output directory")
    gc.add_argument("--alignment-threads", type=int, default=1,
                    help="Protein alignment threads (positive integer; default 1). "
                         "Controls DIAMOND/pyswrd, not optional ANI; Biopython is serial. "
                         "See docs/COMPARE_RESOURCE_CONTROL.md.")
    gc.add_argument("--min-identity", type=float, default=70.0, dest="min_identity",
                    help="Present-gene identity threshold (spec S5 default 70)")
    gc.add_argument("--min-coverage", type=float, default=60.0, dest="min_coverage",
                    help="Present-gene coverage threshold (spec S5 default 60)")
    gc.set_defaults(func=compare_command)

    # Wheelhouse (v9.7.172): lab-data store lifecycle (data, not pipeline code).
    from .wheelhouse import wheelhouse_command
    wh = sub.add_parser("wheelhouse", help="Manage the Wheelhouse lab-data store (strains, scanners, validations)")
    wh_sub = wh.add_subparsers(dest="wh_action")
    wh_sub.add_parser("list", help="Summarize strains, scanners, validations")
    whc = wh_sub.add_parser("clean", help="Prune superseded scanner-registry versions (dry-run unless --apply)")
    whc.add_argument("--apply", action="store_true", help="Actually remove superseded files")
    wha = wh_sub.add_parser("add-strain", help="Merge a strain JSON into the strain registry")
    wha.add_argument("strain_json", help="Path to a strain record JSON")
    wh.set_defaults(func=wheelhouse_command)

    # tab-reconcile (patch-chat fold): deterministic antiSMASH-tab evidence ledger for one BGC.
    # This is the raw-tab parser requested by the BGC028/AS-XXX QC note: it surfaces
    # Gene overview, Tailoring, MIBiG/ClusterBlast/KCB/SubClusterBlast, TFBS, Pfam,
    # TIGRFAM, NRPS/PKS, active-site, and TTA/bldA evidence as a Mode B ledger.
    from .tab_reconcile import tab_reconcile_command
    tr = sub.add_parser(
        "tab-reconcile",
        help="Parse antiSMASH tabs for one BGC/region and emit Mode B evidence ledgers")
    tr.add_argument("--antismash", required=True,
                    help="Raw antiSMASH ZIP or extracted antiSMASH output directory")
    tr.add_argument("--package", default=None,
                    help="Optional sealed Mamey complete-package ZIP or package directory for BGC↔region mapping")
    tr.add_argument("--bgc", default=None, help="Mamey BGC id, e.g. BGC028; requires --package unless --node is also provided")
    tr.add_argument("--node", default=None, help="antiSMASH node/contig id or substring")
    tr.add_argument("--region", default=None, help="antiSMASH region, e.g. region001 or 1")
    tr.add_argument("--out", required=True, help="Output directory for ledger/report files")
    tr.set_defaults(func=tab_reconcile_command)

    # KCB front-page reader (v9.7.176): Layer 0 — read the antiSMASH "Most similar known
    # cluster" column FIRST, with a corroboration tier (similarity% + matching-gene count) that
    # tells a real cluster match from a single-protein coincidence. The fix for the front-page
    # miss (mycotrienin). Named KCB hits are leads to check, not verdicts.
    from .kcb_frontpage import frontpage_command
    fp = sub.add_parser("kcb-frontpage",
                        help="Read antiSMASH KnownClusterBlast front-page hits, ranked + corroboration-tiered")
    fp.add_argument("strain_dir", help="antiSMASH output directory (contains regions.js)")
    fp.add_argument("--top", type=int, default=50, help="Show the top N hits")
    fp.add_argument("--region", default=None, help="Filter to hits on this region (e.g. r32c1 or region001)")
    fp.add_argument("--node", default=None, help="(unsupported: regions.js has no contig — use --region)")
    fp.add_argument("--bgc", default=None, help="(unsupported: regions.js has no BGC id — see the <strain>_2b_bgc_crosswalk.csv package artifact)")
    fp.set_defaults(func=frontpage_command)

    # triage-raw (new, v9.7.233): guided PRE-EXTRACTION genome triage. Chains kcb-frontpage,
    # a new scanner-evidence census, rare_motif, and split_detector into one pass, in the
    # run order docs/Sapote_Mamey_ROADMAP.md documents ("KCB front page -> scanners on every
    # region -> rare-motif -> bgc_walk"). Those four modules exist individually but,
    # per the roadmap's own "Known gaps / not built" note, none is wired as the default
    # entry point — this closes that gap without adding new inference logic (see
    # mamey/raw_antismash_triage.py's module docstring for the claim-safety scoping of
    # step 2). NAMED "triage-raw", not "explore": a separate v9.7.233 session independently
    # built a different, also-valuable "mamey explore" (sealed-package divergence/
    # co-capture correctness checks — see the "explore" subparser above/below). Both were
    # built the same day under the same brief and collided on the name; see
    # raw_antismash_triage.py's module docstring for how the two are complementary.
    # v9.7.268: import lazily. raw_antismash_triage hard-imports `from Bio import SeqIO`
    # (genome-level SeqIO parsing is intrinsic to pre-extraction triage), and importing it
    # here at parser-build time made biopython a hard requirement for EVERY command — even
    # `mamey doctor`/`--help`, which crashed at parser construction when biopython was absent,
    # despite biopython being documented optional (docs/PREREQUISITES.md §0; parsers.py shims it via
    # _gbk_shim). Deferring the import to invocation keeps the parser (and every other command)
    # working without biopython; `triage-raw` itself still needs it and now fails with a clear
    # message only when actually run.
    def triage_raw_command(args):
        try:
            from .raw_antismash_triage import explore_command as _cmd
        except ModuleNotFoundError as e:
            if e.name == "Bio":
                raise SystemExit(
                    "mamey triage-raw needs biopython (Bio.SeqIO) for pre-extraction genome "
                    "triage. Install it (pip install biopython), or offline via a local wheel "
                    "(see docs/PREREQUISITES.md §3). All other "
                    "commands run without it (the extraction path uses the built-in GBK shim)."
                )
            raise
        return _cmd(args)
    ex = sub.add_parser("triage-raw",
                         help="Guided PRE-EXTRACTION genome triage: KCB front page + scanner "
                              "evidence + rare-motif scan + split-detector + bgc_walk on the "
                              "priority regions, in one pass, directly on a raw antiSMASH ZIP/dir "
                              "(see docs/Sapote_Mamey_ROADMAP.md). For sealed-package novelty/"
                              "divergence correctness checks after extraction, see `mamey explore`.")
    ex_in = ex.add_mutually_exclusive_group(required=True)
    ex_in.add_argument("--strain-dir", dest="strain_dir", default=None,
                        help="Already-extracted antiSMASH output directory (contains regions.js)")
    ex_in.add_argument("--input-zip", dest="input_zip", default=None,
                        help="Raw antiSMASH output ZIP (extracted to a temp dir automatically)")
    ex.add_argument("--strain", default=None, help="Strain label for the report header only")
    ex.add_argument("--top-n", dest="top_n", type=int, default=5,
                     help="Number of priority regions to report in detail (default 5)")
    ex.add_argument("--no-walk", dest="no_walk", action="store_true",
                     help="Skip step 5 (bgc_walk) — useful when pyhmmer/an HMM db isn't available")
    ex.add_argument("--out", default=None, help="Write the markdown report to this path (else stdout)")
    ex.add_argument("--json", action="store_true",
                     help="Also emit the full structured report as JSON")
    ex.set_defaults(func=triage_raw_command)

    # figures (v9.7.177): publication figures from the wheel stack. diagram/atlas need
    # dna-features-viewer/pycirclize (in the gemini-stack addon); ani needs pyskani+matplotlib.
    # All degrade with a clear "install the addon" message if wheels are absent.
    from .bgc_figures import figures_command
    fg = sub.add_parser("figures", help="Publication figures (diagram | atlas | ani | gcf-network | clinker)")
    fg_sub = fg.add_subparsers(dest="fig_kind")
    fgd = fg_sub.add_parser("diagram", help="BGC gene-arrow diagram (dna-features-viewer)")
    fgd.add_argument("gbk", help="antiSMASH region GBK")
    fgd.add_argument("out", help="output PNG path")
    fga = fg_sub.add_parser("atlas", help="Circular contig/BGC map (pycirclize)")
    fga.add_argument("strain_dir", help="antiSMASH output directory")
    fga.add_argument("out", help="output PNG path")
    fgn = fg_sub.add_parser("ani", help="All-vs-all ANI heatmap across strains (pyskani)")
    fgn.add_argument("strain_dirs", nargs="+", help="two or more antiSMASH output directories")
    fgn.add_argument("out", help="output PNG path")
    # gcf-network + clinker: BiG-SCAPE GCF network from a BiG-SCAPE 2 DB, and clinker cross-cluster
    # alignment. Supporting figures; membership + gene links are similarity, not identity. run AND
    # cutoff are required (a cutoff changes the whole picture — no silent default).
    fgg = fg_sub.add_parser("gcf-network", help="BiG-SCAPE GCF network for a strain (from a BiG-SCAPE 2 DB)")
    fgg.add_argument("--db", required=True, help="BiG-SCAPE 2 SQLite DB")
    fgg.add_argument("--strain", required=True, help="strain id as it appears in the gbk path (e.g. AS-XXX)")
    fgg.add_argument("--run", type=int, required=True, help="BiG-SCAPE run id (largest/latest is authoritative)")
    fgg.add_argument("--cutoff", type=float, required=True, help="distance cutoff (0.3 strict / 0.5 default / 0.7 loose)")
    fgg.add_argument("--evidence", default=None, help="all_evidence.json to map BGC ids + highlight leads (optional)")
    fgg.add_argument("--out", required=True, help="output PNG path")
    fgc = fg_sub.add_parser("clinker", help="clinker comparative gene-cluster alignment (HTML) across region GBKs")
    fgc.add_argument("gbks", nargs="+", help="two or more region GBKs (a lead + its RG-GMCI partners, or a GCF family)")
    fgc.add_argument("--out", required=True, help="output HTML path")
    # kcb-locusmap (FA5): offline KnownClusterBlast comparative locus map (matplotlib-only, no
    # network). Post-seal, non-blocking figure; renders evidence, never scores/gates. Own dispatch
    # (overrides the group figures_command) into mamey.kcb_locusmap.main.
    from . import kcb_locusmap as _kcb_locusmap
    fgk = fg_sub.add_parser("kcb-locusmap",
                            help="Offline KnownClusterBlast comparative locus map (query vs top-N MIBiG refs)")
    _fgk_src = fgk.add_mutually_exclusive_group(required=True)
    _fgk_src.add_argument("--zip", dest="kcb_zip", help="Raw antiSMASH ZIP (reads knownclusterblast/*.txt)")
    _fgk_src.add_argument("--kcb-txt", dest="kcb_txt", help="A single knownclusterblast/clusterblast .txt file")
    fgk.add_argument("--contig", default="", help="Contig/region key, e.g. NODE_106 (ZIP mode)")
    fgk.add_argument("--out-dir", dest="kcb_out_dir", required=True, help="output directory")
    fgk.add_argument("--top-n", dest="kcb_top_n", type=int, default=6)
    fgk.add_argument("--strain-id", dest="kcb_strain_id", default="")
    fgk.add_argument("--bgc-id", dest="kcb_bgc_id", default="")
    fgk.add_argument("--products", dest="kcb_products", default="")
    fgk.add_argument("--stem", dest="kcb_stem", default="")
    fgk.set_defaults(func=lambda a: _kcb_locusmap.main(
        (["--zip", a.kcb_zip] if a.kcb_zip else ["--kcb-txt", a.kcb_txt])
        + (["--contig", a.contig] if a.contig else [])
        + ["--out-dir", a.kcb_out_dir, "--top-n", str(a.kcb_top_n)]
        + (["--strain-id", a.kcb_strain_id] if a.kcb_strain_id else [])
        + (["--bgc-id", a.kcb_bgc_id] if a.kcb_bgc_id else [])
        + (["--products", a.kcb_products] if a.kcb_products else [])
        + (["--stem", a.kcb_stem] if a.kcb_stem else [])))
    fg.set_defaults(func=figures_command)

    # blastp-online (v9.7.178): the runner+interpreter for the NCBI web BLASTp channel — the
    # independent per-gene homology check that overturned two false antiSMASH calls on BGC006.
    # FAIL-CLOSED + offline-safe: if NCBI is unreachable the channel is simply off; never
    # fabricates hits. Batch <=10, giants solo (ONLINE_BLASTP_PROTOCOL).
    from .blastp_online import blastp_online_command
    bo = sub.add_parser("blastp-online",
                        help="Per-gene NCBI web BLASTp for a BGC (independent homology channel; fail-closed)")
    bo.add_argument("--package", required=True, help="antiSMASH region GBK/ZIP for the BGC (proteins)")
    # v9.7.199 BUGFIX: default was the metavar "BGC" (a truthy placeholder), so EVERY call without
    # an explicit --bgc entered the crosswalk-scoping branch and refused — even a bare region GBK,
    # which is already one region and needs no scoping. This blocked the portable-handoff path
    # (region GBK -> online BLASTp). Default None: no --bgc means "submit the region GBK's proteins".
    bo.add_argument("--bgc", default=None, help="BGC id — with a full-genome ZIP, scopes to this BGC via the crosswalk")
    bo.add_argument("--crosswalk", default=None,
                    help="path to *_2b_bgc_crosswalk.csv or the sealed package dir (needed to scope --bgc on a full ZIP; auto-discovered from a sibling package if omitted)")
    bo.add_argument("--region", default=None,
                    help="explicit NODE·contig / regionNNN locator to scope by (alternative to --bgc)")
    bo.add_argument("--database", default="nr", choices=["nr", "refseq_protein", "swissprot"])
    bo.add_argument("--evalue", default="1e-5")
    bo.add_argument("--batch-size", type=int, default=10, dest="batch_size",
                    help="proteins per submission (default 10, hard cap 30)")
    bo.add_argument("--outdir", default=None, help="output dir for the panel CSV")
    # v9.7.338 (BLP-02): expose the product-novelty cross-check inputs. Previously
    # function_and_novelty read getattr(args,"kcb_top"/"kcb_coverage_genes") from dests that never
    # existed, so the product-novelty axis was permanently UNDETERMINED. When omitted and --bgc is
    # set, both are auto-derived from the sealed package's per-gene MIBiG profile
    # (dominant_mibig_compound / dominant_distinct_query_genes).
    bo.add_argument("--kcb-top", default=None, dest="kcb_top",
                    help="KCB/MIBiG anchor label for the product-novelty cross-check "
                         "(auto-derived from the package's *_3_mibig_profile.csv when omitted and --bgc is set)")
    bo.add_argument("--kcb-coverage-genes", type=int, default=None, dest="kcb_coverage_genes",
                    help="number of cluster genes the KCB anchor covers "
                         "(auto-derived from dominant_distinct_query_genes when omitted)")
    bo.set_defaults(func=blastp_online_command)

    # blastp-ebi (v9.7.215): formal EBI fallback transport for when NCBI nr is unreachable from the run
    # host. One EBI job per protein; retrieves XML so query-coverage survives (mamey.ebi_xml_to_outfmt10
    # converts to the same -outfmt 10 ingest-blastp already accepts). EBI has no nr — DB is stamped into
    # provenance; fallback only, never the default. Resumable: run --submit, then --harvest, then --to-outfmt10.
    from .blastp_ebi import blastp_ebi_command
    be = sub.add_parser("blastp-ebi",
                        help="EBI fallback BLASTp transport (no nr; DB-tagged provenance; coverage-preserving XML path)")
    be.add_argument("--fasta", required=True, help="multi-FASTA of the BGC's proteins (one job per record)")
    be.add_argument("--state", required=True, help="resumable job-id state JSON (persisted after every submit/harvest)")
    be.add_argument("--database", default="uniprotkb_bacteria",
                    help="EBI protein DB (no nr): uniprotkb_bacteria (default), uniprotkb_trembl, uniref90")
    be.add_argument("--email", default=None,
                    help="valid contact email — REQUIRED by EMBL-EBI for --submit (anonymous/placeholder jobs are refused)")
    be.add_argument("--submit", action="store_true", help="submit all sequences as EBI jobs (<=30/transaction; requires --email)")
    be.add_argument("--harvest", action="store_true", help="poll + retrieve XML for finished jobs")
    be.add_argument("--to-outfmt10", default=None, dest="to_outfmt10",
                    help="convert harvested XML -> this -outfmt 10 CSV (coverage intact) for ingest-blastp")
    be.add_argument("--submit-gap", type=float, default=6.0, dest="submit_gap", help="seconds between submits (EBI fair-use)")
    be.add_argument("--poll-budget", type=int, default=600, dest="poll_budget", help="max seconds to poll in one --harvest pass")
    be.add_argument("--hits", type=int, default=6, help="hits/alignments per EBI job (snapped to the nearest valid EBI enum; default 6)")
    be.set_defaults(func=blastp_ebi_command)

    # report-card (PER_BGC_REPORT_CARD_SPEC.md §6.1): render L0-L1 per-BGC report cards from a sealed
    # package (triage board + Patch-G prediction CSVs). Auto layers only; L2/L3 leave authoring slots.
    from .report_card import report_card_command
    rc = sub.add_parser("report-card",
                        help="Render L0-L1 per-BGC report cards from a package (predicted molecule + badges)")
    rc.add_argument("--package", required=True, help="sealed strain package directory")
    rc.add_argument("--bgc", default=None, help="single BGC id (default: all BGCs)")
    rc.add_argument("--out", default=None, help="output markdown path (default: stdout)")
    rc.set_defaults(func=report_card_command)

    # Portable, locator-first L0 report program. External evidence paths are
    # resolved from a user-supplied logical-root configuration and manifest.
    from .bgc_l0_program import add_cli_parser; add_cli_parser(sub)
    from .stage2_overlay import add_cli_parser as add_stage2_overlay_parser; add_stage2_overlay_parser(sub)

    # blastp-round (v9.7.180): phased strain BLASTp planner. Round 1 = FULL proteins for the
    # top-N BGCs (so complete homology is back before their Mode B cards) + one representative
    # protein for EVERY other BGC (saccharides included — a representative hit can promote a
    # saccharide the scanners downgrade). Follow-up rounds deepen the sampled BGCs.
    from .blastp_online import blastp_round_command
    br = sub.add_parser("blastp-round",
                        help="Plan/run a phased strain BLASTp round (full top-N + 1 per remaining BGC)")
    br.add_argument("--package", required=True, help="strain package directory")
    br.add_argument("--full-top", type=int, default=3, dest="full_top",
                    help="how many top-ranked BGCs get FULL per-gene BLASTp (default 3)")
    br.add_argument("--sample-per-bgc", type=int, default=1, dest="sample_per_bgc",
                    help="representative proteins per remaining BGC (default 1)")
    br.add_argument("--round", type=int, default=1, dest="round_num", help="round number")
    br.add_argument("--run", action="store_true", default=False,
                    help="actually submit to NCBI (default: dry-run plan only)")
    br.add_argument("--database", default="nr", choices=["nr", "refseq_protein", "swissprot"])
    br.add_argument("--evalue", default="1e-5")
    br.add_argument("--outdir", default=None)
    br.set_defaults(func=blastp_round_command)

    # auto-blastp (v9.7.345): the resumable automation layer OVER the existing online BLASTp
    # system. Builds a priority worklist of BGCs still needing BLASTp (from the ingest ledger the
    # gate reads), submits ~1 NCBI query / 8 min (courteous public-server cadence), polls the
    # outstanding RIDs, and ingests retrieved results hourly (adjustable) into the package's unmixed
    # channel store. Fail-closed; transport is injectable; NO email/personal id on any request.
    from .blastp_autoharness import auto_blastp_command, DEFAULT_SUBMIT_INTERVAL_S as _AB_SI, \
        DEFAULT_INGEST_INTERVAL_S as _AB_II
    ab = sub.add_parser("auto-blastp",
                        help="Resumable priority BLASTp scheduler (1 query / 8 min, hourly ingest)")
    ab.add_argument("--package", required=True, help="strain package directory")
    ab.add_argument("--strain", required=True, help="strain id (e.g. AS-XXX)")
    ab.add_argument("--priority", default="af_first",
                    choices=["af_first", "ab_first", "rank"],
                    help="worklist ordering (default af_first: antifungal-forward)")
    ab.add_argument("--channel", default="nr",
                    choices=["nr", "clustered_nr", "swissprot"],
                    help="channel store to fill (default nr — the online NCBI channel)")
    ab.add_argument("--submit-interval", type=int, default=_AB_SI, dest="submit_interval",
                    help="seconds between NCBI Puts (default 480 = 8 min)")
    ab.add_argument("--ingest-interval", type=int, default=_AB_II, dest="ingest_interval",
                    help="seconds between ingest sweeps (default 3600 = hourly)")
    ab.add_argument("--max-submits", type=int, default=None, dest="max_submits",
                    help="stop after this many Puts (default: run the whole worklist)")
    ab.add_argument("--dry-run", action="store_true", default=False, dest="dry_run",
                    help="plan the worklist + schedule with NO network")
    ab.set_defaults(func=auto_blastp_command)

    # blastp-availability (v9.7.345): Central Command "activate at onset + declare availability".
    # Scans a runs dir (or one package) and reports, per strain per channel, AVAILABLE-on-disk vs
    # INGESTED-into-package BLASTp — a text table + optional CSV/JSON (the table/widget aggregate).
    # Reader-side, non-scoring; reuses the gate's discovery so it agrees with the gate.
    from .blastp_availability import blastp_availability_command
    bav = sub.add_parser("blastp-availability",
                         help="Declare BLASTp availability (available-vs-ingested) per strain/channel")
    bav_g = bav.add_mutually_exclusive_group(required=True)
    bav_g.add_argument("--runs-dir", dest="runs_dir", help="runs directory (many <strain>/package dirs)")
    bav_g.add_argument("--package", dest="package", help="a single package directory")
    bav.add_argument("--out", default=None, help="write BLASTP_AVAILABILITY.csv/.json here")
    bav.set_defaults(func=blastp_availability_command)

    # deliverable-queue (v9.7.345): the resumable autonomous deliverable driver. Per strain:
    # auto-ingest available channels, verify the BLASTp gate is clear (else record BLASTP_BLOCKED),
    # then run the deterministic layers (Mode B templates + subsections, lead-pages, reference-dark,
    # good-guesses, af-dossier, compile-report). The JUDGMENT layer is flagged PENDING_JUDGMENT, not
    # auto-written (a claim-safe narrative is a judgment task). Idempotent via a ledger.
    from .deliverable_queue import deliverable_queue_command
    dq = sub.add_parser("deliverable-queue",
                        help="Resumable autonomous deliverable driver over a strain list (gate-gated)")
    dq.add_argument("strains", nargs="*", help="strain ids to process (e.g. AS-XXX AS-XXX)")
    dq.add_argument("--runs-dir", dest="runs_dir", required=True, help="runs directory")
    dq.add_argument("--out-root", dest="out_root", required=True, help="deliverable output root")
    dq.add_argument("--activity-table", dest="activity_table", default=None,
                    help="measured-activity CSV for af-dossier (optional)")
    dq.add_argument("--ledger", default=None, help="ledger path (default <out-root>/DELIVERABLE_QUEUE_LEDGER.json)")
    dq.add_argument("--no-resume", dest="no_resume", action="store_true", default=False,
                    help="reprocess strains already marked done in the ledger")
    dq.set_defaults(func=deliverable_queue_command)

    # Registry-backed, read-only user-facing deliverables discovery.  The
    # generated Markdown and the CLI consume the same source of truth.
    from .deliverables_registry import add_deliverables_arguments, deliverables_command
    dm = sub.add_parser(
        "deliverables",
        help="List, explain, preflight, or render the registry-backed deliverables menu",
    )
    add_deliverables_arguments(dm)
    dm.set_defaults(func=deliverables_command)

    # literature (v9.7.345): retrieve full PubMed abstracts (and search them) from the in-bundle,
    # PURGEABLE corpus (mamey/data/literature/_corpus/literature_corpus.jsonl). Reader-side; the
    # per-genus/_families .md files are a curated PMID-cited index INTO this corpus. Abstracts are
    # class-level literature context (similarity not identity; judgment deferred). Degrades cleanly
    # to empty if the corpus was purged for a public tier.
    from .literature_lookup import literature_command
    lit = sub.add_parser("literature",
                         help="Full-abstract lookup / search over the in-bundle PubMed corpus")
    lit_sub = lit.add_subparsers(dest="lit_cmd")
    litl = lit_sub.add_parser("lookup", help="Print the full abstract for a PMID")
    litl.add_argument("pmid", help="PubMed ID")
    lits = lit_sub.add_parser("search", help="Keyword search (AND/OR) over title+abstract")
    lits.add_argument("query", help="e.g. 'antifungal AND Candida' or 'lasso OR enediyne'")
    lits.add_argument("--limit", type=int, default=20)
    lit.set_defaults(func=literature_command)

    # hmm-adjudicate (v9.7.181): the intrinsic-structure HMM channel, reconciled with BLASTp.
    # HMM does what BLASTp can't — ordered domain grammar (module count), orphan/short-gene rescue,
    # and ADJUDICATION of BLASTp-vs-antiSMASH disagreements via the domain signature. Offline,
    # deterministic; degrades cleanly without pyhmmer/the HMM db.
    from .hmm_blastp_adjudicate import walk_domains, module_architecture
    ha = sub.add_parser("hmm-adjudicate",
                        help="Ordered HMM domain readout for a BGC (intrinsic structure; complements BLASTp)")
    ha.add_argument("region_gbk", help="antiSMASH region GBK")
    ha.add_argument("--hmm", default=None, help="HMM database (default: resolve from Wheelhouse/addon)")
    ha.add_argument("--locus", default=None, help="show module architecture for one locus_tag")

    def _hmm_adjudicate_cmd(args):
        hits, genes, reason = walk_domains(args.region_gbk, hmm_file=args.hmm)
        if reason:
            emit(f"[hmm-adjudicate] {reason}")
            return 2
        emit(f"[hmm-adjudicate] {len(genes)} genes, {sum(len(v) for v in hits.values())} domain hits")
        if args.locus:
            arch = module_architecture(hits, args.locus)
            emit(f"[hmm-adjudicate] {args.locus}: {' -> '.join(arch['domain_order']) or '(no domains)'}", f"[hmm-adjudicate]   ks_modules={arch['ks_modules']} single_module={arch['single_module']}", sep="\n")
        else:
            for g in genes:
                lt = g["lt"]
                doms = [nm for _, nm, _ in sorted(hits.get(lt, []))]
                if doms:
                    emit(f"  {lt:16} {' -> '.join(doms)}")
        return 0
    ha.set_defaults(func=_hmm_adjudicate_cmd)

    # W9 (v9.7.150+): emit a canonical §1–§48 Mode B template skeleton
    # pre-filled with the BGC-specific facts. Pairs with the structure gate
    # — cards built on the emitted template are structurally valid by
    # construction. Single-BGC mode prints to stdout (or --out); batch mode
    # writes one card per BGC to <pkg>/mode_b_templates/ + an index file.
    from .mode_b_receipt import emit_modeb_template_command
    et = sub.add_parser(
        "emit-modeb-template",
        help="Emit a canonical §1–§48 Mode B card template for one BGC or a batch "
             "(W9, v9.7.150+)",
    )
    et.add_argument("--package", required=True,
                    help="Path to the strain package directory")
    et.add_argument("--bgc", default=None,
                    help="Single-BGC mode: emit one template for this BGC ID")
    et.add_argument("--batch", action="store_true", default=False,
                    help="Batch mode: emit per-BGC templates for the strain "
                         "to <pkg>/mode_b_templates/ (mutually exclusive with --bgc)")
    et.add_argument("--scope", default="all",
                    choices=["all", "top", "leads", "pending"],
                    help="Batch scope: all=every BGC; top=top-N by Corrected_rank "
                         "(needs --top-n); leads=HIGH+ lead tier; pending=not yet "
                         "COMPLETE in the register. (default: all)")
    et.add_argument("--top-n", default=None, type=int, dest="top_n",
                    help="N for --scope top")
    et.add_argument("--out", default=None,
                    help="Single-BGC mode only: write template to this path "
                         "instead of stdout")
    et.add_argument(
        "--fail-on-empty",
        action="store_true",
        default=False,
        help="Exit 3 when --batch produces 0 templates (any scope). "
             "--scope leads always exits 3 on empty regardless of this flag.",
    )
    et.add_argument("--blastp-waiver", default=None, dest="blastp_waiver", metavar="REASON",
                    help="Override the v9.7.344 BLASTp-completeness HARD gate with a logged reason "
                         "(recorded to manifest provenance). Without this, emission is REFUSED when "
                         "ingestable BLASTp is available on disk but not ingested.")
    et.set_defaults(func=emit_modeb_template_command)
    # --- v9.7.194: contractual Mode B round orchestrator (emit + scaffold-verify + worklist) ---
    from .modeb_round import modeb_round_command
    mr = sub.add_parser("modeb-round",
                        help="Emit + scaffold-verify a round of N triage Mode B cards, write a stateful worklist (authoring is the Sapote step)")
    mr.add_argument("--package", required=True, help="Sealed package dir (manifest.json)")
    mr.add_argument("--top-n", type=int, default=10, dest="top_n", help="N cards per round (default 10)")
    mr.add_argument("--scope", default="top", choices=["all", "top", "leads", "pending"],
                    help="Which BGCs (default: top N by Corrected_rank)")
    mr.add_argument("--from-precompute", default=None, dest="from_precompute",
                    help="cohort precompute dir — pre-fill §8/§11/§14 (and more) from the cohort tables, joined on assembly_locator (Part C)")
    mr.set_defaults(func=modeb_round_command)

    # v9.7.123 (SM-P1-004): claim-safety linter — post-hoc check on Mode B cards
    cs = sub.add_parser(
        "claim-safety",
        help="Run the post-hoc claim-safety linter on a Mode B card or compendium markdown",
    )
    cs.add_argument("path", help="markdown / text file to lint")
    cs.add_argument("--card-id", default="", help="BGC ID for CSV report (e.g. BGC001)")
    cs.add_argument("--section", default="", help="section label (e.g. §1) for severity routing")
    cs.add_argument("--misanchor-flag", default="", help="Misanchor_Flag value from triage board")
    cs.add_argument("--package", default=None,
                    help="v9.7.153: analysis package directory. When supplied, compound "
                         "names are auto-derived from the package's own triage board "
                         "KCB_top candidates and the robust (low-false-positive) check "
                         "path is used by default instead of the bare-name heuristic.")
    cs.add_argument("--compound-names", default=None, dest="compound_names",
                    help="v9.7.153: comma-separated compound names to check identity "
                         "claims against (the robust path). Explicit override; takes "
                         "precedence over --package auto-derivation if both are given. "
                         "Useful for a bare-file invocation with no package directory.")
    cs.add_argument("--report", help="append findings to this CSV file (claim_safety_report.csv)")
    cs.add_argument("--mode", default="warn", choices=["warn", "fail"],
                    help="warn=record and exit 0; fail=exit 1 on any finding (default: warn)")
    cs.add_argument("--json", action="store_true", help="emit JSON instead of plain text")
    cs.set_defaults(func=claim_safety_command)


    # --- directed-pks-study (v9.7.138 research) ---
    dpk = sub.add_parser(
        "directed-pks-study",
        help="Run Directed PKS Study Mode from source CDS CSV + study spec; emits Pre-Sapote Lite, EFLS, figures, LC-MS, citations, workbook, and CDDR-PKS report",
    )
    dpk.add_argument("--source-csv", required=True,
                     help="Source CDS/gene table CSV; minimal columns include node_num/node, locus_tag, start, end, strand, domains_order/product")
    dpk.add_argument("--study-spec", required=True,
                     help="JSON study spec with study_id, groups, excluded_bgcs, figure_quality_gate, optional comparator_gene_table")
    dpk.add_argument("--out", required=True,
                     help="Output directory for directed study package")
    dpk.add_argument("--comparator-gene-table", default=None,
                     help="Optional comparator_gene_table.csv override; if supplied, enables comparator track wiring")
    dpk.set_defaults(func=directed_pks_study_command)

    # --- cddr-pks (v9.7.138 research) ---
    cddr = sub.add_parser(
        "cddr-pks",
        help="Build a CDDR-PKS deep-dive report from an existing directed study, or run Directed PKS first from source/spec",
    )
    cddr.add_argument("--directed-study-dir", default=None,
                      help="Existing directed study output directory containing DIRECTED_PKS_STUDY_RECEIPT.json")
    cddr.add_argument("--source-csv", default=None,
                      help="Optional source CDS/gene CSV; used when --directed-study-dir is not supplied")
    cddr.add_argument("--study-spec", default=None,
                      help="Optional JSON study spec; used when --directed-study-dir is not supplied")
    cddr.add_argument("--out", required=True,
                      help="Output directory for CDDR-PKS report, or directed study output if running from source/spec")
    cddr.add_argument("--comparator-gene-table", default=None,
                      help="Optional comparator_gene_table.csv override when running from source/spec")
    cddr.add_argument("--report-name", default="CDDR_PKS_REPORT.md",
                      help="Report filename when building from existing directed study (default: CDDR_PKS_REPORT.md)")
    cddr.set_defaults(func=cddr_pks_command)

    # --- release-qa (v9.7.138 research) ---
    rqa = sub.add_parser(
        "release-qa",
        help="Run release QA gates: Legacy Feature Matrix + Dual-LLM Handoff Receipt",
    )
    rqa.add_argument("--bundle-root", required=True,
                     help="Bundle/repo root to scan for instruction files")
    rqa.add_argument("--out", required=True,
                     help="Output directory for release QA receipts")
    rqa.add_argument("--legacy-matrix", default=None,
                     help="Existing LEGACY_FEATURE_MATRIX.csv; default writes/uses <out>/LEGACY_FEATURE_MATRIX.csv")
    rqa.add_argument("--create-default-legacy-matrix", action="store_true", default=False,
                     help="Create a default legacy feature matrix if missing")
    rqa.add_argument("--llm", default="chatgpt", choices=["chatgpt", "claude"],
                     help="LLM target for handoff receipt")
    rqa.add_argument("--handshake-visible", action="store_true", default=False,
                     help="Declare that the handshake sentence was visibly emitted in the session")
    rqa.add_argument("--capped-session", "--chatgpt-safe", action="store_true", dest="chatgpt_safe", default=False,
                     help="Request capped-session mode activation in the handoff receipt "
                          "(--chatgpt-safe is a deprecated alias).")
    rqa.add_argument("--strict", action="store_true", default=False,
                     help="Return nonzero if any release QA gate fails")
    rqa.set_defaults(func=release_qa_command)

    # --- bgc-blastp-panel (v9.7.142 starter) ---
    bp = sub.add_parser(
        "bgc-blastp-panel",
        help="Export up to two representative translated proteins per BGC as chunked FASTA files for manual BLASTP",
    )
    bp.add_argument("--input-zip", required=True, help="antiSMASH ZIP to parse for BGCs and CDS translations")
    bp.add_argument("--strain", default=None, help="Strain label for FASTA headers; defaults to ZIP stem")
    bp.add_argument("--outdir", default=None, help="Output directory for FASTA rounds and manifest")
    bp.add_argument("--genes-per-bgc", type=int, default=2, dest="genes_per_bgc",
                    help="Representative proteins to select per BGC (default: 2)")
    bp.add_argument("--proteins-per-file", type=int, default=20, dest="proteins_per_file",
                    help="Maximum FASTA records per BLASTP round file (default: 20)")
    bp.add_argument("--max-residues", type=int, default=85000, dest="max_residues",
                    help="Maximum amino-acid residues per NCBI web BLASTP FASTA (default: 85000; NCBI hard limit treated as 100000)")
    bp.add_argument("--max-query-chars", type=int, default=None, dest="max_query_chars",
                    help="Deprecated alias from REV1; if supplied, treated conservatively as a residue cap")
    bp.add_argument("--first-pass-size", type=int, default=30, dest="first_pass_size",
                    help="Approximate number of high-value proteins in first iterative BLASTP pass (default: 30)")
    bp.add_argument("--giant-aa-threshold", type=int, default=2500, dest="giant_aa_threshold",
                    help="Amino-acid length at which multidomain proteins are flagged for follow-up (default: 2500)")
    bp.add_argument("--isolate-giants", action="store_true", default=False, dest="isolate_giants",
                    help="Troubleshooting mode: isolate giant multidomain proteins into single-record FASTA rounds")
    bp.add_argument("--json-evidence", default="off", dest="json_evidence", choices=["off", "bounded", "full"],
                    help="antiSMASH JSON mode for BGC parsing (default: off for the bounded panel export)")
    bp.set_defaults(func=bgc_blastp_panel_command)


    wf = sub.add_parser(
        "wise-fragmented-pks",
        help="Split ranked fragmented PKS/NRPS FASTA into stable residue-safe BLASTP queue files",
    )
    wf.add_argument("--input-fasta", required=True, help="Ranked FASTA with optional rank= metadata in headers")
    wf.add_argument("--outdir", required=True, help="Output directory for queue FASTAs, ledger, and README")
    wf.add_argument("--prefix", default="ALL_STRAINS_RANKED", help="Filename prefix for queue IDs")
    wf.add_argument("--target-residues", type=int, default=85000, help="Residue target per batch (default: 85000)")
    wf.add_argument("--hard-cap", type=int, default=100000, help="NCBI web BLASTP hard cap (default: 100000)")
    wf.add_argument("--active-files", type=int, default=2, help="Number of ready-to-run files to emit (default: 2)")
    wf.add_argument("--start-q", type=int, default=1, help="Starting Q number for unique queue IDs")
    wf.add_argument("--emit-all", action="store_true", help="Emit all batches instead of only active files")
    wf.set_defaults(func=wise_fragmented_pks_command)

    bf = sub.add_parser(
        "blastp-followup",
        help="Parse NCBI BLASTP Hit Table/XML2 results and make the next iterative FASTA batch",
    )
    bf.add_argument("--hit-table", required=True, help="NCBI BLASTP Hit Table CSV; headerless CSV is supported")
    bf.add_argument("--xml2", default=None, help="Optional NCBI BLASTP Single-file XML2 for hit titles/coverage proof")
    bf.add_argument("--previous-selection", default=None, help="Previous BGC BLASTP panel selection manifest CSV")
    bf.add_argument("--panel-dir", default=None, help="Directory containing prior FASTA panel files; needed to emit next FASTA")
    bf.add_argument("--outdir", required=True, help="Output directory for parsed BLASTP evidence and follow-up files")
    bf.add_argument("--next-proteins", type=int, default=10, help="Maximum proteins in the next follow-up FASTA batch (default: 10)")
    bf.add_argument("--target-residues", type=int, default=20000, help="Residue target for next follow-up FASTA (default: 20000)")
    bf.set_defaults(func=blastp_followup_command)

    # --- modeb-blastp (v9.7.148) ---
    mb_b = sub.add_parser(
        "modeb-blastp",
        help="Emit per-BGC BLASTP FASTA batches from the panel manifest (Mode B §16 automation)",
    )
    mb_b.add_argument("--package", required=True,
                      help="Path to sealed Mamey package directory")
    mb_b.add_argument("--bgc", required=True,
                      help="BGC ID to emit batches for (e.g. BGC044)")
    mb_b.add_argument("--out", default=None,
                      help="Output directory (default: <package>/modeb_blastp/<BGC_ID>/)")
    mb_b.add_argument("--start-batch", type=int, default=1, dest="start_batch",
                      help="Starting batch number (default: 1)")
    mb_b.add_argument("--batch-size", type=int, default=3, dest="batch_size",
                      help="Proteins per batch (default: 3)")
    def _modeb_blastp_cmd(args):
        from .modeb_blastp import command as _mb_cmd
        return _mb_cmd(args)
    mb_b.set_defaults(func=_modeb_blastp_cmd)

    return p




def release_qa_command(args) -> int:
    """Formal CLI entry point for release QA gates."""
    from pathlib import Path as _Path
    import json as _json
    from .release_qa import run_release_qa

    receipt = run_release_qa(
        _Path(args.bundle_root),
        _Path(args.out),
        legacy_matrix=_Path(args.legacy_matrix) if getattr(args, "legacy_matrix", None) else None,
        create_default_legacy_matrix=getattr(args, "create_default_legacy_matrix", False),
        llm=getattr(args, "llm", "chatgpt"),
        handshake_visible=getattr(args, "handshake_visible", False),
        chatgpt_safe_mode_requested=getattr(args, "chatgpt_safe", False),
    )
    emit(_json.dumps({
        "status": receipt.get("status"),
        "receipt": receipt.get("receipt"),
        "report": receipt.get("report"),
        "legacy_status": receipt.get("legacy_feature_gate", {}).get("status"),
        "llm_handoff_status": receipt.get("llm_handoff", {}).get("status"),
    }, indent=2))
    if getattr(args, "strict", False) and receipt.get("status") != "PASS":
        return 1
    return 0



def directed_pks_study_command(args) -> int:
    """Formal CLI entry point for Directed PKS Study Mode."""
    from pathlib import Path as _Path
    import json as _json
    from .directed_studies.pks import load_study_spec, run_directed_pks_study

    spec = load_study_spec(_Path(args.study_spec))
    if getattr(args, "comparator_gene_table", None):
        spec = type(spec)(
            study_id=spec.study_id,
            groups=spec.groups,
            excluded_bgcs=spec.excluded_bgcs,
            figure_quality_gate=spec.figure_quality_gate,
            comparator_gene_table=args.comparator_gene_table,
        )
    receipt = run_directed_pks_study(_Path(args.source_csv), spec, _Path(args.out))
    emit(_json.dumps({
        "status": receipt.get("status"),
        "study_id": receipt.get("study_id"),
        "out": str(_Path(args.out)),
        "workbook": receipt.get("workbook"),
        "cddr_pks_report": receipt.get("cddr_pks_report"),
        "receipt": str(_Path(args.out) / "DIRECTED_PKS_STUDY_RECEIPT.json"),
    }, indent=2))
    return 0 if receipt.get("status") == "READY" else 2


def cddr_pks_command(args) -> int:
    """Formal CLI entry point for the CDDR-PKS report type."""
    from pathlib import Path as _Path
    import json as _json
    from .directed_studies.cddr_pks import build_cddr_pks_report
    from .directed_studies.pks import load_study_spec, run_directed_pks_study

    out = _Path(args.out)
    if getattr(args, "directed_study_dir", None):
        study_dir = _Path(args.directed_study_dir)
        receipt = build_cddr_pks_report(study_dir, out, report_name=getattr(args, "report_name", "CDDR_PKS_REPORT.md"))
        emit(_json.dumps({
            "status": receipt.status,
            "report_md": receipt.report_md,
            "report_json": receipt.report_json,
            "warning_count": receipt.warning_count,
        }, indent=2))
        return 0 if receipt.status in {"READY", "UNKNOWN"} else 2

    if not getattr(args, "source_csv", None) or not getattr(args, "study_spec", None):
        emit("ERROR: provide either --directed-study-dir or both --source-csv and --study-spec")
        return 2

    spec = load_study_spec(_Path(args.study_spec))
    if getattr(args, "comparator_gene_table", None):
        spec = type(spec)(
            study_id=spec.study_id,
            groups=spec.groups,
            excluded_bgcs=spec.excluded_bgcs,
            figure_quality_gate=spec.figure_quality_gate,
            comparator_gene_table=args.comparator_gene_table,
        )
    study_receipt = run_directed_pks_study(_Path(args.source_csv), spec, out)
    report_md = study_receipt.get("cddr_pks_report")
    report_json = study_receipt.get("cddr_pks_receipt")
    emit(_json.dumps({
        "status": study_receipt.get("status"),
        "study_id": study_receipt.get("study_id"),
        "out": str(out),
        "report_md": report_md,
        "report_json": report_json,
    }, indent=2))
    return 0 if study_receipt.get("status") == "READY" else 2



def claim_safety_command(args) -> int:
    """mamey claim-safety — run the post-hoc claim-safety linter (SM-P1-004).

    Starts in --mode warn (record findings, exit 0). Promote to --mode fail only after
    calibrating the false-positive rate on the real card corpus.
    """
    import json as _json
    import sys as _sys
    from pathlib import Path as _Path
    _tools = _Path(__file__).resolve().parents[1] / "tools"
    _sys.path.insert(0, str(_tools))
    try:
        from claim_safety_linter import (
            lint_claim_safety_report, write_claim_safety_csv,
            derive_compound_names_from_package,
        )
    except ImportError as e:
        emit(f"ERROR: could not import claim_safety_linter: {e}", file=_sys.stderr)
        return 1

    # v9.7.409 (AUDIT_cli_edgecases): existence guard before read. A mistyped path used to reach
    # _Path(...).read_text() and crash with a raw FileNotFoundError traceback; sibling readers
    # (verify-guide / verify-modeb / inspect) refuse cleanly. Mirror that: one-line ERROR, rc 1.
    if not _Path(args.path).is_file():
        emit(f"ERROR: claim-safety input not found: {args.path}", file=_sys.stderr, flush=True)
        return 1
    text = _Path(args.path).read_text(encoding="utf-8")

    # v9.7.153 (Part-2 Finding 3): resolve the compound-name set for the robust path.
    # Priority: explicit --compound-names override > --package auto-derivation > none
    # (heuristic fallback, with a one-line notice so the weaker path is never silent).
    compound_names = None
    explicit_names = getattr(args, "compound_names", None)
    package_dir = getattr(args, "package", None)
    if explicit_names:
        compound_names = {n.strip() for n in explicit_names.split(",") if n.strip()}
    elif package_dir:
        derived = derive_compound_names_from_package(package_dir)
        if derived:
            compound_names = derived
            emit(f"claim-safety: auto-derived {len(derived)} compound name(s) from "
                  f"{package_dir} triage board — using the robust check path.")
        else:
            emit(f"claim-safety: --package given but no compound names could be derived "
                  f"from {package_dir} (missing/empty triage board) — falling back to the "
                  f"bare-name heuristic. This path has a substantially higher false-positive "
                  f"rate; supply --compound-names explicitly if you have the real names.",
                  file=_sys.stderr)
    if compound_names is None and not package_dir:
        emit("claim-safety: no --package or --compound-names given — using the bare-name "
              "heuristic. This path has a substantially higher false-positive rate than the "
              "robust path; pass --package <dir> (preferred) or --compound-names a,b,c.",
              file=_sys.stderr)

    rows = lint_claim_safety_report(
        text,
        card_id=getattr(args, "card_id", ""),
        section=getattr(args, "section", ""),
        misanchor_flag=getattr(args, "misanchor_flag", ""),
        compound_names=compound_names,
    )

    if getattr(args, "report", None):
        write_claim_safety_csv(rows, args.report)

    if getattr(args, "json", False):
        emit(_json.dumps({"path": args.path, "clean": not rows, "findings": rows}, indent=2))
    else:
        if rows:
            emit(f"claim-safety: {len(rows)} finding(s) in {args.path}")
            for r in rows:
                emit(f"  [{r['severity']}] §{r.get('section','')} {r['violation_type']}: "
                      f"{r['sentence'][:80]}")
        else:
            emit(f"claim-safety: clean — {args.path}")

    mode = getattr(args, "mode", "warn")
    if mode == "fail" and rows:
        return 1
    return 0


def _domain_level_command(args) -> int:
    """CLI entrypoint for `domain-level`. Post-seal, non-blocking: always returns 0 unless the
    package itself is unreadable, so it can never fail a pipeline. Prints the receipt summary."""
    # v9.7.409 (AUDIT_cli_edgecases): validate the package exists BEFORE run_domain_level, which
    # otherwise mkdir()s its output dir first — crashing with a raw OSError when the (nonexistent)
    # package's parent is read-only, and silently creating a spurious empty dir when it is writable.
    if not Path(args.package).is_dir():
        emit(f"ERROR: not a package directory: {args.package}", file=_sys.stderr, flush=True)
        return 1
    from .domain_level import run_domain_level
    receipt = run_domain_level(
        args.package, source_antismash=getattr(args, "source_antismash", None),
        top_n=getattr(args, "top_n", 10), outdir=getattr(args, "outdir", None))
    status = receipt.get("status", "?")
    emit(f"  domain-level: {status} (mode={receipt.get('mode','?')})")
    if status == "OK":
        emit(f"    {receipt.get('n_domain_rows', 0)} domain rows across "
              f"{receipt.get('n_bgcs', 0)} BGCs → {receipt.get('files', [])}")
    else:
        emit(f"    {receipt.get('reason','')} — core package remains valid")
    if getattr(args, "emit_figures", False):
        try:
            from .domain_figures import render_domain_figures
            dl_dir = Path(getattr(args, "outdir", None) or (Path(args.package) / "domain_level"))
            fig_res = render_domain_figures(dl_dir)
            emit(f"    figures: {fig_res['status']} ({len(fig_res['figures'])} rendered)")
            if fig_res["warnings"]:
                emit(f"    figure warnings: {fig_res['warnings']}")
        except Exception as e:
            emit(f"    [WARN] figure rendering failed: {e} — tables remain valid")
    return 0


def _interactive_figures_command(args) -> int:
    """Lazy wrapper so importing cli.py never requires the figures subpackage."""
    from .interactive_figures.widget_data import interactive_figures_command
    return interactive_figures_command(args)


def _codex_heatmaps_command(args) -> int:
    """Lazy wrapper for the optional Codex Figure Factory heatmap profile."""
    from .interactive_figures.codex_heatmap_pack import build_codex_heatmap_pack
    # v9.7.409 (AUDIT_cli_edgecases): existence guard + typed refusal. A nonexistent CSV used to
    # crash with a raw FileNotFoundError, and an empty / column-less matrix CSV raised an uncaught
    # ValueError to the terminal. Refuse cleanly (one-line ERROR, rc 1) instead of a traceback.
    # --input is nargs="+", so validate every path in the list.
    _inputs = args.input if isinstance(args.input, (list, tuple)) else [args.input]
    _missing = [p for p in _inputs if not Path(p).is_file()]
    if _missing:
        emit(f"ERROR: codex-heatmaps input not found: {', '.join(str(p) for p in _missing)}",
             file=_sys.stderr, flush=True)
        return 1
    try:
        result = build_codex_heatmap_pack(
            args.input,
            args.outdir,
            title=getattr(args, "title", None),
            normalization=getattr(args, "normalization", "log1p"),
            top_rows=getattr(args, "top_rows", 40),
            rows_per_panel=getattr(args, "rows_per_panel", 30),
            columns_per_panel=getattr(args, "columns_per_panel", 24),
            annotate=getattr(args, "annotate", "auto"),
            citations=getattr(args, "citation", ()),
            claim_prefix=getattr(args, "claim_prefix", ""),
        )
    except ValueError as exc:
        emit(f"ERROR: codex-heatmaps could not read matrix CSV: {exc}",
             file=_sys.stderr, flush=True)
        return 1
    emit(json.dumps(result, indent=2))
    return 0 if result.get("status") == "PASS" else 1


def _codex_figure_catalog_command(args) -> int:
    """Lazy wrapper for the optional governed 200-set figure catalog."""
    from .interactive_figures.figure_set_registry import emit_registry
    result = emit_registry(
        args.outdir,
        family=getattr(args, "family", None),
        status=getattr(args, "status", None),
    )
    emit(json.dumps(result, indent=2))
    return 0 if result.get("status") == "PASS" else 1


def _codex_figure_sets_command(args) -> int:
    """Lazy wrapper for implemented Codex Figure Factory registry tranches."""
    from .interactive_figures.figure_set_renderer import render_tranche
    tranche = getattr(args, "tranche", "1")
    if tranche == "1":
        result = render_tranche(args.widget_data, args.outdir)
    else:
        source_bundle = getattr(args, "source_bundle", None)
        if not source_bundle:
            raise ValueError("--source-bundle is required for --tranche 2-6 or all")
        from .interactive_figures.figure_set_renderer_tranche2 import render_tranche_2
        if tranche == "2":
            result = render_tranche_2(args.widget_data, source_bundle, args.outdir)
        elif tranche == "3":
            from .interactive_figures.figure_set_renderer_tranche3 import render_tranche_3
            result = render_tranche_3(args.widget_data, source_bundle, args.outdir)
        elif tranche == "4":
            from .interactive_figures.figure_set_renderer_tranche4 import render_tranche_4
            result = render_tranche_4(args.widget_data, source_bundle, args.outdir)
        elif tranche == "5":
            from .interactive_figures.figure_set_renderer_tranche5 import render_tranche_5
            result = render_tranche_5(args.widget_data, source_bundle, args.outdir)
        elif tranche == "6":
            lead_ledger = getattr(args, "lead_ledger", None)
            if not lead_ledger:
                raise ValueError("--lead-ledger is required for --tranche 6")
            from .interactive_figures.figure_set_renderer_tranche6 import render_tranche_6
            result = render_tranche_6(args.widget_data, source_bundle, lead_ledger, args.outdir)
        else:
            from .interactive_figures.figure_atlas import render_implemented_atlas
            result = render_implemented_atlas(args.widget_data, source_bundle, args.outdir, lead_ledger=getattr(args, "lead_ledger", None))
    emit(json.dumps({
        "status": result.get("status"),
        "implemented_count": result.get("implemented_count"),
        "implemented_ids": result.get("implemented_ids"),
        "outdir": args.outdir,
    }, indent=2))
    return 0 if result.get("status") == "PASS" else 1



def _codex_bigscape_figure_sets_command(args) -> int:
    """Lazy wrapper for the optional BiG-SCAPE Figure Factory extension."""
    from .interactive_figures.bigscape_extension import render_bigscape_extension
    result = render_bigscape_extension(
        args.outdir,
        bigscape_tsv=args.bigscape_tsv,
        bigscape_db=args.bigscape_db,
        bigscape_run=args.bigscape_run,
        bigscape_cutoffs=args.bigscape_cutoffs,
        run_manifest=args.run_manifest,
        bgc_bridge=args.bgc_bridge,
        lead_ledger=args.lead_ledger,
    )
    emit(json.dumps({
        "status": result.get("status"),
        "extension_ids": result.get("extension_ids"),
        "run_id": result.get("run_id"),
        "cutoffs": result.get("cutoffs"),
        "outdir": args.outdir,
    }, indent=2))
    return 0 if result.get("status") == "PASS" else 1


def _codex_figure_sources_command(args) -> int:
    """Lazy wrapper for the sealed-package figure source bundler."""
    from .interactive_figures.figure_source_bundle import build_source_bundle
    result = build_source_bundle(args.widget_data, args.package_dir, args.outdir)
    emit(json.dumps({
        "status": result.get("status"),
        "strain_count": result.get("strain_count"),
        "present_package_count": result.get("present_package_count"),
        "missing_member_count": result.get("missing_member_count"),
        "outputs": result.get("outputs"),
        "outdir": args.outdir,
    }, indent=2))
    return 0 if result.get("status") in {"PASS", "PASS_WITH_ISSUES"} else 1


_PACKAGE_POSITIONAL = "package_positional"


def _install_package_positional_alias(parser) -> dict[str, bool]:
    """v9.7.405 (WAC-01375 items 12/13/15: argument-convention convergence, compatibility-preserving).

    Every subcommand that takes `--package` also accepts the package directory as a bare
    positional (`python mamey_run.py validate <pkg>`), so both spellings work during the migration
    window. Nothing is removed: `--package` keeps working and stays the canonical spelling in every
    error message. Subcommands that already declare positionals are left untouched (no ambiguity is
    introduced). Returns {command: package_was_required} for the post-parse check.
    """
    import argparse as _ap
    required: dict[str, bool] = {}
    for action in parser._actions:
        if not isinstance(action, _ap._SubParsersAction):
            continue
        for name, sub in action.choices.items():
            pkg = next((a for a in sub._actions if "--package" in getattr(a, "option_strings", ())), None)
            if pkg is None or any(not a.option_strings and a.dest != "help" for a in sub._actions):
                continue
            required[name] = bool(pkg.required)
            pkg.required = False
            # BC2-408: if --package lives inside a REQUIRED mutually-exclusive group (e.g.
            # bigscape's --package/--runs-dir/--input-gbk-dir, blastp-availability's
            # --runs-dir/--package), a bare top-level positional added via sub.add_argument()
            # is NOT a member of that group, so argparse's own "one of these is required" check
            # never recognizes it as satisfying the requirement. Verified live: `mamey bigscape
            # <path>` and `mamey blastp-availability <path>` both refused with "one of the
            # arguments ... is required" even though a package path WAS given positionally --
            # the v9.7.405 positional-alias convergence silently never worked for these two
            # commands. Add the positional as a member of that SAME mutually-exclusive group
            # instead of the bare parser, so it participates in both the required-ness and
            # mutual-exclusivity checks the same way --package itself does (argparse supports a
            # nargs='?' positional as a group member; verified this satisfies both checks
            # correctly before landing this fix).
            _grp = next((g for g in getattr(sub, "_mutually_exclusive_groups", ())
                        if pkg in g._group_actions), None)
            (_grp if _grp is not None else sub).add_argument(
                _PACKAGE_POSITIONAL, nargs="?", default=None, metavar="PACKAGE",
                help="positional alias for --package (v9.7.405 convergence)")
    return required


def main(argv=None) -> int:
    import sys
    parser = build_parser()
    _pkg_required = _install_package_positional_alias(parser)
    args = parser.parse_args(argv)
    if hasattr(args, _PACKAGE_POSITIONAL):
        _pos = getattr(args, _PACKAGE_POSITIONAL)
        if getattr(args, "package", None) is None and _pos is not None:
            args.package = _pos
        elif _pos is not None and args.package is not None and _pos != args.package:
            parser.error(f"{args.command}: both a positional package ({_pos}) and --package ({args.package}) were "
                         f"given — canonical invocation: python mamey_run.py {args.command} --package <package_dir>")
        if getattr(args, "package", None) is None and _pkg_required.get(getattr(args, "command", ""), False):
            parser.error(f"{args.command}: a sealed package directory is required — canonical invocation: "
                         f"python mamey_run.py {args.command} --package <package_dir>")
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    # Validate mutually exclusive arguments
    if hasattr(args, "strains") and hasattr(args, "input_zip"):
        input_error = None
        if args.strains and args.input_zip:
            input_error = "Error: use either --strains (batch) or --input-zip (single), not both."
        elif getattr(args, "accession", None) and not args.input_zip:
            emit(json.dumps({
                "status": "UNSUPPORTED_ACCESSION_MODE",
                "accession": args.accession,
                "message": "This release does not fetch NCBI accessions or run antiSMASH preprocessing. Provide an antiSMASH ZIP via --input-zip."
            }, indent=2))
            return 1
        elif not args.strains and not args.input_zip and args.command == "run":
            input_error = "Error: provide --input-zip (single strain) or --strains (batch)."
        if input_error:
            emit(input_error)
            return 1
    # v9.7.409 (post_seal_checksums; audit N1/N2/N9): a sanctioned command that AUTHORS covered
    # post-seal deliverables (mode_b/, blastp_online/, domain_level/, guide/, figures*/, root
    # figures) must refresh post_seal_checksums.txt so its legitimate output is folded into the
    # integrity manifest — otherwise a later `validate` would flag those files as injected. This
    # allowlist is AUTHORING commands only; read-only commands (explain, list-bgcs, validate,
    # seal-package, blastp-status, …) are excluded so the package is never mutated on a pure read
    # (preserves the seal-package/validate read-only contract). refresh_post_seal_checksums is a
    # no-op unless the core is already sealed, so it never fires mid-run.
    _POST_SEAL_AUTHORING_COMMANDS = frozenset({
        "render-figures", "render-all-figures", "mode-b", "guide", "domain-level",
        "ingest-blastp", "ingest-blastp-trove", "blastp-online", "blastp-ebi", "blastp-round",
    })
    from .blastp_gate import BlastpDiscoveryError
    try:
        if getattr(args, "command", None) in _POST_SEAL_AUTHORING_COMMANDS and getattr(args, "package", None):
            _rc = args.func(args)
            try:
                from .packaging import refresh_post_seal_checksums
                # An external guide is a reader output: no package bytes were
                # authored, so its original integrity files must remain intact.
                # Resolve symlinks before deciding whether output is internal.
                _refresh_package = True
                if args.command == "guide" and getattr(args, "outdir", None):
                    _guide_root = Path(args.outdir).expanduser().resolve()
                    _package_root = Path(args.package).expanduser().resolve()
                    _refresh_package = _guide_root == _package_root or _package_root in _guide_root.parents
                if _refresh_package:
                    refresh_post_seal_checksums(args.package)
            except Exception as _swallowed_exc:
                _warnings.warn(f"cli.py: non-blocking step skipped ({type(_swallowed_exc).__name__}: {_swallowed_exc})", RuntimeWarning, stacklevel=2)  # v9.7.409: was a silent swallow
            return _rc
        return args.func(args)
    except BlastpDiscoveryError as exc:
        emit(f"{exc}. Set MAMEY_BLASTP_SCAN_ROOT to the intended evidence project "
             "and resolve access problems before retrying.", file=sys.stderr)
        return 3



if __name__ == "__main__":
    raise SystemExit(main())
