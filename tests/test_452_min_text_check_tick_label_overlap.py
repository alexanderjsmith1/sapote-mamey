"""Card attine_452_min_text_check_tick_label_overlap: the 8 pt gate sees tick labels that overlap each other.

tools/sapote_min_text.R merges rich-text words on one baseline into one line box. It merged any box that started less
than half a font size past the previous one, including a box that started inside it, so crowded tick labels became one
long "label" and their overlap was never tested (attine Fig. 1D passed at 3.5 in with five labels running into each
other). Now only a real word gap is merged; overlapping labels stay separate and fail the gate. Synthetic IDs only.
"""
import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/genus_composition_figures.py"
spec = importlib.util.spec_from_file_location("composition_gate", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# five single-word group names of 13-14 characters (no space, so the C02 wrap leaves them on one line)
GROUPS = ["Synthetomyces", "Exemplarioides", "Probationella", "Testimonialia", "Fabricatospora"]


def roster(tmp_path):
    p = tmp_path / "isolates.tsv"
    module.write_tsv(p, ["strain", "group", "genus"],
                     [dict(strain=f"AS-{971 + i}", group=g, genus="Streptomyces") for i, g in enumerate(GROUPS)])
    return p


def render(tmp_path, width):
    return module.main(["--isolates", str(roster(tmp_path)), "--out", str(tmp_path / f"r{width}"), "--layout", "attine",
                        "--groups", *GROUPS, "--palette-set", "attine", "--print-width", str(width)])


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_five_long_tick_labels_overlap_at_one_column_and_are_refused(tmp_path):
    import subprocess
    with pytest.raises(subprocess.CalledProcessError) as err:
        render(tmp_path, 3.5)
    assert err.value.returncode != 0


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_the_same_labels_fit_at_double_column(tmp_path):
    assert render(tmp_path, 7.2) == 0
    assert (tmp_path / "r7.2" / "C02_genus_composition.png").exists()


def test_only_a_real_word_gap_is_merged():
    src = (ROOT / "tools/sapote_min_text.R").read_text()
    # overlapping boxes (negative gap) must stay separate: only a word a real space after the previous box merges
    assert "b$x0[i] - b$x1[k] >= 0.1 * b$size[i]" in src
