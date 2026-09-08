#!/usr/bin/env python3
"""mamey af-dossier — the Antifungal (AF) Lead Dossier, a cohort deliverable.

THE GAP THIS FILLS
------------------
The engine scores every BGC onto a per-strain AF lead board (`*_4c_AF_lead_board.csv`,
also the `AF_auto` column of the triage board). That board is a *capacity* routing prior:
it says which BGCs have the biosynthetic shape most worth screening for antifungal activity.
What it does NOT do is connect that capacity to the project's actual mission signal — the
MEASURED anti-*Candida* phenotype of each strain from the wet-lab screen. A user chasing
bee/wasp antifungal leads had the capacity board in one place and the measured bioactivity
table in another, with no single ranked artifact that says: *these strains both inhibit
Candida in the dish AND carry high-capacity AF leads — screen these first.*

`build_dossier` closes that. It joins, per strain (and per AF lead BGC):

  * the AF lead board (or the triage board's `AF_auto` column as a fallback source),
  * the strain's MEASURED Candida activity + host + corrected genus, from an OPTIONAL
    bioactivity-crosswalk CSV (path arg). With no crosswalk the engine still runs and
    emits a capacity-only dossier ("no measured data"), because Mamey must run without
    any wet-lab input,
  * novelty / reference-dark status + the KnownClusterBlast (KCB) anchor per BGC.

It emits `AF_LEAD_DOSSIER.csv` + a readable `AF_LEAD_DOSSIER.md`, ranked so that strains
with BOTH measured Candida activity AND high AF-capacity leads rise to the top — the
standout-strain shortlist.

CLAIM SAFETY (critical, load-bearing)
-------------------------------------
Measured bioactivity is a STRAIN-level observation, NOT a per-BGC activity claim. A
co-located AF lead is a *hypothesis for what might underlie* the measured strain-level
activity — never an assertion that BGC X produces the active compound. There are no
structure claims. BGC capacity (class-level, in the `*_class` / `af_score` / `lead_tier`
columns) and measured activity (strain-level, in the `measured_*` columns) are kept in
clearly separate columns and must not be conflated. AF score / lead tier are capacity
ROUTING priors, not activity or novelty.

Usage:
    python mamey_run.py af-dossier [ROOT] [--out DIR] [--activity-table CSV] [--depth N]
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
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
from pathlib import Path
from typing import Optional

# --- claim-safety framing (surfaced in the .md header AND as a machine-readable note) ---
CLAIM_SAFETY_LINES = (
    "Measured Candida/MRSA activity is a STRAIN-level observation from the wet-lab screen, "
    "NOT a per-BGC activity claim.",
    "A co-located AF lead is a hypothesis for what MIGHT underlie the measured strain-level "
    "activity — it is NOT an assertion that this BGC produces the active compound.",
    "AF score and lead tier are class-level capacity ROUTING priors, not activity, novelty, "
    "or structure claims. No structural claims are made anywhere in this dossier.",
    "BGC capacity (class-level) and measured activity (strain-level) are kept in separate "
    "columns and must not be conflated.",
)
CLAIM_SAFETY = " ".join(CLAIM_SAFETY_LINES)

# strain-level ranking tiers. Lower = higher priority in the ranked dossier.
_TIER_STANDOUT = 0     # measured Candida "+" AND >=1 High AF-capacity lead: the shortlist
_TIER_CANDIDA_POS = 1  # measured Candida "+" but no High lead
_TIER_UNTESTED = 2     # no measured data (engine ran without a crosswalk, or strain absent)
_TIER_CANDIDA_NEG = 3  # measured Candida "-"


# --------------------------------------------------------------------------- crosswalk
def load_crosswalk(path: str | Path | None) -> dict[str, dict]:
    """Load the optional measured-bioactivity crosswalk CSV, keyed by strain id.

    Expected (all optional) columns: strain, genus, host, anti_Candida, anti_MRSA,
    pct16S, closest_type, ... Extra columns are ignored; missing columns degrade
    gracefully. Returns {} when path is None/missing/unreadable — the engine must run
    without any wet-lab input.
    """
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    out: dict[str, dict] = {}
    try:
        with p.open(newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                strain = (r.get("strain") or r.get("Strain") or "").strip()
                if not strain:
                    continue
                out[strain] = {k: (v or "").strip() for k, v in r.items()}
    except Exception:
        return out
    return out


def _measured_flag(raw: str) -> str:
    """Normalize a measured +/- cell into a display string. Blank -> no measured data.

    AUDIT_374: case-insensitive. The crosswalk CSV is human-curated (a wet-lab screen
    export), and the synonym check previously matched literal "Y"/"N" but only lowercase word
    forms ("yes"/"positive"/"no"/"negative") -- so a human-typed "Yes"/"POSITIVE"/"No" (very
    plausible; spreadsheet tools routinely auto-capitalize) silently fell through to the
    free-text passthrough branch instead of normalizing, and downstream `.startswith("positive")`
    checks (which gate the standout-shortlist ranking -- this module's whole reason to exist)
    would then read a genuinely positive strain as not-positive.
    """
    v = (raw or "").strip()
    vl = v.lower()
    if vl in ("+", "positive", "pos", "yes", "y", "1"):
        return "positive (+)"
    if vl in ("-", "negative", "neg", "no", "n", "0"):
        return "negative (-)"
    if not v:
        return "no measured data"
    return v  # pass through free-text screen notes verbatim


# --------------------------------------------------------------------------- package IO
def _genus_of(taxonomy: str) -> str:
    tax = (taxonomy or "").strip()
    if not tax:
        return ""
    first = tax.split()[0]
    return first if first[:1].isupper() else ""


def _novelty_and_kcb_map(pkg_dir: Path) -> dict[str, dict]:
    """From the triage board, per BGC_ID -> {novelty, kcb, af_auto, lead_tier_auto}.

    The triage board carries the auto novelty prior and the KCB anchor; the AF board is
    the ranked capacity view. We join the two by BGC_ID.
    """
    board = next(iter(pkg_dir.glob("*_4_triage_board.csv")), None)
    out: dict[str, dict] = {}
    if board is None:
        return out
    try:
        with board.open(newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                bid = (r.get("BGC_ID") or "").strip()
                if not bid:
                    continue
                out[bid] = {
                    "novelty": (r.get("Novelty_auto") or "").strip(),
                    "kcb": (r.get("KCB_top") or "").strip(),
                    "af_auto": (r.get("AF_auto") or "").strip(),
                    "lead_tier_auto": (r.get("Lead_tier_auto") or "").strip(),
                    "products": (r.get("Products") or "").strip(),
                }
    except Exception:
        return out
    return out


def _is_engine_excluded(row: dict) -> bool:
    """True when the engine already excluded this BGC's row from the corrected lead order
    via scoring.py's three-flag gate (standing_rule_flag / primary_metabolism_flag /
    mobile_element_flag, scoring.py:752).

    AUDIT_378: scoring.py leaves `corrected_rank` BLANK for every one of the three
    exclusion reasons uniformly ("Downgraded rows keep their raw scores but get
    corrected_rank=None", scoring.py:749) while `AF_auto`/`Lead_tier`/`Lead_tier_auto` stay
    populated with the raw, PRE-EXCLUSION score/tier regardless. A present-but-blank
    `Corrected_rank` is therefore the authoritative, already-available signal for all three
    reasons on both the AF lead board (`*_4c_AF_lead_board.csv`, which carries a
    `Corrected_rank` column per `AXIS_LEAD_BOARD_HEADERS`) and the triage board — including a
    mobile-element-only exclusion, which the board's own `Downgrade`/`Standing_rule` text
    columns cannot detect (lead_board.py's `Downgrade` cell is built from only
    standing_rule_flag/primary_metabolism_flag, never mobile_element_flag; the triage board
    likewise carries no dedicated Mobile_element_flag column). This mirrors the identical fix
    already made for the same three-flag gate in compile_report.py's `_decision_for()`
    (v9.7.377 AUDIT audit comment there). A genuinely legacy package predating the
    `Corrected_rank` column (key ABSENT from the row, not merely blank) falls back to a text
    check on Standing_rule/Downgrade/Primary_metab_flag.
    """
    if "Corrected_rank" in row:
        return not (row.get("Corrected_rank") or "").strip()
    standing = (row.get("Standing_rule") or row.get("Downgrade") or "").strip()
    primary = (row.get("Primary_metab_flag") or "").strip().lower()
    return bool(standing) or primary in ("1", "true", "yes")


def _read_af_leads(pkg_dir: Path) -> list[dict]:
    """Return AF lead rows for one package: {bgc_id, products, af_score, lead_tier, kcb}.

    Primary source is the dedicated AF lead board (`*_4c_AF_lead_board.csv`). If that file
    is absent, fall back to the triage board's `AF_auto` column (any BGC with AF_auto > 0
    is an AF lead), so the dossier still builds from an older/leaner package.

    AUDIT_378: a BGC the engine already excluded via a standing-rule, primary-metabolism,
    or mobile-element downgrade (`_is_engine_excluded`) must never resurface here unmarked as an
    AF-capacity lead — this is the cohort shortlist deliverable that drives "screen these first,"
    so a leaked exclusion can send wet-lab priority at a BGC the engine itself already ruled out
    (e.g. an NI-siderophore-exclusion or SACCHARIDE-downgraded row can still carry a raw
    Lead_tier of "High", which also feeds the Candida+/High-lead "standout" shortlist tier).
    """
    af_board = next(iter(pkg_dir.glob("*_4c_AF_lead_board.csv")), None)
    leads: list[dict] = []
    if af_board is not None:
        try:
            with af_board.open(newline="", encoding="utf-8", errors="replace") as fh:
                for r in csv.DictReader(fh):
                    bid = (r.get("BGC_ID") or "").strip()
                    if not bid or _is_engine_excluded(r):
                        continue
                    leads.append({
                        "bgc_id": bid,
                        "products": (r.get("Products") or "").strip(),
                        "af_score": _to_float(r.get("AF_score")),
                        "lead_tier": (r.get("Lead_tier") or "").strip(),
                        "kcb": (r.get("KCB_top") or "").strip(),
                        "corrected_rank": (r.get("Corrected_rank") or "").strip(),
                    })
        except Exception:
            pass
        if leads:
            return leads
    # fallback: triage board AF_auto column
    board = next(iter(pkg_dir.glob("*_4_triage_board.csv")), None)
    if board is None:
        return leads
    try:
        with board.open(newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                bid = (r.get("BGC_ID") or "").strip()
                score = _to_float(r.get("AF_auto"))
                if not bid or score <= 0 or _is_engine_excluded(r):
                    continue
                leads.append({
                    "bgc_id": bid,
                    "products": (r.get("Products") or "").strip(),
                    "af_score": score,
                    "lead_tier": (r.get("Lead_tier_auto") or "").strip(),
                    "kcb": (r.get("KCB_top") or "").strip(),
                    "corrected_rank": (r.get("Corrected_rank") or "").strip(),
                })
    except Exception:
        pass
    return leads


def _to_float(v) -> float:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return 0.0


def _is_high_lead(tier: str) -> bool:
    return (tier or "").strip().lower() == "high"


# KCB null placeholders the boards emit when there is no usable comparator anchor.
_KCB_NULLS = {"", "unresolved", "none", "n/a", "na", "-", "no hit", "no_hit"}


def _clean_kcb(*candidates: str) -> str:
    """Return the first real KCB anchor among candidates, treating board null
    placeholders (UNRESOLVED / none / n/a / -) as absent. '' when all are null."""
    for c in candidates:
        c = (c or "").strip()
        if c.lower() not in _KCB_NULLS:
            return c
    return ""


# --------------------------------------------------------------------------- build
def _scan_package(pkg_dir: Path, crosswalk: dict[str, dict]) -> list[dict]:
    """Return per-AF-lead dossier rows for one sealed package (empty if not a package)."""
    manifest = pkg_dir / "manifest.json"
    if not manifest.is_file():
        return []
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return []
    strain = str(m.get("strain_id") or pkg_dir.name).strip()
    manifest_genus = _genus_of(str(m.get("taxonomy") or ""))
    release = str(m.get("release") or "") or ""

    xw = crosswalk.get(strain, {})
    # corrected genus/host come from the crosswalk when present, else the manifest taxonomy.
    genus = (xw.get("genus") or "").strip() or manifest_genus
    host = (xw.get("host") or "").strip()
    measured_candida = _measured_flag(xw.get("anti_Candida", ""))
    measured_mrsa = _measured_flag(xw.get("anti_MRSA", ""))
    closest_type = (xw.get("closest_type") or "").strip()
    has_measured = strain in crosswalk

    leads = _read_af_leads(pkg_dir)
    nov_map = _novelty_and_kcb_map(pkg_dir)

    candida_pos = measured_candida.startswith("positive")
    has_high_lead = any(_is_high_lead(ld["lead_tier"]) for ld in leads)
    standout = candida_pos and has_high_lead
    if standout:
        tier = _TIER_STANDOUT
    elif candida_pos:
        tier = _TIER_CANDIDA_POS
    elif not has_measured or measured_candida == "no measured data":
        tier = _TIER_UNTESTED
    elif measured_candida.startswith("negative"):
        tier = _TIER_CANDIDA_NEG
    else:
        tier = _TIER_UNTESTED

    rows: list[dict] = []
    for ld in leads:
        nk = nov_map.get(ld["bgc_id"], {})
        kcb = _clean_kcb(ld["kcb"], nk.get("kcb", ""))
        reference_dark = "yes" if not kcb else "no"
        rows.append({
            # --- identity ---
            "strain": strain,
            "genus": genus,
            "host": host,
            "release": release,
            # --- measured activity: STRAIN-LEVEL context (never a per-BGC claim) ---
            "measured_candida_strain": measured_candida,
            "measured_mrsa_strain": measured_mrsa,
            "closest_type_strain": closest_type,
            "standout_strain": "yes" if standout else "no",
            # --- BGC capacity: CLASS-LEVEL routing prior (not activity) ---
            "bgc_id": ld["bgc_id"],
            "products_class": ld["products"] or nk.get("products", ""),
            "af_capacity_score": ld["af_score"],
            "af_lead_tier": ld["lead_tier"],
            "novelty_prior": nk.get("novelty", ""),
            "reference_dark": reference_dark,
            "kcb_anchor": kcb,
            "corrected_rank": ld["corrected_rank"],
            # --- internal sort helpers (dropped before CSV write) ---
            "_tier": tier,
        })
    return rows


def _find_packages(root: Path, depth: int) -> list[Path]:
    root = Path(root)
    if (root / "manifest.json").is_file():
        return [root]
    out = []
    for p in root.rglob("manifest.json"):
        rel_depth = len(p.relative_to(root).parts)
        if rel_depth <= depth + 1:
            out.append(p.parent)
    return sorted(set(out))


_CSV_FIELDS = (
    "strain", "genus", "host", "release",
    "measured_candida_strain", "measured_mrsa_strain", "closest_type_strain",
    "standout_strain",
    "bgc_id", "products_class", "af_capacity_score", "af_lead_tier",
    "novelty_prior", "reference_dark", "kcb_anchor", "corrected_rank",
)


def build_dossier(pkgs: list[Path], crosswalk: dict[str, dict]) -> list[dict]:
    """Build and rank the dossier rows across all packages.

    Ranking: standout strains (measured Candida-positive AND a High AF-capacity lead)
    first, then Candida-positive, then untested, then Candida-negative; within a strain
    tier, by AF capacity score descending.
    """
    rows: list[dict] = []
    for pkg in pkgs:
        rows.extend(_scan_package(pkg, crosswalk))
    rows.sort(key=lambda r: (r["_tier"], -r["af_capacity_score"], r["strain"], r["bgc_id"]))
    return rows


def _render_md(rows: list[dict], crosswalk: dict[str, dict]) -> str:
    strains = {r["strain"] for r in rows}
    standout_rows = [r for r in rows if r["standout_strain"] == "yes"]
    standout_strains = sorted({r["strain"] for r in standout_rows})
    measured_strains = sorted(s for s in strains if s in crosswalk)

    L = ["# Antifungal (AF) Lead Dossier", ""]
    L.append("> **Claim safety.** " + " ".join(CLAIM_SAFETY_LINES))
    L.append("")
    L.append(
        f"**{len(rows)} AF-capacity lead BGCs across {len(strains)} strains.** "
        f"Measured bioactivity joined for **{len(measured_strains)} / {len(strains)}** strains"
        + (" (no crosswalk supplied — capacity-only dossier)." if not crosswalk
           else f" from the bioactivity crosswalk.")
    )
    L.append("")

    # --- standout shortlist ---
    L.append(f"## Standout shortlist — measured Candida-positive AND a High AF lead "
             f"({len(standout_strains)} strains)")
    L.append("")
    if standout_rows:
        L.append("These strains inhibit *Candida* in the wet-lab screen (STRAIN-level) and "
                 "carry a High-tier AF-capacity lead. The co-located lead is a **hypothesis "
                 "for what might underlie** that measured activity, not a claim it produces "
                 "the active compound. Screen/prioritize these first.")
        L.append("")
        L.append("| Strain | Genus | Host | Candida (strain) | BGC | Class (capacity) "
                 "| AF score | AF tier | Novelty | Ref-dark | KCB anchor |")
        L.append("|---|---|---|---|---|---|---:|---|---|---|---|")
        for r in sorted(standout_rows, key=lambda r: (-r["af_capacity_score"], r["strain"])):
            if not _is_high_lead(r["af_lead_tier"]):
                continue
            L.append(_md_row(r))
        L.append("")
    else:
        L.append("_No strain currently has BOTH measured Candida activity and a High AF "
                 "lead (either no crosswalk was supplied, or no overlap)._")
        L.append("")

    # --- full ranked table ---
    L.append("## Full AF lead dossier (ranked)")
    L.append("")
    L.append("Ranked: standout strains first, then Candida-positive, then untested "
             "(no measured data), then Candida-negative; within each, by AF capacity score.")
    L.append("")
    L.append("| Strain | Genus | Host | Candida (strain) | MRSA (strain) | BGC "
             "| Class (capacity) | AF score | AF tier | Novelty | Ref-dark | KCB anchor |")
    L.append("|---|---|---|---|---|---|---|---:|---|---|---|---|")
    for r in rows:
        L.append(
            f"| {r['strain']} | {r['genus'] or '—'} | {r['host'] or '—'} "
            f"| {r['measured_candida_strain']} | {r['measured_mrsa_strain']} "
            f"| {r['bgc_id']} | {r['products_class'] or '—'} "
            f"| {r['af_capacity_score']:g} | {r['af_lead_tier'] or '—'} "
            f"| {r['novelty_prior'] or '—'} | {r['reference_dark']} "
            f"| {r['kcb_anchor'] or '—'} |"
        )
    L.append("")
    L.append("---")
    L.append("*Columns marked \"(strain)\" are strain-level measured context; columns marked "
             "\"(capacity)\" plus AF score/tier/novelty are class-level capacity priors. "
             "Judgment deferred; wet-lab evidence required for any activity or structure claim.*")
    return "\n".join(L) + "\n"


def _md_row(r: dict) -> str:
    return (
        f"| {r['strain']} | {r['genus'] or '—'} | {r['host'] or '—'} "
        f"| {r['measured_candida_strain']} | {r['bgc_id']} | {r['products_class'] or '—'} "
        f"| {r['af_capacity_score']:g} | {r['af_lead_tier'] or '—'} "
        f"| {r['novelty_prior'] or '—'} | {r['reference_dark']} | {r['kcb_anchor'] or '—'} |"
    )


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated cohort-level deliverable (AF_LEAD_DOSSIER.csv/.md) on disk."""
    import os
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))


def _write_csv(rows: list[dict], path: Path) -> None:
    import io
    buf = io.StringIO()
    w = _SafeDictWriter(buf, fieldnames=list(_CSV_FIELDS))
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in _CSV_FIELDS})
    _atomic_write_text(path, buf.getvalue())


def run(root: str | Path = ".",
        out_dir: str | Path | None = None,
        activity_table: str | Path | None = None,
        depth: int = 3) -> dict:
    root = Path(root)
    crosswalk = load_crosswalk(activity_table)
    pkgs = _find_packages(root, depth)
    rows = build_dossier(pkgs, crosswalk)
    md = _render_md(rows, crosswalk)
    strains = {r["strain"] for r in rows}
    measured = sorted(s for s in strains if s in crosswalk)
    result = {
        "packages": len(pkgs),
        "lead_rows": len(rows),
        "strains": len(strains),
        "measured_join": len(measured),
        "measured_strains": measured,
        "standout_strains": sorted({r["strain"] for r in rows if r["standout_strain"] == "yes"}),
        "markdown": md,
        "rows": rows,
        "claim_safety": CLAIM_SAFETY,
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "AF_LEAD_DOSSIER.csv"
        md_path = out / "AF_LEAD_DOSSIER.md"
        _write_csv(rows, csv_path)
        _atomic_write_text(md_path, md)
        result["csv_path"] = str(csv_path)
        result["md_path"] = str(md_path)
        result["out_dir"] = str(out)
    return result


def af_dossier_command(args) -> int:
    res = run(getattr(args, "root", ".") or ".",
              out_dir=getattr(args, "out", None),
              activity_table=getattr(args, "activity_table", None),
              depth=getattr(args, "depth", 3))
    if res.get("out_dir"):
        join = res["measured_join"]
        emit(f"af-dossier: {res['packages']} packages -> {res['lead_rows']} AF lead rows "
              f"across {res['strains']} strains; measured Candida join for {join} strain(s); "
              f"{len(res['standout_strains'])} standout strain(s) -> {res['out_dir']}")
    else:
        emit(res["markdown"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Antifungal (AF) Lead Dossier — cohort deliverable")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--out")
    ap.add_argument("--activity-table", dest="activity_table",
                    help="optional measured-bioactivity crosswalk CSV (strain,anti_Candida,...)")
    ap.add_argument("--depth", type=int, default=3)
    return af_dossier_command(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
