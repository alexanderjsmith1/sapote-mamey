#!/usr/bin/env python3
"""CLAUDE_409_optional_deps_guard — fail-before / pass-after evidence.

Two real dependency defects in the .408 bundle crash a deliverable path when an OPTIONAL
package is absent, instead of skipping it with a clear message:

  (a) tools/build_chat_export.py hard-imports `markdown` in to_html(); its absence raises a bare
      ModuleNotFoundError even though the .md deliverable was already written.
  (b) deliverable_tools/build_strain_dossier.py and build_modeb_compilation.py do
      `from md_to_docx import convert` — a Python module that does not exist in the bundle (the
      only md->docx helper is the pandoc-backed shell script tools/md_to_docx.sh) — so the .docx
      pass raises ModuleNotFoundError on every run.

Each test loads the PRISTINE module (proves the raw crash) and the PATCHED module (proves a typed,
actionable skip). The patch is applied to a temp copy inside the test; nothing in the tree is mutated.

Run:  pytest -q test_optional_deps_guard.py
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

LANE = Path(__file__).resolve().parent
ROOT = LANE.parent                            # this bundle (the lane is already folded in)
PRISTINE = Path(os.environ.get("SAPOTE_PRISTINE_ROOT", str(ROOT.parent / "sapote-mamey-v9_7_408-CODE-20260904v97408a")))
PATCH = LANE / "CLAUDE_409_optional_deps_guard.patch"
_needs_pristine = pytest.mark.skipif(not PRISTINE.is_dir(), reason="fail-before probe needs a pristine .408 tree (set SAPOTE_PRISTINE_ROOT)")

# Support files each target imports at import time (co-located siblings).
NEEDED = [
    "tools/build_chat_export.py", "tools/lab_office_render.py", "tools/bgc_deliverable_pdf.py",
    "tools/_console.py", "tools/_wbio.py", "tools/md_to_docx.sh",
    "deliverable_tools/build_strain_dossier.py", "deliverable_tools/build_modeb_compilation.py",
    "deliverable_tools/_console.py",
    "requirements.txt", "pyproject.toml",
]

_UID = [0]


def _load(path: Path, block_imports=()):
    """Import a module from a file path under a unique name, optionally blocking packages."""
    _UID[0] += 1
    name = f"_odg_{_UID[0]}_{path.stem}"
    saved = {m: sys.modules.get(m) for m in block_imports}
    for m in block_imports:
        sys.modules[m] = None            # `import m` then raises ImportError
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for m, v in saved.items():
            if v is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = v


@pytest.fixture(scope="module")
def patched_root(tmp_path_factory):
    """A temp tree with the needed pristine files, with the lane patch applied."""
    # The lane is folded into this bundle: the in-tree files ARE the patched files.
    root = tmp_path_factory.mktemp("patched")
    for rel in NEEDED:
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return root


# ── Defect (a): markdown in build_chat_export.to_html ───────────────────────────────────────
@_needs_pristine
def test_markdown_fail_before():
    """PRISTINE: to_html() with `markdown` absent raises a bare ImportError (the crash)."""
    mod = _load(PRISTINE / "tools/build_chat_export.py")
    assert not hasattr(mod, "OptionalDependencyMissing")   # pristine has no typed guard
    with pytest.raises(ImportError):
        _load(PRISTINE / "tools/build_chat_export.py", block_imports=("markdown",)) \
            .to_html("# hi", "t", False)


def test_markdown_pass_after(patched_root, tmp_path, monkeypatch):
    """PATCHED: to_html() raises the typed guard; main() still writes the .md deliverable."""
    monkeypatch.setitem(sys.modules, "markdown", None)
    mod = _load(patched_root / "tools/build_chat_export.py")
    assert hasattr(mod, "OptionalDependencyMissing")
    with pytest.raises(mod.OptionalDependencyMissing) as ei:
        mod.to_html("# hi", "t", False)
    msg = str(ei.value)
    assert "pip install markdown" in msg and "skipped" in msg.lower()

    # end-to-end: main() must not crash and must leave the .md behind
    tr = tmp_path / "chat.txt"
    tr.write_text("Human:\nhello there\n\nAssistant:\nhi back\n", encoding="utf-8")
    outdir = tmp_path / "out"
    argv = ["build_chat_export.py", "--transcript", str(tr), "--out-dir", str(outdir)]
    old = sys.argv
    sys.argv = argv
    try:
        mod.main()                       # must NOT raise despite markdown being blocked
    finally:
        sys.argv = old
    assert (outdir / "chat.md").is_file(), "markdown deliverable should still be written"


# ── Defect (b): md_to_docx helper in the two deliverable builders ───────────────────────────
@pytest.mark.parametrize("rel", [
    "deliverable_tools/build_strain_dossier.py",
    "deliverable_tools/build_modeb_compilation.py",
])
@_needs_pristine
def test_md_to_docx_fail_before(rel):
    """PRISTINE: to_docx() does `from md_to_docx import convert` -> ModuleNotFoundError."""
    mod = _load(PRISTINE / rel)
    # ensure no stray md_to_docx module can satisfy the import
    sys.modules.pop("md_to_docx", None)
    with pytest.raises(ModuleNotFoundError):
        mod.to_docx("x.md", "x.docx")


@pytest.mark.parametrize("rel", [
    "deliverable_tools/build_strain_dossier.py",
    "deliverable_tools/build_modeb_compilation.py",
])
def test_md_to_docx_pass_after(patched_root, rel, monkeypatch, tmp_path):
    """PATCHED: to_docx() raises the typed guard (not ModuleNotFoundError) when the docx path
    cannot complete; the helper resolves the real pandoc script tools/md_to_docx.sh."""
    mod = _load(patched_root / rel)
    assert hasattr(mod, "OptionalDependencyMissing")
    # Make the Python-side imports available independently of the host. None of
    # their functions may run: the real converter must stop at missing Pandoc.
    def unexpected_use(*args, **kwargs):
        raise AssertionError("DOCX post-processing ran before conversion succeeded")
    stubs = {
        "docx": {"Document": unexpected_use},
        "docx.enum": {},
        "docx.enum.section": {"WD_ORIENT": object()},
        "docx.shared": {"Inches": unexpected_use},
        "docx.oxml": {"OxmlElement": unexpected_use},
        "docx.oxml.ns": {"qn": unexpected_use},
    }
    for name, attributes in stubs.items():
        module = types.ModuleType(name)
        for key, value in attributes.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, name, module)
    # force the "pandoc missing" branch deterministically, regardless of the test host
    monkeypatch.setattr(shutil, "which", lambda *_a, **_k: None)
    md = tmp_path / "d.md"
    md.write_text("# t\n\nbody\n", encoding="utf-8")
    with pytest.raises(mod.OptionalDependencyMissing) as ei:
        mod.to_docx(str(md), str(tmp_path / "d.docx"))
    assert "docx export skipped" in str(ei.value).lower()
    assert "pandoc" in str(ei.value).lower()
    assert md.read_text(encoding="utf-8") == "# t\n\nbody\n"
    assert not (tmp_path / "d.docx").exists()

    # and the helper it now points at actually exists in the bundle
    helper = ROOT / "tools" / "md_to_docx.sh"
    assert helper.is_file(), "md_to_docx.sh (the real pandoc helper) must exist"


@pytest.mark.parametrize("rel", [
    "deliverable_tools/build_strain_dossier.py",
    "deliverable_tools/build_modeb_compilation.py",
])
def test_md_to_docx_missing_python_docx(patched_root, rel, monkeypatch, tmp_path):
    """Missing python-docx is a separate typed, actionable failure before conversion."""
    mod = _load(patched_root / rel)
    monkeypatch.setitem(sys.modules, "docx", None)
    def unexpected_conversion(*args, **kwargs):
        raise AssertionError("conversion attempted without python-docx")
    monkeypatch.setattr(mod, "_md_to_docx_convert", unexpected_conversion)
    md = tmp_path / "d.md"
    md.write_text("# retained\n", encoding="utf-8")
    destination = tmp_path / "d.docx"
    with pytest.raises(mod.OptionalDependencyMissing) as ei:
        mod.to_docx(str(md), str(destination))
    assert "docx post-processing skipped" in str(ei.value).lower()
    assert "pip install python-docx" in str(ei.value)
    assert md.read_text(encoding="utf-8") == "# retained\n"
    assert not destination.exists()


# ── Declaration: the optional deps are now declared, not silently assumed ───────────────────
def test_markdown_is_declared(patched_root):
    txt = (patched_root / "pyproject.toml").read_text(encoding="utf-8")
    # markdown declared in the documents extra (and the all extra)
    docline = next(l for l in txt.splitlines() if l.strip().startswith("documents ="))
    assert "markdown" in docline
    req = (patched_root / "requirements.txt").read_text(encoding="utf-8")
    assert "markdown" in req and "pandoc" in req


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
