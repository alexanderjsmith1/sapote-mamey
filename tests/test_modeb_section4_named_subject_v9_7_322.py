"""v9.7.322 Mode-B §4 guardrails for the recurring wrong-source failure.

Two things authors keep doing: (1) grabbing a thin/region-relative BLASTp source (core_batches,
few genes, bare accessions, no --xml) instead of the full package-tagged wave-2 hittable, then (2)
fighting the resulting PHANTOM_LOCUS error by rewording tags instead of switching source.
- SUBJECTS_UNDESCRIBED fires when §4 has verdicts but no named nr subject organism (the no--xml tell).
- The PHANTOM_LOCUS message now names the wrong-source root cause.
The shipped exemplars (the bar) must never trip the new WARN.
"""
import glob
import inspect

import mamey.modeb_structure_gate as G

EXEMPLARS = glob.glob("docs/reference/modeb_exemplars/*_exemplar.md")

THIN_CARD = """## §1 Scaffold
over-merged enediyne
## §4 Gene-by-gene interpretation
| Locus | BLASTp top hit | %id | Reconciliation |
|---|---|---|---|
| ctg8_24 | WP_359083344.1 | 99.2 | CONFIRM |
| ctg8_35 | WP_030821137.1 | 98.1 | CONFIRM |
## §5 Core logic
y
"""

NAMED_CARD = """## §4 Gene-by-gene
| Locus | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|
| ctg8_205 | type I PKS [*Amycolatopsis* sp.] | 88.1 | CONFIRM |
## §5
z
"""


def test_exemplars_never_flag_subjects_undescribed():
    assert EXEMPLARS, "exemplars must ship"
    for f in EXEMPLARS:
        md = open(f).read()
        codes = [x["code"] for x in G._section4_named_subject_findings(md)]
        assert "SUBJECTS_UNDESCRIBED" not in codes, f"{f} false-positived"


def test_thin_bare_accession_card_flags():
    codes = [x["code"] for x in G._section4_named_subject_findings(THIN_CARD)]
    assert "SUBJECTS_UNDESCRIBED" in codes


def test_named_subject_card_clean():
    codes = [x["code"] for x in G._section4_named_subject_findings(NAMED_CARD)]
    assert "SUBJECTS_UNDESCRIBED" not in codes


def test_subjects_undescribed_is_warn_not_blocking():
    f = G._section4_named_subject_findings(THIN_CARD)[0]
    assert f["severity"] == "WARN"
    assert "SUBJECTS_UNDESCRIBED" not in G._READINESS_BLOCKING


def test_phantom_locus_message_names_wrong_source():
    src = inspect.getsource(G._phantom_locus_findings)
    assert "core_batches" in src and "package-tagged" in src and "--xml" in src
