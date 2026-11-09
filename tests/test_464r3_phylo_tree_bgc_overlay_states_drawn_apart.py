"""tree_bgc_overlay: MISSING, NOT_MEASURED and NOT_APPLICABLE cells are drawn with different marks and
fills, and the track title carries the key. Reuses the shipped overlay fixture; one strain-feature row
is removed so a MISSING cell exists."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
_spec = importlib.util.spec_from_file_location("overlay_fixture_464r3", ROOT / "tests" / "test_tree_bgc_overlay.py")
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)


def test_three_unobserved_states_have_distinct_marks_and_a_key(tmp_path):
    config_path = fx._fixture(tmp_path)
    config = json.loads(config_path.read_text())
    matrix = Path(config["external_data_root"]) / "annotations.tsv"
    rows = [r for r in csv.reader(matrix.open(), delimiter="\t")
            if not (r[0] == "strain-two" and r[1] == "BGC")]          # strain-two BGC becomes MISSING
    fx._tsv(matrix, rows[0], rows[1:])
    for item in config["inputs"]:
        if item["logical_locator"] == "annotations.tsv":
            item["sha256"] = fx._sha(matrix)
    config_path.write_text(json.dumps(config))
    fx.ov.build_publication(config_path)
    svg = (tmp_path / "tree-output-a" / "tree_bgc_overlay_double_column.svg").read_text(encoding="utf-8")
    assert "Track cells:" in svg and "× not measured" in svg and "– not applicable" in svg and "? missing" in svg
    for mark in (">?<", ">×<", ">–<"):
        assert mark in svg, mark
    for fill in ("#d9d9d9", "#ffffff", "#f2f2f2"):
        assert fill in svg.lower(), fill
