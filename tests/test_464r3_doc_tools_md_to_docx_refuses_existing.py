"""Synthetic Markdown and a stub pandoc only: md_to_docx.sh replaces an existing .docx only with --replace."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "md_to_docx.sh"


def _stub_pandoc(tmp_path):
    bins = tmp_path / "bin"
    bins.mkdir()
    stub = bins / "pandoc"
    # Writes the input bytes plus a marker to the -o target, like a converter would.
    stub.write_text('#!/bin/bash\nout=""; inp=""\nwhile [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; -f|-t) shift 2;; *) inp="$1"; shift;; esac; done\n'
                    '{ echo DOCX; cat "$inp"; } > "$out"\n')
    stub.chmod(0o755)
    return dict(os.environ, PATH=str(bins) + os.pathsep + os.environ["PATH"])


def _run(env, *args):
    return subprocess.run(["bash", str(SCRIPT), *map(str, args)], env=env, capture_output=True, text=True, timeout=60)


def _md(tmp_path):
    md = tmp_path / "report.md"
    md.write_text("# Report\n", encoding="utf-8")
    return md


def test_fresh_output_is_written(tmp_path):
    env = _stub_pandoc(tmp_path)
    md = _md(tmp_path)
    result = _run(env, md, tmp_path / "report.docx")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "report.docx").read_text().startswith("DOCX")
    assert not list(tmp_path.glob(".report.docx.*"))


def test_existing_output_is_refused_without_replace(tmp_path):
    env = _stub_pandoc(tmp_path)
    md = _md(tmp_path)
    out = tmp_path / "report.docx"
    out.write_text("EARLIER")
    result = _run(env, md, out)
    assert result.returncode == 2 and "REFUSED" in result.stderr
    assert out.read_text() == "EARLIER"
    result = _run(env, "--replace", md, out)
    assert result.returncode == 0 and out.read_text().startswith("DOCX")


def test_input_and_links_are_never_replaced(tmp_path):
    env = _stub_pandoc(tmp_path)
    md = _md(tmp_path)
    saved = md.read_bytes()
    assert _run(env, "--replace", md, md).returncode == 2
    link = tmp_path / "link.docx"
    link.symlink_to(md)
    assert _run(env, "--replace", md, link).returncode == 2
    assert md.read_bytes() == saved and link.is_symlink()


def test_missing_pandoc_is_reported(tmp_path):
    md = _md(tmp_path)
    empty = tmp_path / "nobin"
    empty.mkdir()
    env = dict(os.environ, PATH=str(empty) + os.pathsep + "/usr/bin:/bin")
    result = _run(env, md, tmp_path / "r.docx")
    assert result.returncode == 2 and not (tmp_path / "r.docx").exists()
