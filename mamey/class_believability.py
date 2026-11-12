"""mamey.class_believability — committed-step believability engine (LQ-PATH-01).

Judges the *believability* of a biosynthetic class call from its enzyme logic, not from the
antiSMASH class label alone. antiSMASH fires a class rule (and Mamey a CCTT trigger) on a single
diagnostic hit, but many classes have a hard *committed step* whose gateway Pfam is degenerate, so
the label over-calls. This engine encodes each class the way a reviewer reads a cluster —
*necessary gateway → committed pull → warhead/tailoring → assembly*, plus the named false-positive
superfamily that makes the label over-call — and returns a tiered call with the evidence.

    HIGH    : gateway (good hit) + committed pull + >=1 downstream (tailoring/TIGR/assembly).
    MEDIUM  : gateway (good hit) + partial corroboration (committed pull OR >=2 associated markers).
    LOW     : gateway only / weak, no committed pull, <=1 associated marker -> named-FP risk.
    SUSPECT : class flagged by antiSMASH/CCTT but NO gateway enzyme captured.
    NONE    : neither gateway nor class flag -> not a candidate for this class.

Boundary/assembly status is CONTEXT, never a demotion (fragment-surfacing principle): a real gateway
on a contig edge is still a real gateway.

TWO PASSES (RFC LQ-PATH-01 1b):
  * LOCAL  (per-BGC): does *this region* carry the committed-step set?
  * POOLED (per-strain): union every CDS across all regions/contigs and ask whether the strain,
    *anywhere*, has the full set for the class — even if split across fragments. When the pooled tier
    is stronger than the best single-BGC tier, that is a **candidate split pathway** (cross-reference
    RG-GMCI 4A_*): the best gene in a strain can be an orphan the BGC-local view rates LOW.

Reads only post-seal artifacts (`*_gene_context.jsonl` + `_2_inventory.csv`), so this runs as a
non-blocking post-seal subcommand and never touches `run_one_strain` or any gate.

The phosphonate module is validated (ran across the AS + SID cohorts; matches the earlier
`pathway_logic/phosphonate_logic.py` prototype). Eleven signature-enzyme modules follow it: the CDPS
route to diketopiperazines, lassopeptide, class I lanthipeptide, thioamitide, mycosamine polyene,
aminocyclitol (2-deoxystreptamine or AHBA), ectoine, NIS siderophore, gamma-butyrolactone, phenazine and melanin.
Each was run on a 44-genome isolate cohort and its HIGH calls compared
with antiSMASH's region label before shipping. Other classes are added as small registry entries;
only validated modules are shipped so the engine never manufactures a believability it can't defend.

`--exclude-contigs <tsv>` leaves out CDS on listed (strain, contig) pairs, for contigs ruled out of
analysis (for example, low-coverage contigs).

CLI:
    python mamey_run.py class-believability <package_dir> [<package_dir> ...] \
        [--class phosphonate] [--json out.json] [--csv out.csv]
"""
from __future__ import annotations
from .logging_setup import get_logger as _get_logger

_OUT = _get_logger(__name__)   # library progress lines, byte-identical to the former print

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
import re
from dataclasses import dataclass, field
from pathlib import Path

WEAK_GATEWAY_BIT = 60.0  # a gateway hit below this bitscore is "weak" (named-FP risk)
RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "SUSPECT": 3, "NONE": 4}
_TIER_ORDER = ["HIGH", "MEDIUM", "LOW", "SUSPECT"]


@dataclass(frozen=True)
class ClassModule:
    """One class's committed-step logic. All patterns match case-insensitively against a BGC's
    union of sec_met_domains + antiSMASH product/gene_functions text."""
    name: str
    gateway: tuple[str, ...]          # necessary gateway enzyme(s); no gateway -> not de-novo biosynthesis
    committed: tuple[str, ...]        # committed pull (traps a reversible/unfavourable gateway step)
    tigr: tuple[str, ...]             # class-diagnostic TIGRFAMs / named tailoring markers
    warhead: tuple[str, ...]          # warhead/tailoring enzymes (counted)
    assembly: tuple[str, ...]         # assembly-line markers (ligase / NRPS / PKS)
    engine_flag: tuple[str, ...]      # antiSMASH/CCTT class tokens (drives SUSPECT when gateway absent)
    fp_superfamily: str               # the named false-positive superfamily the label over-calls into
    gateway_bit_re: re.Pattern = field(default=None)  # optional: extract the gateway bitscore for weak-hit test
    assembly_required: bool = False  # True: HIGH and MEDIUM also need an assembly-line marker in the same set
    medium_requires_committed: bool = False   # True: MEDIUM needs the committed enzyme; generic tailoring alone is LOW


# --- phosphonate (validated; mirrors the pathway_logic/phosphonate_logic.py prototype) ----------------
# PEP --(PEP mutase, PepM)--> phosphonopyruvate --(Ppd, TPP decarboxylase)--> phosphonoacetaldehyde
#     --(aminotransferase / AA-kinase)--> amino-phosphonate warhead --(ATP-grasp / NRPS)--> phospho-PEPTIDE
PHOSPHONATE = ClassModule(
    name="phosphonate",
    gateway=("pep_mutase", "carboxyvinyl-carboxyphosphonate", "smcog1231",
             "phosphoenolpyruvate mutase", "phosphonopyruvate"),
    committed=("tpp_enzyme",),  # phosphonopyruvate decarboxylase (traps the reversible PepM step)
    tigr=("tigr03944", "tigr03945", "tigr03335", "phna", "phosphonatase",
          "phosphonoacet", "aminoethylphosphon"),
    warhead=("aminotran", "aa_kinase", "metallophos", "palp", "ntp_transf", "ocd_mu_crystall"),
    assembly=("atp-grasp", "atpgrasp", "amp-binding", "condensation", "nrps"),
    engine_flag=("phosphonate", "phosphonates", "t43-pho"),
    fp_superfamily="isocitrate-lyase superfamily (carboxyPEP mutase / methylisocitrate lyase — primary metabolism)",
    gateway_bit_re=re.compile(r"PEP_mutase[^)]*bitscore:\s*([\d.]+)", re.I),
)

# --- signature-enzyme classes (v9.7.465) ------------------------------------------------------------
# Each module names the enzyme that commits a region to the class and the enzyme that completes the
# core chemistry. Patterns are domain names as antiSMASH writes them in `sec_met_domains` (detection
# profiles and Pfam names), checked against the AS cohort before shipping. A tier is a capacity read
# of the gene set; it never names a product.

# Cyclodipeptide synthase route: a CDPS joins two aminoacyl-tRNAs into the diketopiperazine ring.
# The CDPS is both the gateway and the committed step; tailoring enzymes decorate the ring.
# Two-module NRPS routes to diketopiperazines are not covered by this module.
DKP_CDPS = ClassModule(
    name="diketopiperazine_cdps",
    gateway=("cdps",),
    committed=("cdps",),
    tigr=(),
    warhead=("p450", "methyltransf", "prenyltrans", "fad_binding", "oxidored"),
    assembly=(),
    engine_flag=("cdps:",),
    fp_superfamily="tRNA-dependent enzymes outside secondary metabolism (verify the CDPS hit)",
)

# Lassopeptide: B1 (RRE, PqqD-like) and B2 (transglutaminase-like cysteine protease) remove the
# leader; C (asparagine-synthetase-like macrolactam synthetase) closes the ring.
LASSOPEPTIDE = ClassModule(
    name="lassopeptide",
    gateway=("asn_synthase",),
    committed=("transglut_core", "pf13471"),  # antiSMASH writes the B2 protease as PF13471
    tigr=("pqqd", "pf05402", "lasso_rre", "stand_alone_lasso", "lasso_fused"),
    warhead=(),
    assembly=("abc_tran",),
    engine_flag=("lassopeptide",),
    fp_superfamily="asparagine synthetase B of primary metabolism (Asn_synthase alone)",
)

# Class I lanthipeptide: LanB dehydratase (two domains) and LanC cyclase form the lanthionine rings.
LANTHIPEPTIDE_I = ClassModule(
    name="lanthipeptide_class_i",
    gateway=("lant_dehydr",),
    committed=("lanc_like",),
    tigr=("lanthipeptide_lanb_rre",),
    warhead=("p450", "fad_binding", "flavoprotein"),
    assembly=("abc_tran", "peptidase"),
    engine_flag=("lanthipeptide-class-i:",),  # the colon keeps class ii, iii and iv out
    fp_superfamily="LanB-like dehydratases of thiopeptides and other RiPPs (LanB without LanC)",
    medium_requires_committed=True,
)

# Thioamitide: the YcaO and TfuA pair installs the thioamide.
THIOAMITIDE = ClassModule(
    name="thioamitide",
    gateway=("ycao",),
    committed=("tfua",),
    tigr=(),
    warhead=("methyltransf", "radical_sam", "p450", "fad_binding"),
    assembly=(),
    engine_flag=("thioamitides",),
    fp_superfamily="YcaO of azole-forming RiPPs (YcaO without TfuA)",
    medium_requires_committed=True,
)

# Glycosylated polyene: a modular type I PKS with the mycosamine cassette. GDP-mannose
# 4,6-dehydratase starts the amino sugar, a DegT/DnrJ/EryC1 aminotransferase adds the amine, a
# glycosyltransferase attaches it, and a P450 often oxidizes the macrolactone. HIGH and MEDIUM need
# the PKS; the sugar cassette alone is LOW (it also occurs in saccharide clusters).
POLYENE_MYCOSAMINE = ClassModule(
    name="polyene_mycosamine",
    gateway=("gdp_man_dehyd",),
    committed=("degt_dnrj_eryc1",),
    tigr=(),
    warhead=("p450", "glycos_transf_1", "glyco_trans_1_4", "glyco_tran_28"),
    assembly=("pks_ks", "pks_at"),
    engine_flag=(),
    fp_superfamily="deoxysugar and cell-wall sugar cassettes without a type I PKS",
    assembly_required=True,
    medium_requires_committed=True,
)

# Aminocyclitol: a DHQS-family carbocycle synthase (or, in the streptamine route, myo-inositol-1-phosphate
# synthase) with a DegT-family aminotransferase or BtrH. This pair is shared by 2-deoxystreptamine
# aminoglycosides and the AHBA route to ansamycins, so the module reads the shared aminocyclitol step and
# does not separate the two. antiSMASH's DOIS profile, specific to 2-deoxystreptamine, is not required.
AMINOCYCLITOL = ClassModule(
    name="aminocyclitol",
    gateway=("dhq_synthase", "dhqs", "inos-1-p_synth"),
    committed=("degt_dnrj_eryc1", "btrh"),
    tigr=("btrh",),
    warhead=("aminotran", "glycos_transf", "glyco_trans", "amidinotransf", "aph"),
    assembly=(),
    engine_flag=("2dos:", "amglyccycl:", "aminoglycoside"),
    fp_superfamily="3-dehydroquinate synthase of the shikimate pathway and inositol synthesis; the AHBA route to ansamycins shares the pair",
    medium_requires_committed=True,
)

# Ectoine: EctA (acetyltransferase), EctB (class III aminotransferase) and EctC (ectoine synthase).
ECTOINE = ClassModule(
    name="ectoine",
    gateway=("ectoine_synth",),
    committed=("aminotran_3",),
    tigr=("acetyltransf",),
    warhead=("ectd", "2og-feii_oxy", "phyh"),
    assembly=(),
    engine_flag=("ectoine",),
    fp_superfamily="none known; the tier reports how complete the EctABC set is",
)

# NIS siderophore: IucA/IucC-type NRPS-independent synthetases condense the hydroxamate building
# blocks; a lysine/ornithine N-hydroxylase (IucD-type flavin monooxygenase) makes them.
NIS_SIDEROPHORE = ClassModule(
    name="nis_siderophore",
    gateway=("iuca_iucc",),
    committed=("lys_orn_oxgnase",),
    tigr=("fhuf", "acyltransferase"),
    warhead=("pyr_redox", "fmo-like"),
    assembly=(),
    engine_flag=("ni-siderophore:",),
    fp_superfamily="IucA/IucC-family synthetases without the N-hydroxylase",
)

# Gamma-butyrolactone signalling molecules: AfsA condenses the precursors, a short-chain reductase
# (BarS1-type) completes the lactone, and a TetR-family receptor usually sits beside them.
BUTYROLACTONE = ClassModule(
    name="butyrolactone",
    gateway=("afsa",),
    committed=("adh_short",),
    tigr=("tetr_n",),
    warhead=(),
    assembly=(),
    engine_flag=("butyrolactone:",),
    fp_superfamily="none known for AfsA; the reductase and receptor families are common",
    medium_requires_committed=True,
)

# Type II PKS is not shipped: the ketoacyl-synthase domain names in package gene context do not
# separate the KS-alpha/chain-length-factor pair from type I PKS and fatty acid synthase KS domains,
# and a trial module called 20 of 52 HIGH regions on type I PKS, NRPS or fatty-acid regions.

# Phenazine: PhzF isomerase and PhzB, PhzG and the chorismate-pathway enzymes (PhzE, PhzD) build the
# phenazine core.
PHENAZINE = ClassModule(
    name="phenazine",
    gateway=("phzc-phzf",),
    committed=("phza_phzb", "pnp_phzg"),
    tigr=("chorismate_bind", "isochorismatase", "dahp_synth"),
    warhead=("methyltransf", "fad_binding", "monooxygenase"),
    assembly=(),
    engine_flag=("phenazine:",),
    fp_superfamily="PhzF-like (DapF-like) isomerases of primary metabolism without PhzB or PhzG",
    medium_requires_committed=True,
)

# Melanin: a tyrosinase and its MelC1 caddie protein, which delivers copper and exports the enzyme.
MELANIN = ClassModule(
    name="melanin",
    gateway=("tyrosinase",),
    committed=("melc1",),
    tigr=("melc1",),
    warhead=(),
    assembly=(),
    engine_flag=("melanin:",),
    fp_superfamily="tyrosinase-like copper oxidases without the MelC1 caddie",
    medium_requires_committed=True,
)

# Registry of shipped, validated modules. Add a module here to extend the engine (RFC proposes
# polyene / enediyne / RiPP-maturation next); only ship a class once its committed-step logic is
# validated against a cohort, so a believability tier is never manufactured.
REGISTRY: dict[str, ClassModule] = {m.name: m for m in (
    PHOSPHONATE, DKP_CDPS, LASSOPEPTIDE, LANTHIPEPTIDE_I, THIOAMITIDE, POLYENE_MYCOSAMINE,
    AMINOCYCLITOL, ECTOINE, NIS_SIDEROPHORE, BUTYROLACTONE, PHENAZINE, MELANIN)}


def _hit(blob: str, patterns) -> bool:
    return any(p in blob for p in patterns)


def scan_bgc(cds_list: list[dict], mod: ClassModule) -> dict:
    """Compute the marker profile for one CDS list (a BGC, or a pooled strain) under `mod`."""
    domains: set[str] = set()
    blob_parts: list[str] = []
    gateway_loci: list[str] = []
    marker_loci: dict[str, list[str]] = {}
    for c in cds_list:
        for d in (c.get("sec_met_domains") or []):
            domains.add(str(d))
        gf = " ".join(str(c.get(k, "")) for k in ("product", "gene_functions"))
        blob_parts.append(gf)
        low = (gf + " " + " ".join(str(d) for d in (c.get("sec_met_domains") or []))).lower()
        lt = c.get("locus_tag", "?")
        if _hit(low, mod.gateway):
            gateway_loci.append(lt)
        for tier_name, pats in (("committed", mod.committed), ("tigr", mod.tigr),
                                ("warhead", mod.warhead), ("assembly", mod.assembly)):
            if _hit(low, pats):
                marker_loci.setdefault(tier_name, []).append(lt)
    blob = " ".join(blob_parts).lower()
    dom_blob = " ".join(domains).lower() + " " + blob
    bit = None
    if mod.gateway_bit_re is not None:
        bits = [float(x) for x in mod.gateway_bit_re.findall(" ".join(blob_parts))]
        bit = max(bits) if bits else None
    return {
        "gateway": bool(gateway_loci),
        "gateway_loci": gateway_loci,
        "gateway_bitscore": bit,
        "committed": _hit(dom_blob, mod.committed),
        "tigr": _hit(dom_blob, mod.tigr),
        "warhead_count": sum(1 for p in mod.warhead if p in dom_blob),
        "assembly": _hit(dom_blob, mod.assembly),
        "engine_flag": _hit(dom_blob, mod.engine_flag),
        "marker_loci": marker_loci,
        "n_cds": len(cds_list),
    }


def classify(m: dict, mod: ClassModule) -> tuple[str, str]:
    """Uniform committed-step tier logic (parameterised by the module)."""
    G, bit = m["gateway"], m["gateway_bitscore"]
    D, T, W, A = m["committed"], m["tigr"], m["warhead_count"], m["assembly"]
    weak = (bit is not None and bit < WEAK_GATEWAY_BIT)
    if not G:
        if m["engine_flag"]:
            return "SUSPECT", (f"{mod.name} called by antiSMASH/CCTT but NO gateway enzyme captured "
                               f"— not believable as de-novo {mod.name} biosynthesis (class trigger "
                               f"without the committed step)")
        return "NONE", f"no {mod.name} gateway or class flag"
    downstream = (T or W >= 1 or A)
    no_assembly = mod.assembly_required and not A
    if D and downstream and not weak and not no_assembly:
        return "HIGH", (f"{mod.name}: gateway + committed pull + downstream marker(s) — canonical "
                        f"committed signature with tailoring/assembly")
    if (D or ((T or W >= 2) and not mod.medium_requires_committed)) and not weak and not no_assembly:
        return "MEDIUM", (f"{mod.name}: gateway + partial corroboration (committed pull or >=2 "
                          f"associated markers) — believable capacity, signature incomplete")
    return "LOW", (f"{mod.name}: gateway only" + (" (weak hit)" if weak else "") +
                   f", no committed pull and <=1 associated marker — verify gateway identity; also "
                   f"hits the {mod.fp_superfamily}, a known false positive")


def _inventory_index(pkg: Path, strain: str) -> dict:
    idx = {}
    inv = pkg / f"{strain}_2_inventory.csv"
    if inv.exists():
        with open(inv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                idx[r.get("BGC_ID")] = r
    return idx


def _load_bgcs(pkg: Path) -> list[dict]:
    """Load [{bgc_id, cds:[...]}] from the sealed package's *_gene_context.jsonl."""
    jsonl = next(pkg.glob("*_gene_context.jsonl"), None)
    if not jsonl:
        return []
    out = []
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and "cds" in rec and "bgc_id" in rec:
                out.append(rec)
    return out


def read_excluded_contigs(path) -> frozenset:
    """(strain, contig) pairs to leave out, from a TSV with `strain` and `contig` columns."""
    if not path:
        return frozenset()
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if rows and not {"strain", "contig"} <= set(rows[0]):
        raise ValueError(f"{path}: needs columns strain and contig")
    return frozenset((r["strain"].strip(), r["contig"].strip()) for r in rows
                     if r.get("strain") and r.get("contig"))


def scan_package(pkg: Path, mod: ClassModule, excluded: frozenset = frozenset()) -> dict:
    """Run the LOCAL (per-BGC) and POOLED (per-strain) passes for one package and one class.
    CDS on an excluded (strain, contig) are left out of both passes."""
    strain = pkg.parent.name
    bgcs = _load_bgcs(pkg)
    if excluded:
        kept = []
        for rec in bgcs:
            cds = [c for c in rec["cds"] if (strain, str(c.get("contig", ""))) not in excluded]
            if cds:
                kept.append({**rec, "cds": cds})
        bgcs = kept
    inv = _inventory_index(pkg, strain)

    local_rows: list[dict] = []
    for rec in bgcs:
        m = scan_bgc(rec["cds"], mod)
        if not m["gateway"] and not m["engine_flag"]:
            continue  # not a candidate for this class
        tier, reason = classify(m, mod)
        if tier == "NONE":
            continue
        row = inv.get(rec["bgc_id"], {})
        local_rows.append({
            "strain": strain, "bgc_id": rec["bgc_id"], "cls": mod.name, "scope": "local",
            "believability": tier, "reason": reason,
            "gateway": m["gateway"], "gateway_bitscore": m["gateway_bitscore"],
            "committed": m["committed"], "tigr": m["tigr"], "warhead_count": m["warhead_count"],
            "assembly": m["assembly"],
            "products": row.get("Products", ""), "boundary": row.get("Boundary", ""),
            "length_kb": row.get("Length_kb", ""), "kcb_top": row.get("KCB_top", ""),
            "contig": row.get("Contig", ""), "gateway_loci": ";".join(m["gateway_loci"]),
            "n_cds": m["n_cds"],
        })
    local_rows.sort(key=lambda r: (RANK[r["believability"]], r["bgc_id"]))

    # POOLED per-strain pass: union all CDS across every region.
    pooled_row = None
    all_cds = [c for rec in bgcs for c in rec["cds"]]
    if all_cds:
        mp = scan_bgc(all_cds, mod)
        if mp["gateway"] or mp["engine_flag"]:
            ptier, preason = classify(mp, mod)
            if ptier != "NONE":
                best_local = min((RANK[r["believability"]] for r in local_rows), default=RANK["NONE"])
                split = RANK[ptier] < best_local  # strain-level stronger than any single BGC
                pooled_row = {
                    "strain": strain, "bgc_id": "(pooled)", "cls": mod.name, "scope": "pooled",
                    "believability": ptier, "reason": preason,
                    "gateway": mp["gateway"], "gateway_bitscore": mp["gateway_bitscore"],
                    "committed": mp["committed"], "tigr": mp["tigr"],
                    "warhead_count": mp["warhead_count"], "assembly": mp["assembly"],
                    "split_pathway_candidate": split,
                    "gateway_loci": ";".join(mp["gateway_loci"]),
                    "marker_loci": {k: sorted(set(v)) for k, v in mp["marker_loci"].items()},
                    "n_cds": mp["n_cds"],
                }
    return {"strain": strain, "cls": mod.name, "local": local_rows, "pooled": pooled_row}


def build_report(package_dirs, classes=None, excluded: frozenset = frozenset()) -> dict:
    """Run the engine over many packages for one or more classes; returns rows + counts."""
    mods = [REGISTRY[c] for c in (classes or list(REGISTRY))]
    local_all: list[dict] = []
    pooled_all: list[dict] = []
    for p in package_dirs:
        pkg = Path(p)
        for mod in mods:
            res = scan_package(pkg, mod, excluded)
            local_all.extend(res["local"])
            if res["pooled"]:
                pooled_all.append(res["pooled"])
    local_all.sort(key=lambda r: (r["cls"], RANK[r["believability"]], r["strain"], r["bgc_id"]))
    pooled_all.sort(key=lambda r: (r["cls"], RANK[r["believability"]], r["strain"]))
    counts: dict[str, dict[str, int]] = {}
    for r in local_all:
        counts.setdefault(r["cls"], {}).setdefault(r["believability"], 0)
        counts[r["cls"]][r["believability"]] += 1
    return {"classes": [m.name for m in mods], "counts": counts,
            "excluded_contigs": len(excluded), "local": local_all, "pooled": pooled_all}


def register_subparser(sub):
    """Register the `class-believability` post-seal subcommand (called from cli.py)."""
    cb = sub.add_parser("class-believability",
                        help="committed-step class believability (HIGH/MEDIUM/LOW/SUSPECT) per BGC "
                             "and pooled per strain; non-blocking, reads a sealed package")
    cb.add_argument("packages", nargs="+", help="sealed package dir(s)")
    cb.add_argument("--class", dest="classes", action="append",
                    choices=sorted(REGISTRY), help="limit to class(es) (default: all shipped)")
    cb.add_argument("--json", dest="json_out", default=None, help="write full JSON report here")
    cb.add_argument("--csv", dest="csv_out", default=None, help="write the local (per-BGC) rows here")
    cb.add_argument("--exclude-contigs", dest="exclude_contigs", default=None,
                    help="TSV with strain and contig columns; CDS on those contigs are left out")
    cb.set_defaults(func=run_from_args)
    return cb


def run_from_args(args) -> int:
    rep = build_report(args.packages, args.classes,
                       read_excluded_contigs(getattr(args, "exclude_contigs", None)))
    for cls in rep["classes"]:
        c = rep["counts"].get(cls, {})
        n_split = sum(1 for r in rep["pooled"]
                      if r["cls"] == cls and r.get("split_pathway_candidate"))
        _OUT.info('%s', f"[{cls}] " + " ".join(f"{t}={c.get(t, 0)}" for t in _TIER_ORDER) +
              f"  | pooled split-pathway candidates: {n_split}")
    if getattr(args, "json_out", None):
        Path(args.json_out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
        _OUT.info('%s', f"  json -> {args.json_out}")
    if getattr(args, "csv_out", None):
        cols = ["strain", "bgc_id", "cls", "believability", "gateway", "gateway_bitscore",
                "committed", "tigr", "warhead_count", "assembly", "products", "boundary",
                "length_kb", "kcb_top", "gateway_loci", "reason"]
        with open(args.csv_out, "w", newline="", encoding="utf-8") as f:
            w = _SafeDictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rep["local"])
        _OUT.info('%s', f"  csv  -> {args.csv_out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("packages", nargs="+", help="sealed package dir(s)")
    ap.add_argument("--class", dest="classes", action="append", choices=sorted(REGISTRY))
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--csv", dest="csv_out", default=None)
    ap.add_argument("--exclude-contigs", dest="exclude_contigs", default=None)
    return run_from_args(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
