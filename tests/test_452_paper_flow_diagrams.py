"""Paper flow diagrams (card 018c0f08_452_paper_flow_diagrams): the default workflow diagram and the two method
diagrams use plain words, with no folder, module or schema names, and every figure choice writes its own .dot."""
import importlib.util, re, shutil, subprocess, sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bwf", ROOT / "tools" / "build_workflow_figure.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
INTERNAL = re.compile(r"tools/|cohort/|schema v|Mode B|Lead_Board|Priority_Leads|MAMEY|SAPOTE|JSON bank|four-axis", re.I)


@pytest.mark.parametrize("name", ["workflow", "gap-rescue", "split-pathway"])
def test_paper_diagrams_have_no_internal_names(name):
    assert not INTERNAL.search(m.FIGURES[name])


def test_default_is_paper_workflow():
    assert m.DOT == m.FIGURES["workflow"] and "antiSMASH archive" in m.DOT


def test_gap_rescue_states_thresholds():
    d = m.FIGURES["gap-rescue"]
    assert "30% identity" in d and "50% of the protein" in d and "70% complete" in d


@pytest.mark.parametrize("name,stem", [("workflow", "fig_workflow"), ("gap-rescue", "fig_gap_rescue"), ("split-pathway", "fig_split_pathway")])
def test_each_figure_writes_its_dot(tmp_path, name, stem):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_workflow_figure.py"), "--out-dir", str(tmp_path), "--figure", name],
                       capture_output=True, text=True)
    assert r.returncode == 0 and (tmp_path / f"{stem}.dot").exists()
