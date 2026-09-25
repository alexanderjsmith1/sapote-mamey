"""sapote_pub_layout.R: one house layout (figure, public caption, rule, internal notes) that passes render QC."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
HELPER = ROOT / "tools" / "sapote_pub_layout.R"

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")


def _render(tmp: Path, stem: str, internal: str, caption_file: str = "CAPTION.md") -> subprocess.CompletedProcess:
    script = f"""
    ok <- all(vapply(c("ggplot2", "ggtext"), requireNamespace, logical(1), quietly = TRUE))
    if (!ok) quit(status = 77)
    source("{HELPER}")
    p <- ggplot(data.frame(g = c("A", "B"), n = c(3, 5)), aes(g, n)) + geom_col() + theme_pub() +
      labs(title = "Regions per isolate", x = NULL, y = "Regions")
    save_pub(p, "{stem}", "Regions per isolate; loose antiSMASH 8.0.4 for every genome.",
             "{internal}", w = 5, h_body = 3.5, caption_file = "{caption_file}", outdir = "{tmp}")
    """
    return subprocess.run(["Rscript", "-e", script], capture_output=True, text=True, timeout=180)


def test_layout_writes_four_outputs_and_passes_qc(tmp_path):
    r = _render(tmp_path, "FIG_T01_regions_crude", "Tool: antiSMASH 8.0.4, strictness loose.")
    if r.returncode == 77:
        pytest.skip("ggplot2/ggtext not installed")
    assert r.returncode == 0, r.stderr
    for name in ["FIG_T01_regions_crude.png", "FIG_T01_regions_crude.pdf",
                 "FIG_T01_regions_crude_plot_only.png", "CAPTION.md"]:
        assert (tmp_path / name).stat().st_size > 0, name
    cap = (tmp_path / "CAPTION.md").read_text()
    assert cap.startswith("# FIG_T01_regions_crude") and "## Internal notes" in cap
    import figure_render_qc as qc
    res = qc.run([tmp_path], tmp_path, ocr_mode="off")
    assert [m for _, fl in res for lv, m in fl if lv in ("error", "warn")] == []


def test_claim_wording_in_internal_notes_is_caught(tmp_path):
    r = _render(tmp_path, "FIG_T02_regions_crude", "Judgment deferred; not production.")
    if r.returncode == 77:
        pytest.skip("ggplot2/ggtext not installed")
    assert r.returncode == 0, r.stderr
    import figure_render_qc as qc
    fl = qc.run([tmp_path], tmp_path, ocr_mode="off")[0][1]
    assert any(lv == "warn" and "CAPTION.md" in m for lv, m in fl)
    if sys.platform == "darwin" and shutil.which("swiftc"):
        # The internal notes are drawn on the page, so OCR sees them: that is an error.
        assert qc.main([str(tmp_path), "--ocr", "require"]) == 2


def test_caption_of_another_figure_is_not_overwritten(tmp_path):
    (tmp_path / "CAPTION.md").write_text("# FIG_OTHER\n\nsomething\n")
    r = _render(tmp_path, "FIG_T03_regions_crude", "notes")
    if r.returncode == 77:
        pytest.skip("ggplot2/ggtext not installed")
    assert r.returncode != 0 and "belongs to another figure" in r.stderr
    assert (tmp_path / "CAPTION.md").read_text().startswith("# FIG_OTHER")
