"""EBI transport (v9.7.215): the XML->outfmt10 converter must preserve query-coverage (q_start/q_end)
and emit the 13-column -outfmt 10 that blastp_ingest accepts. Fixture is a real EBI XML result."""
import pathlib
from mamey.ebi_xml_to_outfmt10 import convert

FIX = pathlib.Path(__file__).parent / "fixtures" / "ebi_sample.xml"

def test_converter_preserves_coverage_and_13_cols():
    rows, qid, qlen = convert(str(FIX))
    assert qid and qlen > 0 and rows, (qid, qlen, len(rows))
    for r in rows:
        assert len(r) == 13, f"expected 13 outfmt10 cols, got {len(r)}: {r}"
    # coverage: q_start/q_end populated on at least the top hit (the field TSV drops)
    top = rows[0]
    qs, qe = top[6], top[7]
    assert qs and qe and int(qe) >= int(qs), f"coverage missing: q_start={qs} q_end={qe}"

def test_outfmt10_feeds_blastp_ingest_unchanged():
    import csv, tempfile, os
    from mamey.blastp_ingest import parse_hit_table
    rows, qid, qlen = convert(str(FIX))
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        csv.writer(f).writerows(rows); path = f.name
    parsed = parse_hit_table(path)   # the real ingest parser must accept it
    os.unlink(path)
    assert parsed and parsed[0]["q_start"] and parsed[0]["query_id"] == qid


# ---- to_outfmt10: the batch orchestrator around convert() had zero test coverage and, before
# today's fix, would crash the ENTIRE batch (unhandled exception) on one malformed/partial XML,
# losing every not-yet-converted locus and never writing the provenance sidecar. ------------------

def test_to_outfmt10_happy_path(tmp_path):
    from mamey.blastp_ebi import to_outfmt10, _save
    import shutil, json as _json

    state = str(tmp_path / "state.json")
    stem = state[:-5]
    shutil.copy(FIX, f"{stem}_ctg1_1.xml")
    _save(state, {"database": "uniprotkb_bacteria", "results": {"ctg1_1": "OK"}})

    out_csv = str(tmp_path / "out.csv")
    n = to_outfmt10(state, out_csv)
    assert n == 1
    with open(out_csv) as f:
        assert f.read().strip()  # rows were written
    with open(out_csv + ".provenance.json") as f:
        prov = _json.load(f)
    assert prov["n_queries"] == 1
    assert prov["n_failed"] == 0


def test_to_outfmt10_skips_malformed_xml_instead_of_crashing(tmp_path, capsys):
    from mamey.blastp_ebi import to_outfmt10, _save
    import shutil, json as _json

    state = str(tmp_path / "state.json")
    stem = state[:-5]
    shutil.copy(FIX, f"{stem}_good_locus.xml")
    (tmp_path / "state_bad_locus.xml").write_text("<html>rate limited", encoding="utf-8")
    _save(state, {"database": "uniprotkb_bacteria",
                   "results": {"good_locus": "OK", "bad_locus": "OK"}})

    out_csv = str(tmp_path / "out.csv")
    n = to_outfmt10(state, out_csv)   # must NOT raise
    assert n == 1  # only the good locus converted
    captured = capsys.readouterr()
    assert "bad_locus" in captured.err
    assert "WARN" in captured.err
    with open(out_csv + ".provenance.json") as f:
        prov = _json.load(f)
    assert prov["n_queries"] == 1
    assert prov["n_failed"] == 1
