"""Card attine_452_c02_italic_genus_groups: C02 sets group labels that are genus names in italics.

Attine Fig. 1D groups isolates by host ant genus (Atta, Acromyrmex, Myrmicocrypta), which must be italic. The italic
names come from an explicit per-layout list (or --italic-groups), never from guessing; bee and moss groups are not
genera and stay upright. Synthetic IDs only.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/genus_composition_figures.py"
spec = importlib.util.spec_from_file_location("composition_italic", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def run(tmp_path, layout, groups, *extra):
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "isolates.tsv"
    module.write_tsv(p, ["strain", "group", "genus"],
                     [dict(strain=f"AS-{971 + i}", group=g, genus="Streptomyces") for i, g in enumerate(groups)])
    out = tmp_path / "render"
    argv = ["--isolates", str(p), "--out", str(out), "--layout", layout, "--groups", *groups, *extra]
    if layout != "bee":
        argv += ["--palette-set", layout]
    assert module.main(argv) == 0
    return json.loads((out / "RUN_INFO.json").read_text())


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_attine_host_genera_are_italic_and_other_groups_are_not(tmp_path):
    info = run(tmp_path, "attine", ["Atta", "Acromyrmex", "Lower attine"])
    assert info["italic_groups"] == ["Atta", "Acromyrmex"]


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_moss_and_bee_groups_stay_upright(tmp_path):
    assert run(tmp_path / "m", "moss", ["Bryophytes", "Lichens", "Mushrooms"])["italic_groups"] == []
    assert run(tmp_path / "b", "bee", ["Bumblebees", "Honeybees", "Other bees", "Wasps"])["italic_groups"] == []


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_the_option_replaces_the_layout_list(tmp_path):
    assert run(tmp_path / "a", "attine", ["Atta", "Acromyrmex"], "--italic-groups", "Atta")["italic_groups"] == ["Atta"]
    assert run(tmp_path / "b", "attine", ["Atta", "Acromyrmex"], "--italic-groups")["italic_groups"] == []


def test_the_list_is_explicit_per_layout():
    assert module.ITALIC_GROUPS == {"bee": [], "moss": [], "attine": ["Atta", "Acromyrmex", "Myrmicocrypta"]}
    assert 'paste0("<i>",glab,"</i>")' in module.R_SCRIPT
