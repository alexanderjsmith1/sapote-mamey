"""Hermetic suite coverage for the ARTS Genelist parse-failure distinguisher.

Black Cherry-2's card ships `test_arts_genelist_parse_failure.py`, which resolves the tool
through the `UUT` and `PRISTINE` environment variables. That works in its author's harness
but fails with `KeyError` the moment the file sits in `tests/`, so the defect it proves is
not covered by `pytest -q`. Every other test in the bundle — `test_arts_ingest.py` included —
resolves the tool from `parents[1]`. This file does the same.

It also pins the two cases the narrowed `except (ValueError, SyntaxError)` does not reach:
`literal_eval` returns successfully on a bare string or a dict literal, raising nothing, so
the row lands on the same silent zero the patch was written to close.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("arts_ingest", ROOT / "tools" / "arts_ingest.py")
ai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ai)

GOOD = "[['1','TIGR01048',100,200,'Core','lysA: diaminopimelate decarboxylase','Amino acid']]"
# An unescaped apostrophe in free text — the realistic malformation, since ARTS descriptions
# are carried through from Pfam/TIGRFAM.
MALFORMED = "[['1','TIGR01048',100,200,'Core','lysA: it's a decarboxylase','Amino acid']]"


def _analyze(tmp_path, genelist):
    t = tmp_path / "tables"
    t.mkdir(parents=True)
    (t / "bgctable.tsv").write_text(
        "#Cluster\tType\tSource\tLocation\tCore hits\tOther hits\tGenelist\n"
        f"cluster-6_1\tNRPS\tscaffold_6\t0 - 5000\t1\t0\t{genelist}\n")
    (t / "coretable.tsv").write_text(
        "#Core_gene\tDescription\tFunction\tDuplication\tBGC_Proximity\tPhylogeny\tKnown_target\n"
        "TIGR01048\tlysA\tAmino acid\tYes\tYes\t-\t-\n")
    (t / "duptable.tsv").write_text(
        "#Core_gene\tCount\tRef_median\tRef_stdev\tRef_RSD\tRef_ubiquity\t[Hits]\tDescription\n"
        "TIGR01048\t2.0\t1.0\t0.4\t0.7\t0.9\t[..]\tlysA\n")
    (t / "knownhits.tsv").write_text(
        "#Model\tDescription\tSequence id\tevalue\tbitscore\tSequence description\n"
        "RF0002\tAAC3\t6296\t1e-53\t179\tlclx\n")
    return ai.analyze(str(tmp_path), strain="AS-TEST")


def test_good_row_is_not_flagged(tmp_path):
    per_bgc, summary = _analyze(tmp_path, GOOD)
    assert per_bgc[0]["genelist_parse_failed"] is False
    assert per_bgc[0]["self_resistance_lead"] is True
    assert summary["n_genelist_parse_failures"] == 0


def test_genuine_empty_row_is_not_flagged(tmp_path):
    per_bgc, summary = _analyze(tmp_path, "[]")
    assert per_bgc[0]["genelist_parse_failed"] is False
    assert summary["n_genelist_parse_failures"] == 0


def test_malformed_row_is_flagged(tmp_path):
    per_bgc, summary = _analyze(tmp_path, MALFORMED)
    assert per_bgc[0]["genelist_parse_failed"] is True
    assert summary["n_genelist_parse_failures"] == 1


def test_bare_string_literal_is_flagged(tmp_path):
    """`literal_eval("'TIGR01048'")` returns a string and raises nothing."""
    per_bgc, summary = _analyze(tmp_path, "'TIGR01048'")
    assert per_bgc[0]["genelist_parse_failed"] is True
    assert summary["n_genelist_parse_failures"] == 1


def test_dict_literal_is_flagged(tmp_path):
    per_bgc, summary = _analyze(tmp_path, "{'TIGR01048': 2}")
    assert per_bgc[0]["genelist_parse_failed"] is True
    assert summary["n_genelist_parse_failures"] == 1


def test_flag_is_the_only_thing_separating_the_two_zeros(tmp_path):
    """Every derived gene-level field is identical; the flag alone carries the difference."""
    failed, _ = _analyze(tmp_path / "a", MALFORMED)
    empty, _ = _analyze(tmp_path / "b", "[]")
    derived = ("n_dup_proximal", "self_resistance_lead", "dup_proximal_core_genes",
               "n_multi_criteria", "lead_confidence")
    assert {k: failed[0][k] for k in derived} == {k: empty[0][k] for k in derived}
    assert failed[0]["genelist_parse_failed"] != empty[0]["genelist_parse_failed"]


def test_csv_carries_the_column(tmp_path):
    per_bgc, summary = _analyze(tmp_path, MALFORMED)
    out_csv, out_md = tmp_path / "o.csv", tmp_path / "o.md"
    ai.write_outputs(per_bgc, summary, str(out_csv), str(out_md))
    rows = out_csv.read_text().splitlines()
    assert rows[0].split(",")[-1] == "genelist_parse_failed"
    assert rows[1].split(",")[-1] == "True"
