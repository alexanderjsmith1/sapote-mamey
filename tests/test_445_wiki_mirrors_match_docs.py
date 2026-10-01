"""Wiki pages that copy a maintained doc must stay identical to it (tools/sync_wiki_mirrors.py).

Eight wiki pages were hand copies that drifted for dozens of cuts behind a current version stamp: the wiki User
Manual still told readers to unzip a June build with `--break-system-packages`, and the wiki Quick Guide was pinned to
v9.7.401. They are now generated mirrors. These tests fail when a mirror is edited by hand, when its source changes
without `--apply`, or when a cut would re-stamp the source but not the mirror.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sync_wiki_mirrors as swm  # noqa: E402


def test_every_mirror_matches_its_source():
    stale = swm.stale_pages()
    assert not stale, f"wiki mirrors differ from their sources (run python3 tools/sync_wiki_mirrors.py --apply): {stale}"


def test_every_mirror_names_its_source_in_the_banner():
    for page, src in swm.MIRRORS.items():
        first = (ROOT / page).read_text(encoding="utf-8").splitlines()[0]
        assert first == swm.BANNER.format(src=src).rstrip("\n"), f"{page}: banner missing or names the wrong source"


def test_sources_exist_outside_history():
    for src in swm.MIRRORS.values():
        assert (ROOT / src).is_file(), f"mirror source missing: {src}"
        assert not src.startswith(("docs/history/", "docs/patch_notes/", "docs/working/")), src


def test_a_cut_restamps_each_mirror_like_its_source():
    import sync_version
    rules = {(path, pat.pattern) for path, pat, _ in sync_version.RULES}
    for page, src in swm.MIRRORS.items():
        for path, pattern in [r for r in rules if r[0] == src]:
            assert (page, pattern) in rules, f"{page} lacks its source's version rule {pattern!r}"
