"""judgment_store.py — Persistent judgment register for Sapote Mode B output.

The judgment store is the write path that was missing: Sapote's LLM output was
produced in-session but never written to disk, so render_brief and the PDF
compilation layer had no data to read. This module provides the structured
accumulation layer.

ARCHITECTURE
    <package_dir>/<strain>_judgment_register.json
        Top-level registry: per-BGC judgment status, session provenance, timestamps.

    <package_dir>/judgment/<strain>_<BGC_ID>_mode_b.md
        Per-BGC Mode B markdown (§1–§8). Written by Sapote after each BGC completes.
        Filename follows §15.3 convention adapted for MD (the PDF compilation step
        renders these to PDF).

    <package_dir>/judgment/<strain>_laypersons_section.md
        Accumulated layperson paragraphs (one per completed BGC).
        Sapote appends after each Mode B; render_brief reads for PDF-003.

    <package_dir>/judgment/<strain>_fermentation_section.md
        Accumulated fermentation notes (§7 from each Mode B).
        Sapote appends after each BGC; render_brief reads for PDF-004.

USAGE BY SAPOTE (judgment layer)
    After completing Mode B for BGC001:

        from mamey.judgment_store import record_mode_b
        record_mode_b(
            package_dir="/path/to/AS-XXX/package",
            bgc_id="BGC001",
            mode_b_md="# §1 Overview\\n...full §1-§8 markdown...",
            layperson_paragraph="BGC001 encodes biosynthetic capacity...",
            fermentation_note="Grow at 28°C in ISP2...",
            session_id="batch_1",
        )

    This writes the §15.3 file, updates the register, and appends to
    laypersons_section.md and fermentation_section.md.

USAGE BY MAMEY CLI
    After a Mamey run, the register is initialised with all BGC IDs from the
    inventory so Sapote knows which BGCs need judgment:

        from mamey.judgment_store import init_register
        init_register(package_dir, strain_id, bgc_ids)

    render_brief reads the register to populate the PDF-003/004 sections:

        from mamey.judgment_store import read_register, read_laypersons, read_fermentation
        reg = read_register(package_dir)
        if reg["completion_pct"] >= 100:
            # all BGCs have Mode B — bind into full compilation PDF
        lay_text = read_laypersons(package_dir)   # for PDF-003
        ferm_text = read_fermentation(package_dir) # for PDF-004
"""
from __future__ import annotations
from contextlib import suppress as _suppress

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any


# Judgment-register status family contract.  Recovery states deliberately use
# the ``CORRUPT_<detail>`` namespace; callers must never compare only the bare
# token and accidentally admit a more specific corrupt state.
def is_corrupt_judgment_status(status: Any) -> bool:
    """Return True only for the governed ``CORRUPT`` status family."""
    token = str(status or "").strip()
    return token == "CORRUPT" or token.startswith("CORRUPT_")


def judgment_status_blocks_ingest(status: Any) -> bool:
    """Return whether a register status makes judgment ingest unsafe."""
    token = str(status or "").strip()
    return token == "NOT_INITIALISED" or is_corrupt_judgment_status(token)


# ── File naming ─────────────────────────────────────────────────────────────

def _register_path(package_dir: str | Path) -> Path:
    pkg = Path(package_dir)
    strain = _strain_from_pkg(pkg)
    return pkg / f"{strain}_judgment_register.json"


def _last_good_path(package_dir: str | Path) -> Path:
    """Sidecar snapshot of the last successfully-written, trustworthy register.

    Written after every normal (non-corrupt-recovery) `_recalculate_and_write`.
    `read_register()` falls back to this on a JSON decode failure so a corrupted
    register file recovers real history instead of collapsing to an empty one.
    """
    return Path(str(_register_path(package_dir)) + ".last-good")


def _judgment_dir_read(package_dir: str | Path) -> Path:
    """Return the judgment-section directory path WITHOUT side effects.

    Use this in any context that only reads or computes a path. Pairs with
    `_judgment_dir_write()` which mkdir's. The split (v9.7.149c, F2 from
    Opus audit) prevents read-path callers — e.g. compile-report's existence
    probe — from silently creating an empty `judgment/` directory and
    muddying the 'is this package untouched?' check.
    """
    return Path(package_dir) / "judgment"


def _judgment_dir_write(package_dir: str | Path) -> Path:
    """Return the judgment-section directory path, creating it if missing.

    Use this immediately before a write. Idempotent.
    """
    d = Path(package_dir) / "judgment"
    d.mkdir(exist_ok=True)
    return d


def _judgment_dir(package_dir: str | Path) -> Path:
    """Back-compat alias. Behaves like the historical mkdir-on-call form so
    any external caller that imported `_judgment_dir` directly is unaffected.
    Internal call sites have been routed to the explicit read/write variants.
    """
    return _judgment_dir_write(package_dir)


def _triage_row_for(
    package_dir: str | Path,
    bgc_id: str,
    load_errors: list[dict[str, str]] | None = None,
) -> dict:
    """Read the BGC's row from the package triage board, or {} if unavailable.

    Used by the card-write locator reconciliation (v9.7.124). Non-fatal: returns {} if
    the triage board is absent or the BGC is not in it, so the caller degrades gracefully.
    """
    import csv as _csv
    pkg = Path(package_dir)
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    if not candidates:
        return {}
    try:
        with open(candidates[0], newline="", encoding="utf-8") as _f:
            for row in _csv.DictReader(_f):
                if (row.get("BGC_ID") or "").strip() == bgc_id:
                    return dict(row)
    except (OSError, UnicodeDecodeError, _csv.Error) as exc:
        if load_errors is not None:
            load_errors.append({
                "stage": "read_triage_row",
                "error_type": type(exc).__name__,
                "message": str(exc),
            })
        return {}
    return {}


def _strain_compound_names(
    package_dir: str | Path,
    load_errors: list[dict[str, str]] | None = None,
) -> set:
    """Collect the strain's KCB/MIBiG compound names from the triage board (v9.7.125b).

    KCB columns hold values like "BGC0001944.2 | funisamine | knownclusterblast #1"; the
    compound name is the middle pipe-field. This set is passed to the claim-safety linter so
    "is <compound>" only flags real compound identities, not descriptive prose. Returns {} if
    no board / no KCB data, in which case the linter uses its heuristic fallback.
    """
    import csv as _csv
    pkg = Path(package_dir)
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    if not candidates:
        return set()
    names: set = set()
    try:
        with open(candidates[0], newline="", encoding="utf-8") as _f:
            for row in _csv.DictReader(_f):
                for col in ("KCB_top", "KCB_clusterblast"):
                    val = (row.get(col) or "").strip()
                    if "|" in val:
                        parts = [p.strip() for p in val.split("|")]
                        if len(parts) >= 2 and parts[1]:
                            # split combined names ("gobichelin A/gobichelin B") into tokens
                            for nm in re.split(r"[/,]", parts[1]):
                                nm = nm.strip().lower()
                                if len(nm) >= 4 and re.match(r"^[a-z][a-z0-9'\- ]+$", nm):
                                    names.add(nm)
                                    # also add the bare leading token, so "is gobichelin" matches
                                    # a card whose KCB anchor is "gobichelin A" (runner concern #1)
                                    lead = nm.split()[0]
                                    if len(lead) >= 4:
                                        names.add(lead)
    except (OSError, UnicodeDecodeError, _csv.Error) as exc:
        if load_errors is not None:
            load_errors.append({
                "stage": "read_triage_compound_names",
                "error_type": type(exc).__name__,
                "message": str(exc),
            })
        return set()
    return names


def _mode_b_path(package_dir: str | Path, bgc_id: str) -> Path:
    strain = _strain_from_pkg(Path(package_dir))
    return _judgment_dir_read(package_dir) / f"{strain}_{bgc_id}_mode_b.md"


def _laypersons_path(package_dir: str | Path) -> Path:
    strain = _strain_from_pkg(Path(package_dir))
    return _judgment_dir_read(package_dir) / f"{strain}_laypersons_section.md"


def _fermentation_path(package_dir: str | Path) -> Path:
    strain = _strain_from_pkg(Path(package_dir))
    return _judgment_dir_read(package_dir) / f"{strain}_fermentation_section.md"


def _strain_from_pkg(pkg: Path) -> str:
    """Infer strain ID from manifest.json, fall back to directory name.

    The production layout (cli.py::run_one_strain) is <outdir>/<strain_id>/package/
    -- package_dir is always literally named "package". When manifest.json is
    missing/unreadable at call time (e.g. init_register runs before the manifest
    write, or a copied/relocated package has lost it), falling back to pkg.name
    yields the literal string "package" instead of the real strain ID, which
    session_resume.py's own fallback (pkg.parent.name) never produces -- the two
    modules then compute different filenames for the same register and silently
    stop seeing each other's writes. Mirror session_resume.py's convention for
    this exact directory shape; keep the historical pkg.name fallback for the
    generic/test case where package_dir is not named "package".
    """
    manifest = pkg / "manifest.json"
    if manifest.exists():
        try:
            return json.loads(manifest.read_text(encoding="utf-8")).get("strain_id", pkg.name)
        except Exception:
            pass
    if pkg.name == "package" and pkg.parent.name:
        return pkg.parent.name
    return pkg.name


# ── Register initialisation ──────────────────────────────────────────────────

def init_register(
    package_dir: str | Path,
    strain_id: str,
    bgc_ids: list[str],
    n_bgcs_total: int | None = None,
) -> dict[str, Any]:
    """Initialise (or re-initialise) the judgment register for a package.

    Called by Mamey CLI after extraction. Idempotent: if a register exists and
    already has Mode B entries, they are preserved — only missing BGC slots are
    added. This means re-running Mamey on the same package does NOT wipe partial
    Sapote progress.

    Returns the register dict.
    """
    reg_path = _register_path(package_dir)
    existing: dict[str, Any] = {}
    if reg_path.exists():
        # Reuse the corruption-aware loader.  Parsing independently here used
        # to collapse an unreadable register to {}, bypass its last-good
        # snapshot, and then overwrite recoverable completion history with a
        # newly-PENDING register.
        existing = read_register(package_dir)
        if is_corrupt_judgment_status(existing.get("judgment_status")):
            raise ValueError(
                f"Existing judgment register is unreadable: {reg_path}; "
                "initialisation refused to overwrite recoverable history"
            )

    existing_bgcs: dict[str, Any] = existing.get("bgcs", {})

    # Add any new BGC IDs not already in the register
    for bgc_id in bgc_ids:
        if bgc_id not in existing_bgcs:
            existing_bgcs[bgc_id] = {
                "status": "PENDING",
                "mode_b_file": None,
                "session_id": None,
                "timestamp": None,
            }

    total = n_bgcs_total or len(bgc_ids)
    done = sum(1 for v in existing_bgcs.values() if v["status"] == "COMPLETE")

    reg: dict[str, Any] = {
        "schema_version": "1.0",
        "strain_id": strain_id,
        "total_bgcs": total,
        "complete_bgcs": done,
        "completion_pct": round(100.0 * done / total, 1) if total else 0.0,
        "judgment_status": "COMPLETE" if done == total and total > 0 else "IN_PROGRESS" if done > 0 else "PENDING",
        "mamey_init_timestamp": existing.get("mamey_init_timestamp") or _now(),
        "last_sapote_session": existing.get("last_sapote_session"),
        "bgcs": existing_bgcs,
    }

    _atomic_write_text(reg_path, json.dumps(reg, indent=2))
    return reg


# ── Sapote write path ─────────────────────────────────────────────────────────

def record_mode_b(
    package_dir: str | Path,
    bgc_id: str,
    mode_b_md: str,
    layperson_paragraph: str = "",
    fermentation_note: str = "",
    session_id: str = "sapote",
    rank: int | None = None,
    edge_status: str | None = None,
    cds_count: int | None = None,
) -> dict:
    """Record completed Mode B for one BGC. Called by Sapote (judgment layer).

    Writes:
      - <strain>_<BGC_ID>_mode_b.md          (§15.3 per-BGC report)
      - Appends to <strain>_laypersons_section.md   (PDF-003 source)
      - Appends to <strain>_fermentation_section.md (PDF-004 source)
      - Updates the judgment register (now with the quality verdict stamped in)

    The card is evaluated by the Mode B quality gate at write time (v9.7.112). The verdict
    (FULL / SHALLOW / STUB + which §-sections are present) is stamped into the register and
    returned, so the judgment-layer session sees immediately whether the card is genuinely
    complete (§1–§10) or stopped short. This does NOT block the write — it records the gap so
    a partial card cannot silently pass as done. `rank` (triage-board rank) sets the priority
    floor; omit it and the most lenient (LOW) floor applies.

    Returns a dict: {"path": <mode_b file path>, "verdict": <ModeB_QualityVerdict-as-dict>}.
    """
    pkg = Path(package_dir)
    strain = _strain_from_pkg(pkg)

    # Quality verdict at write time (v9.7.112) — passive: records, never blocks.
    try:
        from .mode_b_quality_gate import evaluate_card
        _v = evaluate_card(bgc_id, mode_b_md, rank=rank,
                           edge_status=edge_status, cds_count=cds_count)
        verdict = {
            "tier": _v.tier,
            "priority": _v.priority,
            "char_count": _v.char_count,
            "gene_mentions": _v.gene_mentions,
            "section_count": _v.section_count,
            "message": _v.message,
        }
    except Exception as _qg_err:
        verdict = {"tier": "UNKNOWN", "message": f"gate error: {_qg_err}"}

    # Enrichment augmentation (v9.7.125, the BGC028/BGC023 finding) — advisory, never auto-rewrites.
    # If a card comes back below FULL on the §11–§20 floor, offer deterministic generator content
    # (rarest-domain/gene/inventory census from the package gene table) the author can append to
    # clear the floor honestly. Stamped into the verdict; the card is written as-authored regardless.
    if verdict.get("tier") in ("SHALLOW", "STUB"):
        try:
            from .enrichment_sections import augment_enrichment
            _aug = augment_enrichment(package_dir, bgc_id, products="", floor=2000)
            if _aug:
                verdict["enrichment_augmentation"] = {
                    "available": True,
                    "chars": len(_aug),
                    "text": _aug,
                    "note": "deterministic §11–§20 census from the gene table; append to clear the floor",
                }
        except Exception as _aug_err:
            verdict["enrichment_augmentation"] = {"available": False, "error": str(_aug_err)}

    # Claim-safety lint at write time (v9.7.123 SM-P1-004 / STEP 5) — passive: records, never blocks.
    # Mirrors the quality gate above: surfaces identity-overclaim / unanchored-KCB findings into the
    # verdict so the judgment-layer session sees them immediately, without blocking the card write.
    try:
        import sys as _sys
        from pathlib import Path as _P
        _tools = str(_P(__file__).resolve().parents[1] / "tools")
        if _tools not in _sys.path:
            _sys.path.insert(0, _tools)
        from claim_safety_linter import lint_claim_safety
        _compound_load_errors: list[dict[str, str]] = []
        _cnames = _strain_compound_names(package_dir, _compound_load_errors)
        if _compound_load_errors:
            _load_error = _compound_load_errors[0]
            verdict["claim_safety"] = {
                "clean": None,
                "error": ("triage board unreadable while loading compound names "
                          f"({_load_error['error_type']}: {_load_error['message']})"),
                "load_errors": _compound_load_errors,
            }
        else:
            _cs_findings = lint_claim_safety(mode_b_md, compound_names=_cnames or None)
            verdict["claim_safety"] = {
                "clean": not _cs_findings,
                "findings": _cs_findings,
            }
    except Exception as _cs_err:
        verdict["claim_safety"] = {"clean": None, "error": f"linter error: {_cs_err}"}

    # Locator reconciliation at write time (v9.7.124 SM-P0-003 / STEP 5) — passive: records, never blocks.
    # Checks the card's header locator (node/region) against the BGC's canonical triage row. Surfaces
    # node mismatches / unparseable headers into the verdict so a drifted locator is caught at write time.
    try:
        import sys as _sys2
        from pathlib import Path as _P2
        _tools2 = str(_P2(__file__).resolve().parents[1] / "tools")
        if _tools2 not in _sys2.path:
            _sys2.path.insert(0, _tools2)
        from locator_reconciliation import reconcile_heading_only
        _triage_load_errors: list[dict[str, str]] = []
        _trow = _triage_row_for(package_dir, bgc_id, _triage_load_errors)
        if _triage_load_errors:
            _load_error = _triage_load_errors[0]
            verdict["locator"] = {
                "status": "ERROR",
                "error": ("triage board unreadable while loading locator row "
                          f"({_load_error['error_type']}: {_load_error['message']})"),
                "load_errors": _triage_load_errors,
            }
        elif _trow:
            # Exact-locus identity may not infer strain from a directory or display locator.
            # Bind the manifest's declared strain_id into the triage row; when the manifest
            # field is unavailable, leave it empty so the reconciler refuses the incomplete
            # expected identity.
            try:
                _manifest_identity = json.loads(
                    (pkg / "manifest.json").read_text(encoding="utf-8")
                )
                _identity_strain = str(_manifest_identity.get("strain_id") or "").strip()
            except Exception:
                _identity_strain = ""
            _trow = dict(_trow)
            _trow["Strain"] = _identity_strain
            _loc = reconcile_heading_only(mode_b_md, _trow)
            verdict["locator"] = {
                "status": _loc["status"],
                "errors": _loc.get("errors", []),
                "refusal_reason": _loc.get("refusal_reason", ""),
                "identity_display": _loc.get("identity_display", ""),
                "secondary_fields": _loc.get("secondary_fields", {}),
            }
        else:
            verdict["locator"] = {"status": "NO_TRIAGE_ROW", "errors": []}
    except Exception as _loc_err:
        verdict["locator"] = {"status": "ERROR", "error": f"locator error: {_loc_err}"}

    # Write per-BGC Mode B file
    mb_path = _mode_b_path(package_dir, bgc_id)
    header = (
        f"<!-- MODE B: {bgc_id} | strain: {strain} | "
        f"session: {session_id} | {_now()} -->\n\n"
    )
    _atomic_write_text(mb_path, header + mode_b_md.strip() + "\n")

    # Append layperson paragraph
    if layperson_paragraph.strip():
        lay_path = _laypersons_path(package_dir)
        _append_section(lay_path, f"## {bgc_id}\n\n{layperson_paragraph.strip()}\n")

    # Append fermentation note
    if fermentation_note.strip():
        ferm_path = _fermentation_path(package_dir)
        _append_section(ferm_path, f"## {bgc_id}\n\n{fermentation_note.strip()}\n")

    # Update register (with verdict)
    persistence_warnings = _update_register(
        package_dir, bgc_id, session_id, str(mb_path), verdict
    )

    return {
        "path": mb_path,
        "verdict": verdict,
        "persistence_warnings": persistence_warnings,
    }


def record_batch_complete(
    package_dir: str | Path,
    session_id: str,
    bgc_ids_complete: list[str],
) -> dict[str, Any]:
    """Mark a batch as complete in the register without requiring per-BGC content.

    Used when Sapote writes batch-level summaries rather than per-BGC files.
    Returns the updated register.
    """
    reg = read_register(package_dir)
    for bgc_id in bgc_ids_complete:
        if bgc_id in reg["bgcs"] and reg["bgcs"][bgc_id]["status"] != "COMPLETE":
            reg["bgcs"][bgc_id]["status"] = "COMPLETE"
            reg["bgcs"][bgc_id]["session_id"] = session_id
            reg["bgcs"][bgc_id]["timestamp"] = _now()
    persistence_warnings = _recalculate_and_write(package_dir, reg)
    if persistence_warnings:
        reg["persistence_warnings"] = persistence_warnings
    return reg


# ── Read paths (for render_brief and PDF compilation) ────────────────────────

def read_register(package_dir: str | Path) -> dict[str, Any]:
    """Return the judgment register dict. Returns a stub if not initialised.

    Invalid primary/last-good data is represented as a typed ``CORRUPT``
    result with ``load_errors``; optional absence remains ``NOT_INITIALISED``.
    """
    reg_path = _register_path(package_dir)
    if not reg_path.exists():
        return {
            "strain_id": _strain_from_pkg(Path(package_dir)),
            "total_bgcs": 0, "complete_bgcs": 0, "completion_pct": 0.0,
            "judgment_status": "NOT_INITIALISED", "bgcs": {},
        }
    try:
        loaded = json.loads(reg_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("register root must be a JSON object")
        return loaded
    except (OSError, UnicodeDecodeError, json.JSONDecodeError,
            RecursionError, ValueError) as primary_exc:
        # Preserve the unreadable file before any caller's next write can silently
        # replace it. A CORRUPT read used to feed straight into _update_register /
        # _recalculate_and_write with an empty "bgcs": {}, so the very next
        # record_mode_b()/record_batch_complete() call after real-world corruption
        # (disk fault, external truncation, bad manual edit) permanently overwrote
        # the register with just the one BGC being recorded -- silently discarding
        # every previously-COMPLETE BGC's tracked status (the .md cards themselves
        # were untouched, but nothing could find them "COMPLETE" any more).
        # Best-effort, never raises -- this must not turn a tolerant read into a
        # new failure mode.
        load_errors = [{
            "stage": "load_primary_register",
            "error_type": type(primary_exc).__name__,
            "message": str(primary_exc),
        }]
        try:
            backup = reg_path.with_suffix(reg_path.suffix + f".corrupt-{_now().replace(':', '')}")
            if not backup.exists():
                backup.write_bytes(reg_path.read_bytes())
        except OSError as backup_exc:
            load_errors.append({
                "stage": "preserve_corrupt_register",
                "error_type": type(backup_exc).__name__,
                "message": str(backup_exc),
            })
        # v9.7.378b (audit lane wave 18): the backup above preserves the corrupt
        # bytes for forensics but by itself does NOT stop the next write from
        # collapsing total_bgcs/bgcs to whatever is touched next -- see
        # _recalculate_and_write's "recovering_from_unreadable_register" guard.
        # Recover from the last-known-good snapshot (written after every prior
        # trustworthy save) before giving up, so real judgment history recorded
        # before the corruption is not silently discarded.
        last_good = _last_good_path(package_dir)
        if last_good.exists():
            try:
                recovered = json.loads(last_good.read_text(encoding="utf-8"))
                if not isinstance(recovered, dict):
                    raise ValueError("last-good register root must be a JSON object")
                recovered = dict(recovered)
                recovered["register_recovery"] = {
                    "status": "RECOVERED_FROM_LAST_GOOD",
                    "load_errors": load_errors,
                }
                return recovered
            except (OSError, UnicodeDecodeError, json.JSONDecodeError,
                    RecursionError, ValueError) as last_good_exc:
                load_errors.append({
                    "stage": "load_last_good",
                    "error_type": type(last_good_exc).__name__,
                    "message": str(last_good_exc),
                })
        return {"judgment_status": "CORRUPT", "bgcs": {},
                "load_errors": load_errors}


def read_laypersons(package_dir: str | Path) -> str:
    """Return accumulated layperson paragraphs (empty string if none written)."""
    p = _laypersons_path(package_dir)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def read_fermentation(package_dir: str | Path) -> str:
    """Return accumulated fermentation notes (empty string if none written)."""
    p = _fermentation_path(package_dir)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def read_mode_b(package_dir: str | Path, bgc_id: str) -> str:
    """Return Mode B markdown for a specific BGC, or empty string."""
    p = _mode_b_path(package_dir, bgc_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def list_complete_bgcs(package_dir: str | Path) -> list[str]:
    """Return sorted list of BGC IDs that have COMPLETE Mode B."""
    reg = read_register(package_dir)
    return sorted(
        bgc_id for bgc_id, v in reg.get("bgcs", {}).items()
        if v.get("status") == "COMPLETE"
    )


def pending_bgcs(package_dir: str | Path) -> list[str]:
    """Return BGC IDs still awaiting Mode B judgment."""
    reg = read_register(package_dir)
    return sorted(
        bgc_id for bgc_id, v in reg.get("bgcs", {}).items()
        if v.get("status") != "COMPLETE"
    )


def is_judgment_complete(package_dir: str | Path) -> bool:
    """True when all BGCs in the register have COMPLETE Mode B."""
    reg = read_register(package_dir)
    return (
        reg.get("judgment_status") == "COMPLETE"
        and reg.get("total_bgcs", 0) > 0
        and reg.get("complete_bgcs", 0) >= reg.get("total_bgcs", 0)
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text to *path* crash-safely: write to a sibling .tmp, then
    os.replace() into place (atomic on POSIX).  Mirrors the .tmp+replace
    pattern in tools/_wbio.atomic_save and tools/ingest_package.atomic_dump.

    Ensures the parent directory exists (F2, v9.7.149c): path helpers no
    longer mkdir on read, so the writer takes responsibility.

    v9.7.409 (CLAUDE_409 C4): UNIQUE mkstemp temp (was fixed ``str(path)+'.tmp'``). Two concurrent
    authoring writers to one register (``mode-b BGC1`` + ``mode-b BGC2``, ``ingest-receipts``
    batches) previously collided on the one fixed temp and the loser crashed in os.replace with
    FileNotFoundError. A private mkstemp temp per writer keeps the rename atomic without collision.
    (This removes the crash/collision only; the register read-modify-write lost-update still needs a
    lock, tracked separately — see DEEP_AUDIT2 C4.)
    """
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, _tmpname = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    tmp = Path(_tmpname)
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        with _suppress(OSError):  # v9.7.409: best-effort cleanup, intent explicit (was except: pass)
            if tmp.exists():
                tmp.unlink()
        raise


def _append_section(path: Path, text: str) -> None:
    # Parent-dir creation here (F2, v9.7.149c) — see _atomic_write_text note.
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if path.exists() else "w"
    with open(path, mode, encoding="utf-8") as f:
        f.write("\n" + text + "\n")


def _update_register(
    package_dir: str | Path, bgc_id: str, session_id: str, mode_b_file: str,
    verdict: dict | None = None,
) -> list[dict[str, str]]:
    reg = read_register(package_dir)
    if bgc_id not in reg.get("bgcs", {}):
        reg.setdefault("bgcs", {})[bgc_id] = {}
    row = {
        "status": "COMPLETE",
        "mode_b_file": os.path.basename(mode_b_file),
        "session_id": session_id,
        "timestamp": _now(),
    }
    if verdict is not None:
        # v9.7.112: stamp the quality verdict so a SHALLOW/STUB or §9/§10-missing card is
        # visible in the register, not silently equal to a FULL one.
        row["quality_tier"] = verdict.get("tier", "UNKNOWN")
        row["quality_message"] = verdict.get("message", "")
        row["char_count"] = verdict.get("char_count")
        row["section_count"] = verdict.get("section_count")
    reg["bgcs"][bgc_id].update(row)
    reg["last_sapote_session"] = session_id
    return _recalculate_and_write(package_dir, reg)


def incomplete_cards(package_dir: str | Path) -> list[dict[str, Any]]:
    """Return register rows for every recorded BGC whose card is not FULL (v9.7.112).

    A card is incomplete if its stamped quality_tier is anything other than 'FULL'
    (SHALLOW / STUB / UNKNOWN) — i.e. it is short, missing §9/§10, or was recorded before
    verdict-stamping existed. Used by the batch-run compile gate to refuse a partial strain.
    """
    reg = read_register(package_dir)
    out: list[dict[str, Any]] = []
    for bgc_id, row in (reg.get("bgcs", {}) or {}).items():
        if row.get("status") != "COMPLETE":
            continue
        if row.get("quality_tier", "UNKNOWN") != "FULL":
            out.append({
                "bgc_id": bgc_id,
                "quality_tier": row.get("quality_tier", "UNKNOWN"),
                "quality_message": row.get("quality_message", ""),
                "char_count": row.get("char_count"),
                "section_count": row.get("section_count"),
            })
    return out


def batch_status(package_dir: str | Path, ranked_bgc_ids: list[str] | None = None) -> dict[str, Any]:
    """Rank-ordered progress for a batched Mode B run (v9.7.112).

    Returns counts and a rank-ordered per-BGC status list so a resumed (CDSW) session sees exactly
    where it stopped. When `ranked_bgc_ids` (triage-rank order, rank 1 first) is supplied, the
    per-BGC list follows that order — the run analyzes top-ranked BGCs first so a token-limited
    session completes the highest-value cards before stopping.
    """
    reg = read_register(package_dir)
    bgcs = reg.get("bgcs", {}) or {}
    order = ranked_bgc_ids if ranked_bgc_ids is not None else list(bgcs.keys())
    # include any recorded BGCs not in the supplied order, appended at the end
    for bid in bgcs:
        if bid not in order:
            order.append(bid)

    per_bgc, n_full, n_shallow, n_stub, n_not_started = [], 0, 0, 0, 0
    for bid in order:
        row = bgcs.get(bid)
        if not row or row.get("status") != "COMPLETE":
            state = "NOT_STARTED"; n_not_started += 1
        else:
            tier = row.get("quality_tier", "UNKNOWN")
            if tier == "FULL":
                state = "FULL"; n_full += 1
            elif tier == "STUB":
                state = "STUB"; n_stub += 1
            else:
                state = "SHALLOW"; n_shallow += 1
        per_bgc.append({"bgc_id": bid, "state": state})

    total = len(order)
    return {
        "total": total,
        "full": n_full,
        "shallow": n_shallow,
        "stub": n_stub,
        "not_started": n_not_started,
        "compile_ready": (n_full == total and total > 0),
        "summary": f"{total} BGCs | {n_full} FULL / {n_shallow} SHALLOW / {n_stub} STUB / {n_not_started} not-started",
        "per_bgc": per_bgc,
    }


def compile_ready(package_dir: str | Path, ranked_bgc_ids: list[str] | None = None) -> tuple[bool, str]:
    """Compile gate (v9.7.112): the master PDF should only build when every BGC is FULL §1–§10.

    Returns (ok, reason). ok=False lists how many cards are still incomplete so a partial run
    cannot masquerade as a finished strain.
    """
    _reg_status = read_register(package_dir).get("judgment_status", "")
    if is_corrupt_judgment_status(_reg_status):
        # v9.7.378b: a corrupt-and-unrecovered register's bgcs/total reflect only
        # whatever has been touched since the corruption, not the real strain --
        # never let that masquerade as "all BGCs FULL, compile OK".
        return False, (f"compile blocked: judgment register is {_reg_status} -- "
                        f"re-run init_register to restore the full BGC list before compiling")
    st = batch_status(package_dir, ranked_bgc_ids)
    if st["compile_ready"]:
        return True, f"all {st['total']} BGCs FULL — compile OK"
    blockers = st["shallow"] + st["stub"] + st["not_started"]
    return False, (f"compile blocked: {blockers} of {st['total']} BGCs not FULL "
                   f"({st['shallow']} SHALLOW, {st['stub']} STUB, {st['not_started']} not-started)")


def _recalculate_and_write(
    package_dir: str | Path, reg: dict[str, Any]
) -> list[dict[str, str]]:
    # v9.7.378b (audit lane wave 18): a register that reached here via
    # read_register()'s CORRUPT fallback (no last-good backup existed either)
    # carries no real total_bgcs/bgcs -- recomputing "total" as len(bgcs) here
    # would silently count only the BGC(s) touched since the corruption and let
    # the block below report a false COMPLETE/100% over a strain whose earlier
    # judgments were just lost. Detect that state before it gets overwritten.
    register_status = reg.get("judgment_status")
    recovering_from_unreadable_register = is_corrupt_judgment_status(register_status)
    total = reg.get("total_bgcs") or len(reg.get("bgcs", {}))
    done = sum(1 for v in reg.get("bgcs", {}).values() if v.get("status") == "COMPLETE")
    reg["total_bgcs"] = total
    reg["complete_bgcs"] = done
    reg["completion_pct"] = round(100.0 * done / total, 1) if total else 0.0
    if recovering_from_unreadable_register:
        # Never auto-declare COMPLETE/IN_PROGRESS/PENDING off a fabricated total
        # -- surface the honest state so is_judgment_complete()/compile_ready()
        # refuse to treat this package as judged until init_register restores
        # the full BGC list.
        reg["judgment_status"] = "CORRUPT_RECOVERY_INCOMPLETE"
    else:
        reg["judgment_status"] = (
            "COMPLETE" if done == total and total > 0
            else "IN_PROGRESS" if done > 0
            else "PENDING"
        )
    _atomic_write_text(_register_path(package_dir), json.dumps(reg, indent=2))
    persistence_warnings: list[dict[str, str]] = []
    if not recovering_from_unreadable_register:
        # Snapshot this known-good register so a future corruption recovers real
        # history instead of collapsing to whatever is touched next. Best-effort
        # -- never let a snapshot failure affect the register write above.
        try:
            _atomic_write_text(_last_good_path(package_dir), json.dumps(reg, indent=2))
        except Exception as exc:
            persistence_warnings.append({
                "stage": "write_last_good_snapshot",
                "error_type": type(exc).__name__,
                "message": str(exc),
            })
    # Sync JUDGMENT banner with judgment_status in both directions (v9.7.150c).
    # Originally this only cleared PENDING -> COMPLETE; if a card is later
    # invalidated (e.g. a reclassification reverts a COMPLETE BGC to PENDING),
    # nothing restored the PENDING banner, leaving a stale "COMPLETE" header
    # on a package that is actually back in progress. Both directions now
    # call the same sync function.
    banner_warning = _sync_judgment_banner(package_dir, reg)
    if banner_warning:
        persistence_warnings.append(banner_warning)
    return persistence_warnings



_COMPLETE_HEADER = "## ✅ EXTRACTION COMPLETE  ·  ⏳ JUDGMENT PENDING"
_PENDING_HEADER_PREFIX = "## ✅ EXTRACTION COMPLETE  ·  ✅ JUDGMENT COMPLETE"
_COMPLETE_BODY_MARKER = ("Mode B is **complete** for all BGCs. This package is ready "
                         "for compiled report assembly.\n\n")


def _sync_judgment_banner(
    package_dir: str | Path, reg: dict
) -> dict[str, str] | None:
    """Keep START_HERE.md's banner in sync with judgment_status, both directions.

    PENDING/IN_PROGRESS -> COMPLETE: rewrite the header to show JUDGMENT COMPLETE.
    COMPLETE -> PENDING/IN_PROGRESS (e.g. a card was invalidated by a
    reclassification): rewrite the header back to JUDGMENT PENDING so the
    banner never silently claims a state the register no longer holds.

    Non-blocking — a failure here never affects the register write.
    """
    pkg = Path(package_dir)
    start_here = pkg / "START_HERE.md"
    if not start_here.exists():
        return None
    try:
        txt = start_here.read_text(encoding="utf-8")
        status = reg.get("judgment_status")
        n_complete = reg.get("complete_bgcs", 0)
        n_total = reg.get("total_bgcs", 0)

        if status == "COMPLETE" and _COMPLETE_HEADER in txt:
            txt = txt.replace(
                _COMPLETE_HEADER,
                f"## ✅ EXTRACTION COMPLETE  ·  ✅ JUDGMENT COMPLETE ({n_complete}/{n_total} BGCs)"
            )
            txt = txt.replace(
                "This is a **Mamey deterministic-extraction** package",
                _COMPLETE_BODY_MARKER + "This was a **Mamey deterministic-extraction** package"
            )
            _atomic_write_text(start_here, txt)
        elif status != "COMPLETE" and txt.startswith(_PENDING_HEADER_PREFIX, txt.find("## ")):
            # Banner currently says COMPLETE but register has regressed — restore PENDING.
            import re as _re
            txt = _re.sub(
                r"## ✅ EXTRACTION COMPLETE  ·  ✅ JUDGMENT COMPLETE \([^)]*\)",
                _COMPLETE_HEADER, txt
            )
            txt = txt.replace(_COMPLETE_BODY_MARKER, "")
            _atomic_write_text(start_here, txt)
    except Exception as exc:
        # Banner synchronization stays nonblocking, but the write caller can no
        # longer mistake the ancillary presentation update for a success.
        return {
            "stage": "sync_judgment_banner",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    return None
