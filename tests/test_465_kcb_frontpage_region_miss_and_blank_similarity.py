"""kcb-frontpage: a --region that matches nothing names the anchors that carry hits; a missing similarity is a dash."""
from __future__ import annotations
from types import SimpleNamespace

import mamey.kcb_frontpage as K


def _hits():
    return [{"region": "r1c1", "compound": "alpha", "similarity": None, "n_genes": 3, "tier": "LOW"},
            {"region": "r2c1", "compound": "beta", "similarity": 0, "n_genes": 1, "tier": "LOW"}]


def _run(monkeypatch, capsys, region):
    monkeypatch.setattr(K, "read_frontpage", lambda *a, **k: _hits())
    rc = K.frontpage_command(SimpleNamespace(strain_dir="x", region=region, node=None, bgc=None, top=10))
    return rc, capsys.readouterr().out


def test_region_miss_names_the_anchors_with_hits(monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, "region001")
    assert rc == 1
    assert "region=region001" in out
    assert "r1c1, r2c1" in out
    assert "No KnownClusterBlast hits after filter" not in out


def test_missing_similarity_is_a_dash_and_zero_stays_zero(monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, None)
    assert rc == 0
    rows = {line.split()[0]: line.split() for line in out.splitlines() if line.startswith("r")}
    assert rows["r1c1"][2] == "—"
    assert rows["r2c1"][2] == "0"
