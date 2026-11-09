"""Synthetic Markdown only: md_to_pdf.sh never replaces an earlier PDF or sidecar on either route."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "md_to_pdf.sh"


def _run(md, out):
    env = dict(os.environ, PYTHON=sys.executable)
    return subprocess.run(["bash", str(SCRIPT), str(md), str(out)], env=env,
                          capture_output=True, text=True, timeout=300)


def _md(tmp_path):
    md = tmp_path / "report.md"
    md.write_text("# Synthetic report\n\nOne line.\n", encoding="utf-8")
    return md


def test_existing_pdf_is_refused_before_any_route(tmp_path):
    md = _md(tmp_path)
    out = tmp_path / "report.pdf"
    out.write_bytes(b"EARLIER PDF")
    result = _run(md, out)
    assert result.returncode == 2, result.stderr
    assert "REFUSED" in result.stderr
    assert out.read_bytes() == b"EARLIER PDF"


@pytest.mark.parametrize("suffix", [".render_preflight.json", ".wide_tables_appendix.md", ".resource_bindings.json"])
def test_existing_sidecar_is_refused(tmp_path, suffix):
    md = _md(tmp_path)
    out = tmp_path / "new.pdf"
    side = tmp_path / ("new" + suffix)
    side.write_text("EARLIER SIDECAR", encoding="utf-8")
    result = _run(md, out)
    assert result.returncode == 2, result.stderr
    assert side.read_text() == "EARLIER SIDECAR"
    assert not out.exists()


def test_output_equal_to_input_is_refused(tmp_path):
    md = _md(tmp_path)
    saved = md.read_bytes()
    result = _run(md, md)
    assert result.returncode == 2
    assert md.read_bytes() == saved


@pytest.mark.skipif(importlib.util.find_spec("reportlab") is None, reason="primary renderer needs reportlab")
def test_primary_route_second_run_does_not_overwrite(tmp_path):
    md = _md(tmp_path)
    out = tmp_path / "report.pdf"
    first = _run(md, out)
    assert first.returncode == 0, first.stderr
    assert "(colorful reportlab)" in first.stdout
    written = out.read_bytes()
    second = _run(md, out)
    assert second.returncode == 2
    assert out.read_bytes() == written
    assert not list(tmp_path.glob(".report.pdf.*.tmp"))
