"""phylo_postflight / phylo_preflight: --json never replaces an input or an earlier report.

Before: `phylo_postflight.py tree.nwk --json tree.nwk` replaced the tree with the JSON report, and
both tools replaced any existing --json file. Now the shared output check runs before any work.
"""
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
TREE = "((Streptomyces_a:0.1,Streptomyces_b:0.1):0.1,Kitasatospora_OUTGROUP:0.2);\n"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_464r3", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _main(mod, monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    return exc.value.code


def _fixture(tmp_path):
    tree = tmp_path / "t.treefile"
    tree.write_text(TREE)
    gdir = tmp_path / "genomes"
    gdir.mkdir()
    (gdir / "g0.fna").write_text(">x\nA\n")
    return tree, gdir


def test_postflight_refuses_the_tree_as_its_json(monkeypatch, tmp_path, capsys):
    tree, gdir = _fixture(tmp_path)
    mod = _load("phylo_postflight")
    code = _main(mod, monkeypatch, ["phylo_postflight", str(tree), "--json", str(tree)])
    assert code == 2 and "OUTPUT_REFUSED" in capsys.readouterr().err
    assert tree.read_text() == TREE


def test_postflight_refuses_a_genome_file_and_an_existing_report(monkeypatch, tmp_path, capsys):
    tree, gdir = _fixture(tmp_path)
    mod = _load("phylo_postflight")
    genome = gdir / "g0.fna"
    assert _main(mod, monkeypatch, ["phylo_postflight", str(tree), "--genomes-dir", str(gdir),
                                    "--json", str(genome)]) == 2
    assert genome.read_text() == ">x\nA\n"
    earlier = tmp_path / "report.json"
    earlier.write_text("earlier")
    assert _main(mod, monkeypatch, ["phylo_postflight", str(tree), "--json", str(earlier)]) == 2
    assert earlier.read_text() == "earlier"
    assert "already exists" in capsys.readouterr().err


def test_postflight_writes_a_fresh_report(monkeypatch, tmp_path):
    tree, gdir = _fixture(tmp_path)
    mod = _load("phylo_postflight")
    out = tmp_path / "fresh.json"
    code = _main(mod, monkeypatch, ["phylo_postflight", str(tree), "--json", str(out)])
    assert code in (0, 1) and out.is_file()
    assert tree.read_text() == TREE


def test_preflight_refuses_a_genome_and_the_tip_map(monkeypatch, tmp_path, capsys):
    _, gdir = _fixture(tmp_path)
    tipmap = tmp_path / "tips.tsv"
    tipmap.write_text("tree_tag\tspecies\n")
    mod = _load("phylo_preflight")
    genome = gdir / "g0.fna"
    assert _main(mod, monkeypatch, ["phylo_preflight", str(gdir), "--json", str(genome)]) == 2
    assert genome.read_text() == ">x\nA\n"
    assert _main(mod, monkeypatch, ["phylo_preflight", str(gdir), "--tip-map", str(tipmap),
                                    "--json", str(tipmap)]) == 2
    assert tipmap.read_text() == "tree_tag\tspecies\n"
    assert capsys.readouterr().err.count("OUTPUT_REFUSED") == 2
