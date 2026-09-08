"""§3 gene-census deepener — generate a size-proportionate biosynthetic-core section.

For gene-rich clusters whose §3 falls below the size-scaled floor (600 + 60*domain_genes),
this builds a fuller §3 by walking the domain-bearing genes grouped into functional roles,
written as readable prose (not a table dump). Pure gene-table read — no invented content.
Each gene is cited by its real ctg locus, length, and antiSMASH domain content.
"""
import re
from collections import defaultdict, OrderedDict

# Functional role buckets, matched against antiSMASH domain names (first match wins).
# Order matters — assembly-line core first, then tailoring, then accessory.
_ROLE_PATTERNS = [
    ("assembly-line core (NRPS/PKS)", [
        "AMP-binding", "NRPS-A", "Condensation", "C1_LCL", "C2_LCL", "C2_DCL",
        "Heterocyclization",  # v9.7.116: Cy domains are assembly-line core (heterocycle-forming
        # modified condensation domains in thiazoline/oxazoline NRPS); antiSMASH emits the full
        # "Heterocyclization" token alongside the Cy1..Cy7 subtype tags — match the full name
        # (distinctive, collision-safe) rather than the bare CyN tags.
        "Ketoacyl-synt", "PKS_KS", "PKSI-KS", "Acyl_transf", "PKS_AT", "PP-binding",
        "PCP", "ACP", "Thioesterase", "NRPS-te", "Epimerization", "PKS_KR", "PKS_DH",
        "PKS_ER", "KR", "Aminotran_1_2"]),
    ("RiPP maturation", [
        "YcaO", "LanB", "LanC", "LanM", "Lant_dehyd", "rSAM", "PqqD", "Nif11",
        "ranthipeptide", "lasso", "sacti", "thiopeptide", "Lanthipeptide", "TfuA"]),
    ("redox tailoring", [
        "p450", "P450", "FAD_binding", "Amino_oxidase", "Flavin", "NAD_binding",
        "adh_short", "Epimerase", "Hexose_dehydrat", "FA_hydroxylase", "Oxidored",
        "NMO", "2OG-Fe", "Ferric_reduct", "Aldedh", "Aldo_ket_red"]),
    ("group transfer / decoration", [
        "Methyltransf", "Glycos_transf", "Glyco_tran", "Acetyltransf", "Aminotran",
        "DegT_DnrJ", "Hexose", "dTDP", "sugar", "Bac_rhamnosid", "halogenase",
        "Trp_halogen", "Prenyltrans", "polyprenyl", "SQS_PSY", "Caroten",
        "Glycos_transf_2", "G3P_acyltransf"]),
    ("precursor / building-block supply", [
        "Thiolase", "FA_synthesis", "Fatty_acid", "biotin", "BioY", "Chorismate",
        "DAHP", "SIS", "Pribosyltran", "CbiA", "CbiG", "Cob", "corrin", "SQS"]),
    ("regulation", [
        "TetR", "HTH", "LuxR", "MerR", "GntR", "MarR", "LysR", "Response_reg",
        "HisKA", "HATPase", "Trans_reg", "Sigma", "WhiB", "ArsR", "PaaX", "WYL"]),
    ("transport / resistance / efflux", [
        "ABC_tran", "BPD_transp", "MFS", "SBP_bac", "CbiQ", "Peptidase", "oligo_HPY",
        "Abhydrolase", "Metallophos", "transporter", "efflux"]),
]
_CORE_ROLE = "assembly-line core (NRPS/PKS)"


def _role_of(domains):
    dt = " ".join(domains)
    for role, keys in _ROLE_PATTERNS:
        if any(k.lower() in dt.lower() for k in keys):
            return role
    return "other biosynthetic / accessory"


def build_size_scaled_s3(bgc_id, genes, edge_status, length_kb, products,
                         existing_s3=""):
    """Augment an existing §3 with a proportionate gene census from the gene table.

    genes: list of dicts with locus_tag, aa_length, sec_met_domains.
    existing_s3: the current §3 body — kept in full (its interpretation is preserved);
    the structured census is appended. Returns the combined §3 body (no header).
    """
    dom_genes = []
    for g in genes:
        d = (g.get("sec_met_domains") or "").strip()
        if d in ("—", "", "None"):
            continue
        doms = [x.strip() for x in d.split(";") if x.strip()]
        dom_genes.append((g["locus_tag"], int(g.get("aa_length") or 0), doms))

    n_cds = len(genes)
    n_dom = len(dom_genes)

    # group by functional role, preserving role order
    by_role = OrderedDict((role, []) for role, _ in _ROLE_PATTERNS)
    by_role["other biosynthetic / accessory"] = []
    for locus, aa, doms in dom_genes:
        by_role[_role_of(doms)].append((locus, aa, doms))

    parts = []
    if existing_s3.strip():
        parts.append(existing_s3.strip())
        parts.append("")
    parts.append(f"Gene-by-gene biosynthetic census ({n_dom} domain-bearing genes of "
                 f"{n_cds} CDS, grouped by functional role):")

    for role, members in by_role.items():
        if not members:
            continue
        if role == _CORE_ROLE:
            members = sorted(members, key=lambda x: -x[1])
        header = (f"\n• {role.capitalize()} ({len(members)} gene"
                  + ("s" if len(members) != 1 else "") + "): ")
        seg = []
        for locus, aa, doms in members:
            dom_show = ", ".join(doms[:6]) + ("…" if len(doms) > 6 else "")
            seg.append(f"{locus} ({aa} aa; {dom_show})")
        parts.append(header + "; ".join(seg) + ".")

    core = by_role.get(_CORE_ROLE, [])
    if core:
        biggest = max(core, key=lambda x: x[1])
        parts.append(f"\nThe largest assembly-line protein is {biggest[0]} ({biggest[1]} aa), "
                     "the principal biosynthetic engine; the surrounding tailoring, transfer, "
                     "and supply genes elaborate and export the core scaffold.")

    return "\n".join(parts)
