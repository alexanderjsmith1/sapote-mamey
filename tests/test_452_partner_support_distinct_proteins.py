"""Partner support counts distinct genome proteins: two reference genes that match one protein are one find.

Before, two reference rows whose best match was the same genome protein made each other SUPPORTED (an "adjacent find"
at 0 bp) and together met the two-find contig support gate.
"""
from mamey.ref_completion import partner_checks, partner_tests

CORE = {"contig": "ctgA", "start": 0, "end": 5000}
REF = [{"i": i, "id": f"g{i:03d}", "name": f"r{i}", "product": "enzyme"} for i in (1, 2)]


def _prots(second_protein_start=None):
    prots = {"pA": {"contig": "ctgA", "start": 100, "end": 1000, "contig_len": 50000, "aa": "M" * 300,
                    "shown": "TST-1 / ctgA"},
             "q1": {"contig": "ctgB", "start": 200, "end": 1100, "contig_len": 60000, "aa": "M" * 300,
                    "shown": "TST-1 / ctgB"}}
    if second_protein_start is not None:
        prots["q2"] = dict(prots["q1"], start=second_protein_start, end=second_protein_start + 900)
    return prots


def _rows(second="q1"):
    return [{"reference_gene": 1, "status": "MISSING_FOUND_CLEAR", "best_protein": "q1", "best_contig": "ctgB"},
            {"reference_gene": 2, "status": "MISSING_FOUND_CLEAR", "best_protein": second, "best_contig": "ctgB"}]


def _hits(second="q1"):
    return [{"qseqid": "g001", "sseqid": "q1", "pident": 60.0, "qcovhsp": 90.0, "bitscore": 300.0},
            {"qseqid": "g002", "sseqid": second, "pident": 55.0, "qcovhsp": 90.0, "bitscore": 250.0}]


def test_two_reference_genes_on_one_protein_do_not_support_each_other():
    rows = _rows()
    partner_checks(rows, _prots(), _hits(), CORE, "BGC0000001")
    assert [r["adjacent_finds"] for r in rows] == [0, 0]
    assert [r["partner_verdict"] for r in rows] == ["SINGLE_GENE", "SINGLE_GENE"]


def test_two_distinct_adjacent_proteins_still_support_each_other():
    rows = _rows("q2")
    partner_checks(rows, _prots(3000), _hits("q2"), CORE, "BGC0000001")
    assert [r["adjacent_finds"] for r in rows] == [1, 1]
    assert [r["partner_verdict"] for r in rows] == ["SUPPORTED", "SUPPORTED"]


def test_contig_support_needs_two_distinct_proteins():
    rows = [dict(r, partner_verdict="SUPPORTED") for r in _rows()]   # a legacy or direct verdict on one protein
    out = partner_tests(CORE, REF, rows, [], _prots(), [], _hits(), lambda a, b: None)
    assert len(out) == 1 and out[0]["finds"] == 2
    assert out[0]["support_ok"] is False and out[0]["accepted"] is False


def test_contig_support_from_two_distinct_proteins_is_unchanged():
    rows = [dict(r, partner_verdict="SUPPORTED") for r in _rows("q2")]
    out = partner_tests(CORE, REF, rows, [], _prots(3000), [], _hits("q2"), lambda a, b: None)
    assert len(out) == 1 and out[0]["support_ok"] is True and out[0]["accepted"] is True
