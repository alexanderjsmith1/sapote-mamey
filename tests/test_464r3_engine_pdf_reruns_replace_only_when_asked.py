"""PDF reruns into the same folder: refused by default, replaced only with an explicit flag.

The PDF renderer (`tools/md_to_pdf.sh`) never replaces an existing PDF or sidecar, so a
`compile-report --pdf` or `build_all_deliverables.sh` rerun into the same folder now fails.
`compile-report --replace-pdf` and `build_all_deliverables.sh --replace` give a deliberate rerun
a route: the earlier files are set aside, restored if the new render fails, and deleted only
after it succeeds.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mamey import compile_report as cr

ROOT = Path(__file__).resolve().parents[1]


def _fake_route(status, write=b"NEW"):
    def run(gated_md, quality, out_pdf, pkg, script):
        if write is not None:
            out_pdf.write_bytes(write)
            Path(str(out_pdf)[:-4] + ".render_preflight.json").write_text("{}", encoding="utf-8")
        return {"status": status, "path": str(out_pdf) if status == "WRITTEN" else None}
    return run


def _earlier(tmp_path):
    out = tmp_path / "report.pdf"
    out.write_bytes(b"OLD")
    (tmp_path / "report.wide_tables_appendix.md").write_text("old appendix\n", encoding="utf-8")
    return out


def test_an_existing_pdf_is_refused_without_the_flag(tmp_path, monkeypatch):
    out = _earlier(tmp_path)
    monkeypatch.setattr(cr, "_run_pdf_route", _fake_route("WRITTEN"))
    res = cr._render_compiled_pdf("# r\n", out, tmp_path)
    assert res["status"] == "OUTPUT_EXISTS"
    assert "--replace-pdf" in res["detail"]
    assert out.read_bytes() == b"OLD"


def test_replace_swaps_in_the_new_set_and_removes_the_old(tmp_path, monkeypatch):
    out = _earlier(tmp_path)
    monkeypatch.setattr(cr, "_run_pdf_route", _fake_route("WRITTEN"))
    res = cr._render_compiled_pdf("# r\n", out, tmp_path, replace=True)
    assert res["status"] == "WRITTEN"
    assert out.read_bytes() == b"NEW"
    assert not (tmp_path / "report.wide_tables_appendix.md").exists()
    assert not [p for p in tmp_path.iterdir() if ".previous." in p.name]


def test_a_failed_replacement_restores_the_earlier_set(tmp_path, monkeypatch):
    out = _earlier(tmp_path)
    monkeypatch.setattr(cr, "_run_pdf_route", _fake_route("RENDER_FAILED", write=b"PARTIAL"))
    res = cr._render_compiled_pdf("# r\n", out, tmp_path, replace=True)
    assert res["status"] == "RENDER_FAILED"
    assert out.read_bytes() == b"OLD"
    assert (tmp_path / "report.wide_tables_appendix.md").read_text(encoding="utf-8") == "old appendix\n"
    assert not (tmp_path / "report.render_preflight.json").exists()
    assert not [p for p in tmp_path.iterdir() if ".previous." in p.name]


def test_a_symlink_at_an_output_name_is_never_replaced(tmp_path, monkeypatch):
    target = tmp_path / "elsewhere.pdf"
    target.write_bytes(b"KEEP")
    (tmp_path / "report.pdf").symlink_to(target)
    monkeypatch.setattr(cr, "_run_pdf_route", _fake_route("WRITTEN"))
    res = cr._render_compiled_pdf("# r\n", tmp_path / "report.pdf", tmp_path, replace=True)
    assert res["status"] == "OUTPUT_NOT_REPLACEABLE"
    assert target.read_bytes() == b"KEEP"


def test_compile_report_has_the_replace_flag():
    out = subprocess.run(["python3", "mamey_run.py", "compile-report", "--help"], cwd=ROOT,
                         capture_output=True, text=True, timeout=120).stdout
    assert "--replace-pdf" in out


_STUB_PDF = """#!/usr/bin/env bash
# stub renderer with the real one's rule: never replace an existing output
set -euo pipefail
[[ -e "$2" ]] && { echo "REFUSED: output already exists" >&2; exit 2; }
mkdir -p "$(dirname "$2")"; printf 'PDF %s\\n' "$(cat "$1" | head -c 20)" > "$2"
"""
_STUB_DOCX = """#!/usr/bin/env bash
[ "${1:-}" = "--replace" ] && shift
printf 'DOCX\\n' > "$2"
"""
_STUB_MD = """import argparse, os
p = argparse.ArgumentParser(); p.add_argument('--banked-dir'); p.add_argument('--workbook')
p.add_argument('--out'); p.add_argument('--out-dir'); p.add_argument('--thesaurus')
a = p.parse_args()
if a.out:
    os.makedirs(os.path.dirname(a.out), exist_ok=True); open(a.out, 'w').write('# stub\\n')
"""


def _fake_root(tmp_path):
    root = tmp_path / "root"
    tools = root / "tools"
    tools.mkdir(parents=True)
    shutil.copy2(ROOT / "tools" / "build_all_deliverables.sh", tools / "build_all_deliverables.sh")
    (tools / "md_to_pdf.sh").write_text(_STUB_PDF, encoding="utf-8")
    (tools / "md_to_docx.sh").write_text(_STUB_DOCX, encoding="utf-8")
    for name in ("build_modeb_deepdive.py", "build_thesis_vignettes.py", "build_gcf_tags.py", "build_size_profile.py"):
        (tools / name).write_text(_STUB_MD, encoding="utf-8")
    return root


def _run(root, *args):
    return subprocess.run(["bash", "tools/build_all_deliverables.sh", *args, "cohort", ""], cwd=root,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_build_all_rerun_fails_without_replace_and_passes_with_it(tmp_path):
    root = _fake_root(tmp_path)
    first = _run(root)
    assert first.returncode == 0, first.stdout + first.stderr
    pdf = root / "deliverables" / "deep_dives" / "ModeB_DeepDives_Full.pdf"
    assert pdf.is_file()
    second = _run(root)
    assert second.returncode == 1
    assert "rerun with --replace" in second.stderr
    pdf.write_text("EARLIER\n", encoding="utf-8")
    third = _run(root, "--replace")
    assert third.returncode == 0, third.stdout + third.stderr
    assert pdf.read_text(encoding="utf-8").startswith("PDF ")
    leftovers = [p for p in (root / "deliverables").rglob("*") if ".previous." in p.name]
    assert not leftovers
