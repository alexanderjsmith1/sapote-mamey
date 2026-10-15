"""A genome pair with no ANI hit is 'no hit', not 0 % identity; the ani command fails when it writes no figure."""
import math
from types import SimpleNamespace

import numpy as np
from mamey import bgc_figures as bf


def test_symmetrize_keeps_one_measured_direction_and_marks_none():
    m = np.array([[100.0, np.nan, 90.0],
                  [80.0, 100.0, np.nan],
                  [92.0, np.nan, 100.0]])
    s = bf._symmetrize_ani(m)
    assert s[0, 1] == 80.0 and s[1, 0] == 80.0
    assert s[0, 2] == 91.0
    assert math.isnan(s[1, 2]) and math.isnan(s[2, 1])
    assert np.allclose(np.diag(s), 100.0)


def test_ani_command_exits_nonzero_when_no_figure(monkeypatch, capsys):
    monkeypatch.setattr(bf, "ani_heatmap", lambda dirs, out: {"out_png": None, "intransitive": False,
                                                              "error": "needs >=2 genomes"})
    rc = bf.figures_command(SimpleNamespace(fig_kind="ani", strain_dirs=["a"], out="x.png"))
    assert rc == 1
