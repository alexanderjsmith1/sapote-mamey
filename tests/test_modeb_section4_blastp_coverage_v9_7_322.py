"""v9.7.322 §4_BLASTP_COVERAGE — WARN-first gate demanding real per-gene BLASTp in §4.

Reconciled from the other chat's Mode-B investigation (solution B). A §4 can carry a table + prose
that still rests on antiSMASH-Pfam only ("pending BLASTp") and pass the length-based depth gate.
This gate requires core rows to carry a %id value + a CONFIRM/REFINE/OVERTURN reconciliation.
Exemplars (the bar) must never flag; the honest DATA_REQUESTED path passes with a WARN.
"""
import glob
import mamey.modeb_structure_gate as G

EXEMPLARS = glob.glob("docs/reference/modeb_exemplars/*_exemplar.md")

PFAM_ONLY = "## §4\n| Locus | domains |\n|---|---|\n| ctg1_1 ● | KS |\n| ctg1_2 ● | KR |\n## §5\n"
THIN = ("## §4\n| Locus | BLASTp | %id | Recon |\n|---|---|---|---|\n"
        "| ctg1_1 ● | PKS [Streptomyces] | 88.1% | CONFIRM |\n"
        "| ctg1_2 ● | - | - | pending |\n| ctg1_3 ● | - | - | pending |\n"
        "| ctg1_4 ● | - | - | pending |\n## §5\n")
REQUESTED = ("## §4\n| Locus | domains |\n|---|---|\n| ctg1_1 ● | KS |\n\n"
             "REQUEST: region GBKs — BLASTp pending, requested from the operator.\n## §5\n")


def _codes(md):
    return [f["code"] for f in G._section4_blastp_coverage_findings(md)]


def test_exemplars_never_flag_coverage():
    assert EXEMPLARS
    for f in EXEMPLARS:
        codes = _codes(open(f).read())
        assert not ({"BLASTP_ABSENT", "BLASTP_THIN"} & set(codes)), f"{f} false-positived: {codes}"


def test_pfam_only_flags_absent():
    assert "BLASTP_ABSENT" in _codes(PFAM_ONLY)


def test_partial_coverage_flags_thin():
    assert "BLASTP_THIN" in _codes(THIN)


def test_requested_data_passes_with_warn():
    codes = _codes(REQUESTED)
    assert codes == ["DATA_REQUESTED"]


def test_all_codes_are_warn_not_blocking():
    for md in (PFAM_ONLY, THIN, REQUESTED):
        for f in G._section4_blastp_coverage_findings(md):
            assert f["severity"] == "WARN"
    assert not ({"BLASTP_ABSENT", "BLASTP_THIN", "DATA_REQUESTED"} & G._READINESS_BLOCKING)
