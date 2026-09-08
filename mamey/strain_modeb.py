#!/usr/bin/env python3
# COPY / MIRROR — canonical handback: July 19 2026/strain_sapote.py
# (this is the live module the Lab Quest app imports; keep the two in sync)
"""
FULL STRAIN SAPOTE — strain-level Mode B generator
==================================================

The genome-side Sapote deliverable at the STRAIN altitude (above the per-BGC Mode B
cards). Reads a sealed Mamey package and emits the S1-S8 strain card defined in
`July 19 2026/STRAIN_MODE_B_TEMPLATE_from_bigscape_report.md`, filled with the real
deterministic numbers the engine already aggregated into `manifest.json` + the triage
board.

It is a *conversion*, not a new analysis: every number comes from Mamey (manifest /
triage / inventory / RG-GMCI). Sapote (the LLM, or a bench author) deepens the prose
in S4/S5/S8 afterward. This module writes the deterministic skeleton + the claim-safe
scaffolding; it never invents a number.

Layers, per the Mode B contract:
    antiSMASH  = raw detection      Mamey = deterministic (all numbers here)
    Sapote     = judgement (the prose the author adds on top)

Claim discipline (strain-wide, enforced in the emitted text):
    capacity-level only; KCB/MIBiG = similarity not identity; bioactivity metadata is optional
    (never per-BGC without fractionation); node.region on first BGC mention; fragmentation
    caveat up front; no compound-production claims; never call a strain activity-negative.

Usage:
    python strain_sapote.py --package <pkg_dir> [--out card.md]
    # or import build_strain_sapote(pkg_dir) -> (markdown_str, meta_dict)
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
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

try:
    import pandas as pd
except Exception:  # noqa: BLE001
    pd = None

# SSOT for the release tag: dedup_and_guard.derive_release (v9.7.236 PI decision —
# AS- is PUBLIC). Do not re-implement the AS->PRIVATE rule inline.
try:
    from .dedup_and_guard import derive_release
except ImportError:  # standalone `python strain_modeb.py`
    import os as _sm_os
    import sys as _sm_sys
    _sm_sys.path.insert(0, _sm_os.path.dirname(_sm_os.path.dirname(_sm_os.path.abspath(__file__))))
    from mamey.dedup_and_guard import derive_release  # type: ignore

# B7-b8 / Lab Quest (v9.7.405): permanent exact-locus display contract -- an individual BGC is
# named "strain / full node-or-contig / region / BGC alias" wherever this module displays one,
# never a bare alias or a short node token. See mamey/exact_identity.py for the fail-closed
# validation this delegates to.
try:
    from .exact_identity import ExactLocusIdentityError, exact_locus_from_mapping
except ImportError:  # standalone `python strain_modeb.py`
    import os as _identity_os
    import sys as _identity_sys
    _identity_sys.path.insert(0, _identity_os.path.dirname(_identity_os.path.dirname(_identity_os.path.abspath(__file__))))
    from mamey.exact_identity import ExactLocusIdentityError, exact_locus_from_mapping  # type: ignore


# ---- small helpers --------------------------------------------------------
def _clean(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("", "nan", "none", "null", "na") else s


def _cell(v) -> str:
    """Clean a value for a markdown table cell: kill pipes/newlines that break the table."""
    return _clean(v).replace("|", " · ").replace("\n", " ").strip()


def _rank(v) -> str:
    s = _clean(v)
    try:
        return str(int(float(s)))
    except (TypeError, ValueError):
        return s or "?"


def _load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def _load_csv(p: Path):
    if pd is None or not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:  # noqa: BLE001
        return None


def _pct(n, d) -> str:
    return f"{(100.0 * n / d):.0f}%" if d else "—"


def _col(df, *names):
    if df is None:
        return None
    for n in names:
        if n in df.columns:
            return n
    return None


_LEAD_TIER_DISPLAY = {
    "exceptional": "Exceptional", "high": "High", "medium": "Medium",
    "low": "Low", "inventory": "Inventory",
}


def _display_lead_tier(value) -> str:
    """Normalize only the five governed lead-tier labels; preserve unknowns."""
    text = _clean(value)
    return _LEAD_TIER_DISPLAY.get(text.lower(), text or "—")


def _identity_index(strain: str, tri) -> dict[str, str]:
    """Build alias -> exact-locus display for every triage row, fail closed (Lab Quest B7-b8)."""
    if tri is None:
        return {}
    identities: dict[str, str] = {}
    for row in tri.to_dict(orient="records"):
        alias = _clean(row.get("BGC_ID"))
        if not alias or alias in identities:
            raise ExactLocusIdentityError(f"missing or duplicated BGC alias in triage: {alias!r}")
        identities[alias] = exact_locus_from_mapping(strain, row)
    return identities


def _exact(identity_by_alias: dict[str, str], alias: object) -> str:
    key = _clean(alias)
    if key not in identity_by_alias:
        raise ExactLocusIdentityError(f"no exact four-part identity for BGC alias {key!r}")
    return identity_by_alias[key]


def _pair_aliases(candidate: dict) -> tuple[str, str]:
    """Resolve a governed split candidate without deriving identity from display text."""
    for a_key, b_key in (
        ("bgc_a", "bgc_b"), ("bgc_id_a", "bgc_id_b"),
        ("BGC_A", "BGC_B"), ("bgc1", "bgc2"),
    ):
        if _clean(candidate.get(a_key)) and _clean(candidate.get(b_key)):
            return _clean(candidate.get(a_key)), _clean(candidate.get(b_key))
    pair = _clean(candidate.get("pair"))
    import re
    aliases = re.findall(r"\bBGC\d+\b", pair, flags=re.IGNORECASE)
    if len(aliases) == 2:
        return aliases[0], aliases[1]
    raise ExactLocusIdentityError("split-pathway candidate lacks two explicit BGC aliases")


# ---- the generator --------------------------------------------------------
def build_strain_sapote(pkg_dir, cohort_summary=None) -> tuple[str, dict]:
    pkg = Path(pkg_dir)
    strain = pkg.parent.name if pkg.name == "package" else pkg.name
    man = _load_json(pkg / "manifest.json")
    strain = man.get("strain_id") or man.get("display_name") or strain
    intake = _load_json(pkg / f"{strain}_1_intake.json")
    tri = _load_csv(pkg / f"{strain}_4_triage_board.csv")
    identity_by_alias = _identity_index(strain, tri)

    asm = man.get("assembly", {}) or {}
    counts = man.get("bgc_counts", {}) or {}
    tier = counts.get("assembly_tier", "—")
    raw = counts.get("raw", "?")
    taxonomy = man.get("taxonomy", "—")
    source = man.get("source", "—")
    release = intake.get("release") or derive_release(strain)

    L: list[str] = []
    W = L.append
    meta: dict = {"strain": strain, "assembly_tier": tier, "n_bgc": raw}

    # ---- header -----------------------------------------------------------
    W(f"# Full Strain Sapote — {strain}  ·  strain-level Mode B")
    W("")
    W(f"*Genus/source:* **{taxonomy}** · {source} · release **{release}** · "
      f"engine {man.get('workflow_version','?')} · mode {man.get('mode','?')}")
    W("")
    W("> **Provenance.** Every number below is deterministic (Mamey: manifest / triage / "
      "RG-GMCI). Prose in S4/S5/S8 is the Sapote judgement layer to be authored on top. "
      "**Claim-safe:** capacity-level only · KCB/MIBiG = similarity, not identity · "
      "bioactivity metadata is optional strain-level context · no compound-production claims.")
    W("")

    # ---- S1 identity & assembly ------------------------------------------
    small = 0
    c_bd = _col(tri, "Boundary")
    if tri is not None:
        interior = int((tri[c_bd].astype(str).str.lower().eq("interior")).sum()) if c_bd else "—"
    else:
        interior = counts.get("interior", "—")
    genome_mb = (asm.get("genome_bp", 0) or 0) / 1e6
    W("## S1 · Strain identity & assembly quality  *[Mamey-auto]*")
    W("")
    W(f"- **BGC regions:** {raw} total · **assembly tier `{tier}`** · "
      f"interior {counts.get('interior','?')} / edge {counts.get('edge','?')} / "
      f"full-contig {counts.get('full_contig','?')} (interior {counts.get('interior_pct','?')}%)")
    W(f"- **Genome:** {genome_mb:.2f} Mb · {asm.get('contigs','?')} contigs · "
      f"N50 {asm.get('n50','?')} · GC {asm.get('gc_pct','?')}% · "
      f"largest contig {asm.get('largest_contig','?')} bp")
    W(f"- **⚠ Fragmentation caveat (read the whole card through this).** Assembly tier is "
      f"`{tier}`. Per-region hits are **fragments** until a contiguous assembly confirms them; "
      f"a 'best' region may be missing its own gateway or tailoring genes — those can sit on "
      f"another contig (see **S4**).")
    W("")

    # ---- S2 portfolio -----------------------------------------------------
    W("## S2 · Biosynthetic portfolio  *[Mamey-auto]*")
    W("")
    prods = Counter()
    for b in man.get("bgcs", []) or []:
        for p in (b.get("products") or []):
            prods[str(p)] += 1
    c_tier = _col(tri, "Lead_tier_auto", "Lead_tier")
    tier_hist = Counter()
    if tri is not None and c_tier:
        for t in tri[c_tier].astype(str):
            tier_hist[_display_lead_tier(t)] += 1
    meta["tier_hist"] = dict(tier_hist)
    if tier_hist:
        W("**Lead-tier histogram:** " + " · ".join(f"{k} {v}" for k, v in
          sorted(tier_hist.items(), key=lambda x: {
              "Exceptional": 0, "High": 1, "Medium": 2, "Low": 3, "Inventory": 4,
          }.get(x[0], 5))))
        W("")
    if prods:
        W("| class | count |")
        W("|---|--:|")
        for cls, n in prods.most_common(14):
            W(f"| {cls} | {n} |")
        W("")

    # ---- S3 believability leaderboard ------------------------------------
    W("## S3 · Believability leaderboard  *[Mamey-auto → pathway-logic extend]*")
    W("")
    W("Ranked by the engine's corrected triage rank; **believability** here is a "
      "boundary+architecture read (a placeholder for the committed-step class engine, "
      "`LQ-PATH-01`). Intact = complete core assembly line; fragment = edge/full-contig.")
    W("")
    if tri is not None:
        c_id = _col(tri, "BGC_ID")
        c_rank = _col(tri, "Corrected_rank", "Rank")
        c_prod = _col(tri, "Products")
        c_arch = _col(tri, "Arch_Capacity", "Arch")
        c_kcb = _col(tri, "KCB_top")
        c_conf = _col(tri, "Class_Conf")
        c_node = _col(tri, "Node_ID", "Contig")
        c_reg = _col(tri, "antiSMASH_Region")
        d = tri.sort_values(c_rank) if c_rank else tri
        W("| # | exact locus | class | tier | boundary | arch cap. | KCB (similarity) |")
        W("|--:|---|---|---|---|---|---|")
        for _, r in d.head(10).iterrows():
            bid = _cell(r.get(c_id))
            loc = _cell(_exact(identity_by_alias, bid))
            tval = _cell(r.get(c_tier))
            W(f"| {_rank(r.get(c_rank))} | {loc} | {_cell(r.get(c_prod))} | "
              f"{tval} | {_cell(r.get(c_bd))} | {_cell(r.get(c_arch))} | {_cell(r.get(c_kcb)) or '—'} |")
        W("")

    # ---- S4 split-pathway reassembly (NET-NEW) ----------------------------
    W("## S4 · Split-pathway reassembly  *[authored — NET-NEW; the fragmentation payoff]*")
    W("")
    spc = [c for c in (man.get("split_pathway_candidates") or [])
           if c.get("split_signature") or str(c.get("acceptance_gate", "")).startswith("OK")]
    meta["split_candidates"] = len(spc)
    if spc:
        W(f"**{len(spc)} candidate split pathway(s)** where two edge fragments on different "
          f"contigs share signature — likely one pathway fragmented by assembly, not two "
          f"independent clusters (fragment-surfacing: never demote a real core on a contig edge):")
        W("")
        W("| exact locus A | exact locus B | shared class | gate |")
        W("|---|---|---|---|")
        for c in spc[:12]:
            alias_a, alias_b = _pair_aliases(c)
            W(f"| {_cell(_exact(identity_by_alias, alias_a))} "
              f"| {_cell(_exact(identity_by_alias, alias_b))} "
              f"| {_clean(' '.join(c.get('shared_class_tokens', [])) if isinstance(c.get('shared_class_tokens'), list) else c.get('shared_class_tokens'))} "
              f"| {c.get('acceptance_gate','?')} |")
        W("")
        W("*Author task:* for each, state the most parsimonious reassembly and which gene "
          "(gateway / tailoring / ligase) is stranded on which contig. Cross-check RG-GMCI "
          "`_4A_RGGMCI_ranked_pairs.csv`.")
    else:
        W("_No split-pathway candidates flagged for this strain (or single-contig)._")
    W("")

    # ---- S5 cross-cluster & private chemistry -----------------------------
    W("## S5 · Cross-cluster interactions & private chemistry  *[Mamey + authored]*")
    W("")
    if cohort_summary is not None:
        # LQ-STRAIN-03: real cohort context from the BiG-SCAPE cohort (DB or portable TSV).
        from . import cohort_context as _cohort
        for line in _cohort.render_s5(cohort_summary, strain):
            W(line)
        meta["cohort"] = {k: cohort_summary.get(k) for k in
                          ("source", "n_with_gcf", "n_private", "n_shared", "n_known", "n_novel")}
    else:
        xs = man.get("cross_strain_context", {}) or {}
        related = xs.get("related_strains_in_master") or []
        shared = xs.get("shared_bgc_families") or []
        if xs.get("master_workbook") or related or shared:
            W(f"- **Cohort context:** {len(related)} related strain(s) in master; "
              f"{len(shared)} shared BGC family/families.")
            W("- *Author:* shared precursors / regulatory crosstalk across this strain's clusters; "
              "which families are this strain's **private chemistry** (no cohort peer).")
        else:
            W("_No cohort/master-workbook context in this package — pass `--cohort-db "
              "<full_cohort.db>` (or `--cohort-tsv`) to populate neighbours & private chemistry "
              "from the BiG-SCAPE cohort. Single-strain view otherwise._")
    W("")

    # ---- S6 AF/AM story ---------------------------------------------------
    W("## S6 · Strain antifungal / antibacterial story  *[Mamey + authored]*")
    W("")
    bio = man.get("bioactivity", {}) or {}
    c_ab, c_af = _col(tri, "AB_auto"), _col(tri, "AF_auto")
    c_std, c_pm = _col(tri, "Standing_rule"), _col(tri, "Primary_metab_flag")
    n_ab = n_af = 0
    if tri is not None:
        # AUDIT_374 fix: AB_auto/AF_auto carry an auto-floor and are observed to never
        # reach 0 in any real run (min AB_auto=25, min AF_auto=20 across every runs/*/package/
        # board checked) -- so an un-gated ">0" count is always exactly the raw BGC count, with
        # zero discriminating power, AND it launders standing-rule-excluded / primary-metabolism
        # -flagged rows (scoring.py::triage_bgcs's own gate, corrected_rank=None for these) into
        # a strain-wide "carries antibacterial/antifungal prior" headline the Sapote judgment
        # layer reads as signal. Live-verified on AS-XXX: n_ab=n_af=40=raw BGC count, 16/40 of
        # them standing-rule saccharide-exclusions. Excluding those two flagged classes at least
        # removes the known false-positive rows from this count; it is still a floor-inclusive
        # count, not a "meaningfully positive" one -- read alongside S3's corrected-rank board.
        included = tri
        if c_std:
            included = included[included[c_std].fillna("").astype(str).str.strip().eq("")]
        if c_pm:
            included = included[included[c_pm].fillna("").astype(str).str.strip().str.upper().ne("YES")]
        if c_ab:
            n_ab = int((pd.to_numeric(included[c_ab], errors="coerce").fillna(0) > 0).sum())
        if c_af:
            n_af = int((pd.to_numeric(included[c_af], errors="coerce").fillna(0) > 0).sum())
    meta["n_ab"], meta["n_af"] = n_ab, n_af
    W(f"- **Capacity:** {n_ab} BGC(s) carry antibacterial routing priors and {n_af} carry "
      f"antifungal routing priors (standing-rule/primary-metabolism-excluded BGCs not counted). "
      f"Bioactivity metadata state: `{bio.get('metadata_state','NOT_SUPPLIED')}`; this is not BGC-level evidence.")
    rgs = man.get("resistance_gene_summary", {}) or {}
    if rgs.get("tier_counts"):
        W(f"- **Self-resistance context:** {rgs.get('tier_counts')} (resistance genes co-located "
          "in BGCs hint at target class — handling & mechanism only, not a phenotype claim).")
    W("- *Author:* which classes drive the extract signal; class-in-Actinobacteria context "
      "from NP Atlas (aggregate class frequency only). **Never** call the strain activity-negative; "
      "never pin activity to one BGC without fractionation.")
    W("")

    # ---- S7 top leads & next actions --------------------------------------
    W("## S7 · Top leads & next actions for the strain  *[Mamey → authored ordering]*")
    W("")
    leads = []
    if tri is not None and c_tier:
        hi = tri[tri[c_tier].astype(str).str.lower().eq("high")]
        c_id = _col(tri, "BGC_ID"); c_prod = _col(tri, "Products")
        for _, r in hi.head(8).iterrows():
            exact = _exact(identity_by_alias, r.get(c_id))
            leads.append(f"**{exact}** ({_clean(r.get(c_prod))})")
    if leads:
        for i, ld in enumerate(leads, 1):
            W(f"**Action {i}.** Work up {ld} — Mode B card + per-gene BLASTp on the core.")
    else:
        W("_No High-tier leads; prioritise the top corrected-rank rows in S3._")
    steps = man.get("recommended_next_steps") or []
    for i, s in enumerate(steps[:5], len(leads) + 1):
        W(f"**Action {i}.** {s}")
    W("")

    # ---- S8 claim ceiling -------------------------------------------------
    W("## S8 · What cannot be claimed (strain level)  *[Mamey → Sapote deepens]*")
    W("")
    W(f"- Assembly tier `{tier}` — on a fragmented assembly, per-region completeness and any "
      "cross-contig reassembly (S4) are **hypotheses**, not established clusters.")
    W("- All compound/MIBiG names are **class-level** resemblances (KCB = similarity, not identity). "
      "No BGC → compound identity is asserted.")
    W("- Bioactivity is **extract-level** context (MRSA + Candida); it is not pinned to any single "
      "BGC without fractionation, and absence of recorded activity means nothing.")
    W("- Expression is **unknown** without culture data — the wet-lab wing (fermentation, LC-MS/HPLC, "
      "NMR) resolves what the genome can only propose.")
    W("")
    W(f"*Full Strain Sapote · {strain} · generated from the sealed package (deterministic skeleton; "
      "Sapote authoring deepens S4/S5/S8).*")

    return "\n".join(L), meta


# ---- strain-structure gate (LQ-STRAIN, sibling of modeb_structure_gate.py) -----------------------
# Validates that an emitted strain-level Mode B card carries the full S1–S8 contract and the
# claim-safety provenance block, so a truncated or mis-scaffolded strain card can't pass as complete.
REQUIRED_STRAIN_SECTIONS = [
    ("S1", "identity"), ("S2", "portfolio"), ("S3", "believability"),
    ("S4", "split-pathway"), ("S5", "cross-cluster"), ("S6", "antifungal"),
    ("S7", "leads"), ("S8", "cannot be claimed"),
]
_CLAIM_SAFE_MARKERS = ["capacity-level", "similarity", "extract-level"]


def validate_strain_card(md: str) -> tuple[int, list[str]]:
    """Return (rc, problems). rc=1 if the card is missing any S1–S8 section or the claim ceiling."""
    problems: list[str] = []
    low = md.lower()
    for tag, _kw in REQUIRED_STRAIN_SECTIONS:
        t = tag.lower()
        # emitted headers look like "## S1 · Strain identity …"; accept a space or "·" after the tag
        if f"## {t} " not in low and f"## {t}·" not in low:
            problems.append(f"MISSING_SECTION: {tag} header not found")
    missing_claim = [m for m in _CLAIM_SAFE_MARKERS if m not in low]
    if missing_claim:
        problems.append("CLAIM_CEILING_INCOMPLETE: provenance block missing markers "
                        f"{missing_claim} (capacity-level / similarity-not-identity / extract-level)")
    return (1 if problems else 0), problems


class StrainCitationReceiptError(ValueError):
    """Typed refusal when an S1-S8 node citation is not package-crosswalk bound."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_strain_citation_receipt(md: str, pkg_dir: str | Path) -> dict:
    """Bind every S1-S8 exact-locus citation to the package crosswalk.

    Sections without an individual locus receive an explicit
    ``NO_NODE_CITATIONS`` state; they are not treated as missing evidence.
    """
    pkg = Path(pkg_dir)
    manifest = _load_json(pkg / "manifest.json")
    strain = _clean(manifest.get("strain_id") or manifest.get("display_name"))
    if not strain:
        raise StrainCitationReceiptError("STRAIN_CITATION_STRAIN_MISSING")
    crosswalks = sorted(pkg.glob(f"{strain}_2b_bgc_crosswalk.csv"))
    if len(crosswalks) != 1:
        raise StrainCitationReceiptError(f"STRAIN_CITATION_CROSSWALK_COUNT: {len(crosswalks)}")
    crosswalk = crosswalks[0]
    with crosswalk.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"bgc_id", "node_id", "antismash_region"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise StrainCitationReceiptError("STRAIN_CITATION_CROSSWALK_COLUMNS")
        rows = list(reader)
    by_alias: dict[str, dict[str, str]] = {}
    for row in rows:
        alias = _clean(row.get("bgc_id"))
        if not alias or alias in by_alias:
            raise StrainCitationReceiptError(f"STRAIN_CITATION_CROSSWALK_ALIAS: {alias!r}")
        by_alias[alias] = row

    sections: list[dict] = []
    all_citations: list[dict] = []
    exact_pattern = re.compile(
        rf"{re.escape(strain)}\s*/\s*([^/\n|*]+?)\s*/\s*(region\d+)\s*/\s*(BGC\d+)",
        re.IGNORECASE,
    )
    for index, (tag, _label) in enumerate(REQUIRED_STRAIN_SECTIONS):
        next_tag = REQUIRED_STRAIN_SECTIONS[index + 1][0] if index + 1 < len(REQUIRED_STRAIN_SECTIONS) else None
        start = re.search(rf"^##\s+{tag}\b.*$", md, flags=re.MULTILINE | re.IGNORECASE)
        if start is None:
            raise StrainCitationReceiptError(f"STRAIN_CITATION_SECTION_MISSING: {tag}")
        if next_tag:
            end = re.search(rf"^##\s+{next_tag}\b.*$", md[start.end():], flags=re.MULTILINE | re.IGNORECASE)
            body = md[start.end():start.end() + end.start()] if end else md[start.end():]
        else:
            body = md[start.end():]
        citations: list[dict] = []
        exact_matches = list(exact_pattern.finditer(body))
        for match in exact_matches:
            node, region, alias = (_clean(match.group(1)), _clean(match.group(2)), _clean(match.group(3)).upper())
            row = by_alias.get(alias)
            if row is None or _clean(row.get("node_id")) != node or _clean(row.get("antismash_region")).casefold() != region.casefold():
                raise StrainCitationReceiptError(f"STRAIN_CITATION_CROSSWALK_MISMATCH: {tag} {alias}")
            canonical = f"{strain} / {node} / {_clean(row['antismash_region'])} / {alias}"
            row_hash = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            citation = {"exact_locus": canonical, "bgc_alias": alias, "node_id": node,
                        "region": _clean(row["antismash_region"]), "crosswalk_row_sha256": row_hash}
            citations.append(citation)
            all_citations.append({"section": tag, **citation})
        # A full node copied into authored prose outside a four-part identity is
        # still a citation and must not disappear from the receipt.  Known
        # crosswalk nodes must be inside a parsed exact citation; unknown NODE
        # shapes are a direct mismatch.
        exact_spans = [match.span() for match in exact_matches]
        for alias, row in by_alias.items():
            node = _clean(row.get("node_id"))
            for mention in re.finditer(re.escape(node), body):
                if not any(start <= mention.start() and mention.end() <= end for start, end in exact_spans):
                    raise StrainCitationReceiptError(
                        f"STRAIN_CITATION_INCOMPLETE_IDENTITY: {tag} {alias}"
                    )
        known_nodes = {_clean(row.get("node_id")) for row in by_alias.values()}
        for token in re.findall(r"\bNODE_\d+[A-Za-z0-9_.-]*", body, flags=re.IGNORECASE):
            if token not in known_nodes:
                raise StrainCitationReceiptError(f"STRAIN_CITATION_CROSSWALK_MISMATCH: {tag} {token}")
        sections.append({"section": tag, "state": "CROSSWALK_BOUND" if citations else "NO_NODE_CITATIONS",
                         "citation_count": len(citations), "citations": citations})
    return {
        "schema": "mamey_strain_modeb_s1_s8_citation_receipt_v1",
        "status": "PASS",
        "strain_id": strain,
        "card_sha256": hashlib.sha256(md.encode("utf-8")).hexdigest(),
        "crosswalk_file": crosswalk.name,
        "crosswalk_sha256": _sha256(crosswalk),
        "sections": sections,
        "citation_count": len(all_citations),
        "claim_ceiling": "Crosswalk identity binding only; not citation-quality, biological, release, or publication validation.",
    }


def register_subparser(sub):
    """Register the `emit-strain-modeb` post-seal subcommand (called from cli.py)."""
    sm = sub.add_parser("emit-strain-modeb",
                        help="emit the strain-level Mode B (Full Strain Sapote, S1–S8) deterministic "
                             "skeleton from a sealed package; non-blocking, structure-gated")
    sm.add_argument("--package", required=True, help="sealed package dir")
    sm.add_argument("--out", default=None, help="write markdown here (default: <pkg>/<strain>_strain_modeb.md)")
    sm.add_argument("--no-gate", action="store_true", help="skip the strain-structure gate check")
    sm.add_argument("--cohort-db", dest="cohort_db", default=None,
                    help="BiG-SCAPE cohort sqlite DB (full_cohort.db) — populates S5 cross-cluster / "
                         "private chemistry with co-members + nearest-MIBiG (LQ-STRAIN-03)")
    sm.add_argument("--cohort-tsv", dest="cohort_tsv", default=None,
                    help="portable cohort TSV fallback (no co-members; used when no --cohort-db)")
    sm.add_argument("--cutoff", default="0.5", help="BiG-SCAPE GCF cutoff to read (default 0.5)")
    sm.add_argument("--mibig-index", dest="mibig_index", default=None,
                    help="optional MIBiG reference index JSON to name nearest-MIBiG hits")
    sm.set_defaults(func=run_from_args)
    return sm


def run_from_args(args) -> int:
    pkg = Path(args.package)
    cohort_summary = None
    if getattr(args, "cohort_db", None) or getattr(args, "cohort_tsv", None):
        from . import cohort_context as _cohort
        man = _load_json(pkg / "manifest.json")
        strain = man.get("strain_id") or man.get("display_name") or (pkg.parent.name if pkg.name == "package" else pkg.name)
        cohort_summary = _cohort.strain_cohort_summary(
            pkg, strain, cohort_db=args.cohort_db, cohort_tsv=args.cohort_tsv,
            cutoff=getattr(args, "cutoff", "0.5"), mibig_index=getattr(args, "mibig_index", None))
        if cohort_summary is None:
            emit("  cohort: no GCF placement found for this strain in the given cohort source "
                  "(S5 stays single-strain)")
    md, meta = build_strain_sapote(pkg, cohort_summary=cohort_summary)
    strain = meta.get("strain", "strain")
    out = args.out or str(pkg / f"{strain}_strain_modeb.md")
    receipt = build_strain_citation_receipt(md, pkg)
    out_path = Path(out)
    receipt_path = out_path.with_suffix(out_path.suffix + ".citation_receipt.json")
    out_path.write_text(md, encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    emit(f"strain Mode B -> {out}  ({meta})", f"  S1-S8 citation receipt -> {receipt_path}", sep="\n")
    if not getattr(args, "no_gate", False):
        rc, problems = validate_strain_card(md)
        if problems:
            emit("  strain-structure gate: ISSUES (non-blocking) —")
            for p in problems:
                emit("    " + p)
        else:
            emit("  strain-structure gate: OK (S1–S8 present; claim ceiling complete)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True, help="sealed package dir")
    ap.add_argument("--out", default=None, help="write markdown here")
    ap.add_argument("--no-gate", action="store_true")
    a = ap.parse_args()
    return run_from_args(a)


if __name__ == "__main__":
    raise SystemExit(main())
