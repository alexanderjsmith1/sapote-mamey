# Synthetic regression inputs only.
"""build_normalization_matrix finishes with an explicit state when no class reaches 5 BGCs.

Before: the matrix was empty and matplotlib's imshow raised "Invalid shape (0,)", so the run crashed
after writing the CSVs and before the recipe.
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
    spec = importlib.util.spec_from_file_location("build_normalization_matrix_464r3b16", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bank(tmp_path, n_bgcs_per_strain):
    bank = tmp_path / "bank"
    bank.mkdir()
    strains = {f"S{i}": {"organism": "x", "contigs": 2 ** i, "genome_bp": 8_000_000, "raw_bgcs": 3,
                         "corrected_bgcs": 3} for i in range(4)}
    bgcs = [{"sid": f"S{i}", "bgc_id": f"BGC{j:03d}", "products": "NRPS"}
            for i in range(4) for j in range(n_bgcs_per_strain)]
    (bank / "bgc_data.json").write_text(json.dumps({"strains": strains, "bgcs": bgcs}), encoding="utf-8")
    return bank


def test_no_class_at_threshold_writes_outputs_and_states_it(nm, tmp_path, monkeypatch, capsys):
    pytest.importorskip("matplotlib")
    out = tmp_path / "out"
    # 4 strains x 1 NRPS = 4 BGCs: below the 5-BGC class threshold
    monkeypatch.setattr("sys.argv", ["x", "--banked-dir", str(_bank(tmp_path, 1)), "--out-dir", str(out)])
    nm.main()
    for name in ("normalization_per_strain.csv", "normalization_class_ranking.csv", "normalization_matrix.csv"):
        assert (out / name).is_file(), name
    with (out / "normalization_class_ranking.csv").open() as h:
        assert list(csv.reader(h)) == [["class", "n_total", "corr_fragmentation", "regime"]]
    assert not (out / "fig_class_fragmentation.png").exists()
    assert not (out / "fig_normalization_matrix.png").exists()
    recipe = (out / "normalization_recipe.md").read_text(encoding="utf-8")
    assert "NO_CLASS_MET_THRESHOLD" in recipe
    assert "NO_CLASS_MET_THRESHOLD" in capsys.readouterr().out


def test_a_class_at_threshold_still_draws_figures(nm, tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    out = tmp_path / "out"
    # 4 strains x 2 NRPS = 8 BGCs: NRPS is ranked
    monkeypatch.setattr("sys.argv", ["x", "--banked-dir", str(_bank(tmp_path, 2)), "--out-dir", str(out)])
    nm.main()
    assert (out / "fig_class_fragmentation.png").is_file()
    assert "NO_CLASS_MET_THRESHOLD" not in (out / "normalization_recipe.md").read_text(encoding="utf-8")
