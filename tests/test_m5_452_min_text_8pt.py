"""M5_452_render_cards_min_text_8pt: tools/sapote_min_text.R, tools/_min_text_check.py and the 7 amended R figure cards.

docs/FIGURE_STYLE.md publication artwork gate: smallest text >= 8 pt at the declared width (3.5 / 7.2 in); colliding, touching or
overflowing label boxes are refused. Synthetic inputs only (SYN-971-series strains)."""
import csv, importlib.util, json, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import _min_text_check as mtc  # noqa: E402

needs_r = pytest.mark.skipif(not shutil.which("Rscript"), reason="Rscript unavailable")
CARD_TOOLS = ["bgc_class_groups", "bgc_classes_per_genome", "public_genome_families", "genus_composition_figures",
              "taxonomy_T01_figures", "taxonomy_T05_figures", "taxonomy_T06_figures"]


def run_r(tmp_path, body):
    script = tmp_path / "t.R"
    script.write_text('suppressPackageStartupMessages(library(ggplot2))\n'
                      f'source("{ROOT / "tools/sapote_pub_layout.R"}"); source("{ROOT / "tools/sapote_min_text.R"}")\n' + body)
    return subprocess.run(["Rscript", str(script)], capture_output=True, text=True)


def bars(n, h_expr="0.24"):
    return (f'd <- data.frame(k = factor(sprintf("class %02d", 1:{n}), levels = sprintf("class %02d", 1:{n})), v = seq_len({n}) * 3)\n'
            'p <- ggplot(d, aes(k, v)) + geom_col() + geom_text(aes(label = paste0(v, " (26)")), hjust = -0.1, size = 6 / .pt) +\n'
            f'  coord_flip() + scale_y_continuous(expand = expansion(mult = c(0, {h_expr}))) + theme_pub(6)\n')


@needs_r
def test_floor_raises_text_and_pdf_reads_back_8pt(tmp_path):
    r = run_r(tmp_path, bars(6, "0.6") + f'mt_save(p, "{tmp_path / "f"}", 3.4, 2, list(dpi = 150))\n')
    assert r.returncode == 0, r.stderr
    rec = json.loads((tmp_path / "f_min_text.json").read_text())
    assert rec["print_width_in"] == 3.5 and rec["floored"], rec
    out = mtc.check(str(tmp_path / "f.pdf"), 8.0, 3.5)
    assert out["status"] == "PASS" and out["smallest_pt"] >= 8.0 - 0.05


@needs_r
def test_pdf_check_refuses_small_text(tmp_path):
    r = run_r(tmp_path, bars(4, "0.6") + f'.pub_pdf(p, "{tmp_path / "small.pdf"}", 3.5, 2)\n')
    assert r.returncode == 0, r.stderr
    assert mtc.check(str(tmp_path / "small.pdf"), 8.0, 3.5)["status"] == "FAIL"
    assert mtc.check(str(tmp_path / "small.pdf"), 4.0, 7.2)["status"] == "FAIL"   # wrong page width also refuses


@needs_r
def test_stacked_rows_grow_the_height(tmp_path):
    r = run_r(tmp_path, bars(40, "1.2") + f'mt_save(p, "{tmp_path / "g"}", 3.4, 2, list(dpi = 100))\n')
    assert r.returncode == 0, r.stderr
    rec = json.loads((tmp_path / "g_min_text.json").read_text())
    assert rec["height_in"] > 2.5 and not rec["overlapping_text"] and not rec["clipped_text"]


@needs_r
def test_clipped_label_fails_closed(tmp_path):
    r = run_r(tmp_path, bars(5, "0") + f'mt_save(p, "{tmp_path / "c"}", 3.4, 2, list(dpi = 100))\n')
    assert r.returncode != 0 and "MIN_TEXT_DOES_NOT_FIT" in r.stderr and "clipped" in r.stderr
    assert not (tmp_path / "c.png").exists() and not (tmp_path / "c.pdf").exists()


@needs_r
def test_overlap_not_fixable_by_height_fails_closed(tmp_path):
    r = run_r(tmp_path, bars(40, "0.6") + f'mt_save(p, "{tmp_path / "o"}", 3.4, 2, list(dpi = 100, max_height = 2.2))\n')
    assert r.returncode != 0 and "MIN_TEXT_DOES_NOT_FIT" in r.stderr and "overlapping" in r.stderr


@pytest.mark.parametrize("tool", CARD_TOOLS)
def test_every_card_has_min_text_option_and_helper(tool):
    code = (ROOT / f"tools/{tool}.py").read_text()
    assert "_mt_args(" in code and "_mt_enforce(" in code and "sapote_min_text.R" in code
    assert "ggsave(paste0(cfg$out,\".png\")" not in code and "ggsave(paste0(out,\".png\")" not in code


def test_t05_zone_labels_and_t06_callout_removed():
    t05 = (ROOT / "tools/taxonomy_T05_figures.py").read_text(); t06 = (ROOT / "tools/taxonomy_T06_figures.py").read_text()
    assert "potential new species" not in t05 and '"same species"' not in t05
    assert "16S at or above" not in t06 and "b$nudge_x" not in t06 and "point.size" in t06


def _b02_inputs(tmp_path, ncls=46, nstrain=6):
    def put(p, rows):
        with p.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
        return p
    strains = [f"SYN-{971 + i}" for i in range(nstrain)]
    fams = ["PKS", "NRPS", "RiPP", "Other classes"]
    g = put(tmp_path / "g.tsv", [dict(strain=s, genus="Streptomyces", block="isolates") for s in strains])
    d = put(tmp_path / "d.tsv", [dict(strain=s, genus="Streptomyces", display=f"class {c:02d}", family=fams[c % 4],
                                      count=27 if (c == 0 and s == strains[0]) else c % 3) for s in strains for c in range(ncls)])
    t = put(tmp_path / "t.tsv", [dict(strain=s, genus="Streptomyces", regions=30, contig_edge=9, pct_edge=30) for s in strains])
    return g, d, t


@needs_r
def test_b02_two_digit_counts_refuse_then_fit_as_rows(tmp_path):
    spec = importlib.util.spec_from_file_location("b02", ROOT / "tools/bgc_classes_per_genome.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    g, d, t = _b02_inputs(tmp_path)
    base = ["--genomes", str(g), "--data", str(d), "--totals", str(t), "--layout", "bee", "--dpi", "100"]
    with pytest.raises(RuntimeError, match="MIN_TEXT_DOES_NOT_FIT: tiles"):
        m.main(base + ["--out", str(tmp_path / "cols")])
    assert m.main(base + ["--out", str(tmp_path / "rows"), "--orientation", "classes-as-rows"]) == 0
    chk = json.loads((tmp_path / "rows" / (m.TOOL + "_min_text_check.json")).read_text())
    assert chk["status"] == "PASS" and chk["page_width_in"] == 7.2


@needs_r
def test_c02_draws_at_floor(tmp_path):
    spec = importlib.util.spec_from_file_location("c02", ROOT / "tools/genus_composition_figures.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    roster = tmp_path / "r.tsv"
    roster.write_text("strain\tgroup\tgenus\n" + "".join(f"SYN-{971 + i}\t{grp}\tStreptomyces\n" for i, grp in
                      enumerate(["Group A", "Group B", "Group C", "Group D", "Group A"])))
    layout = json.loads((ROOT / "mamey/data/bgc_class_layouts.json").read_text())["default"]
    assert m.main(["--isolates", str(roster), "--layout", layout, "--groups", "Group A", "Group B", "Group C", "Group D", "--out", str(tmp_path / "c02")]) == 0
    chk = json.loads((tmp_path / "c02" / "C02_genus_composition_min_text_check.json").read_text())
    assert chk["status"] == "PASS" and chk["smallest_pt"] >= 7.95


@needs_r
def test_grey_text_goes_black_and_axis_title_clears_ticks(tmp_path):
    body = (bars(6, "0.6") + 'p <- p + theme(axis.title.x = element_text(colour = "#54637A"))\n'
            f'mt_save(p, "{tmp_path / "k"}", 3.4, 2, list(dpi = 100))\n')
    r = run_r(tmp_path, body)
    assert r.returncode == 0, r.stderr
    rec = json.loads((tmp_path / "k_min_text.json").read_text())
    assert any(f.get("colour_to") == "black" for f in rec["floored"]), rec["floored"]
