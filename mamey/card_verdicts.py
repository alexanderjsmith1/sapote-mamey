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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceRead:
    """Typed source-read result while legacy dict/list readers remain compatible."""
    status: str
    value: Any
    path: Optional[Path] = None
    error_type: str = ""
    detail: str = ""


class EvidenceRows(list):
    """List-compatible rescue rows that retain typed source state for legacy callers."""
    def __init__(self, read: EvidenceRead):
        super().__init__(read.value)
        self.source_read = read

    def __bool__(self) -> bool:
        # Preserve an error-bearing empty value through legacy `rows or []` plumbing so
        # render_block can surface it. ABSENT and valid-empty retain normal false semantics.
        return len(self) > 0 or self.source_read.status not in ("ABSENT", "VALID")


def _read_dict_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _read_failure(path: Path, exc: Exception, empty_value: Any) -> EvidenceRead:
    status = "INVALID_CSV" if isinstance(exc, csv.Error) else "UNREADABLE"
    return EvidenceRead(status, empty_value, path, type(exc).__name__, str(exc))


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


def triage_verdict_status(pkg: Path, bgc_id: str) -> EvidenceRead:
    """Typed architecture/capacity source read for one engine BGC alias."""
    out: dict[str, str] = {}
    try:
        tb = _triage_path(pkg)
    except OSError as exc:
        return _read_failure(Path(pkg), exc, out)
    if not tb:
        return EvidenceRead("ABSENT", out)
    try:
        fields, rows = _read_dict_rows(tb)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return _read_failure(tb, exc, out)
    if not ({"BGC_ID", "bgc_id"} & set(fields)):
        return EvidenceRead("INVALID_SCHEMA", out, tb, "MissingColumns",
                            "requires BGC_ID or bgc_id")
    for r in rows:
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
    return EvidenceRead("VALID", out, tb)


def triage_verdict(pkg: Path, bgc_id: str) -> dict[str, str]:
    """Backward-compatible dict view; use `triage_verdict_status` for source state."""
    return triage_verdict_status(pkg, bgc_id).value


def rescue_for_bgc_status(pkg: Path, bgc_id: str) -> EvidenceRead:
    """Typed Diagnostic-Rescue source read for one engine BGC alias."""
    out: list[dict[str, Any]] = []
    try:
        rp = _rescue_path(pkg)
    except OSError as exc:
        return _read_failure(Path(pkg), exc, out)
    if not rp:
        return EvidenceRead("ABSENT", out)
    try:
        fields, rows = _read_dict_rows(rp)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return _read_failure(rp, exc, out)
    missing = sorted({"core_bgc", "arm_bgc"} - set(fields))
    if missing:
        return EvidenceRead("INVALID_SCHEMA", out, rp, "MissingColumns",
                            f"missing columns: {','.join(missing)}")
    for r in rows:
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
    return EvidenceRead("VALID", out, rp)


def rescue_for_bgc(pkg: Path, bgc_id: str) -> list[dict[str, Any]]:
    """Backward-compatible list view; use `rescue_for_bgc_status` for source state."""
    return EvidenceRows(rescue_for_bgc_status(pkg, bgc_id))


# rescue tiers ranked so we can pick the strongest involvement for a one-line summary
_TIER_RANK = {
    "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE": 3,
    "DIAGNOSTIC_RESCUE_MODERATE": 2,
    "DIAGNOSTIC_RESCUE_LOW": 1,
}


def render_block(pkg: Path, bgc_id: str, triage: dict | EvidenceRead | None = None,
                 rescues: list | EvidenceRead | None = None) -> str:
    """Claim-safe markdown block surfacing the engine's capacity verdicts for this BGC.
    Returns '' only if the engine wrote nothing at all (keeps cards clean on empties).
    Callers pass pre-read `triage`/`rescues` to avoid re-reading the package."""
    triage_read = (triage if isinstance(triage, EvidenceRead)
                   else triage_verdict_status(pkg, bgc_id) if triage is None else None)
    rescue_read = (rescues if isinstance(rescues, EvidenceRead)
                   else rescues.source_read if isinstance(rescues, EvidenceRows)
                   else rescue_for_bgc_status(pkg, bgc_id) if rescues is None else None)
    tv = triage_read.value if triage_read is not None else triage
    rc = rescue_read.value if rescue_read is not None else rescues
    source_failures = [
        (label, read) for label, read in (
            ("triage", triage_read), ("Diagnostic-Rescue", rescue_read),
        ) if read is not None and read.status not in ("ABSENT", "VALID")
    ]
    # A triage row with only blank fields carries no capacity signal — treat as empty
    # so cards stay clean (do not print a block of em-dashes).
    tv_has_content = any((tv or {}).get(k) for k in (
        "arch", "arch_capacity", "class_conf", "novelty_auto",
        "concordance", "misanchor_flag", "standing_rule", "primary_metab_flag",
        "mobile_element_flag"))
    if not tv_has_content and not rc and not source_failures:
        return ""

    lines: list[str] = []
    lines.append(
        "**Engine capacity read** *(surfaced from the triage board + Diagnostic-Rescue "
        "layer; class-level CAPACITY, not a compound identity — judgment deferred):*")

    for label, read in source_failures:
        detail = f"; {read.detail}" if read.detail else ""
        lines.append(f"- **{label} source status:** {read.status} ({read.error_type or 'UNKNOWN'}{detail}); "
                     "evidence is unresolved, not absent.")

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
