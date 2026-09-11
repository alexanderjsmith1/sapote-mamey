"""v9.7.355 — pins Tools/check_md_links.py, the guard for the recurring 'dead file link' problem
(un-encoded spaces/parens; nonexistent targets). The tool exists and is wired as a PostToolUse hook
(md_link_check.sh), but it has NO test — so a future refactor could silently stop catching the #8
problem. This pins its four core behaviors.

The tool is currently a workspace-only script (Tools/check_md_links.py). RECOMMENDATION (see PATCH_CARD):
ship it portable into the bundle's Tools/ alongside the portable hooks/, per the portable-rules principle;
this test then travels with it. The loader below tries the bundle Tools/ first, then the workspace Tools/.
"""
from __future__ import annotations
import importlib.util
import pathlib
import pytest
import os

_CANDIDATES = [
    # v9.7.414: the bundle ships `tools/` (lowercase) -- confirmed from the sealed zip, which is
    # case-preserving. The capital-T entry below matched only because macOS is case-INSENSITIVE
    # (Tools/ and tools/ are one inode here); on Linux it would miss and this file would skip
    # exactly where CI runs. Lowercase first so the shipped copy is found on every platform.
    pathlib.Path(__file__).resolve().parents[1] / "tools" / "check_md_links.py",   # shipped in bundle
    pathlib.Path(__file__).resolve().parents[1] / "Tools" / "check_md_links.py",   # legacy capital-T
    pathlib.Path(os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/Tools/check_md_links.py"), # workspace tool
]


def _load():
    for p in _CANDIDATES:
        if p.exists():
            spec = importlib.util.spec_from_file_location("check_md_links", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    pytest.skip("check_md_links.py not found (not yet shipped portable)")


def _write(tmp_path, body: str) -> str:
    f = tmp_path / "doc.md"
    f.write_text(body, encoding="utf-8")
    return str(f)


def test_flags_unencoded_space_and_paren(tmp_path):
    mod = _load()
    # a raw-space + raw-paren target: must be flagged as un-encoded (the #8 problem)
    md = _write(tmp_path, "[x](Patches for next cut Sapote Mamey (v9.7.355)/PATCH_CARD.md)\n")
    probs = mod.check_file(md)
    assert any("un-encoded" in why for _, why in probs), probs


def test_encoded_but_missing_target_is_flagged(tmp_path):
    mod = _load()
    md = _write(tmp_path, "[y](nonexistent%20file.md)\n")
    probs = mod.check_file(md)
    assert any("does not exist" in why for _, why in probs), probs


def test_encoded_existing_relative_link_is_clean(tmp_path):
    mod = _load()
    # create a real sibling target and link to it (properly encoded)
    (tmp_path / "real target.md").write_text("hi", encoding="utf-8")
    md = _write(tmp_path, "[ok](real%20target.md)\n")
    probs = mod.check_file(md)
    assert probs == [], probs


def test_external_and_anchor_links_ignored(tmp_path):
    mod = _load()
    md = _write(tmp_path, "[a](https://example.com/a b)\n[b](#section)\n[c](mailto:x@y.z)\n")
    assert mod.check_file(md) == []


def test_code_fenced_example_links_not_flagged(tmp_path):
    mod = _load()
    # a link INSIDE a code fence is documentation, not a real link → not flagged
    md = _write(tmp_path, "```\n[demo](Some Folder/with spaces.md)\n```\n")
    assert mod.check_file(md) == []
