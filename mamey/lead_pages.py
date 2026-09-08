"""lead_pages.py — Wave B (v9.7.341 follow-up, bundle-only report layer)

Lead-only §31–§40 enrichment + related-genomes dossier pages, rendered from an already-sealed
Mamey package. Ported verbatim from the verified reference implementation
`reference_impl/build_lead_pages.py` (roadmap patch #4 dossier + #7 lead-enrichment), which was
proven over the sealed .339 packages on PTM/GPA/enediyne leads.

Freeze-safe: reads native package CSVs (_2_inventory, _3_mibig_convergence, _domains,
_4A2_ClusterBlast_per_gene, _4B_two_model_decomp, _4c_*_lead_board, _gene_by_gene_all_bgcs,
_4A_RGGMCI_ranked_pairs) and writes NEW files only. No scoring, parser, or gate change.

Claim ceiling (fixed in the template): class-level capacity only; comparators are similarity, not
identity; antiSMASH substrate calls are predictions; reference metadata is the neighbour's, not a
claim about the AS strain; no product/structure/activity/ANI claim.

Lead-only routing: pages are emitted for genuine leads (Lead_tier_auto in Exceptional/High/Medium)
only — never for stubs/Inventory/VOID, per the 2026-07-29 audit that cleared the boilerplate.
"""

#!/usr/bin/env python3
"""Generate a clean-sheet lead analysis page from a sealed Mamey package (the evidence
substrate). Deterministic join over the package CSVs + a per-class literature table.
Scales to ~1,200 leads: `python build_lead_pages.py <package.zip|dir> <BGCid> [--out DIR]`.

Claim ceiling is fixed in the template: class-level capacity; comparators are similarity,
not identity; antiSMASH substrate/extender calls are predictions; judgment deferred.
"""
import csv, json, os, sys, re, glob, zipfile, tempfile, argparse

HERE = os.path.dirname(os.path.abspath(__file__))  # ref-impl default; command passes outdir explicitly
# NOTE: the reference impl did `sys.path.insert(0, HERE)` here so it could `import assembly_logic`
# as a sibling script. In-engine that is REMOVED — it put mamey/ on sys.path[0], which let mamey
# submodules be imported as top-level modules and corrupted the package's relative-import context
# (matplotlib's internal relative imports then failed with "attempted relative import with no known
# parent package", silently disabling figure rendering across the run). We import via the package
# instead (`from . import assembly_line`), so no path surgery is needed.
from . import assembly_line as _assembly_line
from mamey.convergence_band import annotate as _band_pct  # display-only
from mamey.ziputil import safe_extract_all
# BC2-408: this try/except was pasted INSIDE _load_lit()'s docstring below (as inert prose, never
# executed) rather than as real module-level code -- confirmed live: `mamey lead-pages <pkg>` raised
# `NameError: name 'emit' is not defined` unconditionally on its final summary line (lead_pages.py's
# own `lead_pages_command`, ~line 652), a 100% crash rate on this CLI command. The per-BGC dossier
# pages themselves were still written correctly (build() never touches `emit`); only the wrap-up
# summary print and the `except Exception` per-BGC skip-log line were unreachable. Restored to real,
# executing code -- the exact block the v9.7.407 comment describes, just never actually run before.
try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
def _load_lit():
    """Lazily load the lead-literature crosswalk from mamey/data (card #7 location).

    Import-time side-effect-free; falls back to a GENERIC-only table if the data file is absent so
    the module never fails to import in a stripped tier."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lead_literature_table.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"GENERIC": []}


_LIT_CACHE = None


def _lit():
    global _LIT_CACHE
    if _LIT_CACHE is None:
        _LIT_CACHE = _load_lit()
    return _LIT_CACHE
# H1/v9.7.352 — the supplementary cross-analysis tables (compound-families, ClusteredNR ingest,
# nr summaries) live OUTSIDE the sealed bundle, in the workspace. Their location is CONFIG, never a
# hardcoded home dir. Resolution is env-first with a best-effort derived fallback; when a base dir
# cannot be resolved the channel loads empty AND records a WARN (honest-blank, not silent), surfaced
# on the generated page and via data_channel_warnings().
def _data_root():
    """Workspace root holding the cross-analysis dirs. $MAMEY_DATA_ROOT overrides; no home literal."""
    r = os.environ.get("MAMEY_DATA_ROOT")
    return r if (r and os.path.isdir(r)) else None

def _cohort_analysis_dir():
    """Dir holding COMPOUND_FAMILIES/ etc. $MAMEY_COHORT_ANALYSIS_DIR overrides; else the newest
    WHOLE_COHORT_ANALYSIS_* under the data root; else None (channel blanks with a WARN)."""
    d = os.environ.get("MAMEY_COHORT_ANALYSIS_DIR")
    if d and os.path.isdir(d):
        return d
    root = _data_root()
    if root:
        cands = sorted(glob.glob(os.path.join(root, "WHOLE_COHORT_ANALYSIS_*")))
        if cands:
            return cands[-1]
    return None

WCA  = _cohort_analysis_dir()           # cross-analysis dir (COMPOUND_FAMILIES/...); None if unresolved
ROOT = _data_root()                     # workspace root (ClusteredNR ingest lives here); None if unresolved

# Channels that could not resolve their base data dir — surfaced as a visible WARN, never a silent blank.
_DATA_CHANNEL_WARNINGS: list[str] = []
def data_channel_warnings() -> list[str]:
    """Return the list of data channels whose base dir did not resolve (for a visible page banner)."""
    return list(_DATA_CHANNEL_WARNINGS)

def _warn_channel(name: str, why: str):
    msg = f"lead_pages: {name} unavailable — {why} (set the matching env var to populate it)"
    if msg not in _DATA_CHANNEL_WARNINGS:
        _DATA_CHANNEL_WARNINGS.append(msg)

def _load_tsv(path, key_fn):
    d = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as fh:
            lines = [ln for ln in fh if not ln.lstrip().startswith("#")]  # skip mamey provenance lines
        for r in csv.DictReader(lines, delimiter="\t"):
            k = key_fn(r)
            if k and k not in d: d[k] = r
    return d

# (strain,bgc) -> compound-family row  |  anchor -> structure  |  name -> structure
if WCA:
    _CF   = _load_tsv(os.path.join(WCA, "COMPOUND_FAMILIES/ANCHORED_BGC_COMPOUND_FAMILIES.tsv"),
                      lambda r: (r.get("strain"), r.get("bgc_id")))
    _STRA = _load_tsv(os.path.join(WCA, "COMPOUND_FAMILIES/ANCHOR_STRUCTURES.tsv"), lambda r: r.get("anchor"))
    _STRN = _load_tsv(os.path.join(WCA, "COMPOUND_FAMILIES/ANCHOR_STRUCTURES.tsv"),
                      lambda r: (r.get("matched_name") or "").lower())
    if not _CF:
        _warn_channel("compound-family / structure context",
                      f"no COMPOUND_FAMILIES tables under {WCA}")
else:
    _CF, _STRA, _STRN = {}, {}, {}
    _warn_channel("compound-family / structure context",
                  "cohort-analysis dir not resolved ($MAMEY_COHORT_ANALYSIS_DIR / $MAMEY_DATA_ROOT)")

# (strain,bgc) -> [ (locus, nearest_other, refined_class) ] from the ClusteredNR ingest
_CNR = {}
_cnr_path = os.path.join(ROOT, "ClusteredNR_Priority_2026-07-29/ingested/clusterednr_per_query_summary.tsv") if ROOT else None
if _cnr_path and os.path.exists(_cnr_path):
    with open(_cnr_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            _CNR.setdefault((r["strain"], r["bgc"]), []).append(
                (r["locus_tag"], r.get("nearest_other_pident", ""), r.get("refined_class_selfhit_dropped", "")))
else:
    _warn_channel("ClusteredNR context",
                  "ClusteredNR ingest not found under the data root ($MAMEY_DATA_ROOT)")

_NR = {}
_nr_path = os.path.join(HERE, "nr_per_bgc_summary.tsv")
if os.path.exists(_nr_path):
    for r in csv.DictReader(open(_nr_path, encoding="utf-8"), delimiter="\t"):
        _NR[(r["strain"], r["bgc"])] = (r["most_divergent_gene"], r["min_best_nr_identity"])
else:
    _warn_channel("nr divergence context",
                  f"nr_per_bgc_summary.tsv not shipped in the package ({HERE})")

_ROWCACHE = {}
def _clear_cache(): _ROWCACHE.clear()

def find_pkg_dir(path):
    if path.endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="leadpkg_")
        with zipfile.ZipFile(path) as z:
            safe_extract_all(z, tmp)
        path = tmp
    # locate the dir containing *_2_inventory.csv
    for root, _, files in os.walk(path):
        if any(f.endswith("_2_inventory.csv") for f in files):
            return root
    raise SystemExit(f"no package CSVs under {path}")

def rows(pkg, suffix):
    ck = (pkg, suffix)
    if ck in _ROWCACHE: return _ROWCACHE[ck]
    m = glob.glob(os.path.join(pkg, f"*{suffix}"))
    out = []
    if m:
        with open(m[0], newline="", encoding="utf-8") as fh:
            out = list(csv.DictReader(fh))
    _ROWCACHE[ck] = out
    return out

def strain_of(pkg):
    m = glob.glob(os.path.join(pkg, "*_2_inventory.csv"))
    return os.path.basename(m[0]).split("_2_inventory.csv")[0]


def _asm_line(pkg, bgc):
    """Assembly-line string for one BGC, via the shipped Wave A engine module (mamey.assembly_line).

    Ported from the reference impl's `assembly_logic.line(pkg, bgc)`: filter the native _domains.csv
    to this BGC's rows and hand them to the engine's assembly_for_bgc/assembly_line_str, so Wave B
    reuses the exact Wave A walk rather than a duplicate implementation."""
    drows = [r for r in rows(pkg, "_domains.csv") if r.get("bgc_id") == bgc]
    if not drows:
        return ""
    return _assembly_line.assembly_line_str(_assembly_line.assembly_for_bgc(drows))

def classify(cctt, compound, products):
    s = f"{cctt} {compound} {products}".lower()
    if "ptm" in s or "hsaf" in s or "frontalamide" in s or "maltophilin" in s or "ikarugamycin" in s or "clifednamide" in s or "xanthobaccin" in s: return "PTM_HSAF"
    if "glycopeptide" in s or "balhimycin" in s or "teicoplanin" in s or "vancomycin" in s or "a47934" in s: return "GPA_glycopeptide"
    if "enediyne" in s or "calicheamicin" in s or "dynemicin" in s or "c-1027" in s or "ene_ks" in s: return "enediyne"
    if "phosphonate" in s or "pepm" in s or "fosfomycin" in s or "rhizocticin" in s or "dehydrophos" in s: return "phosphonate"
    if "tomaymycin" in s or "anthramycin" in s or "sibiromycin" in s or "limazepine" in s or "pyrrolobenzodiazepine" in s: return "PBD_pyrrolobenzodiazepine"
    if "thioamide" in s or "thioamitide" in s or "thioviridamide" in s: return "thioamitide_thioamide"
    if "lanthipeptide" in s or "lanthi" in s: return "lanthipeptide"
    if "siderophore" in s or "desferrioxamine" in s or "coelichelin" in s or "mirubactin" in s or "iuca" in s: return "siderophore"
    if "aminoglycoside" in s or "2-deoxystreptamine" in s or "dois" in s: return "aminoglycoside"
    if "terpene" in s and "pks" not in s and "nrps" not in s: return "terpene"
    if "t1pks" in s or "transat" in s or "macrolide" in s or "polyene" in s: return "modular_PKS_macrolide"
    if "nrps" in s: return "NRPS_generic"
    return "GENERIC"

def g(d, *keys, default=""):
    for k in keys:
        if k in d and d[k] not in (None, ""): return d[k]
    return default

def build(pkg, bgc, outdir):
    strain = strain_of(pkg)
    inv = {r["BGC_ID"]: r for r in rows(pkg, "_2_inventory.csv")}
    tri = {r["BGC_ID"]: r for r in rows(pkg, "_4_triage_board.csv")}
    conv = [r for r in rows(pkg, "_3_mibig_convergence.csv") if r["bgc_id"] == bgc]
    conv.sort(key=lambda r: int(g(r, "convergence_rank", default="99") or 99))
    twomodel = next((r for r in rows(pkg, "_4B_two_model_decomp.csv") if r["bgc_id"] == bgc), {})
    lwc = next((r for r in rows(pkg, "_3_length_weighted_capacity.csv") if r["bgc_id"] == bgc), {})
    afb = next((r for r in rows(pkg, "_4c_AF_lead_board.csv") if r["BGC_ID"] == bgc), {})
    abb = next((r for r in rows(pkg, "_4c_AB_lead_board.csv") if r["BGC_ID"] == bgc), {})
    genes = [r for r in rows(pkg, "_gene_by_gene_all_bgcs.csv") if r["bgc_id"] == bgc]
    gene_loci = {r["locus_tag"] for r in genes}
    nrpspred = [r for r in rows(pkg, "_nrps_prediction.csv") if r.get("locus_tag") in gene_loci]
    cb = [r for r in rows(pkg, "_4A2_ClusterBlast_per_gene.csv") if r["bgc_id"] == bgc]
    rgg = [r for r in rows(pkg, "_4A_RGGMCI_ranked_pairs.csv") if r.get("bgc_a") == bgc or r.get("bgc_b") == bgc]

    it, tt = inv.get(bgc, {}), tri.get(bgc, {})
    products = g(tt, "Products") or g(it, "Products")
    cctt = g(tt, "CCTT_triggers") or g(it, "CCTT_triggers")
    node = g(tt, "Node_ID") or g(it, "Node_ID")
    region = g(tt, "antiSMASH_Region") or g(it, "Region")
    boundary = g(tt, "Boundary") or g(it, "Boundary")
    length_kb = g(it, "Length_kb")
    af, ab, nov = g(tt, "AF_auto"), g(tt, "AB_auto"), g(tt, "Novelty_auto")
    tier = g(tt, "Lead_tier_auto")
    dom = conv[0] if conv else {}
    compound = g(dom, "mibig_compound")
    klass = classify(cctt, compound, products)
    kname = klass.replace("_", " ")
    page_label = "lead" if tier in ("Exceptional", "High", "Medium") else "capacity read"

    # substrate calls (dedup, drop empties)
    seen_a = set(); a_calls = []
    for r in nrpspred:
        if g(r, "domain_class") != "NRPS_A": continue
        key = (r["locus_tag"], g(r, "substrate"))
        if not key[1] or key in seen_a: continue
        seen_a.add(key); a_calls.append((key[0], key[1], g(r, "confidence")))
    at_calls = []
    seen_at = set()
    for r in nrpspred:
        if g(r, "domain_class") != "PKS_AT": continue
        key = (r["locus_tag"], g(r, "substrate"))
        if not key[1] or key in seen_at: continue
        seen_at.add(key); at_calls.append(key)
    def fmt_a(calls, cap=6):
        shown = [f"`{l}`→**{s}**" for l, s, c in calls[:cap]]
        if len(calls) > cap: shown.append(f"…(+{len(calls)-cap})")
        return ", ".join(shown)
    hi_a_str = fmt_a(a_calls)

    # core genes (biosynthetic, has domains), top by aa
    core = [r for r in genes if g(r, "sec_met_domains")]
    core.sort(key=lambda r: -int(g(r, "aa_length", default="0") or 0))

    L = []
    W = L.append
    W(f"# {strain} {bgc} — {kname} {page_label}")
    W("*Clean-sheet lead analysis — generated from the sealed Mamey package (evidence substrate) by "
      "`build_lead_pages.py`. Class-level capacity only; comparators are similarity, not identity; "
      "antiSMASH substrate calls are predictions; judgment deferred.*\n")
    W(f"**Locus:** {node} {region} · {length_kb} kb · **{boundary}** · **Release:** {g(it,'Release','—')}")
    afrank = g(afb, "Board_rank"); abrank = g(abb, "Board_rank")
    standing = []
    if afrank: standing.append(f"AF board #{afrank}")
    if abrank: standing.append(f"AB board #{abrank}")
    W(f"**Standing:** {' · '.join(standing) or 'lead'} — AF {af} / AB {ab} / novelty {nov} · tier {tier} · CCTT {cctt or '—'}\n")

    # The call
    W("## The call")
    art = "An" if kname[:1].lower() in "aeiou" else "A"
    if dom:
        call = (f"{art} **{kname}** {page_label}. Per-gene MIBiG convergence is **{g(dom,'convergence_tier')}** "
                f"({g(dom,'distinct_query_genes')}/{g(dom,'query_gene_count_total')} genes, "
                f"median {_band_pct(g(dom,'median_pct_identity'))}, {g(dom,'class_concordance')}), "
                f"{g(dom,'dominance_status')} across the family (top: {compound}).")
    else:
        call = (f"{art} **{kname}** {page_label} — no dominant MIBiG family above the convergence floor "
                f"(reference-dark); read from domain grammar, a novelty prior not proof.")
    if a_calls:
        call += f" NRPS A-domain substrate prediction: {hi_a_str} — similarity-level predictions, not biochemistry."
    W(call + "\n")

    # v9.7.343 surfacing patch: the engine's already-computed capacity verdicts
    # (Arch_Capacity/Class_Conf + Diagnostic-Rescue), previously never printed here.
    try:
        from . import card_verdicts as _cv
        _tv = {"arch": g(tt, "Arch"), "arch_capacity": g(tt, "Arch_Capacity"),
               "class_conf": g(tt, "Class_Conf"), "novelty_auto": g(tt, "Novelty_auto"),
               "concordance": g(tt, "Concordance"), "misanchor_flag": g(tt, "Misanchor_Flag"),
               "standing_rule": g(tt, "Standing_rule"), "primary_metab_flag": g(tt, "Primary_metab_flag")}
        _blk = _cv.render_block(pkg, bgc, triage=_tv)
        if _blk:
            W(_blk + "\n")
    except Exception:
        pass

    # Package evidence table
    W("## Package evidence (file → value)")
    W("| Evidence | Value |")
    W("|---|---|")
    if dom:
        runners = "; ".join(f"{g(c,'mibig_compound')[:32]} ({_band_pct(g(c,'median_pct_identity'))})" for c in conv[:4])
        W(f"| MIBiG convergence (`_3_mibig_convergence`) | {g(dom,'convergence_tier')}, {g(dom,'distinct_query_genes')}/{g(dom,'query_gene_count_total')} genes, median {_band_pct(g(dom,'median_pct_identity'))}, {g(dom,'dominance_status')}; clade: {runners} |")
    if a_calls or at_calls:
        astr = ", ".join(f"{l}:{s}({c})" for l,s,c in a_calls) or "—"
        atstr = ", ".join(f"{l}:{s}" for l,s in at_calls) or "—"
        W(f"| Substrate predictions (`_nrps_prediction`) | A-domain: {astr} · PKS-AT extender: {atstr} |")
    if twomodel:
        W(f"| Two-model decomposition (`_4B_two_model_decomp`) | **{g(twomodel,'two_model_confidence')}** — {g(twomodel,'null_reason') or (g(twomodel,'group_a_class')+' / '+g(twomodel,'group_b_class'))} |")
    if lwc:
        W(f"| Captured completeness (`_3_length_weighted_capacity`) | length_fraction {g(lwc,'length_fraction')} ({g(lwc,'boundary')}; {g(lwc,'metric_status')}) |")
    if cb:
        top = cb[0]
        W(f"| Independent ClusterBlast (`_4A2`) | e.g. `{g(top,'query_gene')}` {g(top,'pct_identity')}% → {g(top,'reference_source')[:40]} — SIMILARITY channel, separate from MIBiG |")
    if rgg:
        r0 = max(rgg, key=lambda r: int(g(r,'rggmci_score',default='0') or 0))
        partner = r0["bgc_b"] if r0.get("bgc_a")==bgc else r0["bgc_a"]
        W(f"| Cross-contig linkage (`_4A_RGGMCI`) | best pair {bgc}+{partner} score {g(r0,'rggmci_score')} ({g(r0,'rggmci_confidence')}, {g(r0,'functional_rescue_class')}) — homology-guided, not a nucleotide join |")
    W(f"| Independent BLASTp support | `blastp_supported=FALSE` cohort-wide — no independent all-gene confirmation |")
    W("")

    # How the core cooperates
    W("## How the core cooperates (by locus_tag)")
    a_by_locus = {l: (s, c) for l, s, c in a_calls}
    at_by_locus = {l: s for l, s in at_calls}
    shown = 0
    for r in core:
        if shown >= 6: break
        loc = r["locus_tag"]; aa = g(r, "aa_length"); dom_s = g(r, "sec_met_domains")
        extra = []
        if loc in a_by_locus: extra.append(f"A-domain→{a_by_locus[loc][0]}")
        if loc in at_by_locus: extra.append(f"AT→{at_by_locus[loc]}")
        ex = f" [{', '.join(extra)}]" if extra else ""
        W(f"- **`{loc}`** ({aa} aa) — {dom_s[:90]}{ex}")
        shown += 1
    if not core:
        W("- Core genes without recorded sec_met domains — reference-dark; read from the gene table (§3 of the card).")
    W("")

    # ---- Machinery & modules (from domains.csv + sec_met) ----
    doms = [r for r in rows(pkg, "_domains.csv") if r.get("bgc_id") == bgc and g(r, "feature_type") == "aSDomain"]
    def dcount(*subs):
        return sum(1 for d in doms if any(s.lower() in g(d, "domain").lower() for s in subs))
    ks, at = dcount("PKS_KS", "Ketoacyl-synt"), dcount("PKS_AT")
    c_dom, a_dom = dcount("Condensation"), dcount("AMP-binding")
    te = dcount("Thioesterase", "NRPS-te")
    pptase = dcount("ACPS", "4PPT", "Sfp") or sum(1 for r in genes if "4ppt" in g(r,"sec_met_domains").lower() or "acps" in g(r,"sec_met_domains").lower())
    tail_map = [("cytochrome-P450", ["p450", "cytochrome_p"]), ("halogenase", ["halogen"]),
                ("methyltransferase", ["methyltransf", "ethyltransf"]), ("glycosyltransferase", ["glyco_transf", "glycos_transf"]),
                ("hydroxylase/desaturase", ["fa_hydroxylase", "sterol", "desaturase", "hydroxylase", "2og-feii", "2og_feii"]),
                ("FAD oxidoreductase", ["fad_binding", "amino_oxidase"]),
                ("short-chain reductase/KR", ["adh_short", "adh_zinc", "ketoreduct"]),
                ("dehydrogenase/oxidase", ["dehydrogenase", "gmc_oxred", "oxidored"]),
                ("aminotransferase", ["aminotran"])]
    from collections import Counter as _TC
    _tc = _TC()
    for r in genes:                        # count each gene ONCE (first matching role)
        sm = g(r, "sec_met_domains").lower()
        for label, keys in tail_map:
            if any(k in sm for k in keys):
                _tc[label] += 1; break
    tail = [f"{n}× {label}" for label, n in _tc.items()]
    W("## Machinery & modules")
    mods = []
    if ks or at: mods.append(f"PKS ~{min(ks,at) or max(ks,at)} module(s) (KS×{ks}, AT×{at})")
    if c_dom or a_dom: mods.append(f"NRPS ~{min(c_dom,a_dom) or max(c_dom,a_dom)} module(s) (C×{c_dom}, A×{a_dom})")
    if te: mods.append(f"TE×{te} (release)")
    if pptase: mods.append("PPTase (carrier priming) present")
    W(f"- **Assembly line:** {'; '.join(mods) if mods else 'non-modular / domain-sparse — read from §3 gene table'}. "
      "Module counts are lower bounds (Edge-truncated or fragmented); class-level, not a validated module order.")
    # NC-007 (claim-safety): an absent/invalid length_fraction is UNRESOLVED completeness — never coerce it
    # to 1.0, which would make an unrecovered window look complete and license "genuinely absent" wording below.
    try:
        lff = float(g(lwc, "length_fraction"))
    except (TypeError, ValueError):
        lff = None
    if lff is not None and lff < 0.5:
        W(f"- **⚠ FRAGMENT — only ~{lff*100:.0f}% of a nominal cluster is captured ({length_kb} kb):** the assembly line "
          "is INCOMPLETE and the module counts above are a hard floor. Do NOT read this as a coherent full scaffold; the "
          "missing arm is likely on another contig (check the cross-contig / RG-GMCI evidence below).")
    elif lff is None:
        W("- **⚠ Completeness UNRESOLVED — `length_fraction` not recovered:** the captured fraction of a nominal "
          "cluster is unknown, so module counts are a hard floor and this window must NOT be read as complete.")
    try:
        asm = _asm_line(pkg, bgc)
        if asm and "no ordered" not in asm:
            W(f"- **Predicted assembly (ordered, from `_domains.csv`):** {asm}. antiSMASH Stachelhaus/Minowa "
              "predictions — similarity-level, lower bounds if Edge-truncated; NOT a structure/product claim.")
    except Exception:
        pass
    W(f"- **Tailoring/decoration:** {', '.join(tail) if tail else 'no distinct tailoring domains recorded'} — capacity to decorate the scaffold; not a proven modification.")
    W("")

    # ---- Self-protection (resistance + transport) ----
    def has(r, *keys):
        blob = (g(r,"sec_met_domains")+" "+g(r,"product_qualifier")+" "+g(r,"gene_function_inference")).lower()
        return any(k in blob for k in keys)
    transporters = [r for r in genes if has(r, "transport", "efflux", "abc_tran", "abc_membrane", "mfs", "macb", "bpd_transp", "eama", "na_h_exchanger")]
    resist_genes = [r for r in genes if has(r, "vany", "vana", "vanx", "vanr", "vans", "beta-lactam", "resist", "immun", "self-protection", "23s", "target")]
    rtier = ""
    if genes:
        from collections import Counter as _C
        rtier = _C(g(r,"resistance_tier") for r in genes).most_common(1)[0][0]
    W("## Self-protection (resistance & transport)")
    W(f"- **Resistance tier (engine):** {rtier or '—'}. Class-level self-protection prior from source-derived markers, not a measured resistance phenotype.")
    if resist_genes:
        rg = ", ".join(f"`{r['locus_tag']}` ({g(r,'sec_met_domains').split(';')[0][:16] or 'resistance'})" for r in resist_genes[:6])
        W(f"- **Self-resistance cassette:** {rg} — a target-based/self-immunity prior (e.g. van-type D-Ala-D-Lac remodeling for GPA).")
    else:
        # NC-008 (claim-safety): only say "genuinely absent" when the window is actually resolved-complete.
        # Edge/fragment => off-contig; UNRESOLVED completeness => not evidence of absence.
        if boundary == "Edge" or (lff is not None and lff < 0.5):
            offc = "may be off-contig (edge/fragment)"
        elif lff is None:
            offc = "not recovered in-window; window completeness UNRESOLVED — not evidence of absence"
        else:
            offc = "genuinely absent on current evidence"
        W(f"- **Self-resistance cassette:** none recovered in-window — {offc}.")
    if transporters:
        types = sorted({(g(r,'sec_met_domains').split(';')[0].strip() or 'transporter')[:14] for r in transporters})
        W(f"- **Export/efflux:** {len(transporters)} transporter gene(s) [{', '.join(types[:6])}] — self-protection/secretion prior; efflux can double as resistance.")
    else:
        W("- **Export/efflux:** none distinctly recovered in-window.")
    W("")

    # ---- Rarity & novelty ----
    rare_map = {"ENE":"enediyne (rare warhead)","PHO":"phosphonate (rare warhead)","PBD":"pyrrolobenzodiazepine (rare)",
                "THA":"thioamide/thioamitide","GPA":"glycopeptide","HSAF":"PTM/HSAF antifungal","PTM":"PTM/HSAF antifungal"}
    rare_hits = sorted({v for k,v in rare_map.items() if k.lower() in (cctt or "").lower()})
    W("## Rarity & novelty")
    if rare_hits:
        W(f"- **Rare/warhead class:** {', '.join(rare_hits)} — a high-interest class in this cohort (CCTT: {cctt}).")
    else:
        W(f"- **Class rarity:** common biosynthetic class (CCTT: {cctt or 'none'}); interest driven by scores/novelty, not class rarity.")
    if dom:
        med = g(dom,"median_pct_identity")
        try: mv = float(med)
        except (TypeError, ValueError): mv = 100.0  # NC-006: unknown median => conservative genus-conserved (under-claims novelty)
        nov = ("genuinely divergent core (median <60% — novel-congener prior)" if mv < 60 else
               "moderately divergent (median 60–80% — likely divergent congener)" if mv < 80 else
               "genus-conserved at the converging genes (median ≥80% — precedented; novelty from architecture, not sequence)")
        W(f"- **Novelty read:** convergence {g(dom,'convergence_tier')} at {med}% median, {g(dom,'dominance_status')} → {nov}. "
          "Confirm against the per-gene nearest-OTHER homolog (ClusteredNR, self-hits dropped) before calling novelty.")
    else:
        W("- **Novelty read:** reference-dark (no MIBiG family above floor) — a novelty prior from domain grammar, "
          "pending nearest-OTHER homology to separate genuine divergence from a database gap.")
    cnr = _CNR.get((strain, bgc))
    if cnr:
        vals = [(l, float(no)) for l, no, cls in cnr if no not in ("", None)]
        if vals:
            lloc, lo = min(vals, key=lambda t: t[1])
            verdict = ("GENUINELY DIVERGENT" if lo < 70 else "moderately divergent" if lo < 90 else "genus-conserved")
            W(f"- **ClusteredNR nearest-OTHER (self-hits >97% dropped):** most-divergent core `{lloc}` at **{lo:.1f}%** "
              f"→ {verdict} ({len(vals)} core(s) queried). ClusteredNR ≠ nr; representative identity, not organism/ANI.")
    nr = _NR.get((strain, bgc))
    if nr:
        try: nv = float(nr[1])
        except (TypeError, ValueError): nv = None  # NC-006: typed; unknown nr identity stays None (no novelty claim)
        if nv is not None:
            nverd = ("GENUINELY DIVERGENT" if nv < 70 else "moderately divergent" if nv < 90 else "genus-conserved")
            W(f"- **NCBI-nr nearest homolog (self-hits >97% dropped):** most-divergent gene `{nr[0]}` at **{nv:.1f}%** "
              f"→ {nverd}. nr database similarity, NOT identity/ANI/organism; separate channel from ClusteredNR.")
    W("")

    # Literature-to-locus crosswalk
    W("## Literature-to-locus crosswalk (published biochemistry → this locus; DOIs to VERIFY vs library)")
    W("| Established biochemistry | Locus evidence | Allowed conclusion |")
    W("|---|---|---|")
    for bio, ev, allowed in _lit().get(klass, _lit().get("GENERIC", [])):
        W(f"| {bio} | {ev} | {allowed} |")
    for bio, ev, allowed in _lit().get("GENERIC", []):
        W(f"| {bio} | {ev} | {allowed} |")
    W("")

    # ---- Compound-family & structure context (join to anchored-family + structure tables) ----
    cf = _CF.get((strain, bgc))
    W("## Compound-family & structure context")
    if cf:
        anchor = g(cf, "anchor"); fam = g(cf, "parent_family"); tgt = g(cf, "target_class"); moa = g(cf, "moa")
        conc = g(cf, "class_concordance")
        st = _STRA.get(anchor, {})
        if conc and conc.lower().split("(")[0].strip() not in ("ok", "concordant", ""):
            W(f"- **⚠ Anchor DISCORDANT ({conc.split('(')[0].strip()}):** the '{anchor}' anchor / '{fam}' family does "
              f"NOT match the physical grammar — do NOT use this family for interpretation; use the domain-based read (§4/§9). "
              f"Reason: {conc.split('(',1)[1].rstrip(')') if '(' in conc else '—'}")
            st = {}   # never show a structure for a discordant anchor
        else:
            W(f"- **Parent family:** {fam or '—'} · **target class:** {tgt or '—'}{' · MoA: '+moa if moa else ''} "
              f"(anchor: {anchor}).")
    else:
        # fall back to the convergence dominant compound as the related known compound
        related = (compound.split("/")[0].strip() if compound else "")
        fam = klass.replace("_", " ")
        st = _STRN.get(related.lower(), {})
        W(f"- **Parent family:** {fam} (from class); related known compound: **{related or 'unresolved'}** "
          f"(convergence anchor, SIMILARITY not identity).")
    if st and g(st, "inchikey"):
        W(f"- **Related KNOWN structure** ({g(st,'matched_name')}, NPAtlas {g(st,'npaid')}): "
          f"InChIKey `{g(st,'inchikey')}` · {g(st,'mol_formula')} · SMILES `{g(st,'smiles')[:70]}{'…' if len(g(st,'smiles'))>70 else ''}`")
        W("  — this is the structure of a **related characterized compound**, shown for chemical context; it is **NOT** a structure of this BGC's product.")
    else:
        W("- **Related structure:** not resolved to NPAtlas here — see `COMPOUND_FAMILIES/ANCHOR_STRUCTURES.tsv` / NPAtlas by family. No product-structure claim.")
    W("")

    # Alternative + experiment
    W("## Leading alternative & decisive experiment")
    if dom and g(dom,'dominance_status','').startswith(("CO_DOMINANT","NOT","MIXED")):
        W(f"**Alternative:** a divergent member of the {kname} family (convergence is "
          f"{g(dom,'dominance_status')} at {_band_pct(g(dom,'median_pct_identity'))} — no single reference wins), "
          f"i.e. a novel congener rather than the named compound.")
    else:
        W("**Alternative:** a divergent congener of the named family, or a class-compatible reassignment (see the card §9).")
    exp = "targeted LC-MS/MS for the class mass series under inducing conditions"
    if a_calls: exp = "confirm the predicted A-domain substrates above and the product by " + exp
    W(f"**Decisive experiment:** {exp}; this upgrades or kills the lead.\n")

    # H1/v9.7.352 — honest-blank: surface any data channel that could not resolve, so an empty
    # compound-family / ClusteredNR / nr section reads as "not available here", never a silent gap.
    if _DATA_CHANNEL_WARNINGS:
        W("## Data availability")
        for _w in data_channel_warnings():
            W(f"> ⚠️ {_w}")
        W("")

    # Claim ceiling
    W("## Claim ceiling")
    W(f"Class-level **{klass.replace('_',' ')}** capacity from packaged domain/substrate evidence + literature "
      "logic. Substrate/extender calls are antiSMASH predictions (similarity-level), not biochemistry. "
      "Comparators are similarity anchors, not identity. No structure, stereochemistry, production, activity, "
      "exact-product, or novelty-proof claim. No genome assembly → no ANI/organism claim. "
      "`blastp_supported=FALSE`. DOIs above are author-year-anchored and flagged for verification against the "
      "project library before citing. Judgment deferred.")

    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{strain}_{bgc}_LEAD.md")
    # v9.7.374: write to a .tmp sibling then os.replace() into place, so a process killed mid-write
    # (SIGKILL/OOM/power loss) -- including on a `lead-pages` re-run over an outdir that already
    # carries a valid prior page for this BGC -- cannot truncate a previously-valid deliverable to
    # zero/partial bytes. A per-BGC try/except in lead_pages_command() cannot catch this class of
    # interruption, so the write itself must be crash-safe.
    _out_tmp = out + ".tmp"
    with open(_out_tmp, "w", encoding="utf-8") as _fh:
        _fh.write("\n".join(L) + "\n")
    os.replace(_out_tmp, out)

    # index record
    cf2 = _CF.get((strain, bgc))
    disc = bool(cf2) and g(cf2, "class_concordance").lower().split("(")[0].strip() not in ("ok", "concordant", "")
    struct = ""
    if cf2 and not disc:
        s2 = _STRA.get(g(cf2, "anchor"), {})
        struct = g(s2, "inchikey")
    cnr2 = _CNR.get((strain, bgc)); cnr_worst = ""
    if cnr2:
        vv = [float(no) for _, no, _ in cnr2 if no not in ("", None)]
        if vv: cnr_worst = f"{min(vv):.1f}"
    # reference-genome context (NCBI/MIBiG references are higher-quality than the draft genome)
    mibig_ref = f"{g(dom,'mibig_accession')} {g(dom,'mibig_compound').split('/')[0]} ({_band_pct(g(dom,'median_pct_identity'))})" if dom else ""
    cb_refs = []; seen_r = set()
    for c in sorted(cb, key=lambda r: -float(g(r, "pct_identity", default="0") or 0)):
        ref = g(c, "reference"); org = g(c, "reference_source").split(",")[0]
        if ref and ref not in seen_r:
            seen_r.add(ref); cb_refs.append(f"{org[:42]} [{ref}] {g(c,'pct_identity')}%")
        if len(cb_refs) >= 3: break
    idx = dict(strain=strain, bgc=bgc, klass=klass, page_label=page_label, lead_tier=tier,
               AF=af, AB=ab, novelty=g(tt, "Novelty_auto"), products=products, node=node, boundary=boundary,
               cctt=cctt, top_compound=(compound.split("/")[0].strip() if compound else ""),
               convergence_tier=g(dom, "convergence_tier"), median_id=g(dom, "median_pct_identity"),
               dominance=g(dom, "dominance_status"), af_board_rank=g(afb, "Board_rank"),
               rare_flag=("Y" if rare_hits else ""), discordant_flag=("Y" if disc else ""),
               structure_inchikey=struct, clusterednr_nearest_other=cnr_worst,
               two_model=g(twomodel, "two_model_confidence"),
               mibig_ref=mibig_ref, clusterblast_refs=" | ".join(cb_refs),
               nr_nearest=(_NR.get((strain, bgc), ("", ""))[1]), page=os.path.relpath(out, HERE))
    return out, klass, idx

# ---------------------------------------------------------------------------
# Wave B command wrapper (engine front-door integration)
# ---------------------------------------------------------------------------
LEAD_TIERS = {"Exceptional", "High", "Medium"}


def _is_lead(triage_row) -> bool:
    """Lead-only gate: emit enrichment pages only for genuine leads, never stubs/Inventory/VOID.

    AUDIT_378 (excluded-BGC-leak family, 6th confirmed instance): Lead_tier_auto alone is
    not sufficient. scoring.py's standing-rule / primary-metabolism / mobile-element three-flag
    gate withholds corrected_rank but leaves the BGC's raw Lead_tier_auto untouched -- so an
    engine-excluded BGC (e.g. a SACCHARIDE housekeeping-operon false positive) can still read
    Lead_tier_auto=High and, before this fix, would get a full §31-40 enrichment + related-genomes
    dossier page emitted under the DEFAULT (non---all-tiers) scope -- read by anyone opening it as
    exactly the "genuine lead" this function's own docstring says it exists to isolate. Use the
    canonical shared predicate (scoring.py:25, v9.7.376) so this file applies the same 3-signal
    check every other guarded consumer in the codebase uses, rather than reinventing it locally."""
    if g(triage_row, "Lead_tier_auto") not in LEAD_TIERS:
        return False
    try:
        from .scoring import is_lead_excluded
    except Exception:
        return False  # v9.7.409 A6: fail CLOSED -- an import hiccup must not emit an unconfirmed lead page (the old `return True` did exactly what this comment forbade)
    return not is_lead_excluded(triage_row)


def lead_pages_command(args):
    """`mamey lead-pages <package> [--out DIR] [--bgc BGC|ALL] [--all-tiers]`

    Renders lead-only §31–§40 enrichment + related-genomes dossier pages from a sealed package.
    Default scope is genuine leads only (Lead_tier_auto in Exceptional/High/Medium); --all-tiers
    lifts the gate for a full capacity read. Additive/report-only — writes new files, changes none.
    """
    import os as _os
    pkg = find_pkg_dir(args.package)
    _clear_cache()
    outdir = getattr(args, "out", None) or _os.path.join(pkg, "LEAD_PAGES")
    tri = {r["BGC_ID"]: r for r in rows(pkg, "_4_triage_board.csv")}
    inv = rows(pkg, "_2_inventory.csv")
    all_tiers = getattr(args, "all_tiers", False)

    want = (args.bgc.upper() if getattr(args, "bgc", None) else "ALL")
    if want == "ALL":
        bgcs = [r["BGC_ID"] for r in inv if r.get("BGC_ID")]
    else:
        bgcs = [want]

    emitted, skipped_nonlead, failed = [], 0, 0
    for b in bgcs:
        if not all_tiers and not _is_lead(tri.get(b, {})):
            skipped_nonlead += 1
            continue
        try:
            out, klass, _idx = build(pkg, b, outdir)
            emitted.append((b, klass, out))
        except Exception as e:  # a malformed single BGC must not sink the batch
            failed += 1
            emit(f"  skip {b}: {e}")

    emit(f"lead-pages: {len(emitted)} page(s) -> {outdir}"
          + (f"  ({skipped_nonlead} non-lead skipped)" if skipped_nonlead else "")
          + (f"  ({failed} failed)" if failed else ""))
    return 0
