from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]


def test_mafft_calls_use_quiet_to_avoid_dev_stderr_wrapper_failure():
    source = (ROOT / "tools/phylo_place.py").read_text(encoding="utf-8")
    commands = [node for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.List) and node.elts
                and isinstance(node.elts[0], ast.Name) and node.elts[0].id == 'mafft']
    assert len(commands) == 2
    flags = [{item.value for item in node.elts if isinstance(item, ast.Constant)
              and isinstance(item.value, str)} for node in commands]
    assert all({'--anysymbol', '--quiet'} <= values for values in flags)
    assert sum('--auto' in values for values in flags) == 1
    assert sum('--keeplength' in values for values in flags) == 1


def test_bumblebee_and_plant_source_colours_are_visually_distinct_hues():
    import csv
    with (ROOT / "tools/phylo_display_palette.tsv").open(encoding="utf-8") as handle:
        palette = {(row["field"], row["value"]): row["color"]
                   for row in csv.DictReader(handle, delimiter="\t")}
    assert palette[("source", "plant-associated")] == "#228833"
    assert palette[("source", "bumblebee")] == "#0072B2"
    assert palette[("source", "plant-associated")] != palette[("source", "bumblebee")]
