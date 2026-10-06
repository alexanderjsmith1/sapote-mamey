"""mamey/figures_smoke.py: a free-text product label never becomes an unbounded matplotlib label.

fresh-clone audit, 2026-10-01 (D7): tests/test_hostile_gates_round3_v97409.py prepends 300,000 characters to a
/product qualifier; the class-composition figure drew it as one x tick, matplotlib passed 5.5 GB RSS and the kernel
killed the run (rc 137) after the package had sealed. The try/except around the smoke step cannot catch an OOM kill.
"""
import csv
import time

import pytest

from mamey import figures_smoke as fs


def test_cap_label_keeps_short_labels_and_cuts_long_ones():
    assert fs._cap_label("NRPS") == "NRPS"
    cut = fs._cap_label("A" * 300_000)
    assert len(cut) == fs.LABEL_MAX and cut.endswith("…")


def test_class_composition_draws_a_300kb_token_quickly_and_keeps_it_in_the_sidecar(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    huge = "A" * 300_000 + "lanthipeptide"
    triage = [{"Products": f"{huge}; NRPS"}, {"Products": "NRPS"}]
    t0 = time.time()
    png = fs._fig_class_composition(plt, triage, [], tmp_path)
    assert png is not None and png.exists()
    assert time.time() - t0 < 60
    csv.field_size_limit(2**31 - 1)   # as mamey.validate does; the default 128 KB cap refuses the field
    rows = list(csv.reader(open(tmp_path / "fig_class_composition_data.csv")))
    assert any(r and r[0] == huge for r in rows)   # the full value is kept in the data CSV
