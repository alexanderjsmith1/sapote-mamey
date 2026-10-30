"""Software-only label and numbered-removal regressions; no inferred tree."""
import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "tools" / "phylo_roster.py"
SPEC = importlib.util.spec_from_file_location("roster_label_regression", SOURCE)
roster = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roster)


@pytest.mark.parametrize("tree,expected", [
    ("('engineering_fixture,one':0.1,fixture_two:0.2);", ["engineering_fixture,one", "fixture_two"]),
    ("('engineering_fixture:one':0.1,fixture_two:0.2);", ["engineering_fixture:one", "fixture_two"]),
    ("('engineering_fixture(one)':0.1,fixture_two:0.2);", ["engineering_fixture(one)", "fixture_two"]),
    ("('engineering_fixture''one':0.1,fixture_two:0.2);", ["engineering_fixture'one", "fixture_two"]),
    ('("engineering_fixture,one":0.1,fixture_two:0.2);', ["engineering_fixture,one", "fixture_two"]),
    ("engineering_fixture:0.1;", ["engineering_fixture"]),
    ("((fixture_one:0.1,fixture_two:0.2)90:0.3,fixture_three:0.4);", ["fixture_one", "fixture_two", "fixture_three"]),
])
def test_exact_tip_labels_in_leaf_order(tree, expected):
    assert roster.tree_tips(tree) == expected


def test_numbered_removal_keeps_exact_surviving_label(tmp_path):
    source = tmp_path / "software.treefile"
    source.write_text("('engineering_fixture,one':0.1,fixture_two:0.2);\n")
    output = tmp_path / "keep.txt"
    assert roster.main(["--tree", str(source), "--remove", "2", "--out", str(output)]) == 0
    assert output.read_text() == "engineering_fixture,one\n"


@pytest.mark.parametrize("tree", [
    "(fixture_one,fixture_two)",
    "((fixture_one,fixture_two);",
    "(fixture_one,fixture_one);",
    "('fixture_one,fixture_two);",
    "(fixture_one[annotation],fixture_two);",
])
def test_invalid_or_unsupported_tree_is_refused(tree):
    with pytest.raises(ValueError):
        roster.tree_tips(tree)


def test_cli_refuses_invalid_tree_before_writing(tmp_path):
    source = tmp_path / "incomplete.treefile"
    source.write_text("(fixture_one,fixture_two)")
    output = tmp_path / "keep.txt"
    with pytest.raises(SystemExit) as raised:
        roster.main(["--tree", str(source), "--remove", "2", "--out", str(output)])
    assert raised.value.code == 2
    assert not output.exists()
