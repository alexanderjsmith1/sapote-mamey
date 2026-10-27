"""phylo_postflight P6 does not report "tip count matches" when it found no input genomes.

With an empty or mistyped --genomes-dir, n_in was 0 and P6 printed PASS "Tip count matches
input genomes", having compared nothing.
"""
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _run(monkeypatch, tmp_path, n_fna):
    spec = importlib.util.spec_from_file_location("phylo_postflight_458", ROOT / "tools" / "phylo_postflight.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tree = tmp_path / "t.treefile"
    tree.write_text("((Streptomyces_a:0.1,Streptomyces_b:0.1):0.1,Kitasatospora_OUTGROUP:0.2);\n")
    gdir = tmp_path / "genomes"
    gdir.mkdir()
    for i in range(n_fna):
        (gdir / f"g{i}.fna").write_text(">x\nA\n")
    got = {}
    monkeypatch.setattr(mod, "_emit", lambda rep, a: got.setdefault("rep", rep))
    monkeypatch.setattr(sys, "argv", ["phylo_postflight", str(tree), "--genomes-dir", str(gdir)])
    with pytest.raises(SystemExit):
        mod.main()
    return [i for i in got["rep"].items if i["check"] == "P6"]


def test_no_inputs_is_not_a_match(monkeypatch, tmp_path):
    p6 = _run(monkeypatch, tmp_path, 0)
    assert len(p6) == 1 and p6[0]["status"] == "WARN" and "No input genomes" in p6[0]["message"]


def test_matching_count_still_passes(monkeypatch, tmp_path):
    p6 = _run(monkeypatch, tmp_path, 3)
    assert p6[0]["status"] == "PASS"
