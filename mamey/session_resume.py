"""session_resume.py — session-state reducer for Mamey packages.

Produces a one-read paste-ready markdown briefing (or JSON handoff) from a sealed
package: strain context, assembly tier, judgment progress, per-BGC table, RGGMCI
HIGH pairs touching the next-up BGCs, standing-rule exclusions, and a derived
`compile-report --strict` runnability flag.

The goal is to collapse the session-boundary overhead: one `mamey resume` should
give the next analysis LLM everything it needs to start Mode B without re-reading
the triage board or the register.

Usage:
    mamey resume <package_dir>
    mamey resume <package_dir> --json
    mamey resume <package_dir> --ranked BGC028,BGC020,BGC003
    mamey resume <package_dir> --cross-strain-note "HGLE:present; IOLR:bryo-signal"

Wishlist W1 (v9.7.149b → next): full implementation replacing the stub.
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

import argparse
import csv
import json
import pathlib
import re
from typing import Optional

from .manifest_schema import (
    read_manifest_field, F_ASSEMBLY_TIER, F_RAW_BGCS, F_CORRECTED_BGCS, F_INTERIOR_PCT,
)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def resume_command(args: argparse.Namespace) -> None:
    """CLI entry point for `mamey resume`."""
    pkg = pathlib.Path(args.package_dir)
    ranked: Optional[str] = getattr(args, 'ranked', None)
    cross_note: Optional[str] = getattr(args, 'cross_strain_note', None)
    as_json: bool = getattr(args, 'json', False)

    result = build_resume(pkg, ranked=ranked, cross_strain_note=cross_note)
    if as_json:
        emit(json.dumps(result, indent=2, default=str))
    else:
        emit(result['markdown'])


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Narrative section files that compile-report --strict requires (relative to
# pkg/judgment/). All must exist for strict_runnable=True.
#
# Single source of truth is compile_report.NARRATIVE_SLOTS — imported below so
# this list never drifts. (W1-F5 collateral, v9.7.149c.) Falls back to a local
# hard-coded list only if the import fails at module-load time (e.g. partial
# install), so `mamey resume` still works even if compile_report is broken.
try:
    from .compile_report import STRICT_NARRATIVE_KEYS as _STRICT_KEYS
    from .compile_report import narrative_filename as _narrative_filename
    _STRICT_NARRATIVE_SECTIONS = tuple(
        _narrative_filename(k, "{strain}") for k in _STRICT_KEYS
    )
except Exception:  # pragma: no cover — defensive only
    _STRICT_NARRATIVE_SECTIONS = (
        "{strain}_execsummary_section.md",
        "{strain}_laypersons_section.md",
        "{strain}_ecology_section.md",
        "{strain}_deepdives_section.md",
    )

# Quality tiers that warrant enrichment surfacing
_NEEDS_ENRICHMENT_TIERS = {"SHALLOW", "STUB", "PARTIAL"}

# RGGMCI confidence value the wishlist asks us to filter to
_RGGMCI_HIGH_VALUE = "HIGH_RG_GMCI_RESCUE"

# Column-name candidates per logical field. Triage boards have drifted across
# v9.7.x; we accept any of these and the first present wins.
_NODE_COLS    = ("Node", "Contig", "contig/NODE", "contig", "NODE")
_CLASS_COLS   = ("Products", "Class", "Product_class", "products")
_LEAD_COLS    = ("Lead_tier_auto", "Lead_tier", "lead_tier_auto")
_RANK_COLS    = ("Corrected_rank", "Rank", "corrected_rank")
_STANDING_COLS = ("Standing_rule", "standing_rule", "Downgrade")
_KCB_COLS     = ("KCB_top", "kcb_top")
_LENGTH_COLS  = ("Region_Length_kb", "region_length_kb")
_LOCATOR_COLS = ("Assembly_Locator", "Boundary", "assembly_locator")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def build_resume(pkg: pathlib.Path,
                 ranked: Optional[str] = None,
                 cross_strain_note: Optional[str] = None) -> dict:
    """Build a session-resume briefing from a sealed package.

    Returns a dict with both machine fields and a rendered `markdown` string.
    """
    pkg = pathlib.Path(pkg)
    short = _read_manifest_short(pkg)
    full  = _read_manifest_full(pkg)

    strain_id = (short.get('strain_id')
                 or full.get('strain_id')
                 or pkg.parent.name)
    display   = full.get('display_name') or strain_id
    taxonomy  = full.get('taxonomy') or 'unknown'
    source    = full.get('source') or 'unknown'
    release   = short.get('release') or full.get('release') or 'PRIVATE'

    # Assembly — via canonical accessor (v9.7.160). Fixes the latent wrong-fallback
    # bug: the old code looked for assembly_tier/interior_pct under full['bgc_counts'],
    # but they live in full['assembly'] (tier/interior_pct) — the accessor knows the
    # right nested location, and raw/corrected correctly fall back to bgc_counts.
    tier        = read_manifest_field(F_ASSEMBLY_TIER, manifest=full, manifest_short=short, default='UNKNOWN')
    raw         = read_manifest_field(F_RAW_BGCS, manifest=full, manifest_short=short, default='?')
    corrected   = read_manifest_field(F_CORRECTED_BGCS, manifest=full, manifest_short=short, default='?')
    interior_pct = read_manifest_field(F_INTERIOR_PCT, manifest=full, manifest_short=short, default='?')

    top_ab = short.get('top_3_ab') or []
    top_af = short.get('top_3_af') or []

    # Triage rows: canonical ordered list + per-BGC dict view
    triage_rows = _read_triage_board(pkg)

    # Register: status + quality tier per BGC, plus last_sapote_session and
    # judgment_status (W4 item 3, v9.7.149c — surfaces register's roll-up
    # state alongside the per-BGC table).
    register = _read_register(pkg, strain_id)
    reg_bgcs = register.get('bgcs', {}) if register else {}
    last_session = (register or {}).get('last_sapote_session')
    judgment_status = (register or {}).get('judgment_status')

    # Build per-BGC table rows (joined view)
    bgc_table = _build_bgc_table(triage_rows, reg_bgcs)

    # Done / pending — derived from the joined table
    done    = [r['bgc_id'] for r in bgc_table if r['status'] == 'COMPLETE']
    pending = [r['bgc_id'] for r in bgc_table if r['status'] != 'COMPLETE']

    # Standing-rule exclusions (always-excluded BGCs the analysis LLM should
    # skip from the start)
    exclusions = [
        {'bgc_id': r['bgc_id'], 'node': r['node'], 'reason': r['standing_rule']}
        for r in bgc_table if r['standing_rule']
    ]
    excluded_ids = {e['bgc_id'] for e in exclusions}

    # Next-up: ranked override → otherwise the pending list (already ordered by
    # triage rank). Standing-rule exclusions are pruned out — no point asking
    # the analyst to card a downgraded BGC.
    if ranked:
        rank_order = [b.strip() for b in ranked.split(',') if b.strip()]
        next_up_raw = [b for b in rank_order if b not in done]
    else:
        next_up_raw = list(pending)
    next_up = [b for b in next_up_raw if b not in excluded_ids][:3]

    # Cards needing enrichment (COMPLETE but SHALLOW/STUB/PARTIAL)
    enrichment_needed = [
        {'bgc_id': r['bgc_id'], 'quality_tier': r['quality_tier']}
        for r in bgc_table
        if r['status'] == 'COMPLETE' and r['quality_tier'].upper() in _NEEDS_ENRICHMENT_TIERS
    ]

    # RGGMCI HIGH pairs touching the next-up set
    rggmci_pairs = _rggmci_high_pairs_for(pkg, next_up)

    # BLASTP batch status for next-up
    blastp_outstanding = _blastp_outstanding_for(pkg, next_up)

    # compile-report --strict runnability
    strict_runnable, strict_missing = _strict_runnable(pkg, strain_id)

    # Structured cross-strain note (new)
    cross_struct = _parse_structured_note(cross_strain_note)

    # Quality notes (back-compat: list of (bgc_id, quality_tier))
    quality_notes = [(r['bgc_id'], r['quality_tier'])
                     for r in bgc_table
                     if r['status'] == 'COMPLETE'
                     and r['quality_tier']
                     and r['quality_tier'].upper() != 'FULL']

    # ---------- markdown render ----------
    md = _render_markdown(
        display=display, strain_id=strain_id, taxonomy=taxonomy, source=source,
        release=release, tier=tier, interior_pct=interior_pct,
        raw=raw, corrected=corrected,
        bgc_table=bgc_table, done=done, pending=pending,
        next_up=next_up, exclusions=exclusions,
        enrichment_needed=enrichment_needed,
        rggmci_pairs=rggmci_pairs,
        blastp_outstanding=blastp_outstanding,
        strict_runnable=strict_runnable, strict_missing=strict_missing,
        top_ab=top_ab, top_af=top_af,
        cross_struct=cross_struct, cross_raw=cross_strain_note,
        last_session=last_session, judgment_status=judgment_status,
    )

    return {
        # back-compat keys (do not rename — existing tests + callers depend on these)
        'strain_id':       strain_id,
        'display':         display,
        'assembly_tier':   tier,
        'raw_bgcs':        raw,
        'corrected_bgcs':  corrected,
        'done':            done,
        'pending':         pending,
        'next_up':         next_up,
        'quality_notes':   quality_notes,
        'markdown':        md,
        # new (W1) keys
        'release':         release,
        'taxonomy':        taxonomy,
        'source':          source,
        'interior_pct':    interior_pct,
        'bgc_table':       bgc_table,
        'exclusions':      exclusions,
        'enrichment_needed': enrichment_needed,
        'rggmci_high_pairs': rggmci_pairs,
        'blastp_outstanding': blastp_outstanding,
        'strict_runnable': strict_runnable,
        'strict_missing_sections': strict_missing,
        'cross_strain_note_structured': cross_struct,
        'cross_strain_note_raw': cross_strain_note,
        'last_sapote_session': last_session,
        'judgment_status': judgment_status,
        'top_ab':          top_ab,
        'top_af':          top_af,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _render_markdown(*, display, strain_id, taxonomy, source, release,
                     tier, interior_pct, raw, corrected,
                     bgc_table, done, pending, next_up, exclusions,
                     enrichment_needed, rggmci_pairs, blastp_outstanding,
                     strict_runnable, strict_missing,
                     top_ab, top_af, cross_struct, cross_raw,
                     last_session, judgment_status) -> str:
    lines: list[str] = []
    lines.append(f"## Session resume — {display}")
    lines.append("")
    lines.append(f"**Strain:** {display} ({taxonomy}) | "
                 f"**Source:** {source} | **Release:** {release}")
    lines.append(f"**Assembly:** {tier} ({interior_pct}% interior) | "
                 f"**BGCs:** {raw} raw / {corrected} corrected")
    if last_session:
        lines.append(f"**Last Sapote session:** {last_session}")
    if judgment_status:
        lines.append(f"**Judgment status:** {judgment_status}")
    lines.append("")

    # ---- Mode B progress + next-up ----
    total = len(done) + len(pending)
    lines.append(f"**Mode B progress:** {len(done)}/{total} complete")
    if done:
        lines.append(f"  - Carded (COMPLETE): {', '.join(done)}")
    else:
        lines.append("  - Carded: none yet")
    if next_up:
        lines.append(f"  - **Next up:** {', '.join(next_up)}")
    elif pending:
        lines.append("  - **Next up:** (all remaining pending are standing-rule excluded)")
    else:
        lines.append("  - All BGCs complete ✓")
    lines.append("")

    # ---- compile-report --strict gate ----
    if strict_runnable:
        lines.append("**`compile-report --strict`:** runnable ✓ "
                     "(all narrative sections on disk)")
    else:
        miss = ", ".join(strict_missing) if strict_missing else "all narrative sections"
        lines.append(f"**`compile-report --strict`:** not yet runnable — missing: {miss}")
    lines.append("")

    # ---- Per-BGC table ----
    if bgc_table:
        lines.append("### Per-BGC progress")
        lines.append("")
        lines.append("| BGC | Node | Class | Lead | Mode B | Quality | Last session |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in bgc_table:
            lines.append(
                f"| {r['bgc_id']} | {r['node'] or '—'} | "
                f"{r['class_'] or '—'} | {r['lead_tier'] or '—'} | "
                f"{r['status']} | {r['quality_tier'] or '—'} | "
                f"{r['last_session'] or '—'} |"
            )
        lines.append("")

    # ---- Cards needing enrichment ----
    if enrichment_needed:
        lines.append("### Cards needing enrichment (SHALLOW/STUB/PARTIAL)")
        for e in enrichment_needed:
            lines.append(f"- {e['bgc_id']}: {e['quality_tier']}")
        lines.append("")

    # ---- Standing-rule exclusions ----
    if exclusions:
        lines.append("### Standing-rule exclusions (skip from start)")
        for e in exclusions:
            node = f" ({e['node']})" if e['node'] else ""
            lines.append(f"- {e['bgc_id']}{node}: {e['reason']}")
        lines.append("")

    # ---- RGGMCI HIGH pairs touching next-up ----
    if rggmci_pairs:
        lines.append("### RGGMCI HIGH pairs touching next-up BGCs")
        for p in rggmci_pairs:
            cls = p.get('functional_rescue_class') or '—'
            lines.append(f"- {p['bgc_a']} ↔ {p['bgc_b']} — {cls}")
        lines.append("")

    # ---- BLASTP batches outstanding for next-up ----
    if next_up:
        if blastp_outstanding:
            lines.append("### BLASTP batches outstanding")
            for bgc in blastp_outstanding:
                lines.append(f"- {bgc}: no `modeb_blastp/{bgc}/` directory yet")
            lines.append("")
        else:
            lines.append("**BLASTP batches:** emitted for all next-up BGCs ✓")
            lines.append("")

    # ---- Top leads ----
    if top_ab:
        lines.append("**Top AB leads:**")
        for entry in top_ab[:3]:
            lines.append(f"  - {entry.get('bgc_id', '?')} — AB score "
                         f"{entry.get('ab_score', '?')}")
    if top_af:
        lines.append("**Top AF leads:**")
        for entry in top_af[:3]:
            lines.append(f"  - {entry.get('bgc_id', '?')} — AF score "
                         f"{entry.get('af_score', '?')}")
    if top_ab or top_af:
        lines.append("")

    # ---- Cross-strain context ----
    if cross_struct:
        lines.append("### Cross-strain context")
        for k, v in cross_struct.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
    elif cross_raw:
        lines.append(f"**Cross-strain context:** {cross_raw}")
        lines.append("")

    lines.append("**To continue:** run `mamey mode-b --package <pkg> --top-n N --outdir mode_b/`")
    lines.append("Full Mode B = §1–§20 + §28 + §30 (mandatory) + applicable conditional §21–§27/§29.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-BGC table assembly
# ---------------------------------------------------------------------------

def _build_bgc_table(triage_rows: list[dict], reg_bgcs: dict) -> list[dict]:
    """Join triage rows + register entries into a list of per-BGC dicts.

    Sorted by Corrected_rank (numeric ascending). BGCs only in the register
    (not in the triage board) appear at the end.

    Note: a register row's per-BGC session key is "session_id" (set by
    judgment_store.py's init_register/_update_register), not "last_session" --
    "last_session" never exists as a per-BGC key (only the register's
    top-level "last_sapote_session" is strain-wide), so reading it here
    surfaces the actual per-BGC session_id under this table's "last_session"
    column name.
    """
    rows: list[dict] = []
    triage_ids = set()
    for tr in triage_rows:
        bgc_id = tr.get('BGC_ID') or tr.get('bgc_id')
        if not bgc_id:
            continue
        triage_ids.add(bgc_id)
        reg_entry = reg_bgcs.get(bgc_id, {})
        rows.append({
            'bgc_id':        bgc_id,
            'node':          _first_present(tr, _NODE_COLS),
            'class_':        _first_present(tr, _CLASS_COLS),
            'lead_tier':     _first_present(tr, _LEAD_COLS),
            'corrected_rank': _safe_float(_first_present(tr, _RANK_COLS)),
            'standing_rule':  _first_present(tr, _STANDING_COLS),
            'kcb_top':        _first_present(tr, _KCB_COLS),
            'region_length_kb': _first_present(tr, _LENGTH_COLS),
            'locator':        _first_present(tr, _LOCATOR_COLS),
            'status':         reg_entry.get('status', 'PENDING'),
            'quality_tier':   reg_entry.get('quality_tier', ''),
            'last_session':   reg_entry.get('session_id', ''),
        })

    # BGCs only in register (e.g. carded BGCs that have since been pruned from
    # the triage board) — append at end so they don't get lost.
    for bgc_id, reg_entry in reg_bgcs.items():
        if bgc_id in triage_ids:
            continue
        rows.append({
            'bgc_id':        bgc_id,
            'node':          '',
            'class_':        '',
            'lead_tier':     '',
            'corrected_rank': None,
            'standing_rule':  '',
            'kcb_top':        '',
            'region_length_kb': '',
            'locator':        '',
            'status':         reg_entry.get('status', 'PENDING'),
            'quality_tier':   reg_entry.get('quality_tier', ''),
            'last_session':   reg_entry.get('session_id', ''),
        })

    rows.sort(key=lambda r: (r['corrected_rank'] is None, r['corrected_rank']
                             if r['corrected_rank'] is not None else 1e9))
    return rows


# ---------------------------------------------------------------------------
# Structured cross-strain note parsing
# ---------------------------------------------------------------------------

_KV_RE = re.compile(r'^\s*([A-Za-z][\w\-]*)\s*:\s*(.+?)\s*$')


def _parse_structured_note(note: Optional[str]) -> dict:
    """Parse a "KEY:value; KEY:value" structured note into an ordered dict.

    Returns {} if `note` is falsy or doesn't look structured (no colons in any
    semicolon-delimited segment). This keeps the free-text fallback intact for
    legacy callers.
    """
    if not note:
        return {}
    parts = [p for p in (s.strip() for s in note.split(';')) if p]
    if not parts:
        return {}
    parsed: dict[str, str] = {}
    for part in parts:
        m = _KV_RE.match(part)
        if not m:
            # Any non-KV segment → not structured; treat the whole thing as
            # free text by returning {}. This preserves the cross_raw fallback.
            return {}
        key, val = m.group(1), m.group(2)
        parsed[key] = val
    return parsed


# ---------------------------------------------------------------------------
# RGGMCI HIGH pairs
# ---------------------------------------------------------------------------

def _rggmci_high_pairs_for(pkg: pathlib.Path, next_up: list[str]) -> list[dict]:
    """Read `*_4A_RGGMCI_ranked_pairs.csv` and return HIGH-confidence pairs
    where either bgc_a or bgc_b is in `next_up`.

    Returns [] if the file is absent or unreadable. Never raises.
    """
    if not next_up:
        return []
    candidates = sorted(pkg.glob("*_4A_RGGMCI_ranked_pairs.csv"))
    if not candidates:
        return []
    target = set(next_up)
    out: list[dict] = []
    try:
        with open(candidates[0], newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                conf = (r.get('rggmci_confidence') or '').strip()
                if conf != _RGGMCI_HIGH_VALUE:
                    continue
                a = (r.get('bgc_a') or '').strip()
                b = (r.get('bgc_b') or '').strip()
                if a in target or b in target:
                    out.append({
                        'bgc_a': a, 'bgc_b': b,
                        'rggmci_confidence': conf,
                        'functional_rescue_class': (r.get('functional_rescue_class')
                                                    or r.get('rescue_class') or ''),
                    })
    except (OSError, csv.Error):
        return []
    return out


# ---------------------------------------------------------------------------
# BLASTP outstanding check
# ---------------------------------------------------------------------------

def _blastp_outstanding_for(pkg: pathlib.Path, next_up: list[str]) -> list[str]:
    """For each BGC in `next_up`, return the IDs that lack a
    `modeb_blastp/<BGC_ID>/` directory with at least one completed batch file.

    AUDIT_378 fix: the presence check used to accept ANY file in the
    directory, including a stray macOS `.DS_Store` (created merely by
    Finder/`ls` browsing the folder) or a `.fasta.tmp` sibling left behind by
    a process killed between BlastpBatchEmitter.write_batches()'s
    `write_text()` and its atomic `.replace()` (see blastp_batch_emitter.py --
    that .tmp+replace pattern is exactly what a crash mid-write leaves half
    done). Either stray file made this function silently report "batches
    emitted" for a BGC that in fact has zero usable BLASTP submission files,
    masking a genuine gap as done instead of surfacing it as outstanding.
    The real emitter only ever writes `<prefix>_batch<N>.fasta` (and its
    `_README.txt` companion) directly into place, never partially, so
    requiring a `.fasta` suffix is a precise, non-fragile completion check.
    """
    if not next_up:
        return []
    blastp_root = pkg / "modeb_blastp"
    out: list[str] = []
    for bgc_id in next_up:
        d = blastp_root / bgc_id
        if not d.is_dir():
            out.append(bgc_id)
            continue
        # Directory exists — check it has at least one COMPLETED batch fasta
        # file, not just any file (stray .DS_Store / .tmp leftovers don't count).
        try:
            has_file = any(p.is_file() and p.suffix == ".fasta" for p in d.iterdir())
        except OSError:
            has_file = False
        if not has_file:
            out.append(bgc_id)
    return out


# ---------------------------------------------------------------------------
# compile-report --strict runnability
# ---------------------------------------------------------------------------

def _strict_runnable(pkg: pathlib.Path, strain_id: str) -> tuple[bool, list[str]]:
    """Check whether `compile-report --strict` can succeed without manual fills.

    Returns (runnable, missing_section_filenames).
    """
    judgment_dir = pkg / "judgment"
    missing: list[str] = []
    for tmpl in _STRICT_NARRATIVE_SECTIONS:
        fname = tmpl.format(strain=strain_id)
        if not (judgment_dir / fname).exists():
            missing.append(fname)
    return (not missing), missing


# ---------------------------------------------------------------------------
# Triage board reader
# ---------------------------------------------------------------------------

def _read_triage_board(pkg: pathlib.Path) -> list[dict]:
    """Read all rows from `*_4_triage_board.csv` in pkg root.

    Returns [] if absent or unreadable. Never raises.
    """
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    if not candidates:
        return []
    try:
        with open(candidates[0], newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except (OSError, csv.Error):
        return []


def _read_register(pkg: pathlib.Path, strain_id: str) -> dict:
    """Read `<strain>_judgment_register.json` or return {}."""
    p = pkg / f"{strain_id}_judgment_register.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _first_present(row: dict, cols: tuple[str, ...]) -> str:
    """Return the first non-empty value from row for any column in cols."""
    for c in cols:
        v = row.get(c)
        if v not in (None, ''):
            return str(v).strip()
    return ''


def _safe_float(v) -> Optional[float]:
    if v in (None, '', '—'):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _read_manifest_short(pkg: pathlib.Path) -> dict:
    p = pkg / 'manifest_short.json'
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _read_manifest_full(pkg: pathlib.Path) -> dict:
    p = pkg / 'manifest.json'
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}
