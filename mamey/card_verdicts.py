"""card_verdicts.py — surface the engine's EXISTING per-BGC capacity verdicts onto
the reader-facing Mode-B cards (.343 surfacing patch).

Motivation (audit 2026-07-30): the engine already computes an architectural-capacity
call (`Arch_Capacity`/`Class_Conf` on the triage board, written by
class_architecture.py::annotate_architecture(), called from source_scans.py -- NOT by the
similarly-named architecture_first.py, which is a separate, currently-unwired KCB-concordance
engine; v9.7.371 doc-currency fix),
a novelty prior (`Novelty_auto`), concordance / mis-anchor guards, and split-pathway
Diagnostic-Rescue verdicts (`*_4B_Diagnostic_Rescue_Leads.csv`, written by
diagnostic_rescue.py). But the per-BGC card emitters never PRINT them — so a card can
read "GENERIC" while the engine has already made a class-level capacity call. This module
is the display-layer plumbing that closes that gap. It reads only already-sealed package
files and renders claim-safe markdown. It changes NO scoring and writes NO package files.

CLAIM CEILING (travels with every line this emits):
- Arch_Capacity is a class-level CAPACITY / mechanism read, NOT a compound identity.
- A diagnostic gene / trigger sets capacity, never the product made.
- A Diagnostic-Rescue verdict is a homology-guided reconstruction HYPOTHESIS — not a
  nucleotide contig join and not a product-identity claim (its own `safe_claim` says so).
- Everything here is judgment-deferred; the reader (Sapote) adjudicates.
"""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Any, Optional


def _as_path(pkg) -> Optional[Path]:
    """Accept str | Path | None. None means 'no package to read' (caller passed
    pre-read data instead)."""
    if pkg is None:
        return None
    return pkg if isinstance(pkg, Path) else Path(pkg)


def _triage_path(pkg) -> Optional[Path]:
    p = _as_path(pkg)
    if p is None:
        return None
    hits = sorted(p.glob("*_4_triage_board.csv"))
    return hits[0] if hits else None


def _rescue_path(pkg) -> Optional[Path]:
    p = _as_path(pkg)
    if p is None:
        return None
    hits = sorted(p.glob("*_4B_Diagnostic_Rescue_Leads.csv"))
    return hits[0] if hits else None


def _g(row: dict, *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def triage_verdict(pkg: Path, bgc_id: str) -> dict[str, str]:
    """The architecture/capacity fields the engine already wrote for this BGC.
    Honest-blank on absence; never raises."""
    out: dict[str, str] = {}
    tb = _triage_path(pkg)
    if not tb:
        return out
    try:
        with tb.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if _g(r, "BGC_ID", "bgc_id") == bgc_id:
                    out = {
                        "arch": _g(r, "Arch"),
                        "arch_capacity": _g(r, "Arch_Capacity"),
                        "class_conf": _g(r, "Class_Conf"),
                        "novelty_auto": _g(r, "Novelty_auto"),
                        "concordance": _g(r, "Concordance"),
                        "misanchor_flag": _g(r, "Misanchor_Flag"),
                        "standing_rule": _g(r, "Standing_rule"),
                        "primary_metab_flag": _g(r, "Primary_metab_flag"),
                        # AUDIT_378 (card_verdicts_mobile_element_flag_guard): the third
                        # flag that gates corrected_rank alongside standing_rule_flag and
                        # primary_metabolism_flag (scoring.py:752). Read here so the guard is
                        # not silently dropped once Mobile_element_flag is a triage-board column.
                        "mobile_element_flag": _g(r, "Mobile_element_flag"),
                        "two_pathway_flag": _g(r, "Two_Pathway_Flag"),
                    }
                    break
    except (OSError, csv.Error):
        return {}
    return out


def rescue_for_bgc(pkg: Path, bgc_id: str) -> list[dict[str, Any]]:
    """Every Diagnostic-Rescue reconstruction hypothesis this BGC participates in,
    as core or as arm. One row per (pair, shared_scaffold). Honest-empty on absence."""
    rp = _rescue_path(pkg)
    if not rp:
        return []
    out: list[dict[str, Any]] = []
    try:
        with rp.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                core, arm = _g(r, "core_bgc"), _g(r, "arm_bgc")
                if bgc_id not in (core, arm):
                    continue
                role = "core" if bgc_id == core else "arm"
                out.append({
                    "pair": _g(r, "pair"),
                    "role": role,
                    "rescue_tier": _g(r, "rescue_tier"),
                    "core_bgc": core, "arm_bgc": arm,
                    "core_triggers": _g(r, "core_triggers"),
                    "core_kcb_family": _g(r, "core_kcb_family"),
                    "arm_roles": _g(r, "arm_roles"),
                    "arm_kcb_family": _g(r, "arm_kcb_family"),
                    "shared_scaffold": _g(r, "shared_scaffold"),
                    "tiling_verdict": _g(r, "tiling_verdict"),
                    "rggmci_gate": _g(r, "rggmci_gate"),
                    "kcb_concordance": _g(r, "kcb_concordance"),
                    "safe_claim": _g(r, "safe_claim"),
                    "claim_ceiling": _g(r, "claim_ceiling"),
                })
    except (OSError, csv.Error):
        return []
    return out


# rescue tiers ranked so we can pick the strongest involvement for a one-line summary
_TIER_RANK = {
    "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE": 3,
    "DIAGNOSTIC_RESCUE_MODERATE": 2,
    "DIAGNOSTIC_RESCUE_LOW": 1,
}


def render_block(pkg: Path, bgc_id: str, triage: dict | None = None,
                 rescues: list | None = None) -> str:
    """Claim-safe markdown block surfacing the engine's capacity verdicts for this BGC.
    Returns '' only if the engine wrote nothing at all (keeps cards clean on empties).
    Callers pass pre-read `triage`/`rescues` to avoid re-reading the package."""
    tv = triage if triage is not None else triage_verdict(pkg, bgc_id)
    rc = rescues if rescues is not None else rescue_for_bgc(pkg, bgc_id)
    # A triage row with only blank fields carries no capacity signal — treat as empty
    # so cards stay clean (do not print a block of em-dashes).
    tv_has_content = any((tv or {}).get(k) for k in (
        "arch", "arch_capacity", "class_conf", "novelty_auto",
        "concordance", "misanchor_flag", "standing_rule", "primary_metab_flag",
        "mobile_element_flag"))
    if not tv_has_content and not rc:
        return ""

    lines: list[str] = []
    lines.append(
        "**Engine capacity read** *(surfaced from the triage board + Diagnostic-Rescue "
        "layer; class-level CAPACITY, not a compound identity — judgment deferred):*")

    cap = tv.get("arch_capacity") or tv.get("arch") or "—"
    conf = tv.get("class_conf") or "—"
    lines.append(f"- **Architectural capacity:** {cap}  ·  **class confidence:** {conf}"
                 f"  ·  **novelty prior:** {tv.get('novelty_auto') or '—'}")

    guards = []
    if tv.get("concordance"):
        guards.append(f"concordance: {tv['concordance']}")
    if tv.get("misanchor_flag") and tv["misanchor_flag"].upper() not in ("", "NONE", "FALSE"):
        guards.append(f"mis-anchor: {tv['misanchor_flag']}")
    if tv.get("standing_rule"):
        guards.append(f"standing rule: {tv['standing_rule']}")
    if tv.get("primary_metab_flag") and tv["primary_metab_flag"].upper() not in ("", "NONE", "FALSE", "0"):
        guards.append(f"primary-metabolism flag: {tv['primary_metab_flag']}")
    if tv.get("mobile_element_flag") and tv["mobile_element_flag"].upper() not in ("", "NONE", "FALSE", "0"):
        guards.append(f"mobile element: {tv['mobile_element_flag']}")
    if guards:
        lines.append(f"- **Guards / context:** {'  ·  '.join(guards)}")

    if rc:
        # Split engine-SUPPORTED reconstructions from ones the engine evaluated and
        # DEMOTED (distant loci / low shared-reference signal). Presenting demoted
        # candidates as live "hypotheses" would over-read them — the engine already
        # rejected the complementarity proof (RG-GMCI two-proof: homology AND
        # biosynthetic-logic complementarity; these have homology only).
        def _supported(r: dict) -> bool:
            return r.get("tiling_verdict", "").startswith("RECONSTRUCTION_SUPPORTED")
        sup = [r for r in rc if _supported(r)]
        dem = [r for r in rc if not _supported(r)]
        role = rc[0].get("role", "?")
        if sup:
            n = len(sup)
            lines.append(
                f"- **Diagnostic-Rescue (engine-SUPPORTED):** this BGC is the **{role}** of "
                f"{n} split-pathway reconstruction hypothes{'is' if n == 1 else 'es'} the engine "
                f"scored as complementary (homology-based; strongest "
                f"{max(sup, key=lambda x: _TIER_RANK.get(x.get('rescue_tier',''),0)).get('rescue_tier','?')}):")
            for r in sorted(sup, key=lambda x: -_TIER_RANK.get(x.get("rescue_tier", ""), 0))[:4]:
                core_fam = r.get("core_kcb_family") or r.get("core_triggers") or "?"
                arm_fam = r.get("arm_kcb_family") or r.get("arm_roles") or "?"
                lines.append(
                    f"  - `{r.get('pair','?')}` — {r.get('rescue_tier','?')} "
                    f"({core_fam} core + {arm_fam} arm; shared ref {r.get('shared_scaffold','?')}); "
                    f"tiling: {r.get('tiling_verdict','?')}; gate: {r.get('rggmci_gate','?')}.")
        if dem:
            # one honest summary line — the engine considered these and did NOT support them
            gates = sorted({r.get("rggmci_gate", "") for r in dem if r.get("rggmci_gate")})
            gate_txt = "; ".join(g for g in gates)[:160] if gates else "distant loci / low shared-reference signal"
            lines.append(
                f"- **Diagnostic-Rescue (evaluated, NOT supported):** {len(dem)} further "
                f"{role}-side pairing(s) were tested and demoted by the engine — reconstruction "
                f"not supported. Reason(s): {gate_txt}. Not leads; shown for completeness.")
        # claim ceiling for ANY rescue involvement (supported or demoted): these are
        # homology-guided reconstruction hypotheses, never physical joins or identity claims.
        lines.append(
            "  - *Claim ceiling:* Diagnostic-Rescue pairings are homology-guided reconstruction "
            "hypotheses only — NOT a nucleotide contig join and NOT a product-identity claim; "
            "confirm physical linkage by long-read resequencing or PCR across the contig boundary.")

    lines.append(
        "<!-- Surfaced by card_verdicts.py (.343): these are the engine's own class-level "
        "capacity verdicts, shown so the card need not read GENERIC while the engine has "
        "already made a capacity call. Author: adjudicate them — do not restate as identity. -->")
    return "\n".join(lines)
