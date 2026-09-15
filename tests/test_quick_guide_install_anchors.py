"""Keep current Quick Guide installation examples aligned to the release manifest."""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quick_guide_install_and_sync_examples_match_release_manifest() -> None:
    manifest = (ROOT / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/GUIDE/02_Quick_Guide.md").read_text(encoding="utf-8")
    bundle = re.search(r"^\*\*Authoritative bundle version:\*\* `([^`]+)`\s*$", manifest, re.M).group(1)
    engine = re.search(r"^\*\*Engine:\*\* Mamey v([^\s*]+)\s*$", manifest, re.M).group(1)
    assert f"**Version:** v{bundle} / engine Mamey {engine}" in guide
    assert "[Your first analysis](../MASTER_WALKTHROUGH.md)" in guide
    assert (ROOT / "docs/MASTER_WALKTHROUGH.md").is_file()
