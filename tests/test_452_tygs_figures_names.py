"""v9.7.452: tools/tygs_figures.py keeps collection numbers whole across a wrapped TYGS line, and gives a
family-level name no "sp." in the T05 row label. These tests construct temporary formatting tables."""
import importlib.util, sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "tygs_figures.py"
spec = importlib.util.spec_from_file_location("tygs_figures", TOOL)
tf = importlib.util.module_from_spec(spec); spec.loader.exec_module(tf)

HDR = ("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d0\tconfidence_interval_d0\tdigital_ddh_d4\tconfidence_interval_d4\t"
       "digital_ddh_d6\tconfidence_interval_d6\tpercent_gc_diff\n")
TSV = HDR + ("U vs. T\t'AS-971.fna'\tGenusa alpha NRRL B- 24058\t90\t[88 - 92]\t21.7\t[19.4 - 24.1]\t90\t[88 - 92]\t0.2\n"
             "U vs. T\t'AS-972.fna'\tGenusb beta DSM 2\t90\t[88 - 92]\t31.0\t[28.6 - 33.5]\t90\t[88 - 92]\t0.1\n")


def test_join_wrapped_keeps_hyphenated_numbers_whole():
    assert tf.join_wrapped("Genusa alpha NRRL B-", "24058") == "Genusa alpha NRRL B-24058"
    assert tf.join_wrapped("Genusa alpha", "DSM 43854") == "Genusa alpha DSM 43854"
    assert tf.join_wrapped("", "DSM 1") == "DSM 1"


def test_tidy_subject_repairs_an_earlier_parse_only_inside_a_number():
    assert tf.tidy_subject("Genusa alpha NRRL B- 24058") == "Genusa alpha NRRL B-24058"
    assert tf.tidy_subject("Genusa alpha-beta DSM 1") == "Genusa alpha-beta DSM 1"     # hyphen not before a digit: unchanged
    assert tf.tidy_subject("Genusa alpha CGMCC 4.7433") == "Genusa alpha CGMCC 4.7433"


def test_row_label_family_rank_has_no_sp():
    assert tf.row_label("Familiaceae", "AS-971") == "<i>Familiaceae</i> AS-971"
    assert tf.row_label("Genusb", "AS-972") == "<i>Genusb</i> sp. AS-972"


def test_data_table_carries_tidy_names_and_row_labels(tmp_path, monkeypatch):
    p = tmp_path / "t.tsv"; p.write_text(TSV)
    s = tmp_path / "s.tsv"
    s.write_text("isolate\tgenus\tgroup\tsimilarity\nAS-971\tFamiliaceae\tSite A\tNA\nAS-972\tGenusb\tSite A\tNA\n")
    out = tmp_path / "out"
    monkeypatch.setattr(tf.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", ["tygs_figures.py", "--tygs", str(p), "--strain-table", str(s), "--out", str(out),
                                      "--palette", str(p)])
    tf.main()
    rows = [l.split("\t") for l in (out / "T05_T06_data.tsv").read_text().splitlines()]
    head, body = rows[0], {r[0]: dict(zip(rows[0], r)) for r in rows[1:]}
    assert head[-2:] == ["row_label", "reference_label"]
    assert body["AS-971"]["closest_type_strain"] == "Genusa alpha NRRL B-24058"
    assert body["AS-971"]["row_label"] == "<i>Familiaceae</i> AS-971"
    assert body["AS-972"]["row_label"] == "<i>Genusb</i> sp. AS-972"


def test_reference_label_rule6_form():
    assert tf.reference_label("Genusa alpha", "DSM 1", "GCA_000000001.2") == "<i>Genusa alpha</i> DSM 1<br>(GCA_000000001)"
    assert tf.reference_label("Genusa alpha subsp. beta", "JCM 2", "") == "<i>Genusa alpha</i> subsp. <i>beta</i> JCM 2"
    assert tf.reference_label("Genusa alpha", "DSM 1", "IMG 2918313847") == "<i>Genusa alpha</i> DSM 1<br>(IMG 2918313847)"


def _run(tmp_path, monkeypatch, names_text):
    p = tmp_path / "t.tsv"; p.write_text(TSV)
    s = tmp_path / "s.tsv"; s.write_text("isolate\tgenus\tgroup\tsimilarity\nAS-971\tFamiliaceae\tSite A\tNA\nAS-972\tGenusb\tSite A\tNA\n")
    n = tmp_path / "names.tsv"; n.write_text(names_text)
    monkeypatch.setattr(tf.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", ["tygs_figures.py", "--tygs", str(p), "--strain-table", str(s), "--out", str(tmp_path / "out"),
                                      "--palette", str(p), "--reference-names", str(n)])
    tf.main()
    return tmp_path / "out"


def test_reference_names_drawn_and_receipted(tmp_path, monkeypatch):
    import json
    out = _run(tmp_path, monkeypatch, "tygs_closest_type_strain\tname\tstrain\taccession\n"
               "Genusa alpha NRRL B- 24058\tGenusa alpha\tNRRL B-24058\tGCA_000000001.1\n"
               "Genusb beta DSM 2\tGenusb beta\tDSM 2\t\n")
    rows = [l.split("\t") for l in (out / "T05_T06_data.tsv").read_text().splitlines()]
    body = {r[0]: dict(zip(rows[0], r)) for r in rows[1:]}
    assert body["AS-971"]["reference_label"] == "<i>Genusa alpha</i> NRRL B-24058<br>(GCA_000000001)"
    assert body["AS-972"]["reference_label"] == "<i>Genusb beta</i> DSM 2"
    assert json.loads((out / "RECEIPT.json").read_text())["reference_names_without_accession"] == ["AS-972"]


def test_reference_names_must_cover_every_drawn_type_strain(tmp_path, monkeypatch):
    try:
        _run(tmp_path, monkeypatch, "tygs_closest_type_strain\tname\tstrain\taccession\nGenusb beta DSM 2\tGenusb beta\tDSM 2\tGCA_2\n")
        assert False
    except SystemExit as e:
        assert "REFERENCE_NAMES_MISSING" in str(e) and "NRRL B-24058" in str(e)
    assert not (tmp_path / "out").exists()


def test_legend_title_is_passed_to_the_renderer(tmp_path, monkeypatch):
    p = tmp_path / "t.tsv"; p.write_text(TSV)
    s = tmp_path / "s.tsv"; s.write_text("isolate\tgenus\tgroup\tsimilarity\nAS-971\tFamiliaceae\tSite A\tNA\n")
    calls = []
    monkeypatch.setattr(tf.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    monkeypatch.setattr(sys, "argv", ["tygs_figures.py", "--tygs", str(p), "--strain-table", str(s), "--out", str(tmp_path / "o"),
                                      "--palette", str(p), "--legend-title", "Genus or family (16S rRNA)"])
    tf.main()
    assert calls[0][-2] == "Genus or family (16S rRNA)" and calls[0][-1] == ""
