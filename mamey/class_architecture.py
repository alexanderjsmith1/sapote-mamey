"""class_architecture.py — architecture-based class-capacity layer (Mamey, deterministic).

The keyword-marker layer (T43-*) reaches only ~30% of characterised antimicrobial classes (validated across a
29-cluster reference set). But the *architecture* — backbone type, PKS/NRPS module counts, and the tailoring
constellation — is annotation-robust (it survives the gene-symbol divergence that defeats keyword matching) and
class-diagnostic. This module classifies a BGC by that architecture into a claim-safe class-CAPACITY call.

It does NOT assert product identity and does NOT replace the markers; it produces a capacity call for the many
clusters the markers cannot see, as evidence for the judgment layer (Sapote).

Rules are grounded in the reference set (examples named per rule). Module counts are the deduplicated canonical
aSDomain PKS_KS / Condensation / AMP-binding counts; tailoring is the set of annotated tailoring enzyme classes.
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
from dataclasses import dataclass, field

from .crosswalk import contig_key

# tailoring enzyme classes -> annotation substrings (same vocabulary as the gene-by-gene profiler)
TAILORS = {
    # v9.7.335: these are substrings, so they match DEhalogenase. Six real BGCs
    # (AS-XXX BGC011/017/040/043, AS-XXX BGC002/009) assert "+ halogenase" capacity in the
    # user-facing Mode-B §2 line on a dehalogenase annotation — the opposite enzyme.
    # CCTT_PATTERNS already guards this exact hazard with (?<!de); TAILORS did not.
    "halogenase": ["(?<!de)halogenase", "(?<!de)halogenat"], # v9.7.335: "glycos" matched any glycoside hydrolase / Glycos_transf housekeeping gene,
    # which is half of the HIGH-confidence glycopeptide pre-check. Require a transferase.
    "glycosyltransferase": ["glycosyltransf", "glycosyl transf", "gtf", "transglycosyl"],
    "oxygenase": ["p450", "cytochrome", "oxygenase", "monooxygen"], "sulfotransferase": ["sulfotransf"],
    "methyltransferase": ["methyltransf", "methyltran"], "thioesterase": ["thioester", "nrps-te"],
    "prenyltransferase": ["prenyltransf", "ubia", "geranyl", "farnesyl"], "aminotransferase": ["aminotran"],
    "epimerase": ["epimer"], "cyclase_aromatase": ["polyketide_cyc", "aromatase", "cyclase", "tcmi", "tcmn"],
    "FMO": ["flavin", "fad-depend", "fad-binding", "fad_binding"], "epoxidase": ["epoxid"],
}


@dataclass
class ArchitectureCall:
    bgc_id: str
    capacity: str                       # claim-safe class-capacity label
    confidence: str                     # HIGH / MODERATE / LOW
    evidence: str
    products: list[str] = field(default_factory=list)
    pks_ks: int = 0
    nrps_c: int = 0
    nrps_a: int = 0
    tailoring: list[str] = field(default_factory=list)

    def as_capacity_line(self) -> str:
        return (f"{self.bgc_id}: biosynthetic capacity consistent with {self.capacity} "
                f"[{self.confidence}] — {self.evidence}")


def _ptypes(products) -> set[str]:
    return {str(p).lower() for p in (products or [])}


def classify_architecture(bgc_id: str, products, pks_ks: int, nrps_c: int, nrps_a: int,
                          tailoring) -> ArchitectureCall:
    """Pure decision procedure over architecture. Claim-safe capacity call."""
    p = _ptypes(products)
    tl = set(tailoring or [])
    nrps = max(nrps_c, nrps_a)
    has = lambda *names: any(n in tl for n in names)

    def call(cap, conf, ev):
        return ArchitectureCall(bgc_id, cap, conf, ev, list(products or []), pks_ks, nrps_c, nrps_a, sorted(tl))

    # 0a. Glycopeptide pre-check: must run before the multi-class guard because glycopeptide clusters
    #     commonly carry NRPS + PKS + T3PKS (3 real classes) which would otherwise route to "complex hybrid".
    #     Glycosyltransferases are the defining diagnostic (halogenases confirm but are not required).
    if nrps_c >= 6 and has("halogenase") and has("glycosyltransferase"):
        return call("glycopeptide", "HIGH",
                    f"NRPS ({nrps_c}C/{nrps_a}A) + halogenase + glycosyltransferase")  # teicoplanin, pekiskomycin
    # 0. Multi-class megacluster guard: >=3 distinct biosynthetic product classes (excluding noise annotations
    #    such as saccharide/other/terpene-precursor) indicates a complex hybrid locus that no single-class
    #    capacity label adequately represents. Run before any class-specific routing to avoid mislabelling a
    #    multi-class BGC (e.g. NRPS+PKS+RiPP+lanthipeptide+terpene) as just "small NRPS peptide". (Audit Flag D)
    _NOISE = {"other", "saccharide", "terpene-precursor"}
    _REAL_CLASSES = {"nrps", "nrps-like", "pks", "t1pks", "t2pks", "t3pks", "transat-pks",
                     "ripp", "ripp-like", "lanthipeptide-class-i", "lanthipeptide-class-ii",
                     "lanthipeptide-class-iii", "lanthipeptide-class-iv", "lassopeptide",
                     "terpene", "betalactone", "cdps", "nucleoside", "indole", "hserlactone",
                     "aminocoumarin", "arylpolyene", "2dos", "amglyccycl"}
    _real = {x for x in p if x in _REAL_CLASSES}
    if len(_real) >= 3:
        classes_str = "/".join(sorted(_real))
        return call(f"complex multi-class hybrid ({classes_str})", "MODERATE",
                    f">=3 biosynthetic classes ({len(_real)}) -- no single-class label adequate; see section 3 for class detail")
    # 1. CDPS / diketopiperazine (handled by T43-DKP too) -- albonoursin
    if "cdps" in p:
        return call("diketopiperazine (CDPS)", "HIGH", "CDPS backbone")
    # 2. aromatic type II PKS -- actinorhodin, pradimicin, fogacin, maduralactomycin
    if "t2pks" in p:
        extra = " + cyclase/aromatase" if has("cyclase_aromatase") else ""
        return call("aromatic type II PKS (aromatic polyketide)", "HIGH", f"T2PKS backbone{extra}")
    # 3. PKS-NRPS hybrid, small -- HSAF / PTM tetramate
    if pks_ks >= 1 and nrps_c >= 1 and nrps_a >= 1 and pks_ks <= 3 and nrps <= 3:
        return call("PKS-NRPS hybrid (tetramate/PTM-type)", "MODERATE",
                    f"hybrid: {pks_ks} KS + {nrps_c}C/{nrps_a}A")
    # 4. siderophore / metallophore — read antiSMASH's OWN product type (it types these directly). pseudomonine,
    #    scabichelin are antiSMASH "NRP-metallophore"; trust the supplied type rather than the generic NRPS call.
    if any("metallophore" in x or "siderophore" in x for x in p):
        return call("siderophore / metallophore", "HIGH", "antiSMASH product type = metallophore/siderophore")
    # 5. meroterpenoid — checked before NRPS, since a lone CoA-ligase AMP-binding domain (e.g. marinoterpin's
    #    benzoate-CoA ligase, C=0) is not a true NRPS module. prenyltransferase + a PKS backbone is distinctive.
    if has("prenyltransferase") and (pks_ks >= 1 or "t1pks" in p or "t2pks" in p or "pks" in p):
        return call("meroterpenoid (terpene + polyketide)", "MODERATE",
                    f"prenyltransferase + PKS ({pks_ks} KS)")  # marinoterpin
    if "terpene" in p and pks_ks == 0 and nrps == 0 and not has("prenyltransferase"):
        return call("terpene", "MODERATE", "terpene backbone")
    # terpene guard: if the product annotation is terpene-only (or terpene + other/saccharide noise) and no
    # significant PKS/NRPS domain evidence, route to terpene even if a stray domain hit leaked from a boundary
    # gene. This fixes the routing error where a terpene BGC with an adjacent NRPS-like gene gets misclassified
    # as "small NRPS peptide" because 1 condensation domain from a boundary CDS fires nrps_c >= 1. (Audit Flag C)
    _pcore = {x for x in p if x not in ("other","saccharide","terpene-precursor","terpene")}
    if "terpene" in p and not _pcore and nrps_c <= 1 and pks_ks == 0:
        return call("terpene (sesquiterpene / diterpene class)", "MODERATE",
                    "terpene product annotation; minor domain noise from boundary gene suppressed")
    # 5. NRPS-dominant (a real NRPS needs a condensation OR >=2 adenylation domains)
    if (nrps_c >= 1 or nrps_a >= 2) and pks_ks <= 2:
        # (glycopeptide already handled by rule 0a pre-check above; no duplicate needed here)
        if nrps >= 7:
            return call("large lipopeptide / acidic lipopeptide", "HIGH",
                        f"large NRPS ({nrps_c}C/{nrps_a}A)")  # A54145, 8D1
        return call("small NRPS peptide (β-lactam / nucleoside-peptide / siderophore class)", "MODERATE",
                    f"NRPS ({nrps_c}C/{nrps_a}A)" + (" + halogenase" if has("halogenase") else ""))  # nocardicin, pacidamycin, streptothricin
    # 6. PKS-dominant (modular)
    if pks_ks >= 3:
        if pks_ks >= 14 and has("glycosyltransferase"):
            return call("glycosylated macrolactone / macrolide", "HIGH",
                        f"large modular PKS ({pks_ks} KS) + glycosyltransferase")  # notonesomycin, ibomycin, monensin, ionostatin
        if pks_ks >= 14:
            return call("large modular PKS (macrolactone / polyene / polyether)", "MODERATE",
                        f"large modular PKS ({pks_ks} KS)" + (" + oxygenase" if has("oxygenase") else ""))  # nystatin, candicidin, corallopyronin
        return call("modular PKS (polyketide)", "LOW", f"modular PKS ({pks_ks} KS)")
    # 7. RiPP / other handled elsewhere
    if any(x in p for x in ("ripp", "lanthipeptide", "lassopeptide", "lanthipeptide-class")):
        return call("RiPP", "LOW", "RiPP backbone (see RiPP markers)")
    return call("unresolved (capacity not architecture-classifiable)", "LOW",
                f"products={sorted(p)} KS={pks_ks} NRPS={nrps_c}C/{nrps_a}A")


def _module_counts(bgc, doms):
    din = [d for d in doms if contig_key(d.contig) == contig_key(bgc.contig)
           and not (d.end < bgc.start or d.start > bgc.end)]
    ks = len({(d.start, d.end) for d in din if getattr(d, "feature_type", "") == "aSDomain" and getattr(d, "domain", "") == "PKS_KS"})
    c = len({(d.start, d.end) for d in din if getattr(d, "feature_type", "") == "aSDomain" and getattr(d, "domain", "") == "Condensation"})
    a = len({(d.start, d.end) for d in din if getattr(d, "feature_type", "") == "aSDomain" and getattr(d, "domain", "") == "AMP-binding"})
    return ks, c, a, din


def _tailoring(bgc, cds, din):
    cin = [x for x in cds if contig_key(x.contig) == contig_key(bgc.contig)
           and not (x.end < bgc.start or x.start > bgc.end)]
    blob = (" ".join((x.product or "") for x in cin) + " " +
            " ".join(getattr(d, "domain", "") or "" for d in din)).lower()
    # v9.7.335: patterns are now treated as REGEX (they were re.escape'd, i.e. literal). Every
    # pre-existing TAILORS pattern is regex-inert — plain alphanumerics with "-"/"_" only, which
    # are not metacharacters outside a character class — so their behaviour is unchanged. This
    # enables the (?<!de) negative lookbehind on the halogenase patterns.
    return [name for name, pats in TAILORS.items() if any(re.search(pp, blob) for pp in pats)]


def derive_architecture(bgc, cds, doms) -> ArchitectureCall:
    """Run the full architecture classification on a BGC record using its CDS + domain features."""
    ks, c, a, din = _module_counts(bgc, doms)
    tl = _tailoring(bgc, cds, din)
    return classify_architecture(getattr(bgc, "bgc_id", "?"), getattr(bgc, "products", []), ks, c, a, tl)


def annotate_architecture(bgcs, cds, doms) -> None:
    """Compute the architecture capacity call per BGC and store it on each record (in place).

    Called in the standard flow (run_source_scans) so the BGCRecord — and the triage record built from it —
    carries a claim-safe class-capacity call for the marker-invisible classes, always next to the contig.
    """
    failures = []
    for bgc in bgcs:
        try:
            call = derive_architecture(bgc, cds, doms)
            bgc.architecture_capacity = call.capacity
            bgc.architecture_class_confidence = call.confidence
        except Exception as exc:
            bgc.architecture_capacity = ""
            bgc.architecture_class_confidence = ""
            failures.append((getattr(bgc, "bgc_id", "?"), repr(exc)))
    if failures:
        # Per-BGC failures fail closed (blank capacity, same as before) — but a systematic bug here
        # was previously invisible: every BGC in a run could silently lose architecture_capacity with
        # no signal anywhere in the package. This is the minimum fix: surface it, don't change scoring.
        import sys
        shown = ", ".join(f"{bid} ({err})" for bid, err in failures[:5])
        more = f" … +{len(failures) - 5} more" if len(failures) > 5 else ""
        emit(f"[class_architecture] WARN: architecture_capacity failed for {len(failures)}/{len(bgcs)} "
              f"BGC(s): {shown}{more}", file=sys.stderr)


# Siderophore atlas projection: consumes bound owner outputs; no annotation scan.
def siderophore_evidence_projection(locus, genes, references, family_rules):
    """Keep locus chemistry unresolved; attach separately typed reference chemistry.

    Callers must admit source files with the governed readers before constructing
    this envelope. Hash and population fields are required, never inferred.
    """
    import hashlib
    identity_fields = ("strain", "full_node", "region", "bgc_alias")
    parts = [locus.get(k) for k in identity_fields]
    if any(not isinstance(x, str) or not x.strip() or x != x.strip() for x in parts):
        raise ValueError("EXACT_IDENTITY_HOLD")
    identity = " / ".join(parts)
    if locus.get("exact_identity") != identity:
        raise ValueError("EXACT_IDENTITY_HOLD")
    for key in ("source_member_sha256", "population_sha256"):
        value = locus.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("SOURCE_OR_POPULATION_PIN_HOLD")
    if not locus.get("population") or locus.get("taxonomy_state") not in ("SOURCE_BOUND", "UNBOUND"):
        raise ValueError("COHORT_TAXONOMY_HOLD")
    if type(locus.get("cds_count")) is not int or len(genes) != locus["cds_count"]:
        raise ValueError("MISSING_OR_INCOMPLETE_ROSTER_HOLD")
    orders = set()
    for gene in genes:
        if gene.get("exact_identity") != identity or gene.get("source_member_sha256") != locus["source_member_sha256"]:
            raise ValueError("GENE_LOCUS_BINDING_HOLD")
        order = gene.get("gene_order")
        if type(order) is not int or order in orders:
            raise ValueError("GENE_DUPLICATE_OR_ORDER_HOLD")
        orders.add(order)
        protein = gene.get("protein_sha256")
        if protein is not None and (len(protein) != 64 or any(c not in "0123456789abcdef" for c in protein)):
            raise ValueError("PROTEIN_IDENTITY_HOLD")
        if gene.get("membership") != "EXACT_REGION":
            raise ValueError("BOUNDARY_GENE_HOLD")
    products = locus.get("products")
    if not isinstance(products, list) or not all(isinstance(x, str) for x in products):
        raise ValueError("PRODUCT_STATE_HOLD")
    # Exact source product types describe route hypotheses, never chemistry.
    types = set(x.lower() for x in products)
    routes = sorted(({"NIS"} if "ni-siderophore" in types else set()) |
                    ({"NRPS"} if "nrp-metallophore" in types else set()))
    route = routes[0] if len(routes) == 1 else "unresolved"
    calls = []
    for ref in references:
        if ref.get("exact_identity") != identity:
            raise ValueError("REFERENCE_LOCUS_BINDING_HOLD")
        name = ref.get("family_name")
        rule = family_rules.get(name)
        item = dict(ref)
        item.update(reference_chemistry="unresolved", reference_route="unresolved",
                    applicability="UNREVIEWED_REFERENCE_FAMILY")
        if rule is not None:
            if rule.get("chemistry") not in ("hydroxamate", "catecholate", "carboxylate", "mixed", "other", "unresolved") or rule.get("route") not in ("NRPS", "NIS", "other", "unresolved") or not rule.get("citations"):
                raise ValueError("FAMILY_RULE_HOLD")
            item.update(reference_chemistry=rule["chemistry"], reference_route=rule["route"],
                        applicability="REFERENCE_ONLY_NOT_LOCUS_CHEMISTRY", citations=rule["citations"])
        calls.append(item)
    transport = [g for g in genes if g.get("transport_groups")]
    cassette = [g for g in genes if "siderophore_metallophore" in g.get("cassette_groups", [])]
    state = "SOURCE_PRODUCT_CLASS_OBSERVED" if routes else ("IRON_CASSETTE_CONTEXT_ONLY" if cassette else "NO_SELECTED_OWNER_CALL_NOT_BIOLOGICAL_ABSENCE")
    return dict(exact_identity=identity, population=locus["population"], population_sha256=locus["population_sha256"],
                source_member_sha256=locus["source_member_sha256"], taxonomy_state=locus["taxonomy_state"],
                taxonomy=locus.get("taxonomy"), products=products, chemistry="unresolved",
                chemistry_state="LOCUS_CHEMISTRY_NOT_ADMITTED", route=route, route_candidates=routes,
                route_state="SOURCE_PRODUCT_HYPOTHESIS" if routes else "UNRESOLVED",
                biosynthesis_state=state, uptake_state="GENERIC_TRANSPORT_ANNOTATIONS_ONLY" if transport else "NO_GENERIC_TRANSPORT_OWNER_CALL",
                production="unknown", secretion="unknown", activity="unknown", genes=genes,
                references=calls, iron_cassette_gene_count=len(cassette), transport_gene_count=len(transport),
                owner_capacity=locus.get("owner_capacity"),
                claim_ceiling="Source annotations and reference hypotheses; no synthesis, secretion, activity or chemical identity demonstrated")
