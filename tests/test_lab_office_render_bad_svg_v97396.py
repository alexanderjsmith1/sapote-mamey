"""Regression test — v97396: lab_office_render.py crashes the ENTIRE batch render on one figure
whose rendered SVG has no viewBox attribute.

`ET.parse(svg).getroot().get("viewBox").split()` raises AttributeError when a renderer produces
an SVG lacking a viewBox (a real, plausible renderer output shape -- not every SVG carries one).
The only surrounding except clause catches `subprocess.CalledProcessError` specifically, so this
different exception type propagates out of the per-figure loop entirely: the ONE bad figure
crashes `main()` before it ever attempts any remaining figure, and no INDEX.md / manifest is
written at all -- for a tool whose whole design is "one command turns a folder of figure JSONs
into a report-ready figure set" and "writes an INDEX.md and sha256 manifest so a report folder is
reproducible."
"""
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))


def _run_against(tmp_path, monkeypatch, first_svg_has_viewbox, second_svg_has_viewbox=True):
    import lab_office_render as m

    figs = tmp_path / "figs"
    figs.mkdir()
    (figs / "bad_figure.json").write_text('{"template": "bar_chart", "data": {"x": [1,2,3]}}')
    (figs / "good_figure.json").write_text('{"template": "line_chart", "data": {"x": [1,2,3]}}')

    monkeypatch.setattr(m, "NODE", sys.executable)
    monkeypatch.setattr(m, "RENDERER", sys.executable)

    calls = {"n": 0}

    def fake_run(args, check=True, capture_output=True, text=True):
        svg_path = args[-1]
        calls["n"] += 1
        has_vb = first_svg_has_viewbox if calls["n"] == 1 else second_svg_has_viewbox
        body = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"></svg>'
            if has_vb else
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"></svg>'
        )
        open(svg_path, "w").write(body)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    class FakeCairo:
        @staticmethod
        def svg2png(url, write_to, output_width):
            open(write_to, "wb").write(b"PNG")

    monkeypatch.setitem(sys.modules, "cairosvg", FakeCairo())

    monkeypatch.setattr(sys, "argv", ["lab_office_render.py", "--dir", str(figs)])
    rc = m.main()
    return rc, calls["n"], figs / "_rendered" / "INDEX.md"


def test_one_bad_svg_does_not_crash_the_whole_batch_v97396(tmp_path, monkeypatch):
    rc, n_calls, index = _run_against(tmp_path, monkeypatch, first_svg_has_viewbox=False)
    assert n_calls == 2, (
        f"only {n_calls} figure(s) were attempted -- a bad SVG must not stop the remaining "
        "figures in the batch from being tried"
    )
    assert index.exists(), "INDEX.md must still be written even when one figure failed"


def test_all_good_svgs_still_render_cleanly_no_regression_v97396(tmp_path, monkeypatch):
    rc, n_calls, index = _run_against(tmp_path, monkeypatch, first_svg_has_viewbox=True)
    assert rc == 0
    assert n_calls == 2
    assert index.exists()
