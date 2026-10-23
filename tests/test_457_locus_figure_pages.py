"""Locus-map figure pages as a bundle route (owner, 21 Oct, ruling 290: GECCO "for the mibig entry too, as part of the bundle
and not a moss-specific script").

tools/locus_figure_pages.py replaces the dated-folder spec wrapper; tools/gap_rescue_locus_map.py draws a GECCO track under
the reference row from GECCO run on the MIBiG GenBank file (load_reference_gecco) and gains a 9.0 in landscape width;
tools/gap_directed_rescue.py passes --mibig-gecco-dir and --print-width landscape. Synthetic data only."""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("labels447b", ROOT / "tests" / "test_447_gap_rescue_locus_map_anchor_and_labels.py")
fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
glm = fx.glm
_inspected_figures = fx._inspected_figures
spec2 = importlib.util.spec_from_file_location("lfp457", ROOT / "tools" / "locus_figure_pages.py")
lfp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(lfp)


def gecco_genes(tmp_path, rows, record="BGC0000000"):
    p = tmp_path / "ref.genes.tsv"
    p.write_text("sequence_id\tprotein_id\tstart\tend\tstrand\taverage_p\tmax_p\n" +
                 "".join(f"{record}\t{record}_{i}\t{s}\t{e}\t+\t{pr}\t{pr}\n" for i, (s, e, pr) in enumerate(rows, 1)))
    return p


def test_reference_genes_bind_to_gecco_genes_by_overlap(tmp_path):
    ref = [{"s": 0.0, "e": 1.0}, {"s": 1.2, "e": 2.0}, {"s": 5.0, "e": 6.0}]
    g = gecco_genes(tmp_path, [(1, 1000, 0.9), (1201, 1990, 0.4)])           # nothing covers the third gene
    r = glm.load_reference_gecco(g, None, ref)
    assert r["p"] == {0: 0.9, 1: 0.4}
    assert r["binding"]["reference_genes_scored"] == 2 and r["binding"]["reference_genes_unscored"] == 1


def test_a_table_of_several_records_is_refused(tmp_path):
    g = tmp_path / "two.genes.tsv"
    g.write_text("sequence_id\tprotein_id\tstart\tend\tstrand\taverage_p\tmax_p\nA\tA_1\t1\t100\t+\t0.9\t0.9\nB\tB_1\t1\t100\t+\t0.9\t0.9\n")
    with pytest.raises(ValueError, match="REFERENCE_GECCO_RECORDS"):
        glm.load_reference_gecco(g, None, [{"s": 0.0, "e": 0.1}])


def test_reference_track_is_drawn_and_reported(monkeypatch, tmp_path, _inspected_figures):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (fx.REF, fx.REF_LEN))
    prots, rows, core = fx._genome()
    g = gecco_genes(tmp_path, [(round(x["s"] * 1000) + 1, round(x["e"] * 1000), 0.95) for x in fx.REF])
    ref_gecco = glm.load_reference_gecco(g, None, fx.REF)
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "test", tmp_path / "m.png",
                             ref_gecco=ref_gecco)
    assert res["ref_gecco"]["boxes"] == len(fx.REF)
    plain = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "test", tmp_path / "n.png")
    assert "ref_gecco" not in plain                                          # without the option nothing changes


def test_landscape_is_a_print_width():
    assert glm.PRINT_WIDTHS["landscape"] == 9.0
    src = (ROOT / "tools" / "gap_directed_rescue.py").read_text()
    assert '"landscape"' in src and "--mibig-gecco-dir" in src


def test_spec_validation(tmp_path):
    run = tmp_path / "run"; run.mkdir(); (run / "gap_rescue_receipt.json").write_text("{}")
    z = tmp_path / "g.zip"; z.write_bytes(b"PK")
    good = tmp_path / "spec.tsv"; good.write_text(f"letter\trun\tstrain\tzip\na\t{run}\tS1\t{z}\nb\t{run}\tS1\t{z}\n")
    assert [r["letter"] for r in lfp.read_spec(good, tmp_path)] == ["a", "b"]
    dup = tmp_path / "dup.tsv"; dup.write_text(f"letter\trun\tstrain\tzip\na\t{run}\tS1\t{z}\na\t{run}\tS1\t{z}\n")
    with pytest.raises(ValueError, match="unique"):
        lfp.read_spec(dup, tmp_path)
    solo = tmp_path / "solo.tsv"; solo.write_text(f"letter\trun\tstrain\tzip\n-\t{run}\tS1\t{z}\nb\t{run}\tS1\t{z}\n")
    with pytest.raises(ValueError, match="one map"):
        lfp.read_spec(solo, tmp_path)
    norun = tmp_path / "norun.tsv"; norun.write_text(f"letter\trun\tstrain\tzip\na\t{tmp_path}\tS1\t{z}\n")
    with pytest.raises(ValueError, match="not a gap_directed_rescue run"):
        lfp.read_spec(norun, tmp_path)


def test_pages_are_grouped_greedily_under_the_limit():
    assert lfp.page_groups(list("abcd"), [3.0, 3.0, 3.0, 3.0], 9.0) == [["a", "b"], ["c", "d"]]
    assert lfp.page_groups(list("ab"), [8.5, 2.0], 9.0) == [["a"], ["b"]]         # a tall map gets its own page


def test_map_command_carries_every_setting(tmp_path):
    a = lfp.argparse.Namespace(mibig_dir="/m", width="landscape", trim_kb=2.0, own_key=False, mibig_names="n.json",
                               gene_names="g.tsv", gecco_dir=None, mibig_gecco_dir="/mg", map_height=10.0)
    cmd = lfp.map_command(dict(zip="z.zip", strain="S1", run="/r"), a, tmp_path / "d")
    for flag in ("--no-key", "--panel", "--scale-bar-up", "--mibig-gecco-dir", "--map-height", "--gene-names", "--mibig-names"):
        assert flag in cmd
    assert cmd[cmd.index("--print-width") + 1] == "landscape"
