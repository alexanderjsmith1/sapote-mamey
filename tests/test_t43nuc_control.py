"""T43-NUC control-behavior test (derived from real antiSMASH cases, no strain data shipped).

Positive: a CDS whose antiSMASH rule-based annotation carries a `nikJ` domain — the path the
internal nikJ-bearing lead exercises (`/sec_met_domain="nikJ ..."`), even when `/product` is empty.
Negatives: pacidamycin (antibacterial uridyl-peptide, `pac*`, wrong subclass) and angustmycin
(simple purine nucleoside, non-peptidyl) must stay silent — the marker is antifungal-specific.

Fixtures are synthetic and contain no unpublished identifiers.
"""
from mamey.models import CDSFeature
from mamey.source_scans import _scan_patterns, CCTT_PATTERNS

NUC = {"T43-NUC_nucleoside": CCTT_PATTERNS["T43-NUC_nucleoside"]}


def _fires(cds):
    return _scan_patterns([cds], NUC)["counts"]["T43-NUC_nucleoside"] > 0


def test_t43nuc_fires_on_nikJ_secmet_domain():
    # locus-tag-only /product, but nikJ in the rule-based annotation (the NODE_162 pattern)
    cds = CDSFeature("ctg_pos", 1, 1371, 1, "ctg_pos_1", None, qualifiers={
        "gene_functions": ["biosynthetic (rule-based-clusters) nucleoside: nikJ"],
        "sec_met_domain": ["nikJ (E-value: 1.8e-172, bitscore: 563.5, seeds: 4)"],
    })
    assert _fires(cds), "T43-NUC must fire on a rule-based nikJ domain annotation"


def test_t43nuc_silent_on_pacidamycin_like():
    # antibacterial uridyl-peptide; pac* genes, no nik/nikkomycin/polyoxin token
    cds = CDSFeature("ctg_pac", 1, 900, 1, "ctg_pac_1", "hypothetical protein", qualifiers={
        "gene": ["pacB"], "note": ["uridyl-peptide / MraY translocase-I inhibitor"],
    })
    assert not _fires(cds), "T43-NUC must stay silent on antibacterial pacidamycin-like CDS"


def test_t43nuc_silent_on_angustmycin_like():
    # simple purine nucleoside (adenosine analog); generic 'nucleoside' is NOT a T43-NUC token
    cds = CDSFeature("ctg_ang", 1, 600, 1, "ctg_ang_1", "adenosine/purine nucleoside biosynthesis",
                     qualifiers={"note": ["decoyinine / angustmycin, non-peptidyl"]})
    assert not _fires(cds), "T43-NUC must stay silent on simple non-peptidyl nucleoside"
