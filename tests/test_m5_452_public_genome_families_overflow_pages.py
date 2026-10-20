"""m5_452_public_genome_families_overflow_pages: B04 (tools/public_genome_families.py) gains
- --overflow pages: when the genome rows need more than the 8.5 in panel at the min-text floor (one text line per label line), rows are
  split across full-width pages (<out>_page1, _page2, ...), labels unchanged; <out>_pages.json lists the rows of each page;
- --row-order input: rows keep the --genomes order (default 'sorted' keeps genus, block, strain).
Without the flags, a too-tall page still refuses with MIN_TEXT_TOO_TALL and the row order is unchanged. Synthetic names only."""
import csv, importlib.util, json, shutil
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pgf", ROOT / "tools/public_genome_families.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
TOOL = "public_genome_families"
N_TALL = 60   # two-line labels: 60 rows x 2 lines x 0.167 in = 20 in > 8.5 in at 8 pt


def put(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    return path


def inputs(tmp_path, n, reverse=False):
    ids = list(range(n))[::-1] if reverse else list(range(n))
    g = put(tmp_path / "g.tsv", [dict(strain=f"SYN-{i:03d}", genus="Synthgenusa", block="Synthgenusa",
                                      label=f"<i>Synthgenusa</i> sp. SYN {i}\\n[SYN_{i:06d}.1]") for i in ids])
    d = put(tmp_path / "d.tsv", [dict(strain=f"SYN-{i:03d}", genus="Synthgenusa", families=10 + i % 7, in_public=6, not_in_public=4 + i % 7)
                                 for i in range(n)])
    return g, d


def args(g, d, out, *extra):
    return ["--genomes", str(g), "--data", str(d), "--out", str(out), "--layout", "bee", "--dpi", "100", "--min-text-pt", "8",
            "--print-width", "6.5", "--part-labels", "In 2 or more genomes|In this genome only", *extra]


def test_tall_page_still_refused_without_overflow(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g, d = inputs(tmp_path, N_TALL)
    with pytest.raises(RuntimeError, match="MIN_TEXT_TOO_TALL"):
        m.main(args(g, d, tmp_path / "out"))


def test_overflow_pages_draws_full_width_pages(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g, d = inputs(tmp_path, N_TALL)
    out = tmp_path / "out"
    assert m.main(args(g, d, out, "--overflow", "pages")) == 0
    pages = json.loads((out / f"{TOOL}_pages.json").read_text())
    assert pages["pages"] >= 2 and sum(pages["rows_per_page"]) == N_TALL and pages["lines_per_row"] == 2
    assert not (out / f"{TOOL}.pdf").exists()
    for i in range(1, pages["pages"] + 1):
        mt = json.loads((out / f"{TOOL}_page{i}_min_text.json").read_text())
        assert mt["overflow"] == "pages" and mt["print_width_in"] == 6.5
        chk = json.loads((out / f"{TOOL}_page{i}_min_text_check.json").read_text())
        assert chk["status"] == "PASS" and chk["smallest_pt"] >= 8
        assert (out / f"{TOOL}_page{i}.png").exists()
    info = json.loads((out / "RUN_INFO.json").read_text())
    assert info["overflow"] == "pages" and info["pages"] == pages["pages"]


def test_overflow_pages_leaves_a_fitting_page_unchanged(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g, d = inputs(tmp_path, 6)
    a, b = tmp_path / "a", tmp_path / "b"
    assert m.main(args(g, d, a)) == 0 and m.main(args(g, d, b, "--overflow", "pages")) == 0
    assert not (b / f"{TOOL}_pages.json").exists() and (b / f"{TOOL}.pdf").exists()
    ma = json.loads((a / f"{TOOL}_min_text.json").read_text()); mb = json.loads((b / f"{TOOL}_min_text.json").read_text())
    assert mb["overflow"] == "none" and ma["rows"] == mb["rows"] == 6 and ma["height_in"] == mb["height_in"]


def test_row_order_input_keeps_genome_order(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g, d = inputs(tmp_path, 5, reverse=True)
    a, b = tmp_path / "a", tmp_path / "b"
    assert m.main(args(g, d, a)) == 0 and m.main(args(g, d, b, "--row-order", "input")) == 0
    order = lambda o: [r["strain"] for r in csv.DictReader((o / "plot_data.tsv").open(), delimiter="\t")]
    assert order(b) == [f"SYN-{i:03d}" for i in (4, 3, 2, 1, 0)]          # the --genomes order
    assert json.loads((b / "render_config.json").read_text())["row_order"] == "input"
    assert "row_order" in json.loads((a / "render_config.json").read_text())   # default 'sorted' recorded; R keeps arrange()
    assert json.loads((a / "render_config.json").read_text())["row_order"] == "sorted"


def test_option_choices(tmp_path):
    g, d = inputs(tmp_path, 2)
    for bad in (["--overflow", "split"], ["--row-order", "random"]):
        with pytest.raises(SystemExit):
            m.main(args(g, d, tmp_path / "o", *bad))
