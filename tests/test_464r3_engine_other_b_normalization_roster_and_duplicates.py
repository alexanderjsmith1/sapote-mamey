# Synthetic regression inputs only.
"""build_normalization_matrix reports BGC rows outside the strain roster and refuses duplicate rows.

Before: BGC rows whose strain id was not in the bank roster vanished from every output with no
report, and a replot accepted two rows for one strain, so deleting one left the strain in.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_normalization_matrix.py"


@pytest.fixture(scope="module")
def nm():
    spec = importlib.util.spec_from_file_location("build_normalization_matrix_464r3b", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bank(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    strains = {f"S{i}": {"organism": "x", "contigs": 2 ** i, "genome_bp": 8_000_000, "raw_bgcs": 20,
                         "corrected_bgcs": 18} for i in range(12)}
    bgcs = [{"sid": f"S{i}", "bgc_id": f"BGC{j:03d}", "products": "NRPS"}
            for i in range(12) for j in range(1, i % 4 + 2)]
    bgcs += [{"sid": "GHOST", "bgc_id": "BGC001", "products": "NRPS"},
            {"sid": "GHOST", "bgc_id": "BGC002", "products": "terpene"}]
    (bank / "bgc_data.json").write_text(json.dumps({"strains": strains, "bgcs": bgcs}), encoding="utf-8")
    return bank


def test_unrostered_bgc_rows_are_counted_not_lost(nm, tmp_path):
    unmatched = {}
    rows = nm.compute_per_strain(str(_bank(tmp_path)), unmatched)
    assert unmatched == {"GHOST": 2}
    assert sorted(r["sid"] for r in rows) == sorted(f"S{i}" for i in range(12))


def _row(nm, sid):
    r = {"sid": sid, "organism": "x", "contigs": 3, "genome_Mbp": 8, "raw_BGC": 20, "corrected_BGC": 20,
         "den_ecto+napaa": 1, "den_terpene": 1, "den_halogenase": 1}
    for k in nm.CLASSES:
        r[f"cls_{k}"] = 1
    return r


def test_duplicate_strain_rows_are_refused(nm):
    with pytest.raises(nm.DuplicateStrainRows, match="S1"):
        nm.derive([_row(nm, "S0"), _row(nm, "S1"), _row(nm, "S1")])


def test_main_reports_unmatched_rows_in_the_recipe(nm, tmp_path, monkeypatch, capsys):
    pytest.importorskip("matplotlib")
    out = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["x", "--banked-dir", str(_bank(tmp_path)), "--out-dir", str(out)])
    nm.main()
    recipe = (out / "normalization_recipe.md").read_text(encoding="utf-8")
    assert "GHOST (2)" in recipe and "not counted" in recipe
    assert "GHOST (2)" in capsys.readouterr().out


def test_replot_with_a_duplicate_row_stops(nm, tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    rows = [_row(nm, "S0"), _row(nm, "S0")]
    with (out / "normalization_per_strain.csv").open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    monkeypatch.setattr("sys.argv", ["x", "--out-dir", str(out), "--replot"])
    with pytest.raises(SystemExit, match="more than one per-strain row"):
        nm.main()
    assert not (out / "normalization_class_ranking.csv").exists()
