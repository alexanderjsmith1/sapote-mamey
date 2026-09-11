"""mamey/report_card.py — render the cohesive L0–L1 per-BGC report card from a sealed package.

Implements §6.1 of PER_BGC_REPORT_CARD_SPEC (the L0–L3 report-card content spec — distinct from the
existing docs/PER_BGC_PAGE_LAYOUT_SPEC.md, which governs page co-location; the two are complementary):
a progressive-disclosure card that renders the auto layers (L0 headline + 3 badges + action; L1 predicted molecule) for every BGC straight from the package —
triage board + the Patch-G prediction CSVs — with an RDKit-computed predicted mass on wildcard-free
SMILES and an explicit partial-assembly caveat on Edge/Full-contig clusters. L2/L3 render their
auto-available parts (comparators, provenance skeleton); the authored prose is left as slots.

Claim discipline is enforced in the wording: capacity-level, KCB = similarity not identity, bioactivity
extract-level, node·region locators, provenance tags. Does NOT resolve the polymer's `X` positions into
the mass — that requires a module→position mapping and is a separate step (a wrong assignment would
misstate the monomer, which the science rules forbid).

Degrades cleanly: no RDKit → mass line says "rdkit not installed"; no prediction CSVs → the molecule
layer says so. Never raises on missing inputs.
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

import csv
import json  # F09 (v9.7.353): required by module-scope _loadj(); its absence silently NameError'd,
             # was swallowed by render_report_cards' try/except, and left the version hard-coded.
import os
import re


def _loadj(p):   # B1: context-managed json load (no leaked handle); +utf-8 (B2)
    with open(p, encoding="utf-8") as _f:
        return json.load(_f)



# ---- optional RDKit (predicted formula/mass from a wildcard-free SMILES) --------------------------
def _mass_from_smiles(smiles: str) -> dict | None:
    if not smiles or "[*]" in smiles or "*" in smiles:
        return {"status": "pending", "reason": "SMILES has wildcards (unresolved X positions)"}
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
    except Exception:
        return {"status": "no_rdkit", "reason": "rdkit not installed (optional dep)"}
    try:
        m = Chem.MolFromSmiles(smiles)
        if m is None:
            return {"status": "unparsed", "reason": "RDKit could not parse the SMILES"}
        mw = Descriptors.ExactMolWt(m)
        return {"status": "ok", "formula": rdMolDescriptors.CalcMolFormula(m),
                "monoisotopic": round(mw, 3), "m_plus_h": round(mw + 1.00728, 3)}
    except Exception as exc:
        return {"status": "error", "reason": f"{type(exc).__name__}: {exc}"}


# ---- deterministic badges (spec §3; thresholds are first-pass, calibrate cohort-wide) -------------
def _kcb_named(bgc: dict) -> tuple[str, float | None]:
    raw = (bgc.get("KCB_top") or "").strip()
    name = raw.split("|")[1].strip() if "|" in raw else ("" if raw.upper() in ("", "NONE") else raw)
    raw_score = bgc.get("KCB_score")
    if raw_score is None or (isinstance(raw_score, str) and not raw_score.strip()):
        score = None
    else:
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = None
    return name, score


def _num(bgc: dict, key: str) -> float | None:
    raw = bgc.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _novelty_tier(bgc: dict, poly: dict | None = None) -> str:
    """Single source of truth for the novelty spine, used by BOTH headline and badge so a
    KCB-weak/novel cluster is never described as 'similar to X family' in one place and
    'KCB-dark' in another."""
    name, score = _kcb_named(bgc)
    nov = _num(bgc, "Novelty_auto")
    if score is None or nov is None:
        return "UNRESOLVED"
    if name and score >= 10000:
        return "LOW"
    if (not name) or score < 1500 or nov >= 60:
        return "HIGH"
    return "MODERATE"


def _badges(bgc: dict, poly: dict | None) -> dict:
    name, score = _kcb_named(bgc)
    ab, af = _num(bgc, "AB_auto"), _num(bgc, "AF_auto")
    boundary = (bgc.get("Boundary") or "").strip()
    over_merge = bool(poly and str(poly.get("over_merge_flag", "")).startswith("YES"))
    polymer = (poly.get("predicted_polymer") if poly else "") or ""

    tier = _novelty_tier(bgc, poly)
    novelty = {"LOW": "LOW (known — strong named-compound KCB)",
               "HIGH": "HIGH (KCB-dark / weak anchor)",
               "MODERATE": "MODERATE (known family)",
               "UNRESOLVED": "UNRESOLVED (invalid or missing KCB/novelty input)"}[tier]

    # Predicted activity (capacity-level, extract-level)
    if ab is None or af is None:
        activity = "UNRESOLVED (invalid or missing AB/AF routing prior)"
    elif af >= 60:
        activity = "HIGH antifungal (capacity)"
    elif ab >= 60:
        activity = "HIGH antibacterial (capacity)"
    elif max(ab, af) >= 45:
        activity = f"moderate (capacity; AB {ab:.0f}/AF {af:.0f})"
    else:
        activity = f"low-confidence (AB {ab:.0f}/AF {af:.0f})"

    # Tractability
    xheavy = polymer.count("X") >= max(3, polymer.count("-") // 2) if polymer else True
    if boundary == "Interior" and not over_merge and polymer and not xheavy:
        tract = "HIGH (Interior, single cluster, assembled)"
    elif boundary in ("Edge", "Full-contig") or over_merge or not polymer:
        reasons = []
        if boundary in ("Edge", "Full-contig"):
            reasons.append(f"{boundary} — truncated")
        if over_merge:
            reasons.append("over-merged — split first")
        if not polymer:
            reasons.append("no assembled polymer")
        tract = "LOW (" + "; ".join(reasons) + ")"
    else:
        tract = "MODERATE"

    # Action
    if over_merge:
        action = "run the two-model split before any product claim, then targeted LC-MS."
    elif boundary in ("Edge", "Full-contig"):
        action = "long-read finish to recover the full cluster before structural claims."
    elif tier == "UNRESOLVED" or ab is None or af is None:
        action = "hold routing interpretation until malformed or missing numeric inputs are resolved."
    elif name and score >= 10000:
        action = "confirm the known-family compound by bioassay + LC-MS (predicted mass in L1)."
    elif "HIGH" in novelty:
        action = "prioritise: activation + LC-MS; per-gene BLASTp to place it against uncharacterised relatives."
    else:
        action = "targeted LC-MS around the predicted product."
    return {"novelty": novelty, "activity": activity, "tractability": tract, "action": action}


def _headline(bgc: dict, poly: dict | None) -> str:
    products = (bgc.get("Products") or "").strip() or "cluster"
    name, _score = _kcb_named(bgc)
    tier = _novelty_tier(bgc, poly)
    if tier == "UNRESOLVED":
        return f"a {products} cluster with unresolved KCB/novelty inputs (capacity-level prediction)."
    if tier == "LOW" and name:
        return f"a {products} cluster of the {name.split('/')[0]} family (known-compound similarity)."
    if tier == "MODERATE" and name:
        return f"a {products} cluster, similar to the {name.split('/')[0]} family."
    return f"a {products} cluster with no strong known-metabolite match (capacity-level prediction)."


# ---- card rendering ------------------------------------------------------------------------------
def _locator(bgc: dict) -> str:
    node = (bgc.get("Contig") or "").split("_cov")[0]
    return f"{node} · {bgc.get('antiSMASH_Region', '')}".strip(" ·")


def build_card(bgc: dict, poly: dict | None, modules: list[dict], strain: str, version: str,
               contig_region_count: int, rescues: list | None = None,
               rescue_status=None) -> str:
    loc = _locator(bgc)
    b = _badges(bgc, poly)
    name, score = _kcb_named(bgc)
    polymer = (poly.get("predicted_polymer") if poly else "") or "(none assembled)"
    smiles = (poly.get("predicted_smiles") if poly else "") or ""
    mass = _mass_from_smiles(smiles)
    boundary = (bgc.get("Boundary") or "").strip()
    over = bool(poly and str(poly.get("over_merge_flag", "")).startswith("YES"))

    # L1 mass line
    if not smiles:
        mass_line = "Predicted mass: no SMILES for this region."
    elif mass["status"] == "ok":
        frag = " **(assembled polymer is partial — Edge/Full-contig; this is a fragment mass, not the compound)**" if boundary in ("Edge", "Full-contig") else ""
        mass_line = f"Predicted mass (from assembled SMILES): formula {mass['formula']}, monoisotopic **{mass['monoisotopic']} Da** ([M+H]+ {mass['m_plus_h']}).{frag}"
    else:
        mass_line = f"Predicted mass: pending — {mass['reason']}."

    # L2 module detail
    if modules:
        mr = "; ".join(f"{m['substrate']}({m['confidence'][:3]})" for m in modules[:14] if m.get("substrate"))
        nA = sum(1 for m in modules if m.get("domain_class") == "NRPS_A")
        nT = sum(1 for m in modules if m.get("domain_class") == "PKS_AT")
        multi = f" *(contig has {contig_region_count} regions; module list is contig-scoped — per-region coord scoping pending)*" if contig_region_count > 1 else ""
        mod_line = f"{len(modules)} substrate-selecting modules ({nA} NRPS-A + {nT} PKS-AT): {mr}.{multi}"
    else:
        mod_line = "no per-module substrate calls (non-NRPS/PKS, trans-AT, or unpredicted)."

    # v9.7.343 surfacing patch: the engine's already-computed capacity verdict
    # (Arch_Capacity/Class_Conf + Diagnostic-Rescue). Class-level capacity, not identity.
    cap = (bgc.get("Arch_Capacity") or bgc.get("Arch") or "").strip()
    conf = (bgc.get("Class_Conf") or "").strip()
    rescue_source_failed = (hasattr(rescue_status, "status")
                            and getattr(rescue_status, "status", "") not in ("ABSENT", "VALID"))
    if cap or conf or rescues or rescue_source_failed:
        rtxt = ""
        if rescue_source_failed:
            status = getattr(rescue_status, "status", "UNRESOLVED")
            error_type = getattr(rescue_status, "error_type", "") or "UNKNOWN"
            rtxt = (f"; Diagnostic-Rescue source: {status} ({error_type}) — evidence unresolved, "
                    "not absent")
        elif rescues:
            sup = [r for r in rescues if r.get("tiling_verdict", "").startswith("RECONSTRUCTION_SUPPORTED")]
            if sup:
                rtxt = f"; Diagnostic-Rescue: {len(sup)} engine-SUPPORTED split-pathway reconstruction(s) (homology-based hypothesis, not a contig join)"
            else:
                rtxt = f"; Diagnostic-Rescue: {len(rescues)} pairing(s) evaluated, none supported"
        cap_line = f"Engine capacity read (class-level, not identity): **{cap or '—'}** (class conf {conf or '—'}){rtxt}."
    else:
        cap_line = "Engine capacity read: none recorded."

    if score is None:
        kcb_line = (f"KCB `{name}` (score unresolved) — **similarity, not identity**"
                    if name else "KCB: unresolved (invalid or missing score)")
    else:
        kcb_line = (f"KCB `{name}` (score {score:.0f}) — **similarity, not identity**"
                    if name else "KCB: none (KCB-dark)")
    over_line = (f"**YES** — {poly.get('n_protoclusters')} protoclusters, kind `{poly.get('candidate_kind')}`"
                 if over else "no") if poly else "n/a"

    return f"""## {strain} · {loc} — {_headline(bgc, poly)} (engine id {bgc.get('BGC_ID','?')})

**L0 · Headline**
- **Predicted:** {_headline(bgc, poly)}
- **Badges:** Novelty **{b['novelty']}** · Predicted activity **{b['activity']}** · Tractability **{b['tractability']}**
- **Action:** {b['action']}

**L1 · Predicted molecule**
- Products: {bgc.get('Products','')}
- Predicted backbone: `{polymer}`
- {mass_line}
- Boundary: {boundary or 'n/a'}{' · over-merged (see L2)' if over else ''}

**L2 · Evidence (auto)**
- Per-module (antiSMASH-inferred specificity, similarity-level): {mod_line}
- {cap_line}
- Comparator: {kcb_line}
- Over-merge (antiSMASH kind/protocluster): {over_line}
- <!-- AUTHOR L2: per-gene BLASTp reconciliation, domain grammar, ecology -->

**L3 · Provenance & claim ceiling**
- Store-backed: triage scores, polymer/SMILES, KCB, boundary/over-merge (antiSMASH JSON/GBK, {version}).
- Not established: product identity, exact mass{'/structure (cluster truncated)' if boundary in ('Edge','Full-contig') else ''}, bioactivity phenotype (extract-level only).
- <!-- AUTHOR L3: reconstructed reads, claim-ceiling narrative -->
"""


# ---- package plumbing ----------------------------------------------------------------------------
def _load(path):
    return list(csv.DictReader(open(path, encoding="utf-8"))) if os.path.exists(path) else []


def _strain_from_pkg(pkg: str) -> str:
    for f in os.listdir(pkg):
        m = re.match(r"(.+?)_4_triage_board\.csv$", f)
        if m:
            return m.group(1)
    return os.path.basename(pkg.rstrip("/")) or "STRAIN"


def _bind_rescue_provider(package_dir: str):
    """Bind the bundled Diagnostic-Rescue reader without hiding import failures."""
    from . import card_verdicts
    return lambda bgc_id: card_verdicts.rescue_for_bgc_status(package_dir, bgc_id)


def render_report_cards(package_dir: str, bgc_id: str | None = None, out: str | None = None) -> dict:
    S = _strain_from_pkg(package_dir)
    tri = _load(os.path.join(package_dir, f"{S}_4_triage_board.csv"))
    poly = _load(os.path.join(package_dir, f"{S}_predicted_polymers.csv"))
    subs = _load(os.path.join(package_dir, f"{S}_nrps_prediction.csv"))
    # F09 (v9.7.353): derive engine identity from the sealed manifest, not a frozen literal.
    # The primary source is the package's manifest.json `workflow_version` (e.g. "Mamey v1.9.119").  version-sync-ok: illustrative format example, not a self-version claim
    # If the manifest is absent/unreadable, fall back to the LIVE engine __version__ so the label
    # tracks the running engine instead of a stale hard-coded "v1.9.110". (Previously _loadj raised
    # NameError — no module-scope json import — which the except swallowed, pinning the stale value.)
    from . import __version__ as _engine_version
    version = f"Mamey v{_engine_version}"
    manp = os.path.join(package_dir, "manifest.json")
    if os.path.exists(manp):
        try:
            manifest = _loadj(manp)
            if not isinstance(manifest, dict):
                version = f"Mamey v{_engine_version} (manifest invalid: root must be an object)"
            else:
                wv = manifest.get("workflow_version")
                if wv is not None and not isinstance(wv, str):
                    version = (f"Mamey v{_engine_version} "
                               "(manifest invalid: workflow_version must be a string)")
                elif wv:
                    version = wv
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            version = f"Mamey v{_engine_version} (manifest unreadable: {type(exc).__name__})"

    # index polymers by (contig, region_number); keep the longest polymer per region
    polymap: dict = {}
    for r in poly:
        key = (r.get("record_id"), str(r.get("region_number")))
        cur = polymap.get(key)
        if cur is None or len(r.get("predicted_polymer", "")) > len(cur.get("predicted_polymer", "")):
            polymap[key] = r
    # count regions per contig
    region_count: dict = {}
    for (contig, _rn) in polymap:
        region_count[contig] = region_count.get(contig, 0) + 1

    def _poly_for(bgc):
        contig = bgc.get("Contig")
        reg = re.sub(r"\D", "", bgc.get("antiSMASH_Region", "") or "") or "1"
        return polymap.get((contig, str(int(reg))))

    def _modules_for(bgc):
        m = re.search(r"NODE_(\d+)", bgc.get("Contig", "") or "")
        if not m:
            return []
        pref = f"ctg{m.group(1)}_"
        return [x for x in subs if x.get("locus_tag", "").startswith(pref)]

    def _rank(r):
        try:
            return int(r.get("Corrected_rank") or r.get("Rank") or 999)
        except Exception:
            return 999

    # v9.7.371 fix: was case-sensitive (unlike lead_pages.py:602, which normalizes --bgc with
    # .upper()). A user passing --bgc bgc001 against a board keyed BGC001 got a silent 0-card
    # result printed as if there genuinely were no cards for that ID, not an error.
    _bgc_id_norm = bgc_id.upper() if bgc_id else None
    rows = [b for b in tri if (_bgc_id_norm is None or (b.get("BGC_ID") or "").upper() == _bgc_id_norm)]
    rows.sort(key=_rank)
    # v9.7.343: pre-read Diagnostic-Rescue involvement per BGC (display-only).
    rescue_provider_note = ""
    try:
        _resc = _bind_rescue_provider(package_dir)
    except Exception as exc:
        _resc = lambda bid: []
        rescue_provider_note = (f"*RESCUE_PROVIDER_UNAVAILABLE: {type(exc).__name__}; Diagnostic-Rescue "
                                "evidence is unresolved, not absent.*\n\n")
    cards = []
    for b in rows:
        pr = _poly_for(b)
        rescue_read = _resc(b.get("BGC_ID") or b.get("bgc_id") or "")
        rescue_rows = getattr(rescue_read, "value", rescue_read)
        cards.append(build_card(b, pr, _modules_for(b), S, version,
                                region_count.get(b.get("Contig"), 1),
                                rescues=rescue_rows, rescue_status=rescue_read))
    body = (f"# {S} — Per-BGC Report Cards (L0–L3)\n\n"
            f"*Auto-rendered L0–L1 from the sealed package ({version}); L2/L3 carry auto comparators + "
            f"authoring slots. Claim-safe: capacity-level, KCB = similarity, bioactivity extract-level.*\n\n"
            + rescue_provider_note
            + "\n---\n\n".join(cards))
    written = None
    if out:
        # v9.7.409 (AUDIT_cli_edgecases): create parent dirs before open(out,"w"). Passing --out a
        # path inside a not-yet-existing folder used to crash with a raw FileNotFoundError; mode-b
        # handles the identical case by mkdir'ing its nested --outdir. Mirror that.
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(body)
        written = out
    return {"strain": S, "cards": len(cards), "with_polymer": sum(1 for b in rows if _poly_for(b)),
            "out": written, "markdown": body if not out else None}


def report_card_command(args) -> int:
    res = render_report_cards(args.package, getattr(args, "bgc", None), getattr(args, "out", None))
    if res.get("markdown"):
        emit(res["markdown"])
    else:
        emit(f"[report-card] {res['strain']}: {res['cards']} card(s) "
              f"({res['with_polymer']} with predicted polymer) -> {res['out']}")
    return 0
