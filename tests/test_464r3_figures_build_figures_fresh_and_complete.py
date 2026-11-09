"""tools/build_figures.py: the compute route never replaces existing CSVs or figures, and a replot
that skips a figure says so and exits 1."""
import csv
import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_figures.py"
spec = importlib.util.spec_from_file_location("build_figures_464r3", TOOL)
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)


def _stub(rows, path):
    Path(path).write_text(f"{len(rows)} rows\n")


@pytest.fixture
def two_figs(monkeypatch):
    figs = {
        "fig_a": (lambda a: ([{"x": "1"}], ["x"]), _stub),
        "fig_b": (lambda a: ([{"x": "2"}], ["x"]), _stub),
    }
    monkeypatch.setattr(bf, "FIGS", figs)
    return figs


def test_compute_refuses_an_existing_edited_csv(tmp_path, two_figs, capsys):
    bank = tmp_path / "bank"; bank.mkdir()
    out = tmp_path / "figs"; out.mkdir()
    edited = out / "fig_a_data.csv"
    edited.write_text("x\nedited by hand\n")
    rc = bf.main(["--banked-dir", str(bank), "--out-dir", str(out)])
    assert rc == 2
    assert edited.read_text() == "x\nedited by hand\n"
    assert not (out / "fig_b.png").exists()
    assert "refused" in capsys.readouterr().err


def test_compute_into_a_new_folder_writes_everything(tmp_path, two_figs):
    bank = tmp_path / "bank"; bank.mkdir()
    out = tmp_path / "figs"
    assert bf.main(["--banked-dir", str(bank), "--out-dir", str(out)]) == 0
    for name in ("fig_a_data.csv", "fig_a.png", "fig_b_data.csv", "fig_b.png", "figures_recipe.md"):
        assert (out / name).exists(), name


def test_replot_with_a_missing_csv_reports_and_exits_1(tmp_path, two_figs, capsys):
    bank = tmp_path / "bank"; bank.mkdir()
    out = tmp_path / "figs"; out.mkdir()
    with open(out / "fig_a_data.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["x"], ["1"]])
    rc = bf.main(["--banked-dir", str(bank), "--out-dir", str(out), "--replot"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "1 of 2 figures drawn" in err and "fig_b" in err
    assert (out / "fig_a.png").exists() and not (out / "fig_b.png").exists()


def test_replot_leaves_the_edited_csv_untouched(tmp_path, two_figs):
    bank = tmp_path / "bank"; bank.mkdir()
    out = tmp_path / "figs"; out.mkdir()
    for name in ("fig_a", "fig_b"):
        (out / f"{name}_data.csv").write_text("x\nedited\n")
    assert bf.main(["--banked-dir", str(bank), "--out-dir", str(out), "--replot"]) == 0
    assert (out / "fig_a_data.csv").read_text() == "x\nedited\n"
