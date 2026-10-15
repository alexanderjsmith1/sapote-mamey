"""Card attine_452_c02_wrap_long_group_labels: the genus composition plot (C02) wraps a long group name.

A five-group panel with a group named "Attine, genus not recorded" failed the 8 pt check: the x-axis labels clipped.
(At 3.5 in five such labels also overlap each other, which the gate refuses since attine_452_min_text_check_tick_label_overlap,
so the test renders at 4.5 in.) Names longer than 14 characters now wrap at a space; shorter names (every bee and moss group)
are unchanged. Synthetic IDs only.
"""
import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/genus_composition_figures.py"
spec = importlib.util.spec_from_file_location("composition_wrap", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
GROUPS = ["Atta", "Acromyrmex", "Myrmicocrypta", "Lower attine", "Attine, genus not recorded"]


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_five_groups_with_a_long_name_render_at_8pt(tmp_path):
    p = tmp_path / "isolates.tsv"
    module.write_tsv(p, ["strain", "group", "genus"],
                     [dict(strain=f"AS-{971 + i}", group=g, genus="Streptomyces") for i, g in enumerate(GROUPS)])
    out = tmp_path / "render"
    assert module.main(["--isolates", str(p), "--out", str(out), "--layout", "attine", "--groups", *GROUPS,
                        "--palette-set", "attine", "--print-width", "4.5"]) == 0
    assert (out / "C02_genus_composition.png").exists()


def test_only_names_longer_than_14_characters_wrap():
    assert 'if (nchar(g)>14) paste(strwrap(g,width=14),collapse="<br>") else g' in module.R_SCRIPT
    assert all(len(g) <= 14 for g in ["Bumblebees", "Honeybees", "Other bees", "Wasps", "Bryophytes", "Lichens", "Mushrooms"])
