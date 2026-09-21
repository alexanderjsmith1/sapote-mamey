import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "docs/GUIDE/07_Newsletter_June_2026.html"
ARCHIVE = ROOT / "docs/history/07_Newsletter_June_2026.html"


def test_newsletter_is_absent_from_distributed_documentation_tree():
    assert not OLD.exists()
    assert not ARCHIVE.exists()


def test_current_navigation_does_not_reference_retired_newsletter():
    for relative in (
        "docs/GUIDE/00_README.md",
        "CURRENT_DOCS_INDEX.md",
        "TIER_MANIFEST.txt",
        "SOURCE_CHECKSUMS_SHA256.txt",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "07_Newsletter_June_2026" not in text
        assert "June 2026 newsletter" not in text


def test_current_guide_readme_relative_links_resolve():
    guide = ROOT / "docs/GUIDE/00_README.md"
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", guide.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        path = (guide.parent / target.split("#", 1)[0]).resolve()
        assert path.exists(), f"broken current GUIDE link: {target}"
