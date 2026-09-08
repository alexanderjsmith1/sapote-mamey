"""Regression tests for the P4/P11 defect family (v9.7.184): a figure/classifier reading a value
from the wrong column or lacking a pattern for the real token, silently bucketing into a catch-all.
From the 2026-07-03 reference-strain audit."""
import re

from mamey.source_scans import DOMAIN_CLASS_PATTERNS


def _classify(token):
    for cls, pats in DOMAIN_CLASS_PATTERNS.items():
        for p in pats:
            if re.search(p, token):
                return cls
    return "Other_domain"


def test_p11_pks_reductive_loop_tokens_classify_not_other():
    # \bDH\b never matched inside "PKS_DH" (underscore is a word char) -> silent Other_domain.
    # The literal PKS_<abbr> pattern must now win.
    for tok in ("PKS_KS", "PKS_AT", "PKS_DH", "PKS_ER", "PKS_KR", "PKS_ACP"):
        assert _classify(tok) == tok, f"{tok} misfiled as {_classify(tok)}"


def test_p11_registry_and_literal_parity_preserved():
    # the runtime dict is built from the registry; the literal PKS_DH pattern must be present in it
    assert "PKS_DH" in DOMAIN_CLASS_PATTERNS["PKS_DH"]


def test_p4_all_interior_triage_resolves_boundary_not_locator():
    # the bug: _first returned Assembly_Locator (a locus string) instead of Boundary (the status),
    # so every BGC bucketed as "Other". With Boundary read first, the status token wins.
    from mamey.figures_smoke import _first, _LOC_COLS
    row = {"BGC_ID": "BGC001", "Boundary": "Interior",
           "Assembly_Locator": "NZ_CP076457.1 region001"}
    assert _first(row, _LOC_COLS) == "Interior"   # not the locus string


def test_p4_boundary_read_before_locator():
    from mamey.figures_smoke import _LOC_COLS
    # Boundary must precede Assembly_Locator so the status token wins over the locus string
    assert _LOC_COLS.index("Boundary") < _LOC_COLS.index("Assembly_Locator")


def test_p1_single_gbk_file_parses_not_badzip(tmp_path):
    # blastp-online --package advertises "GBK/ZIP"; a bare .gbk used to hit BadZipFile.
    from mamey.parsers import read_genbank_records
    gbk = tmp_path / "test.region001.gbk"
    gbk.write_text(
        "LOCUS       test         30 bp    DNA     linear   BCT 01-JAN-2026\n"
        "FEATURES             Location/Qualifiers\n"
        "     CDS             1..30\n"
        "                     /locus_tag=\"t_1\"\n"
        "                     /translation=\"MKV\"\n"
        "ORIGIN\n"
        "        1 atgaaagttt aaggccaatt ggccaattgg\n"
        "//\n")
    recs = read_genbank_records(str(gbk))
    assert len(recs) == 1
    assert recs[0][0] == "test.region001.gbk"
