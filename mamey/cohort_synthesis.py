"""cohort_synthesis.py — Gap 3: deterministic cross-strain synthesis writer.

THE GAP THIS FILLS
------------------
The cohort figures and sheets exist, but nothing turns them into the methods-paper "cross-strain
results" prose. This reads the VERIFIED cohort master and emits that synthesis deterministically:
cohort composition, convergent capacities, host-biased classes, the novelty gradient, the
cohort-unique differentiating leads, and genus signatures. Capacity-level throughout; every number
traces to a named sheet.

THE novelty_basis PARAMETER (the reason this module is careful)
--------------------------------------------------------------
"Reference-dark" has two legitimate definitions that differ by >2x on this cohort:
  - "fully_dark"          : no MIBiG anchor at all (the B1 `kcb_top` field is not a BGC####### accession)
                            -> 164/1131 (15%) on the 24-strain cohort; matches the
                               Cross_Strain_Findings "fully KCB-dark" column.
  - "dark_or_unresolved"  : also counts BGCs whose KCB hit is only a bare genome reference
                            (no MIBiG accession) -> 423/1131 (37%); the broader novelty signal.
Reporting 37% against a sheet that means 15% is a silent wrong-answer. So EVERY novelty number this
writer emits is tagged with its basis, and `novelty_basis` (default "fully_dark", matching the
canonical sheet) selects which definition the headline numbers use. The non-selected figure is
still reported, explicitly labeled, so the two are never conflated.

DETERMINISTIC. No scoring change. PRIVATE by construction (cohort spans AS strains).
DEPENDENCY: a verified master (DAPR populated, Cross_Strain_Findings recomputed, denominator
invariant holding). On a stale master it refuses rather than emitting wrong prose.
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
import re
from pathlib import Path
from collections import defaultdict, Counter
from openpyxl import load_workbook

_MIBIG_RE = re.compile(r"\bBGC\d{7}\b")  # a real MIBiG accession in KCB_Top_Hit

# host grouping from a free-text host field
# --- ubiquitous-class exclusion sets (Bunny Hop v9.7.119) -------------------
# These two sets intentionally DIFFER. Keep them named and commented so a future
# editor does not "unify" them and silently break genus signatures.
#
# _DIFF_UBIQ: classes excluded from cohort-unique DIFFERENTIATING-lead detection.
#   Broader — ectoine/melanin/terpene-precursor are too common across genera to
#   mark a strain as a *differentiator* even when only one strain carries them.
# _GENUS_UBIQ: classes excluded from GENUS-SIGNATURE display (§6). Smaller —
#   ectoine/melanin ARE retained as signatures because e.g. "all Pseudonocardia
#   make ectoine" is a real genus finding.
_DIFF_UBIQ = {"other", "saccharide", "fatty_acid", "terpene", "NI-siderophore",
              "NRP-metallophore", "ectoine", "melanin", "terpene-precursor",
              "RiPP", "NRPS", "PKS", "T1PKS", "NRPS-like", "PKS-like", "RiPP-like"}
_GENUS_UBIQ = {"other", "saccharide", "fatty_acid", "terpene", "RiPP", "NRPS",
               "PKS", "T1PKS", "NRPS-like", "PKS-like", "RiPP-like",
               "NI-siderophore", "NRP-metallophore"}


def meta_from_differentiating_csv(csv_path: str | Path) -> dict:
    """Build {strain: {"genus":..., "host":...}} from a differentiating-capacities CSV.

    Used to populate genus/host when the master registry's taxonomy columns are unpopulated. The CSV
    typically covers only the strains that carry a differentiating capacity (a subset of the cohort),
    so the resulting genus signatures / host gradient are over the covered subset — the writer states
    this coverage rather than implying the full cohort.
    """
    import csv as _csv
    meta = {}
    p = Path(csv_path)
    if not p.exists():
        return meta
    with open(p, newline="") as f:
        for row in _csv.DictReader(f):
            sid = (row.get("strain") or "").strip()
            if not sid:
                continue
            meta[sid] = {"genus": (row.get("genus") or "").strip(),
                         "host": (row.get("host") or "").strip()}
    return meta


def _host_group(h: str) -> str:
    h = (h or "").lower()
    if "bombus" in h: return "Bombus"
    if any(x in h for x in ("attine", "acromyrmex", "atta")): return "Attine"
    if "apis" in h: return "Apis"
    if "wasp" in h or "vespid" in h: return "Wasp"
    if "moss" in h or "bryo" in h: return "Moss"
    if "apidae" in h: return "Other Apidae"
    return "Other"


def _is_fully_dark(kcb_top: str) -> bool:
    """fully-dark = NO knownclusterblast hit at all (empty KCB_Top_Hit).

    On the verified master this reproduces 164/1131 (15%) and matches both the manifest
    `no kcb_top` count and the Cross_Strain_Findings 'fully KCB-dark' column.
    """
    s = str(kcb_top or "").strip()
    return s == "" or s.lower() == "none"


def _is_dark_or_unresolved(kcb_top: str) -> bool:
    """broader = no MIBiG accession in the hit (empty OR a bare genome-reference hit).

    On the verified master this reproduces 423/1131 (37%) — the 164 empty plus the 259
    bare-genome-reference hits that never resolved to a MIBiG cluster.
    """
    s = str(kcb_top or "").strip()
    if s == "" or s.lower() == "none":
        return True
    return not bool(_MIBIG_RE.search(s))


# COH-02: the registry/BGC columns are resolved against the REAL master_workbook schema
# (mamey/master_workbook.py::CANONICAL_V1_HEADERS), NOT capitalized display names. The previous
# version resolved by keys ("KCB_Top_Hit", "Products", "Genus", "Corrected_BGCs") that do NOT exist
# in a real master, then fell back to fixed POSITIONAL indices that landed on the wrong columns
# (KCB_Top_Hit->products, Products->a coordinate, Genus->ecology_source, Corrected_BGCs->top_ab_bgc)
# — emitting confident WRONG prose on a real master while a fixture with the same fake headers hid
# it. We now resolve by the real lowercase headers and RAISE on a missing required column rather
# than silently mis-reading a positional fallback.
_A2_REQUIRED = ("strain", "taxonomy", "ecology_source")
_B1_REQUIRED = ("strain", "products", "kcb_top")
_UNPOPULATED_TAX = ("", "not", "not verified", "none", "—", "unresolved", "unknown")


def _genus_from_taxonomy(tax) -> str:
    """Genus = first token of the taxonomy string. 'Streptomyces sp.' -> 'Streptomyces'.

    The shipped A2_Strain_Registry has no dedicated Genus column — it carries `taxonomy`
    (e.g. 'Streptomyces sp.'), so genus is derived from it. Returns '' for empty/placeholder
    taxonomy so the meta-override path can supply genus."""
    s = str(tax or "").strip()
    if s.lower() in _UNPOPULATED_TAX:
        return ""
    toks = s.split()
    if toks[0].lower() == "candidatus" and len(toks) > 1:
        return toks[1]
    return toks[0]


def _resolve_headers(ws, required, sheet_name: str) -> dict:
    """Return {header_name: col_index} for a worksheet's header row.

    Raises RuntimeError if any required column is absent. NO positional fallback — a real master
    always ships the CANONICAL_V1_HEADERS columns; a master lacking them is stale/foreign and must
    refuse rather than mis-read a coordinate as a compound name (COH-02)."""
    row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    header = [str(x) if x is not None else "" for x in row]
    idx = {name: i for i, name in enumerate(header) if name}
    missing = [c for c in required if c not in idx]
    if missing:
        raise RuntimeError(
            f"master sheet {sheet_name} is missing required column(s) {missing} "
            f"(present headers: {header}). This master does not match the shipped master_workbook "
            f"schema; refusing to emit cross-strain prose from a foreign/stale schema (COH-02)."
        )
    return idx


def load_master(master_path: str | Path, host_overrides: dict | None = None,
                meta_overrides: dict | None = None) -> dict:
    """Read the verified master into the structures the writer needs. Returns {} if stale.

    Columns are resolved against the shipped master_workbook schema (CANONICAL_V1_HEADERS):
    A2_Strain_Registry has `strain, taxonomy, ecology_source, habitat, …, n50, bgc_count, …`
    (genus is derived from `taxonomy`, host from `ecology_source`); B1_BGC_Master has
    `strain, …, products, boundary, arch, kcb_top, …`. A master missing a required column RAISES.

    host_overrides: legacy {strain: host} map (kept for back-compat).
    meta_overrides: {strain: {"genus": ..., "host": ...}} — used when the master registry's
    `taxonomy`/`ecology_source` columns are unpopulated (some cuts ship a structural registry
    without taxonomy). The differentiating-capacities CSV is the usual source; see
    meta_from_differentiating_csv()."""
    from .xlsx_determinism import guard_workbook_size as _guard_xlsx  # v9.7.410: shared-strings still inflate under read_only
    _guard_xlsx(master_path)
    wb = load_workbook(Path(master_path), read_only=True, data_only=True)
    sheets = set(wb.sheetnames)
    # F4 fix: the dedicated Cross_Strain_Class_Prevalence sheet is only added post-hoc by
    # tools/add_xstrain_sheets.py; a plain gold-run master never has it. But the equivalent
    # per-class strain counts live in B2_Product_Class_Matrix, which master_workbook.py writes
    # into EVERY base master. Accept either, and derive prevalence from B2 when the dedicated
    # sheet is absent (see below) so `mamey cohort` works on a bare gold master.
    required = {"A2_Strain_Registry", "B1_BGC_Master"}
    has_prevalence = ("Cross_Strain_Class_Prevalence" in sheets) or ("B2_Product_Class_Matrix" in sheets)
    if not (required <= sheets and has_prevalence):
        return {}
    meta_overrides = meta_overrides or {}

    # registry: strain -> genus/host/n50/bgc_count (resolved by real lowercase headers)
    reg = {}
    ws = wb["A2_Strain_Registry"]
    gi = _resolve_headers(ws, _A2_REQUIRED, "A2_Strain_Registry")
    si = gi["strain"]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or si >= len(r) or not r[si]:
            continue
        sid = r[si]
        ov = meta_overrides.get(sid, {})
        reg_genus = _genus_from_taxonomy(r[gi["taxonomy"]] if gi["taxonomy"] < len(r) else "")
        # a registry whose taxonomy is unpopulated ("", "not", …) yields no genus → prefer the override
        if not reg_genus:
            reg_genus = ov.get("genus", "")
        host = (host_overrides or {}).get(sid) or ov.get("host") \
            or (r[gi["ecology_source"]] if gi["ecology_source"] < len(r) else "") or ""
        reg[sid] = {
            "genus": reg_genus,
            "host": host,
            "host_group": _host_group(host),
            "n50": r[gi["n50"]] if "n50" in gi and gi["n50"] < len(r) else None,
            "corrected": r[gi["bgc_count"]] if "bgc_count" in gi and gi["bgc_count"] < len(r) else None,
        }
    N = len(reg)

    # prevalence — prefer the dedicated sheet; else derive it from B2_Product_Class_Matrix (F4 fix)
    prevalence = {}
    if "Cross_Strain_Class_Prevalence" in sheets:
        ws = wb["Cross_Strain_Class_Prevalence"]
        h = [str(x) for x in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
        pi = {k: h.index(k) for k in h}
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or not r[pi.get("product_class", 0)]:
                continue
            cls = str(r[pi["product_class"]])
            prevalence[cls] = {
                "n_strains": int(r[pi["n_strains"]]) if r[pi["n_strains"]] is not None else 0,
                "band": str(r[pi.get("band", -1)]) if "band" in pi else "",
                # AUDIT_374: was `r[pi.get("informative_for_comparison", -1)]` unguarded —
                # when that column is absent (a foreign/older-schema prevalence sheet), the -1
                # sentinel is not "missing", it is a valid Python index: it silently read whatever
                # value sits in the sheet's LAST column (e.g. a notes field) instead of refusing or
                # defaulting. Mirror the "band" field's own `if "X" in pi` guard immediately above;
                # default to non-informative (claim-safe: never let an absent column spuriously
                # promote a class into the host-bias/differentiator signal in §3).
                "informative": (str(r[pi["informative_for_comparison"]]).lower().startswith("yes")
                                if "informative_for_comparison" in pi else False),
            }
    else:
        # derive from the strain×class count matrix: n_strains = # strains with a nonzero count
        ws = wb["B2_Product_Class_Matrix"]
        h = [str(x) for x in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
        class_cols = [(i, c) for i, c in enumerate(h)
                      if c not in ("strain", "label_provenance", "counts_reliability")]
        counts = {c: 0 for _, c in class_cols}
        provenance_i = h.index("label_provenance") if "label_provenance" in h else None
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or not r[0]:
                continue
            if provenance_i is not None and str(r[provenance_i]).upper() != "GENE_BACKED":
                continue
            for i, c in class_cols:
                v = r[i] if i < len(r) else 0
                try:
                    if v is not None and float(v) > 0:
                        counts[c] += 1
                except (TypeError, ValueError):
                    continue
        for cls, ns in counts.items():
            if ns == 0:
                continue
            frac = ns / N if N else 0
            band = ("ubiquitous" if N and ns == N else "common" if frac >= 0.5
                    else "occasional" if frac >= 0.2 else "rare")
            prevalence[cls] = {"n_strains": ns, "band": band,
                               "informative": 1 <= ns < N}  # differentiates when not carried by all

    # B1: per-BGC for novelty, joined to host via registry (resolved by real lowercase headers)
    bgcs = []
    ws = wb["B1_BGC_Master"]
    bi = _resolve_headers(ws, _B1_REQUIRED, "B1_BGC_Master")
    b_strain, b_kcb, b_products = bi["strain"], bi["kcb_top"], bi["products"]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or b_strain >= len(r) or not r[b_strain]:
            continue
        sid = r[b_strain]
        kcb = r[b_kcb] if b_kcb < len(r) else ""
        products = r[b_products] if b_products < len(r) else ""
        bgcs.append({
            "strain": sid,
            "host_group": reg.get(sid, {}).get("host_group", "Other"),
            "genus": reg.get(sid, {}).get("genus", ""),
            "products": str(products or ""),
            "fully_dark": _is_fully_dark(kcb),
            "dark_or_unresolved": _is_dark_or_unresolved(kcb),
        })

    return {"registry": reg, "N": N, "prevalence": prevalence, "bgcs": bgcs}


def novelty_by_host(bgcs: list, basis: str) -> dict:
    """KCB-dark fraction per host group under the chosen basis. Returns {host: (pct, n)}."""
    assert basis in ("fully_dark", "dark_or_unresolved")
    by = defaultdict(list)
    for b in bgcs:
        by[b["host_group"]].append(b[basis])
    return {hg: (sum(v) / len(v) * 100, len(v)) for hg, v in by.items() if v}


def differentiating_capacities(prevalence: dict) -> list:
    """Classes carried by exactly one strain (cohort-unique), excluding backbone/ubiquitous."""
    return sorted(c for c, p in prevalence.items() if p["n_strains"] == 1 and c not in _DIFF_UBIQ)


def write_synthesis(master_path: str | Path, novelty_basis: str = "fully_dark",
                    host_overrides: dict | None = None,
                    meta_overrides: dict | None = None) -> str:
    """Emit the cross-strain synthesis markdown. Raises on a stale/unverified master."""
    if novelty_basis not in ("fully_dark", "dark_or_unresolved"):
        raise ValueError(f"novelty_basis must be 'fully_dark' or 'dark_or_unresolved', got {novelty_basis!r}")
    M = load_master(master_path, host_overrides, meta_overrides)
    if not M:
        raise RuntimeError(f"master {master_path} is missing required sheets or is stale; refusing to write")
    reg, N, prev, bgcs = M["registry"], M["N"], M["prevalence"], M["bgcs"]
    total_bgc = len(bgcs)
    # v9.7.117 (Bug Hunt): a master whose required sheets are present but B1_BGC_Master is empty
    # (header-only scaffold) passes the load_master sheet check but would ZeroDivisionError on the
    # novelty-fraction math. Refuse cleanly, same contract as the stale-master refusal above.
    if total_bgc == 0:
        raise RuntimeError(f"master {master_path} has an empty B1_BGC_Master (0 BGCs); "
                           "refusing to write a synthesis with no cohort data")

    # novelty under BOTH bases, headline = chosen
    nov_chosen = novelty_by_host(bgcs, novelty_basis)
    other_basis = "dark_or_unresolved" if novelty_basis == "fully_dark" else "fully_dark"
    chosen_total = sum(b[novelty_basis] for b in bgcs)
    other_total = sum(b[other_basis] for b in bgcs)

    genera = Counter(v["genus"] for v in reg.values())
    hosts = Counter(v["host_group"] for v in reg.values())
    diff_caps = differentiating_capacities(prev)

    L = []
    L.append("# Cross-Strain Biosynthetic Synthesis (auto-generated)")
    L.append("")
    L.append(f"**Cohort:** {N} strains · {total_bgc} BGCs · {len(genera)} genera · {len(hosts)} host groups  ")
    L.append(f"**Novelty basis:** `{novelty_basis}` "
             f"({'no MIBiG anchor at all' if novelty_basis=='fully_dark' else 'no MIBiG accession incl. unresolved genome-ref hits'})  ")
    L.append("**Source:** verified cohort master · capacity-level (KCB = similarity, not identity) · "
             "bioactivity extract-level · PRIVATE (unpublished AS strains)")
    L.append("")
    L.append("All numbers trace to named master sheets. Every reference-dark number is tagged with its "
             "basis; the alternate definition is reported alongside so the two are never conflated.")
    L.append("")

    # 1. composition
    L.append("## 1. Cohort composition")
    L.append(f"{N} strains across {len(genera)} genera "
             f"({', '.join(f'{g} ×{n}' for g, n in genera.most_common(5))}…) and {len(hosts)} host "
             f"groups ({', '.join(f'{h} ×{n}' for h, n in hosts.most_common())}). "
             f"{total_bgc} BGCs detected. [A2_Strain_Registry, B1_BGC_Master]")
    L.append("")

    # 2. convergent iron
    sider = prev.get("NI-siderophore", {}).get("n_strains", 0)
    metal = prev.get("NRP-metallophore", {}).get("n_strains", 0)
    L.append("## 2. Convergent capacities (down-weighted as differentiators)")
    L.append(f"Iron acquisition is near-universal: NI-siderophore in {sider}/{N} strains, "
             f"NRP-metallophore in {metal}/{N}. Per the standing exclusion rule these are treated as "
             f"convergent cohort-ubiquitous capacities, not differentiating signals — the convergence "
             f"itself is the finding. [Cross_Strain_Class_Prevalence]")
    L.append("")

    # 3. host-biased
    L.append("## 3. Host-biased capacities")
    host_class = defaultdict(Counter)
    for b in bgcs:
        for c in re.split(r"[;,]", b["products"]):
            c = c.strip()
            if c and c in prev and prev[c]["informative"]:
                host_class[c][b["host_group"]] += 1
    biased = []
    for c, dist in host_class.items():
        tot = sum(dist.values())
        if tot < 4:
            continue
        top, n = dist.most_common(1)[0]
        # COH-05: no host allowlist. The old `and top in ("Bombus", "Attine")` made
        # Apis/Wasp/Moss/Other-Apidae host-specialization structurally unreportable. The
        # 55%-of-≥4-BGCs threshold already guards significance for ANY host group.
        if n / tot >= 0.55:
            biased.append((c, top, n, tot))
    if biased:
        for c, top, n, tot in sorted(biased, key=lambda x: -x[3])[:8]:
            L.append(f"- **{c}** — {n/tot:.0%} {top}-associated ({n}/{tot} BGCs)")
    else:
        L.append("- (No class exceeded the 55% host-bias threshold at n≥4.)")
    L.append("")

    # 4. novelty gradient (THE basis-tagged section)
    L.append(f"## 4. Novelty gradient by host (basis: `{novelty_basis}`)")
    L.append(f"Cohort reference-dark total: **{chosen_total}/{total_bgc} "
             f"({chosen_total/total_bgc*100:.0f}%)** under `{novelty_basis}`; "
             f"for comparison, `{other_basis}` gives {other_total}/{total_bgc} "
             f"({other_total/total_bgc*100:.0f}%). The two are different metrics — do not mix.")
    L.append("")
    L.append("| Host group | dark % | n BGCs |")
    L.append("|---|---|---|")
    for hg, (pct, n) in sorted(nov_chosen.items(), key=lambda x: x[1][0]):
        L.append(f"| {hg} | {pct:.1f}% | {n} |")
    L.append("")

    # 5. differentiating capacities
    L.append("## 5. Cohort-unique differentiating capacities")
    L.append(f"{len(diff_caps)} classes carried by exactly one strain — the discovery-frontier leads:")
    L.append("")
    for c in diff_caps:
        # token-split match (not bare substring) so "lanthipeptide" does not
        # false-match "class-i-lanthipeptide"; mirrors the split used in §3 and §6.
        carrier = next(
            (b["strain"] for b in bgcs
             if c in [t.strip() for t in re.split(r"[;,]", b["products"])]),
            "?")
        L.append(f"- **{c}** → {carrier} (*{reg.get(carrier, {}).get('genus','')}*, "
                 f"{reg.get(carrier, {}).get('host_group','')})")
    L.append("")

    # 6. genus signatures
    L.append("## 6. Genus signatures")
    genus_class = defaultdict(Counter)
    UBIQ = _GENUS_UBIQ
    _UNRESOLVED_GENUS = {"", "not", "not verified", "none", "—", "unresolved"}
    for b in bgcs:
        for c in re.split(r"[;,]", b["products"]):
            c = c.strip()
            if c and c not in UBIQ:
                genus_class[b["genus"]][c] += 1
    resolved = [g for g in sorted(genus_class) if str(g).strip().lower() not in _UNRESOLVED_GENUS]
    n_unresolved = sum(1 for g in genus_class if str(g).strip().lower() in _UNRESOLVED_GENUS)
    if resolved:
        for genus in resolved:
            top = [(c, n) for c, n in genus_class[genus].most_common(4)]
            if top:
                L.append(f"- **{genus}**: {', '.join(f'{c} ({n})' for c, n in top)}")
        if n_unresolved:
            L.append(f"- *(Strains without a genus assignment are omitted; genus signatures cover "
                     f"only the taxonomy-assigned subset. Provide genus for all {N} strains to "
                     f"complete this section.)*")
    else:
        L.append("*Genus is not populated for any strain in this master (registry taxonomy empty "
                 "and no override supplied); per-genus signatures require strain genus assignments.*")
    L.append("")
    L.append("---")
    L.append(f"*Auto-generated from the verified cohort master. novelty_basis=`{novelty_basis}`. "
             f"Capacity-level; KCB = similarity not identity; bioactivity extract-level.*")
    return "\n".join(L)


def load_from_capacity_csv(csv_path):
    """Load cohort data from a CCSM capacity-integration CSV (no master workbook required).

    Schema: strain, genus, host, host_group, total_bgcs_raw, deeply_carded, pct_carded,
    analytical_depth, n_xstrain_flags, [class_flag_cols...]. Returns a minimal M dict
    compatible with write_synthesis_from_capacity_csv. This is the no-workbook path.
    """
    import csv as _csv
    with open(Path(csv_path), encoding="utf-8", newline="") as _fh:
        rows = list(_csv.DictReader(_fh))
    if not rows:
        return {}
    if "strain" not in rows[0]:
        raise ValueError(
            f"capacity CSV {csv_path!r} is missing a required 'strain' column; "
            f"found columns: {list(rows[0].keys())}")
    meta_cols = {"strain", "genus", "host", "host_group", "total_bgcs_raw",
                 "deeply_carded", "pct_carded", "analytical_depth", "n_xstrain_flags"}
    class_cols = [k for k in rows[0].keys() if k not in meta_cols]
    reg = {}
    class_by_strain = {}
    for r in rows:
        sid = r["strain"]
        reg[sid] = {
            "genus": r.get("genus", ""),
            "host": r.get("host", ""),
            "host_group": r.get("host_group") or _host_group(r.get("host", "")),
        }
        class_by_strain[sid] = {c: int(r.get(c, 0) or 0) for c in class_cols}
    N = len(reg)
    prevalence = {}
    for c in class_cols:
        n = sum(class_by_strain[s].get(c, 0) for s in class_by_strain)
        prevalence[c] = {"n_strains": n, "informative": n > 0 and n < N}
    return {"registry": reg, "N": N, "prevalence": prevalence,
            "class_by_strain": class_by_strain, "class_cols": class_cols}


def write_synthesis_from_capacity_csv(csv_path):
    """Emit a cross-strain synthesis from the capacity integration CSV (no master required).

    Covers cohort composition, class landscape, cohort-unique capacities, genus signatures.
    Does NOT cover the novelty gradient (requires B1_BGC_Master) — states the absence explicitly.
    """
    M = load_from_capacity_csv(csv_path)
    if not M:
        raise RuntimeError(f"Could not load capacity CSV from {csv_path}")
    reg = M["registry"]; N = M["N"]; prev = M["prevalence"]
    class_by_strain = M["class_by_strain"]; class_cols = M["class_cols"]
    from collections import Counter as _Counter
    genera = _Counter(v["genus"] for v in reg.values())
    hosts = _Counter(v["host_group"] for v in reg.values())
    L = []
    L.append("# Cross-Strain Capacity Synthesis (from capacity CSV)")
    L.append("")
    L.append(f"**Cohort:** {N} strains \u00b7 {len(genera)} genera \u00b7 {len(hosts)} host groups  ")
    L.append("**Source:** CCSM capacity integration CSV \u00b7 class presence flags (not corrected BGC counts)  ")
    L.append("**Note:** Novelty gradient (KCB-dark %) requires the master workbook B1_BGC_Master sheet \u2014 absent here.  ")
    L.append("**PRIVATE** \u2014 unpublished AS strains \u00b7 capacity-level throughout")
    L.append("")
    L.append("## 1. Cohort composition")
    L.append(f"{N} strains \u00b7 {len(genera)} genera: "
             f"{', '.join(f'*{g}* \u00d7{n}' for g, n in genera.most_common(6))}\u2026  ")
    L.append(f"Host groups: {', '.join(f'{h} n={n}' for h, n in hosts.most_common())}")
    L.append("")
    L.append("## 2. Class landscape (strain-presence counts)")
    L.append("")
    # FIG-02: derive host-group columns from the data (preferred order first, then any others
    # sorted) so host groups outside the hardcoded list are no longer silently dropped.
    _pref = ["Bombus", "Attine", "Wasp", "Apis", "Other Apidae", "Moss"]
    _seen = {reg[s]["host_group"] for s in class_by_strain}
    hg_order = [h for h in _pref if h in _seen] + sorted(_seen - set(_pref))
    L.append("| Class | n/" + str(N) + " | " + " | ".join(hg_order) + " |")
    L.append("|" + "|".join(["---"] * (len(hg_order) + 2)) + "|")
    for c in sorted(class_cols, key=lambda x: -prev[x]["n_strains"]):
        n = prev[c]["n_strains"]
        if n == 0:
            continue
        by_hg = _Counter()
        for s, flags in class_by_strain.items():
            if flags.get(c, 0):
                by_hg[reg[s]["host_group"]] += 1
        cells = [str(by_hg.get(hg, 0)) if by_hg.get(hg, 0) else "\u00b7" for hg in hg_order]
        L.append(f"| {c} | {n}/{N} | {' | '.join(cells)} |")
    L.append("")
    L.append("## 3. Cohort-unique capacities (n=1 strains)")
    unique = [(c, p["n_strains"]) for c, p in prev.items() if p["n_strains"] == 1]
    if unique:
        for c, _ in sorted(unique):
            carrier = next((s for s, f in class_by_strain.items() if f.get(c, 0)), "?")
            g = reg.get(carrier, {}).get("genus", "?")
            hg = reg.get(carrier, {}).get("host_group", "?")
            L.append(f"- **{c}** \u2192 {carrier} (*{g}*, {hg})")
    else:
        L.append("- (No class present in exactly 1 strain.)")
    L.append("")
    L.append("## 4. Genus signatures")
    genus_class = defaultdict(list)
    for s, flags in class_by_strain.items():
        g = reg.get(s, {}).get("genus", "?")
        if g and g.strip().lower() not in ("", "?", "not", "none"):
            for c, v in flags.items():
                if v:
                    genus_class[g].append(c)
    for g in sorted(genus_class):
        classes = sorted(set(genus_class[g]))
        L.append(f"- **{g}** (n={genera.get(g,0)} strains): {', '.join(classes)}")
    L.append("")
    L.append("---")
    L.append("*Auto-generated from CCSM capacity integration CSV. Class flags derived from "
             "strain-specific BGC descriptions. Claim-safe throughout.*")
    return "\n".join(L)


def main(argv=None):
    """CLI: emit the cross-strain synthesis. Genus/host are sourced from --differentiating when the
    master registry lacks taxonomy."""
    import argparse
    ap = argparse.ArgumentParser(description="Deterministic cross-strain synthesis writer (Gap 3).")
    ap.add_argument("--master", default=None,
                    help="Verified cohort master workbook (xlsx). Required unless --capacity-csv.")
    ap.add_argument("--capacity-csv", default=None,
                    help="CCSM capacity integration CSV (no-workbook path). Use when the private "
                         "master is unavailable. Novelty gradient section will be absent.")
    ap.add_argument("--differentiating", default=None,
                    help="differentiating-capacities CSV (supplies genus/host when the master "
                         "registry taxonomy columns are unpopulated). Ignored with --capacity-csv.")
    ap.add_argument("--novelty-basis", default="fully_dark",
                    choices=["fully_dark", "dark_or_unresolved"],
                    help="KCB-dark definition for headline novelty numbers (default fully_dark = "
                         "canonical 164/1131 floor); the alternate basis is always reported alongside. "
                         "Ignored with --capacity-csv.")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.capacity_csv:
        md = write_synthesis_from_capacity_csv(a.capacity_csv)
    elif a.master:
        meta = meta_from_differentiating_csv(a.differentiating) if a.differentiating else None
        md = write_synthesis(a.master, novelty_basis=a.novelty_basis, meta_overrides=meta)
    else:
        import sys as _sys
        emit("error: one of --master or --capacity-csv is required", file=_sys.stderr)
        return 2
    _atomic_write_text(Path(a.out), md)
    emit(f"wrote cohort synthesis -> {a.out} ({len(md)} chars)")
    return 0


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated cohort-level deliverable (the cross-strain synthesis markdown) on disk."""
    import os
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))


if __name__ == "__main__":
    raise SystemExit(main())
