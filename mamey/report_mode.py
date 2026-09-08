"""mamey.report_mode — terse by default, legacy compact Mode B scaffold on demand (W7/W24).

THE PROBLEM
-----------
Emitting the legacy compact §1–§8 Mode B scaffold for EVERY BGC is token-heavy and fatigue-prone — the exact
condition that produced the AS-XXX silent omission — and it floods signal-to-noise so
far that the reader skims, defeating the rigor it was meant to add. The fix is to make
terse the default and generate deep interpretive work only for the BGCs that earn it. Current Full Mode B is the separate prose-first §1–§20 contract.

This is safe precisely because the boundary audit (mamey.boundary_audit) runs on the
STRUCTURED record, not the prose. Rigor no longer depends on prose volume: a terse run
is exactly as audited as a verbose one.

WHAT'S HERE vs WHAT'S PROMPT-SIDE
--------------------------------
The legacy §1–§8 scaffold prose is written by the judgment layer (the Sapote prompt), not by
Python. What this module owns:
  * the compact one-line renderer used for the default board (terse);
  * the legacy §1–§8 SCAFFOLD with the deterministic facts pre-slotted, emitted on demand so the
    judgment layer fills prose into a fixed, fact-anchored skeleton (not from scratch).
"""
from __future__ import annotations
from .render_safe import safe_kcb_display

DEFAULT_MODE = "terse"

MODE_B_SECTIONS = [
    "1. Identity & location",
    "2. Architecture & class capacity",
    "3. Boundary / truncation caveats",
    "4. KCB / MIBiG similarity (similarity, not identity)",
    "5. Source-derived scans (cassettes, resistance, regulators)",
    "6. Non-isolation / bioactivity context",
    "7. Lead tier & claim calibration",
    "8. Standing-rule / mis-anchor flags",
]


def _flags(v: dict) -> str:
    bits = []
    if v.get("standing_rule_flag"):
        bits.append(f"DOWNGRADE:{v['standing_rule_flag']}")
    if v.get("primary_metabolism_flag"):
        bits.append("PRIMARY-METAB")
    if v.get("misanchor_flag"):
        bits.append(f"MIS-ANCHOR:{v['misanchor_flag']}")
    return ("  [" + "; ".join(bits) + "]") if bits else ""


def render_terse(record: dict, verdict: dict) -> str:
    """One compact, fact-anchored line per BGC. Always carries the contig (never a bare
    BGC id) and the similarity BAND, never a bare number (W26)."""
    label = record.get("user_label") or f"{record.get('node_id') or record.get('contig')} ({record.get('bgc_id')})"
    cap = record.get("architecture_capacity") or ", ".join(record.get("products", [])[:3]) or "unresolved"
    band = verdict.get("kcb_similarity_band", "unresolved")
    return (f"{label}  —  {verdict.get('lead_tier')}/{verdict.get('claim_confidence')}  ·  "
            f"{cap}  ·  KCB:{band} (similarity, not identity){_flags(verdict)}")


def render_full_scaffold(record: dict, verdict: dict) -> str:
    """The legacy compact §1–§8 skeleton with deterministic facts pre-slotted.

    This is not the current Full Mode B §1–§20 contract; callers must not label
    this scaffold as a completed Full Mode B card. Returns markdown.
    """
    label = record.get("user_label") or f"{record.get('node_id') or record.get('contig')} ({record.get('bgc_id')})"
    facts = {
        "1. Identity & location": f"{label} · contig {record.get('contig')} · region "
                                  f"{record.get('antismash_region') or record.get('region_number')}",
        "2. Architecture & class capacity": f"{record.get('architecture_capacity') or 'unresolved'} "
                                            f"(arch conf {record.get('architecture_confidence')})",
        "3. Boundary / truncation caveats": f"edge_status = {record.get('edge_status')}",
        "4. KCB / MIBiG similarity (similarity, not identity)":
            f"band = {verdict.get('kcb_similarity_band', 'unresolved')}; "
            f"top = {safe_kcb_display(record)}",
        "7. Lead tier & claim calibration": f"{verdict.get('lead_tier')} / "
                                            f"claim_confidence {verdict.get('claim_confidence')}",
        "8. Standing-rule / mis-anchor flags": _flags(verdict).strip() or "none",
    }
    lines = [f"### {label} — legacy compact Mode B scaffold (not Full §1–§20)", ""]
    for sec in MODE_B_SECTIONS:
        lines.append(f"**{sec}**")
        lines.append(facts.get(sec, "_(judgment layer: prose here)_"))
        lines.append("")
    return "\n".join(lines)


def render_board(records: list, verdicts: list, mode: str = DEFAULT_MODE,
                 full_ids: set | None = None) -> str:
    """Render a strain's board. Default terse; pass mode='full' for everything, or
    full_ids={...} to expand only specific BGCs (terse for the rest)."""
    verds = {v["bgc_id"]: v for v in verdicts}
    full_ids = full_ids or set()
    out = []
    for r in records:
        uid = r["bgc_id"]
        v = verds.get(uid, {})
        if mode == "full" or uid in full_ids:
            out.append(render_full_scaffold(r, v))
        else:
            out.append(render_terse(r, v))
    return "\n".join(out) + "\n"
