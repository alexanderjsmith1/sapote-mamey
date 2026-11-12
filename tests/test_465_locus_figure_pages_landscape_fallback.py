"""9.7.465: a map too wide for the chosen width falls back to landscape instead of failing the figure.

Fail-before on sealed 9.7.464: a map that gap_directed_rescue could not fit to 6.5 in (GAP_RESCUE_MAP_PRINT_WIDTH, for
example widths [7.31, 7.31, 7.31, 7.31] in) failed the whole figure, and its partial panel folder made a rerun into the
same --out refuse. Pass-after: that map is redrawn at landscape as panels/<map>__landscape/, the figure is composed at
landscape width, and <prefix>_PAGES.json records the fallback. A map failing for any other reason still fails the figure.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
if "mamey" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

T = pytest.importorskip("locus_figure_pages")


class _P:
    def __init__(self, rc, stdout=""):
        self.returncode, self.stdout, self.stderr = rc, stdout, ""


def _spec(tmp, n=2):
    rows = ["letter\trun\tstrain\tzip"]
    for i, letter in zip(range(n), "ab"):
        run = tmp / f"SYN-{i}_BGC00{i}_x"
        run.mkdir()
        (run / "gap_rescue_receipt.json").write_text("{}")
        z = tmp / f"SYN-{i}.zip"
        z.write_bytes(b"zip")
        rows.append(f"{letter}\t{run}\tSYN-{i}\t{z}")
    spec = tmp / "spec.tsv"
    spec.write_text("\n".join(rows) + "\n")
    return spec


def _fake(wide_runs, other_fail=(), height_px=600):
    """subprocess.run stand-in: maps in wide_runs fail every width but landscape; maps in other_fail always fail."""
    from PIL import Image
    seen = []

    def run(cmd, **kw):
        seen.append(cmd)
        if "gap_rescue_panel_figure.py" in cmd[1]:
            return _P(0)
        width, run_dir, out = cmd[cmd.index("--print-width") + 1], cmd[cmd.index("--redraw") + 1], Path(cmd[cmd.index("--out") + 1])
        log = kw.get("stdout")
        if Path(run_dir).name in other_fail:
            log.write("ValueError: something else\n"); return _P(1)
        if Path(run_dir).name in wide_runs and width != "landscape":
            out.mkdir(parents=True)                      # a failed attempt leaves its folder, as the real tool does
            log.write("ValueError: GAP_RESCUE_MAP_PRINT_WIDTH: could not fit the map to 6.5 in\n"); return _P(1)
        out.mkdir(parents=True)
        Image.new("RGB", (int((9.0 if width == "landscape" else 6.5) * 300), height_px), "white").save(out / "gap_rescue.png")
        return _P(0)
    return run, seen


def test_a_too_wide_map_is_redrawn_at_landscape(tmp_path, monkeypatch):
    spec = _spec(tmp_path)
    run, seen = _fake({"SYN-0_BGC000_x"})
    monkeypatch.setattr(T.subprocess, "run", run)
    out = tmp_path / "out"
    assert T.main(["--spec", str(spec), "--out", str(out), "--prefix", "fig", "--mibig-dir", str(tmp_path)]) == 0
    pages = json.loads((out / "fig_PAGES.json").read_text())
    assert pages["landscape_fallback"] == ["SYN-0_BGC000_x"] and pages["width_used"] == "landscape"
    assert pages["page_width_in"] == 9.0
    assert (out / "panels" / "SYN-0_BGC000_x__landscape" / "gap_rescue.png").is_file()
    compose = next(c for c in seen if "gap_rescue_panel_figure.py" in c[1])
    assert compose[compose.index("--print-width") + 1] == "9.0"


def test_no_fallback_when_every_map_fits(tmp_path, monkeypatch):
    spec = _spec(tmp_path)
    run, _ = _fake(set())
    monkeypatch.setattr(T.subprocess, "run", run)
    out = tmp_path / "out"
    assert T.main(["--spec", str(spec), "--out", str(out), "--prefix", "fig", "--mibig-dir", str(tmp_path)]) == 0
    pages = json.loads((out / "fig_PAGES.json").read_text())
    assert pages["landscape_fallback"] == [] and pages["width_used"] == "page6.5" and pages["page_width_in"] == 6.5


def test_another_failure_still_fails_the_figure(tmp_path, monkeypatch):
    spec = _spec(tmp_path)
    run, _ = _fake(set(), other_fail={"SYN-1_BGC001_x"})
    monkeypatch.setattr(T.subprocess, "run", run)
    assert T.main(["--spec", str(spec), "--out", str(tmp_path / "out"), "--prefix", "fig",
                   "--mibig-dir", str(tmp_path)]) == 2


def test_fallback_pages_fit_the_landscape_page_height(tmp_path, monkeypatch):
    """Two 4 in maps fit one 9 in page-limit stack, but not the 6.5 in landscape page: they go on two pages."""
    spec = _spec(tmp_path)
    run, seen = _fake({"SYN-0_BGC000_x"}, height_px=1200)
    monkeypatch.setattr(T.subprocess, "run", run)
    out = tmp_path / "out"
    assert T.main(["--spec", str(spec), "--out", str(out), "--prefix", "fig", "--mibig-dir", str(tmp_path)]) == 0
    compose = next(c for c in seen if "gap_rescue_panel_figure.py" in c[1])
    assert compose[compose.index("--max-page-height") + 1] == "6.5"
    assert compose[compose.index("--pages") + 1] == "a,b"
