"""Regression: pyproject.toml's `all` extras group must stay in sync with the individual
`figures`/`bio`/`render` groups it's meant to be a convenience union of. Nothing currently
guards this (confirmed: no test file references `optional-dependencies` before this one) --
`all`'s package list is a hand-duplicated copy, not a group reference, so a future change to
any one group's version pin (e.g. bumping matplotlib's ceiling) can silently drift `all` out of
sync with no test catching it. Uses the same tiny-regex TOML parse tools/sync_version.py already
uses (no tomllib dependency, so this runs on Python 3.10+, matching that file's own stated
compatibility target).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _extras_block(text: str, name: str) -> list[str]:
    """Return the quoted dependency specifiers for one `[project.optional-dependencies]`
    entry, e.g. `figures = ["matplotlib>=3.7,<4.0", "numpy>=1.24"]` -> the two strings.
    """
    m = re.search(rf'(?m)^{re.escape(name)}\s*=\s*\[([^\]]*)\]', text)
    assert m, f"optional-dependencies group {name!r} not found"
    return re.findall(r'"([^"]+)"', m.group(1))


def test_all_extras_group_is_the_union_of_optional_dep_groups():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    figures = _extras_block(text, "figures")
    bio = _extras_block(text, "bio")
    render = _extras_block(text, "render")
    documents = _extras_block(text, "documents")   # v9.7.405: governed DOCX/PDF authoring group
    all_group = _extras_block(text, "all")
    expected = set(figures) | set(bio) | set(render) | set(documents)
    assert set(all_group) == expected, (
        f"pyproject.toml [all] has drifted from the union of [figures]+[bio]+[render]+[documents].\n"
        f"all:      {sorted(all_group)}\n"
        f"expected: {sorted(expected)}\n"
        f"missing from all: {sorted(expected - set(all_group))}\n"
        f"extra in all, not in any source group: {sorted(set(all_group) - expected)}"
    )


def test_the_check_actually_catches_a_synthetic_version_drift():
    """Proves the assertion logic above is a real check, not a tautology -- feed it a
    deliberately drifted synthetic TOML snippet (matplotlib bumped in [figures] but not
    mirrored into [all]) and confirm the comparison fails as expected.
    """
    drifted = '''
figures = ["matplotlib>=3.9,<4.0", "numpy>=1.24", "pandas>=2.0,<3.1"]
bio = ["biopython>=1.83,<2.0"]
render = ["cairosvg>=2.7,<3.0"]
all = ["matplotlib>=3.7,<4.0", "numpy>=1.24", "pandas>=2.0,<3.1", "biopython>=1.83,<2.0", "cairosvg>=2.7,<3.0"]
'''
    figures = _extras_block(drifted, "figures")
    bio = _extras_block(drifted, "bio")
    render = _extras_block(drifted, "render")
    all_group = _extras_block(drifted, "all")
    expected = set(figures) | set(bio) | set(render)
    assert set(all_group) != expected, "sanity check itself is broken: drifted fixture didn't drift"
