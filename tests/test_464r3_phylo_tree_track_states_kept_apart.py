"""tree_track_render.R: a query tip with no value is NOT_MEASURED and marked; a reference or outgroup
tip is NOT_APPLICABLE and unmarked; a recorded zero stays RECORDED_ZERO. The per-cell states are
written to <prefix>.cell_states.tsv. Renders a 4-tip display figure; no tree is inferred."""
import csv
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RSCRIPT = shutil.which("Rscript")


def _have_r_packages():
    if not RSCRIPT:
        return False
    r = subprocess.run([RSCRIPT, "-e", "q(status=!all(sapply(c('ape','ggtree','ggplot2','patchwork'),requireNamespace,quietly=TRUE)))"],
                       capture_output=True)
    return r.returncode == 0


pytestmark = pytest.mark.skipif(not _have_r_packages(), reason="Rscript with ape/ggtree/ggplot2/patchwork not available")


def test_cell_states_distinguish_not_measured_from_not_applicable(tmp_path):
    (tmp_path / "t.nwk").write_text("((Q1:0.1,Q2:0.1):0.1,(R1:0.1,O1_OUTGROUP:0.2):0.1);")
    (tmp_path / "tracks.tsv").write_text("tip\tlabel\trole\ts1\nQ1\tQuery one\tquery\t42\nQ2\tQuery two\tquery\t\n"
                                         "R1\tRef one\treference\t\nO1_OUTGROUP\tOut one\toutgroup\t\n")
    (tmp_path / "series.tsv").write_text("column\tlabel\tcolour\ns1\tSeries 1\t#1B9E77\n")
    out = tmp_path / "fig" / "track"
    r = subprocess.run([RSCRIPT, str(ROOT / "tools" / "render_tree_bar_groups.R"), str(tmp_path / "t.nwk"),
                        str(tmp_path / "tracks.tsv"), str(tmp_path / "series.tsv"), str(out), "Test", "none", "none"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    states = {row["tip"]: row["state"] for row in csv.DictReader(open(f"{out}.cell_states.tsv"), delimiter="\t")}
    assert states == {"Q1": "OBSERVED", "Q2": "NOT_MEASURED", "R1": "NOT_APPLICABLE", "O1_OUTGROUP": "NOT_APPLICABLE"}
    r2 = subprocess.run([RSCRIPT, str(ROOT / "tools" / "render_tree_bar_groups.R"), str(tmp_path / "t.nwk"),
                         str(tmp_path / "tracks.tsv"), str(tmp_path / "series.tsv"), str(out), "Test"],
                        capture_output=True, text=True)
    assert r2.returncode != 0 and "output exists" in r2.stderr
