# Synthetic regression inputs only.
"""render-figures --figure-set domain-level reads <package>/domain_level/ and says when it writes there.

The domain-level page tells readers to write domain tables to an external --out folder. The figure
route does not read that folder; when the package folder has no tables it runs domain-level into the
package. It must say so instead of doing it silently.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import mamey.domain_figures as domain_figures
import mamey.domain_level as domain_level
from mamey import chatgpt_commands as cc


def test_figure_route_discloses_package_write(tmp_path, monkeypatch, capsys):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "TEST"}), encoding="utf-8")
    calls = []
    import sys as _sys

    def fake_run(p, **kw):
        # the package-write warning must already be out when the run starts
        _sys.stderr.flush()
        calls.append((p, "running domain-level into the package" in capsys.readouterr().err))
        return {"status": "REFUSED", "reason": "occupied"}

    monkeypatch.setattr(domain_level, "run_domain_level", fake_run)
    monkeypatch.setattr(domain_figures, "render_domain_figures",
                        lambda d, outdir=None: {"status": "SKIPPED", "figures": [], "warnings": []})
    args = SimpleNamespace(package=str(pkg), figure_set="domain-level", outdir=None, top_n=3,
                           source_antismash=None)
    assert cc.render_figures_command(args) == 0
    text = capsys.readouterr()
    text = text.out + text.err
    assert calls == [(pkg.resolve(), True)], "warning must print before the run"
    assert "REFUSED (occupied)" in text
