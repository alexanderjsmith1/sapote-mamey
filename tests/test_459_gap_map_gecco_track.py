"""Card 018c0f08_459_gap_map_gecco_track: a GECCO track under the strain row of a gap-rescue locus map, and the
5 kb scale bar moved up onto the contig-caption line (owner, 19 Oct, rulings 116 and 122). Synthetic two-row map; no
GECCO run, no DIAMOND."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
HERE = Path(__file__).resolve().parents[1]
TOOLS = HERE / "tools"
sys.path.insert(0, str(TOOLS))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load(TOOLS / "gap_rescue_locus_map.py", "gap_rescue_locus_map_459")
REF = [{"i": i + 1, "name": f"madA{i}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
        "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(10)]
REF_LEN = REF[-1]["e"] + 0.5
CONTIG = "NODE_7_length_90000_cov_19.050000"          # GECCO writes it as cov_19.50000


def _genome():
    prots, rows = {}, []
    for k, g in enumerate(REF):
        start = 5000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": CONTIG, "start": start,
                          "end": start + int((g["e"] - g["s"]) * 1000), "strand": 1, "contig_len": 90000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 60.0 + k,
                     "reciprocal_best": True, "partner_verdict": ""})
    core = {"contig": CONTIG, "start": 4000, "end": 22000, "identity": f"AS-0 / {CONTIG} / region001 / BGC001"}
    return prots, rows, core


def _gecco_files(tmp_path, prots):
    g = tmp_path / "AS-0.genes.tsv"
    lines = ["sequence_id\tprotein_id\tstart\tend\tstrand\taverage_p\tmax_p"]
    for k, (pid, p) in enumerate(prots.items()):
        if k == 0:
            continue                                     # one strain gene GECCO did not score
        lines.append(f"NODE_7_length_90000_cov_19.50000\tctg7_{k}\t{p['start'] + 1}\t{p['end']}\t+\t{k / 10:.2f}\t{k / 10:.2f}")
    g.write_text("\n".join(lines) + "\n")
    c = tmp_path / "AS-0.clusters.tsv"
    c.write_text("sequence_id\tcluster_id\tstart\tend\taverage_p\tmax_p\ttype\n"
                 f"NODE_7_length_90000_cov_19.50000\tNODE_7_cluster_1\t9000\t16000\t0.95\t0.99\tNRP\n")
    return g, c


def test_load_gecco_binds_by_node_number_and_overlap(tmp_path):
    prots, _, _ = _genome()
    g, c = _gecco_files(tmp_path, prots)
    gec = glm.load_gecco(g, c, prots, "AS-0")
    assert "p0" not in gec["p"] and gec["p"]["p3"] == pytest.approx(0.3)
    assert gec["binding"]["strain_genes_scored"] == 9 and gec["binding"]["strain_genes_unscored"] == 1
    assert gec["clusters"][0]["node"] == "NODE_7" and gec["clusters"][0]["type"] == "NRP"


def test_track_drawn_at_print_width_without_small_or_touching_text(monkeypatch, tmp_path):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core = _genome()
    g, c = _gecco_files(tmp_path, prots)
    gec = glm.load_gecco(g, c, prots, "AS-0")
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "madurastatin",
                             tmp_path / "m.png", print_width="page6.5", panel=True, key=False, gecco=gec,
                             scale_bar_up=True)
    assert res["gecco"]["boxes"] == 9
    span = res["gecco"]["cluster_spans"][0]
    assert span["cluster_id"] == "NODE_7_cluster_1" and 0 < span["genes_drawn"] < 10
    assert res["min_font_pt"] >= 8.0 and res["text_overlaps"] == 0
    assert res["scale_bar_moved_up"] is True


def test_default_map_is_unchanged_by_the_card(monkeypatch, tmp_path):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core = _genome()
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "madurastatin",
                             tmp_path / "m0.png", print_width="double")
    assert "gecco" not in res and "scale_bar_moved_up" not in res


def test_cli_refuses_gecco_options_without_redraw(tmp_path):
    gdr = _load(TOOLS / "gap_directed_rescue.py", "gap_directed_rescue_459")
    with pytest.raises(SystemExit, match="redraw options"):
        gdr.main(["--zip", str(tmp_path / "x.zip"), "--label", "AS-0", "--gecco-genes", str(tmp_path / "g.tsv")])
    with pytest.raises(SystemExit, match="needs --gecco-genes"):
        gdr.main(["--zip", str(tmp_path / "x.zip"), "--label", "AS-0", "--redraw", str(tmp_path),
                  "--gecco-clusters", str(tmp_path / "c.tsv")])


def test_panel_figure_prints_the_gecco_key_only_when_a_map_has_a_track(tmp_path):
    from PIL import Image
    pf = _load(TOOLS / "gap_rescue_panel_figure.py", "gap_rescue_panel_figure_459")
    for name, gecco in (("m1", True), ("m2", False)):
        d = tmp_path / name; d.mkdir()
        Image.new("RGB", (900, 600), "white").save(d / "gap_rescue.png", dpi=(300, 300))
        (d / "gap_rescue_key.json").write_text(json.dumps({"classes": [], "class_unclear": False, "key": False,
                                                            **({"gecco": True} if gecco else {})}))
    on = pf.compose([tmp_path / "m1", tmp_path / "m2"], tmp_path / "out_on", letters="ab")
    off = pf.compose([tmp_path / "m2"], tmp_path / "out_off", letters="a")
    assert on["gecco_key"] is True and off["gecco_key"] is False
    assert on["pages"][0]["height_in"] == pytest.approx(2 * 2.0 + pf.GAP_IN + pf.key_height(0) + pf.GECCO_KEY_H, abs=0.01)


def test_a_reused_node_number_on_a_different_contig_is_not_joined(tmp_path):
    """Audit F01: GECCO's NODE_1_length_999 is not the genome's NODE_1_length_2000; neither genes nor cluster spans join."""
    prots = {"q1": {"tag": "t1", "contig": "NODE_1_length_2000_cov_7.000000", "start": 1, "end": 100, "strand": 1, "contig_len": 2000}}
    g = tmp_path / "x.genes.tsv"
    g.write_text("sequence_id\tprotein_id\tstart\tend\tstrand\taverage_p\tmax_p\n"
                 "NODE_1_length_999_cov_3.0\tg1\t1\t100\t+\t0.99\t0.99\n")
    c = tmp_path / "x.clusters.tsv"
    c.write_text("sequence_id\tcluster_id\tstart\tend\taverage_p\tmax_p\ttype\nNODE_1_length_999_cov_3.0\tc1\t1\t100\t0.99\t0.99\tNRP\n")
    gec = glm.load_gecco(g, c, prots, "SYN")
    assert gec["p"] == {} and gec["clusters"] == []
    assert gec["binding"]["strain_genes_scored"] == 0 and gec["binding"]["gecco_contigs_not_joined"] == 1


def test_an_alias_shared_by_two_genome_contigs_is_not_joined(tmp_path):
    prots = {"q1": {"tag": "t1", "contig": "NODE_2_length_500_cov_1.5", "start": 1, "end": 100, "strand": 1, "contig_len": 500},
             "q2": {"tag": "t2", "contig": "NODE_2_length_500_cov_9.5", "start": 1, "end": 100, "strand": 1, "contig_len": 500}}
    g = tmp_path / "y.genes.tsv"
    g.write_text("sequence_id\tprotein_id\tstart\tend\tstrand\taverage_p\tmax_p\nNODE_2_length_500_cov_1.50\tg1\t1\t100\t+\t0.9\t0.9\n")
    gec = glm.load_gecco(g, None, prots, "SYN")
    assert gec["p"] == {} and gec["binding"]["gecco_contigs_not_joined"] == 1
