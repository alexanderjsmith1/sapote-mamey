"""A deliberate rerun with --replace reaches every renderer that now refuses an existing output.

`tools/md_to_docx.sh` refuses an existing .docx unless it is given `--replace`, so
`build_all_deliverables.sh --replace` passes the flag through to it. `good-guesses` reads
`args.replace` to replace an earlier GOOD_GUESSES.pdf, so the `mamey_run.py good-guesses`
subcommand carries the `--replace` flag. `tools/build_gcf_tags.py` refuses an existing
GCF_Tags.csv and has no replace flag, so `build_all_deliverables.sh` refuses it by name without
`--replace` and, with it, sets the earlier file aside and restores it if the step fails.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mamey import cli
from mamey import good_guesses as gg

ROOT = Path(__file__).resolve().parents[1]

_STUB_PDF = """#!/usr/bin/env bash
set -euo pipefail
[[ -e "$2" ]] && { echo "REFUSED: output already exists" >&2; exit 2; }
mkdir -p "$(dirname "$2")"; printf 'PDF\\n' > "$2"
"""
# Stands in for pandoc only; the real tools/md_to_docx.sh does the refusing and replacing.
_STUB_PANDOC = """#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; *) shift;; esac; done
printf 'DOCX NEW\\n' > "$out"
"""
_STUB_MD = """import argparse, os
p = argparse.ArgumentParser(); p.add_argument('--banked-dir'); p.add_argument('--workbook')
p.add_argument('--out'); p.add_argument('--out-dir'); p.add_argument('--thesaurus')
a = p.parse_args()
if a.out:
    os.makedirs(os.path.dirname(a.out), exist_ok=True); open(a.out, 'w').write('# stub\\n')
"""


# Stub with the real tool's rule: refuse an existing GCF_Tags.csv. STUB_TAGS_FAIL=1 makes it fail.
_STUB_TAGS = """import argparse, os, sys
p = argparse.ArgumentParser(); p.add_argument('--banked-dir'); p.add_argument('--workbook')
p.add_argument('--out-dir'); p.add_argument('--thesaurus')
a = p.parse_args(); os.makedirs(a.out_dir, exist_ok=True); out = os.path.join(a.out_dir, 'GCF_Tags.csv')
if os.path.exists(out):
    sys.exit('refusing ' + out)
if os.environ.get('STUB_TAGS_FAIL'):
    sys.exit('tags failed')
open(out, 'w').write('TAGS NEW\\n')
"""


def _fake_root(tmp_path):
    root = tmp_path / "root"
    tools = root / "tools"
    tools.mkdir(parents=True)
    for name in ("build_all_deliverables.sh", "md_to_docx.sh"):
        shutil.copy2(ROOT / "tools" / name, tools / name)
    (tools / "md_to_pdf.sh").write_text(_STUB_PDF, encoding="utf-8")
    for name in ("build_modeb_deepdive.py", "build_thesis_vignettes.py", "build_size_profile.py"):
        (tools / name).write_text(_STUB_MD, encoding="utf-8")
    (tools / "build_gcf_tags.py").write_text(_STUB_TAGS, encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pandoc").write_text(_STUB_PANDOC, encoding="utf-8")
    (bin_dir / "pandoc").chmod(0o755)
    return root, bin_dir


def _run(root, bin_dir, *args, **extra):
    py_dir = str(Path(sys.executable).parent)
    env = {"PATH": f"{bin_dir}:{py_dir}:/usr/bin:/bin", "HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1", **extra}
    return subprocess.run(["bash", "tools/build_all_deliverables.sh", *args, "cohort", ""], cwd=root,
                          env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_build_all_replace_reaches_the_docx_renderer(tmp_path):
    root, bin_dir = _fake_root(tmp_path)
    first = _run(root, bin_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    docx = root / "deliverables" / "deep_dives" / "ModeB_DeepDives_Full.docx"
    assert docx.read_text(encoding="utf-8") == "DOCX NEW\n"
    docx.write_text("EARLIER\n", encoding="utf-8")
    second = _run(root, bin_dir)
    assert second.returncode == 1
    assert f"REFUSED: output already exists: deliverables/deep_dives/{docx.name}; choose a new path or pass --replace" in second.stderr
    assert docx.read_text(encoding="utf-8") == "EARLIER\n"
    third = _run(root, bin_dir, "--replace")
    assert third.returncode == 0, third.stdout + third.stderr
    assert docx.read_text(encoding="utf-8") == "DOCX NEW\n"
    assert not [p for p in docx.parent.iterdir() if p.name.startswith(".")]


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_gcf_tags_are_refused_by_name_replaced_with_the_flag_and_restored_on_failure(tmp_path):
    root, bin_dir = _fake_root(tmp_path)
    assert _run(root, bin_dir).returncode == 0
    tags = root / "deliverables" / "analyses" / "GCF_Tags.csv"
    tags.write_text("EARLIER\n", encoding="utf-8")
    second = _run(root, bin_dir)
    assert second.returncode == 1
    assert ("REFUSED: earlier GCF tags exist (rerun with --replace): deliverables/analyses/GCF_Tags.csv"
            in second.stderr)
    assert tags.read_text(encoding="utf-8") == "EARLIER\n"
    failed = _run(root, bin_dir, "--replace", STUB_TAGS_FAIL="1")
    assert failed.returncode == 1
    assert tags.read_text(encoding="utf-8") == "EARLIER\n"
    assert not [p for p in tags.parent.iterdir() if p.name.startswith(".")]
    third = _run(root, bin_dir, "--replace")
    assert third.returncode == 0, third.stdout + third.stderr
    assert tags.read_text(encoding="utf-8") == "TAGS NEW\n"
    assert not [p for p in tags.parent.iterdir() if p.name.startswith(".")]


def test_good_guesses_subcommand_passes_replace(tmp_path, monkeypatch):
    seen = []

    def fake_render_pdf(md_path, pdf_path, pkg_hint=None, replace=False):
        seen.append(replace)
        return {"status": "PASS", "path": str(pdf_path)}

    monkeypatch.setattr(gg, "render_pdf", fake_render_pdf)
    out = tmp_path / "gg"
    assert cli.main(["good-guesses", str(tmp_path / "empty"), "--out", str(out), "--pdf"]) == 0
    assert cli.main(["good-guesses", str(tmp_path / "empty"), "--out", str(out), "--pdf", "--replace"]) == 0
    assert seen == [False, True]


def test_good_guesses_help_shows_replace():
    text = cli.build_parser()._subparsers._group_actions[0].choices["good-guesses"].format_help()
    assert "--replace" in text
