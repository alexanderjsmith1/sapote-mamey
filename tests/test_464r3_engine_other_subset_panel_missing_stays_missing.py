"""build_subset_panel: unavailable coupling and missing length stay blank; outputs are fresh.

Before: a locus with no coupling record was written `n` (an observed negative), a missing
length was written 0 and plotted at 0 kb, `--replot` with a missing CSV rebuilt the table from the
bank, and every output name was replaced on a re-run.
"""
import csv
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _load():
    spec = importlib.util.spec_from_file_location("bsp_464r3", ROOT / "tools" / "build_subset_panel.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bank(tmp_path, coupling=True):
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"bgcs": [
        {"sid": "SYN1", "bgc_id": "BGC001", "region": "region001", "contig": "ctg_1", "products": "phenazine",
         "length_kb": 21.5, "edge_status": "Interior", "closest_kcb_product": "x", "closest_mibig": "BGC0000001"},
        {"sid": "SYN1", "bgc_id": "BGC002", "region": "region002", "contig": "ctg_2", "products": "phenazine",
         "edge_status": "Edge", "closest_kcb_product": "", "closest_mibig": ""},
    ]}))
    (bank / "strains.json").write_text(json.dumps([{"sid": "SYN1", "organism": "Streptomyces synthetic"}]))
    if coupling:
        (bank / "tfbs_coupling.json").write_text(json.dumps({"SYN1": {"BGC001": ["SARP"]}}))
    return bank


def _run(mod, monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["build_subset_panel", *argv])
    mod.main()


def test_missing_coupling_and_length_are_blank(tmp_path, monkeypatch, capsys):
    mod = _load()
    bank, out = _bank(tmp_path), tmp_path / "figs"
    _run(mod, monkeypatch, ["--banked-dir", str(bank), "--tag", "phenazine", "--out-dir", str(out)])
    rows = {r["bgc_id"]: r for r in csv.DictReader((out / "subset_phenazine_loci.csv").open())}
    assert rows["BGC001"]["sarp"] == "y" and rows["BGC001"]["kb"] == "21.5"
    assert rows["BGC002"]["sarp"] == "" and rows["BGC002"]["kb"] == ""
    assert rows["BGC002"]["contig"] == "ctg_2"
    assert "1 loci have no recorded length" in capsys.readouterr().out


def test_no_coupling_table_is_not_a_negative(tmp_path, monkeypatch):
    mod = _load()
    bank, out = _bank(tmp_path, coupling=False), tmp_path / "figs"
    _run(mod, monkeypatch, ["--banked-dir", str(bank), "--tag", "phenazine", "--out-dir", str(out)])
    assert {r["sarp"] for r in csv.DictReader((out / "subset_phenazine_loci.csv").open())} == {""}


def test_rerun_into_the_same_folder_is_refused(tmp_path, monkeypatch):
    mod = _load()
    bank, out = _bank(tmp_path), tmp_path / "figs"
    argv = ["--banked-dir", str(bank), "--tag", "phenazine", "--out-dir", str(out)]
    _run(mod, monkeypatch, argv)
    before = (out / "subset_phenazine_loci.csv").read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run(mod, monkeypatch, argv)
    assert exc.value.code == 2
    assert (out / "subset_phenazine_loci.csv").read_bytes() == before


def test_replot_with_a_missing_csv_is_refused_not_rebuilt(tmp_path, monkeypatch):
    mod = _load()
    bank, out = _bank(tmp_path), tmp_path / "figs"
    missing = tmp_path / "subset_phenazine_loci.csv"
    with pytest.raises(SystemExit) as exc:
        _run(mod, monkeypatch, ["--banked-dir", str(bank), "--replot", "--csv", str(missing), "--out-dir", str(out)])
    assert exc.value.code == 2 and not missing.exists()
