"""Docs-Version-Drift-v9.7.74: front-facing guide docs must not carry stale version labels.

Greps the four user-facing guide files for stale version strings (v9.7.57, v9.4, 1.9.64)
and verifies the Quick Guide and 00_README carry the current bundle version.
"""
import re
from pathlib import Path

ROOT  = Path(__file__).parent.parent
GUIDE = ROOT / "docs" / "GUIDE"

import mamey
BUNDLE  = mamey.__version__  # engine version; patch reads bundle from pyproject
import importlib.util, sys
_spec = importlib.util.spec_from_file_location("_pyproject_reader", ROOT / "pyproject.toml")
def _bundle_version():
    txt = (ROOT / "pyproject.toml").read_text()
    m = re.search(r'^bundle_version\s*=\s*"([^"]+)"', txt, re.MULTILINE)
    return m.group(1) if m else None

BUNDLE_VER  = _bundle_version()
ENGINE_VER  = mamey.__version__

# Version strings that must NOT appear in current front-facing docs
STALE_PATTERNS = [
    r"v9\.7\.57",
    r"v9\.4\b",
    r"1\.9\.64",
]

FRONT_FACING = [
    GUIDE / "00_README.md",
    GUIDE / "01_User_Manual.md",   # consolidated manual (v9.7.84); former .html/.md Guide retired to .retired
    GUIDE / "02_Quick_Guide.md",
    GUIDE / "03_Technical_Manual_Encyclopedia.html",
    GUIDE / "04_Glossary.md",
    GUIDE / "06_Concepts_QandA.md",   # running concepts companion (added v9.7.100)
]


# CANDIDATE_251 (v9.7.371): root front-door files, previously outside this gate's coverage —
# CURRENT_DOCS_INDEX.md froze three times (.136/.337/.367) with the suite green.
FRONT_FACING_ROOT = [
    ROOT / "CURRENT_DOCS_INDEX.md",
    ROOT / "README.md",
    ROOT / "docs/BUNDLE_CAPABILITIES.md",
    ROOT / "docs/PLAYBOOK.md",
]


def test_current_docs_index_header_current():
    """CANDIDATE_251: the docs-index header must restate the CURRENT bundle, engine, and build.

    This is the test half of the ratchet; the write half is the CURRENT_DOCS_INDEX.md rule in
    tools/sync_version.py (--apply re-stamps, --check flags drift). Either alone can rot; together
    a stale index header cannot survive a cut."""
    path = ROOT / "CURRENT_DOCS_INDEX.md"
    assert path.exists(), "CURRENT_DOCS_INDEX.md missing"
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert BUNDLE_VER and BUNDLE_VER in header, (
        f"CURRENT_DOCS_INDEX.md header does not restate bundle v{BUNDLE_VER}: {header!r}")
    assert ENGINE_VER in header, (
        f"CURRENT_DOCS_INDEX.md header does not restate engine {ENGINE_VER}: {header!r}")


def test_no_stale_version_in_root_front_door_files():
    """CANDIDATE_251: the root front-door files must not carry the known-stale version labels.

    Same STALE_PATTERNS + history-line exemption as the GUIDE check; scope extended to the root
    files a new session is pointed at first."""
    hits = []
    for path in FRONT_FACING_ROOT:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in STALE_PATTERNS:
            for m in re.finditer(pattern, text):
                line = text[max(0, text.rfind('\n', 0, m.start())+1):text.find('\n', m.end())]
                if any(kw in line.lower() for kw in ("historic", "changelog", "prior", "was ", "upgraded from", "migrated")):
                    continue
                hits.append(f"{path.name}:{text[:m.start()].count(chr(10))+1}: {m.group()!r}")
    assert not hits, "Stale version labels found in root front-door files:\n" + "\n".join(hits)


def test_no_stale_version_in_guide_files():
    """None of the front-facing guide files should contain stale version labels."""
    hits = []
    for path in FRONT_FACING:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in STALE_PATTERNS:
            for m in re.finditer(pattern, text):
                # Allow occurrences only inside changelog/history comments
                line = text[max(0, text.rfind('\n', 0, m.start())+1):text.find('\n', m.end())]
                if any(kw in line.lower() for kw in ("historic", "changelog", "prior", "was ", "upgraded from", "migrated")):
                    continue
                hits.append(f"{path.name}:{text[:m.start()].count(chr(10))+1}: {m.group()!r}")
    assert not hits, "Stale version labels found in front-facing docs:\n" + "\n".join(hits)


def test_quick_guide_current_version():
    """Quick Guide must declare the current bundle version."""
    path = GUIDE / "02_Quick_Guide.md"
    assert path.exists(), "02_Quick_Guide.md missing"
    text = path.read_text(encoding="utf-8")
    assert BUNDLE_VER in text, f"Quick Guide does not mention bundle v{BUNDLE_VER}"


def test_guide_readme_current_version():
    """00_README.md must reference the current bundle version."""
    path = GUIDE / "00_README.md"
    assert path.exists(), "00_README.md missing"
    text = path.read_text(encoding="utf-8")
    assert BUNDLE_VER in text, f"00_README.md does not mention bundle v{BUNDLE_VER}"


def test_user_manual_html_title_current():
    """User Manual HTML title must not say v9.7.57."""
    path = GUIDE / "01_User_Manual.html"
    if not path.exists():
        return  # optional file
    text = path.read_text(encoding="utf-8", errors="replace")
    title_m = re.search(r"<title>([^<]+)</title>", text, re.IGNORECASE)
    if title_m:
        title = title_m.group(1)
        for pat in STALE_PATTERNS:
            assert not re.search(pat, title), f"Stale version in HTML title: {title!r}"


def test_encyclopedia_html_title_current():
    """Encyclopedia HTML title must not say v9.7.57."""
    path = GUIDE / "03_Technical_Manual_Encyclopedia.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    title_m = re.search(r"<title>([^<]+)</title>", text, re.IGNORECASE)
    if title_m:
        title = title_m.group(1)
        for pat in STALE_PATTERNS:
            assert not re.search(pat, title), f"Stale version in encyclopedia title: {title!r}"
