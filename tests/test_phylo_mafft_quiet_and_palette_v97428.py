from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mafft_calls_use_quiet_to_avoid_dev_stderr_wrapper_failure():
    source = (ROOT / "tools/phylo_place.py").read_text(encoding="utf-8")
    assert '[mafft, "--addfragments" if fragmentary else "--add", queries,\n                                       "--keeplength", "--anysymbol", "--quiet", reference]' in source
    assert '[mafft, "--auto", "--anysymbol", "--quiet", ref_safe]' in source


def test_bumblebee_and_plant_source_colours_are_visually_distinct_hues():
    import csv
    with (ROOT / "tools/phylo_display_palette.tsv").open(encoding="utf-8") as handle:
        palette = {(row["field"], row["value"]): row["color"]
                   for row in csv.DictReader(handle, delimiter="\t")}
    assert palette[("source", "plant-associated")] == "#228833"
    assert palette[("source", "bumblebee")] == "#0072B2"
    assert palette[("source", "plant-associated")] != palette[("source", "bumblebee")]
