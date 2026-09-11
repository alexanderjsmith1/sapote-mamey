#!/usr/bin/env python3
"""domain_reference.py — the Mode-B domain functional-context dictionary (DOMREF-01).

Closes the DOMREF-01 gap: for years the Mode-B cards/figures referred to a
`domain_reference.tsv` that was never shipped in the bundle. This module ships the
*substrate* — a deterministic function->category vocabulary — so any consumer
(cards, figures, `tools/build_domain_reference.py`) resolves each antiSMASH domain to
one functional **category** + a one-line biochemical **context** the same way.

Two layers:
  * ``CURATED`` — hand-written one-liners for the ~30 aSDomain core-vocabulary domains
    (PKS_KS/PKS_AT/PCP/Condensation/AMP-binding/Thioesterase ...) that ship from
    antiSMASH with no description text.
  * ``RULES`` — an ordered (regex -> category, fallback-context) table applied to every
    other domain (Pfam / TIGRFAM), first match wins; the antiSMASH description is kept
    as the context when present, otherwise the rule's fallback.

CLAIM SAFETY (mandatory): every entry is a statement of what the *domain* does
biochemically (its catalytic/structural role) — NEVER a statement that a given BGC makes
a given product. Categories are function buckets, not activity or structure claims. This
is a reference dictionary, not a scorer: it ranks nothing and moves no tier.

This vocabulary is *complementary* to `mamey.mamey_markers.MAMEY_MARKERS` (which drives
detection): MARKERS answer "is this a diagnostic marker?"; this answers "what is this
domain's biochemical role, in one line?". `tools/build_domain_matrix.py` keeps sourcing
its detection vocab from MAMEY_MARKERS; this dictionary is the human-facing context layer.
"""
from __future__ import annotations

import csv
import glob
import os
import re

# --- curated one-liners for the aSDomain core vocabulary (domains with no antiSMASH text) ---
# value = (category, context). Kept strictly factual: the biochemical role of the domain.
CURATED: dict[str, tuple[str, str]] = {
    "PKS_KS":            ("PKS-core", "Ketosynthase (KS): condenses the extender unit onto the growing polyketide chain (C–C bond)."),
    "PKS_AT":            ("PKS-core", "Acyltransferase (AT): selects and loads the extender unit (e.g. malonyl / methylmalonyl-CoA)."),
    "PKS_KR":            ("PKS-reductive", "Ketoreductase (KR): reduces the β-keto group to a β-hydroxyl."),
    "PKS_DH":            ("PKS-reductive", "Dehydratase (DH): removes water from β-hydroxyl to give an α,β-enoyl."),
    "PKS_DHt":           ("PKS-reductive", "Dehydratase variant (DHt): PKS dehydratase-type domain."),
    "PKS_DH2":           ("PKS-reductive", "Dehydratase (DH2): second dehydratase subtype."),
    "PKS_ER":            ("PKS-reductive", "Enoylreductase (ER): reduces the enoyl double bond to a saturated methylene."),
    "PKS_PP":            ("carrier", "Acyl carrier protein (ACP/PP): phosphopantetheine tether for the polyketide intermediate."),
    "PCP":               ("carrier", "Peptidyl carrier protein (PCP/T): phosphopantetheine tether for the peptide intermediate."),
    "ACP":               ("carrier", "Acyl carrier protein (ACP): phosphopantetheine tether for the acyl/polyketide chain."),
    "MT":                ("tailoring-methylation", "Methyltransferase (MT): transfers a methyl group (C-, N-, or O-methylation) onto the intermediate."),
    "cMT":               ("tailoring-methylation", "C-methyltransferase (cMT): carbon methylation within an assembly-line module."),
    "nMT":               ("tailoring-methylation", "N-methyltransferase (nMT): nitrogen methylation within an assembly-line module."),
    "oMT":               ("tailoring-methylation", "O-methyltransferase (oMT): oxygen methylation within an assembly-line module."),
    "Epimerization":     ("NRPS-core", "Epimerization (E) domain: converts an L-amino acid residue to the D-configuration."),
    "Heterocyclization": ("NRPS-core", "Heterocyclization (Cy) domain: condenses and cyclizes Cys/Ser/Thr to azol(in)e rings."),
    "CAL_domain":        ("loading", "Co-enzyme A ligase / loading (CAL) domain: activates and loads a starter acid."),
    "TD":                ("release", "Terminal reductase (TD): reductively releases the chain (aldehyde/alcohol product)."),
    "A-OX":              ("NRPS-core", "Adenylation domain with integral oxidase (A-OX): activates the amino acid and oxidizes it."),
    "cAT":               ("PKS-core", "Cis-acyltransferase docking (cAT) region associated with the AT domain."),
    "ECH":               ("tailoring-other", "Enoyl-CoA hydratase / crotonase (ECH): β-branching or hydratase tailoring step."),
    "FkbH":              ("loading", "FkbH-like loading domain: generates/loads a glycolate-derived starter unit."),
    "PKS_Docking_Nterm": ("structural", "N-terminal docking domain: mediates ordered PKS subunit–subunit assembly."),
    "PKS_Docking_Cterm": ("structural", "C-terminal docking domain: mediates ordered PKS subunit–subunit assembly."),
    "Trans-AT_docking":  ("structural", "Trans-AT docking region: recruits a standalone (trans-acting) acyltransferase."),
    "NRPS-COM_Nterm":    ("structural", "NRPS communication domain (N-term): mediates ordered NRPS subunit assembly."),
    "NRPS-COM_Cterm":    ("structural", "NRPS communication domain (C-term): mediates ordered NRPS subunit assembly."),
    "X":                 ("NRPS-core", "X domain: cytochrome-P450 recruitment domain found in glycopeptide NRPS."),
    "Interface":         ("structural", "Inter-domain interface region."),
    "Amino-transfer":    ("NRPS-core", "Aminotransferase domain: introduces an amino group into the intermediate."),
    "Condensation":      ("NRPS-core", "Condensation (C) domain: forms the peptide (amide) bond between two carrier-bound residues."),
    "AMP-binding":       ("NRPS-core", "Adenylation (A) domain: selects and activates the amino / aryl acid substrate."),
    "AMP-binding_C":     ("NRPS-core", "Adenylation domain C-terminal subdomain (A domain)."),
    "TIGR01733":         ("NRPS-core", "Amino-acid adenylation (A) domain (TIGR01733)."),
    "PP-binding":        ("carrier", "Phosphopantetheine attachment site: the carrier-protein tether point (ACP/PCP)."),
    "Thioesterase":      ("release", "Thioesterase (TE): hydrolyzes or macrocyclizes the chain to release the product."),
}

# ordered (regex-on-name-or-desc -> (category, fallback context)); first match wins. Applied only when
# the domain is not in CURATED. Context defaults to the antiSMASH description when present.
RULES: list[tuple[str, str, str | None]] = [
    (r"halogen",                         "tailoring-halogenation", "Halogenase: installs a halogen (Cl/Br) onto the scaffold."),
    (r"p450|cytochrome|monooxygenase|Rieske|Oxidored|oxidoreduct|dehydrogenase|reductase|oxidase|FAD|flavin|Ferredoxin",
                                         "tailoring-oxidoreduction", "Oxidoreductase-type tailoring enzyme."),
    (r"methyltransf|Methyltransf|SAM-",  "tailoring-methylation", "Methyltransferase-type tailoring enzyme."),
    (r"Glycos|Glyco_tran|glycosyl|NDP|Epimerase|dTDP|sugar|Hexose|aminotransferase|Aminotran",
                                         "tailoring-glycosylation", "Sugar biosynthesis / glycosyltransfer tailoring enzyme."),
    (r"YcaO|PqqD|RRE|Lant|LanC|Lanthi|thiopeptide|Nif11|TfuA|SagB|azol|Cytolysin|Bottromycin|microviridin|lasso|Lasso",
                                         "RiPP-maturation", "RiPP precursor-maturation enzyme (leader binding / heterocyclization / crosslink)."),
    (r"Terpene|terpen|SQHop|SQS_PSY|polyprenyl|prenyl|Polyprenyl|Squalene|IPP|Lycopene|Phytoene",
                                         "terpene/prenyl", "Terpene / prenyl biosynthesis enzyme."),
    (r"Beta-lactam|beta-lactam|Aminoglyc|VanC|Van[A-Z]|efflux|resistance|Resistance|Streptomycin_3|Fom|Bcr",
                                         "resistance", "Resistance-associated marker (self-protection / efflux)."),
    (r"ABC_tran|ABC2|MFS|BPD_transp|Peripla|permease|OEP|transport|TonB|SBP_bac|FecCD|MacB",
                                         "transport", "Transport / export (ABC or MFS-type membrane transporter)."),
    (r"HTH|TetR|LuxR|MerR|AraC|GerE|Sigma|sigma|Response_reg|HisKA|LacI|PadR|MarR|WhiB|ROK|Fis|Crp",
                                         "regulatory", "Transcriptional regulator / two-component signalling."),
    (r"Condensation|Cy_",                "NRPS-core", "NRPS condensation-type domain."),
    (r"Ketoacyl|ketoacyl|Acyl_transf|KAsynt|Chal_sti|PksD",
                                         "PKS-core", "PKS chain-extension domain (KS/AT-associated)."),
    (r"DUF\d",                           "uncharacterized", None),
    (r"Peptidase|Inhibitor_I9|Peptidase_S8|Reprolysin",
                                         "tailoring-other", "Peptidase / protease-type accessory enzyme."),
    (r"Abhydrolase|hydrolase|Esterase|Lipase|Alpha-amylase|CBM",
                                         "tailoring-other", "Hydrolase / esterase-type accessory enzyme."),
]

_COMPILED_RULES = [(re.compile(pat), cat, ctx) for pat, cat, ctx in RULES]

# categories that represent genuine biosynthetic machinery (used by novelty / realistic-count consumers)
BIOSYNTHETIC_CATEGORIES = frozenset({
    "PKS-core", "PKS-reductive", "NRPS-core", "carrier", "loading", "release",
    "tailoring-oxidoreduction", "tailoring-methylation", "tailoring-glycosylation",
    "tailoring-halogenation", "tailoring-other", "RiPP-maturation", "terpene/prenyl",
})

CAT_ORDER: list[str] = [
    "PKS-core", "PKS-reductive", "NRPS-core", "carrier", "loading", "release",
    "tailoring-oxidoreduction", "tailoring-methylation", "tailoring-glycosylation",
    "tailoring-halogenation", "tailoring-other", "RiPP-maturation", "terpene/prenyl",
    "transport", "regulatory", "resistance", "structural", "uncharacterized", "other",
]


def categorize(domain: str, desc: str = "") -> tuple[str, str]:
    """Return (category, context) for a domain name + optional antiSMASH description.

    Deterministic and side-effect free. CURATED wins; then the ordered RULES table on the
    combined ``"<domain> <desc>"`` haystack; else ``("other", desc)``.
    """
    if domain in CURATED:
        return CURATED[domain]
    hay = f"{domain} {desc or ''}"
    for rx, cat, ctx in _COMPILED_RULES:
        if rx.search(hay):
            return cat, ((desc or "").strip() or ctx or "")
    return ("other", (desc or "").strip())


def is_curated(domain: str) -> bool:
    return domain in CURATED


# --------------------------------------------------------------------------------------
# Package readers — build a per-package domain reference from the sealed outputs.
# --------------------------------------------------------------------------------------

def _find_one(package_dir: str, suffix: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(package_dir, f"*{suffix}")))
    return hits[0] if hits else None


def iter_package_domains(package_dir: str) -> dict[str, dict]:
    """Collect every unique domain name seen in a sealed package.

    Reads two banked tables (either may be absent):
      * ``*_domains.csv``        — column ``domain`` (+ ``pfam_acc``); aSDomain/Pfam feature names.
      * ``*_3_antismash_hmm.csv``— columns ``domain_name`` (+ ``accession``, ``description``).

    Returns ``{domain: {"pfam_acc", "description", "n_bgcs"}}`` merged across both, where
    ``description`` prefers the antiSMASH-HMM text (the only table that ships one).
    """
    out: dict[str, dict] = {}
    seen_bgcs: dict[str, set] = {}

    dpath = _find_one(package_dir, "_domains.csv")
    if dpath:
        with open(dpath, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                dom = (r.get("domain") or "").strip()
                if not dom:
                    continue
                e = out.setdefault(dom, {"pfam_acc": "", "description": ""})
                if not e["pfam_acc"] and r.get("pfam_acc"):
                    e["pfam_acc"] = r["pfam_acc"]
                seen_bgcs.setdefault(dom, set()).add(r.get("bgc_id", ""))

    hpath = _find_one(package_dir, "_3_antismash_hmm.csv")
    if hpath:
        with open(hpath, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                dom = (r.get("domain_name") or "").strip()
                if not dom:
                    continue
                e = out.setdefault(dom, {"pfam_acc": "", "description": ""})
                if not e["pfam_acc"] and r.get("accession"):
                    e["pfam_acc"] = r["accession"]
                if not e["description"] and r.get("description"):
                    e["description"] = r["description"]
                seen_bgcs.setdefault(dom, set()).add(r.get("bgc_id", ""))

    for dom, e in out.items():
        e["n_bgcs"] = len({b for b in seen_bgcs.get(dom, set()) if b})
    return out


def build_reference_rows(package_dir: str) -> list[dict]:
    """Return sorted reference rows for one sealed package (category order, then n_bgcs desc)."""
    doms = iter_package_domains(package_dir)
    rows = []
    for dom, e in doms.items():
        cat, ctx = categorize(dom, e.get("description", ""))
        rows.append({
            "domain": dom, "pfam_acc": e.get("pfam_acc", ""), "category": cat,
            "context": ctx, "n_bgcs": e.get("n_bgcs", 0),
            "antismash_desc": e.get("description", ""), "curated": int(is_curated(dom)),
        })
    rows.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99,
                             -int(x["n_bgcs"]), x["domain"]))
    return rows
