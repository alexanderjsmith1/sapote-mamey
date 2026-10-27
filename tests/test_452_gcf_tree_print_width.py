"""render_gcf_synteny_tree.py at a print width (card 452_gcf_tree_print_width_8pt): every text at least 8 pt on
a page exactly the column wide, the legend listing only roles drawn, optional title; --print-width none keeps the old
layout. Synthetic families from the .433 test helpers."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pypdf = pytest.importorskip("pypdf")
HERE = Path(__file__).resolve().parent
_h = importlib.util.spec_from_file_location("gcf433_helpers", HERE / "test_trees_433_gcf_synteny_tree_layers_and_pruning.py")
h = importlib.util.module_from_spec(_h); _h.loader.exec_module(h)
gs = h.gs


def _sizes(pdf):
    out = []
    pypdf.PdfReader(str(pdf)).pages[0].extract_text(
        visitor_text=lambda t, cm, tm, fd, fs: out.append(abs(fs * tm[0]) if tm[0] else fs) if t.strip() else None)
    return out


def _page_w(pdf):
    return float(pypdf.PdfReader(str(pdf)).pages[0].mediabox.width) / 72


@pytest.mark.parametrize("width,inches", [("double", 7.2), ("single", 3.5)])
def test_print_width_page_and_8pt(tmp_path, width, inches):
    files, inv, nwk = h._family(tmp_path, n_ref=3)
    out = tmp_path / f"fam_{width}"
    extra = ["--print-width", width] + (["--no-title"] if width == "single" else [])
    try:
        rc = gs.main(h._args(files, inv, nwk, out, extra))
    except SystemExit as exc:   # single column may be refused when the labels leave no room: say so, never shrink
        assert width == "single" and "GCF_TREE_PRINT_WIDTH" in str(exc)
        return
    assert rc == 0
    pdf = Path(str(out) + ".pdf")
    assert abs(_page_w(pdf) - inches) < 0.01
    assert min(_sizes(pdf)) >= 8.0 - 1e-6


def test_default_is_double_width(tmp_path):
    files, inv, nwk = h._family(tmp_path, n_ref=2)
    out = tmp_path / "fam"
    assert gs.main(h._args(files, inv, nwk, out)) == 0
    assert abs(_page_w(Path(str(out) + ".pdf")) - 7.2) < 0.01
    assert "(scale bar)" in Path(str(out) + "_caption.txt").read_text()


def test_legend_lists_only_drawn_roles(tmp_path):
    files, inv, nwk = h._family(tmp_path, n_ref=2)
    out = tmp_path / "fam"
    assert gs.main(h._args(files, inv, nwk, out, ["--no-title"])) == 0
    text = " ".join(pypdf.PdfReader(str(out) + ".pdf").pages[0].extract_text().split())
    roles = {r[5] for r in (l.split("\t") for l in Path(str(out) + "_gene_roles.tsv").read_text().splitlines()[1:])}
    for name in gs.ROLE_COLOURS:
        assert (name in text) == (name in roles), name


def test_screen_layout_unchanged_with_none(tmp_path):
    files, inv, nwk = h._family(tmp_path, n_ref=2)
    out = tmp_path / "fam"
    assert gs.main(h._args(files, inv, nwk, out, ["--print-width", "none"])) == 0
    assert _page_w(Path(str(out) + ".pdf")) > 7.2   # the earlier layout grows with its labels and tracks
    assert "(10 kb bar)" in Path(str(out) + "_caption.txt").read_text()
