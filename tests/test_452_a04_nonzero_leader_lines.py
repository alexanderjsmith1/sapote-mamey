"""A04 'nonzero' labels get leader lines (card attine_452_a04_nonzero_leader_lines). With every isolate off 0/0 labelled,
several labels sit in the cluster near the origin; without a line a label can read as belonging to the next point. The
'nonzero' mode now draws the same thin leader lines and spacing as 'strong'; 'all' is unchanged. Synthetic data only."""
import pytest
import shutil
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a04_nonzero_labels_452l", ROOT / "tests" / "test_452_a04_nonzero_labels.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
LEADER = "#6B7483"


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_nonzero_labels_draw_leader_lines(tmp_path):
    out, text = base.run(tmp_path)
    assert all(s in text for s in ("SYN-971", "SYN-972", "SYN-973"))
    svg = next(out.glob("*.svg")).read_text()
    assert LEADER.lower() in svg.lower()


def test_leader_rule_covers_strong_and_nonzero_only():
    r = (ROOT / "tools" / "bioassay_a04.R").read_text()
    assert 'segment.colour=if(lab_mode %in% c("strong","nonzero"))"#6B7483" else NA' in r
    for knob in ("box.padding", "point.padding", "force", "max.iter"):
        assert f'{knob}=if(lab_mode %in% c("strong","nonzero"))' in r
