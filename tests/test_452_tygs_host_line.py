"""Card attine_452_tygs_host_line: T05 can print each isolate's host under its row label.

The owner asked (13 Oct) for the ant host genus under each strain on the dDDH figure, "(Atta sp.)". --host-column names
a strain-table column; a one-word host is set as a genus, "(<i>Atta</i> sp.)", a trailing "?" stays after the name,
and anything else is printed upright as given. Without the option the labels are unchanged. Synthetic data only.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tygs_452h", HERE / "tools" / "tygs_figures.py")
tf = importlib.util.module_from_spec(spec); spec.loader.exec_module(tf)


def test_host_label_forms():
    assert tf.host_label("Atta") == "(<i>Atta</i> sp.)"
    assert tf.host_label("Trachymyrmex?") == "(<i>Trachymyrmex</i>? sp.)"
    assert tf.host_label("Attine, genus not recorded") == "(Attine, genus not recorded)"
    assert tf.host_label("") == "" and tf.host_label(None) == ""


def test_row_label_keeps_its_old_form_without_a_host():
    assert tf.row_label("Genusa", "SYN-970") == "<i>Genusa</i> sp. SYN-970"
    assert tf.row_label("Familyaceae", "SYN-971") == "<i>Familyaceae</i> SYN-971"
    assert tf.row_label("Genusa", "SYN-970", "Hosta") == "<i>Genusa</i> sp. SYN-970<br>(<i>Hosta</i> sp.)"


def test_a_missing_host_column_is_refused(tmp_path, monkeypatch):
    tygs = tmp_path / "t.tsv"
    tygs.write_text("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4\tconfidence_interval_d4\n"
                    "U vs. T\t'SYN-970.fna'\tGenusa alpha DSM 1\t30.0\t[28.0 - 32.0]\n")
    st = tmp_path / "s.tsv"
    st.write_text("isolate\tgenus\tgroup\nSYN-970\tGenusa\tHosta\n")
    monkeypatch.setattr(sys, "argv", ["tygs_figures.py", "--tygs", str(tygs), "--strain-table", str(st),
                                      "--host-column", "host", "--out", str(tmp_path / "out")])
    with pytest.raises(SystemExit, match="HOST_COLUMN_MISSING"):
        tf.main()
    assert not (tmp_path / "out").exists()


def test_taller_rows_when_row_labels_have_two_lines():
    r = (HERE / "tools" / "tygs_figures.R").read_text()
    assert 'any(grepl("<br>", as.character(d$lab_md)))' in r
