from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mafft_calls_use_quiet_to_avoid_dev_stderr_wrapper_failure():
    source = (ROOT / "tools/phylo_place.py").read_text(encoding="utf-8")
    assert '[mafft, "--addfragments" if fragmentary else "--add", queries,\n                                       "--keeplength", "--anysymbol", "--quiet", reference]' in source
    assert '[mafft, "--auto", "--anysymbol", "--quiet", ref_safe]' in source


def test_bumblebee_and_plant_source_colours_are_visually_distinct_hues():
    source = (ROOT / "tools/ggtree_rect_heatmap.R").read_text(encoding="utf-8")
    assert '"plant-associated" = "#2E8B57"' in source
    assert '"bumblebee" = "#0072B2"' in source
