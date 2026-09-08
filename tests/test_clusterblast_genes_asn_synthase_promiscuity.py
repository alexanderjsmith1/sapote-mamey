"""BLACK_CHERRY_377 regression: `_CORE_DOMAIN_HINTS` in mamey/clusterblast_genes.py must not
trust a bare 'Asn_synthase' domain hit as unconditional CORE evidence.

Ground truth already established elsewhere in THIS codebase: `mamey/bgc_decomp.py` deliberately
does NOT add Asn_synthase to its own gene-classification allowlist, with the explicit comment
"NOT added: ... Asn_synthase (too promiscuous)" / "Asn_synthase (widespread primary metabolite
enzyme — the lasso cyclase IS an Asn_synthase but the domain itself is too promiscuous to trust
alone)", and `tests/test_bgc_decomp.py` pins `_classify_gene("Asn_synthase") == "unknown"`.

`mamey/clusterblast_genes.py::_CORE_DOMAIN_HINTS`, used by `_role_of()` to classify a CDS as
CORE for RG-GMCI rescue-eligibility purposes (`rescue_functional_complementarity` ->
`functional_rescue_class`, which `scoring.py::_rescue_eligible` and
`rescue_two_proof.py::_logic_proof` both gate a real rescue claim on), contradicts that
established policy: it lists bare "asn_synthase" as an unconditional CORE trigger with no
co-occurrence guard. A single incidental primary-metabolism asparagine-synthetase gene swept
into a BGC region window (a real, common antiSMASH region-boundary artifact — the exact
mis-anchor/primary-metabolism false-positive class this project already guards against
elsewhere, e.g. scoring.py's primary-metabolism guard) gets counted as a biosynthetic CORE gene,
inflating that fragment's core-fraction and can flip a genuinely ACCESSORY_ONLY pair into a false
COMPLEMENTARY (or other non-blocking) `functional_rescue_class` — letting a false split-pathway
rescue claim through the very two-proof gates this session already hardened in scoring.py /
rggmci.py.
"""
from mamey.clusterblast_genes import (functional_profile_from_gene_context,
                                       rescue_functional_complementarity, _core_fraction)


def _fragment(rows):
    return functional_profile_from_gene_context({"F": rows})["F"]


def test_bare_asn_synthase_is_not_trusted_as_core():
    """A lone gene whose ONLY signal is a bare 'Asn_synthase' domain hit, with no antiSMASH
    gene_kind=='biosynthetic' tag (i.e. antiSMASH's own rule engine did NOT call this gene part
    of the cluster's biosynthetic core) must not, by itself, be counted as a core gene. This
    matches bgc_decomp.py's own "too promiscuous" ruling on the same domain name."""
    prof = _fragment([
        {"gene_kind": "", "gene_functions": "", "sec_met_domains": ["Asn_synthase"], "product": ""},
    ])
    assert prof["core"] == 0, (
        f"bare Asn_synthase (no gene_kind=='biosynthetic') was counted as core: {prof!r}"
    )


def test_genuinely_accessory_only_pair_not_flipped_by_incidental_asn_synthase():
    """Two fragments that are BOTH genuinely accessory-only (no real biosynthetic core gene on
    either side) must classify ACCESSORY_ONLY -- not get flipped to COMPLEMENTARY just because
    one fragment happens to carry one incidental, non-rule-triggered Asn_synthase-domain gene
    (a realistic primary-metabolism sweep-in, not a lasso-peptide cyclase call)."""
    # Fragment A: three genuinely tailoring genes, nothing else. No core anywhere.
    frag_a = _fragment([
        {"gene_kind": "biosynthetic-additional", "gene_functions": "", "sec_met_domains": ["p450"], "product": ""},
        {"gene_kind": "biosynthetic-additional", "gene_functions": "", "sec_met_domains": ["methyltransferase"], "product": ""},
        {"gene_kind": "biosynthetic-additional", "gene_functions": "", "sec_met_domains": ["halogenase"], "product": ""},
    ])
    # Fragment B: one genuinely tailoring gene, plus ONE incidental primary-metabolism
    # asparagine-synthetase gene swept into the region window (gene_kind not 'biosynthetic' --
    # antiSMASH's own cluster rule did NOT call this gene part of the core).
    frag_b = _fragment([
        {"gene_kind": "biosynthetic-additional", "gene_functions": "", "sec_met_domains": ["p450"], "product": ""},
        {"gene_kind": "", "gene_functions": "", "sec_met_domains": ["Asn_synthase"], "product": "asparagine synthetase"},
    ])
    assert frag_a["core"] == 0 and frag_b["core"] == 0, (
        f"neither fragment has a real biosynthetic core gene by construction: a={frag_a!r} b={frag_b!r}"
    )
    res = rescue_functional_complementarity(frag_a, frag_b)
    assert res["functional_rescue_class"] == "ACCESSORY_ONLY", (
        f"two genuinely core-free fragments were NOT classified ACCESSORY_ONLY: {res!r} "
        f"(a_core_fraction={res.get('a_core_fraction')}, b_core_fraction={res.get('b_core_fraction')})"
    )


def test_genuine_lasso_cyclase_still_reads_core_via_gene_kind():
    """Backward-compat pin: a REAL lasso-peptide cyclase Asn_synthase gene -- one antiSMASH's own
    rule engine actually tagged gene_kind=='biosynthetic' -- must still classify as core. The
    fix must not weaken genuine antiSMASH-rule-confirmed core-gene detection; it only removes
    blind trust in the bare domain-name string as a standalone signal."""
    prof = _fragment([
        {"gene_kind": "biosynthetic", "gene_functions": "", "sec_met_domains": ["Asn_synthase"], "product": ""},
    ])
    assert prof["core"] == 1
