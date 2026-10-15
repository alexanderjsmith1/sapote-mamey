"""Every entry of CURRENT_DOCS_INDEX.md says whether it is current, reference or experimental, and points at a real file."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "CURRENT_DOCS_INDEX.md"
TAGS = {"current", "reference", "experimental"}


def entries():
    return [ln for ln in INDEX.read_text(encoding="utf-8").splitlines() if re.match(r"^- (`[a-z]+` )?\[", ln)]


def test_every_entry_carries_one_status_tag():
    untagged = [ln[:80] for ln in entries() if not re.match(r"^- `(%s)` \[" % "|".join(TAGS), ln)]
    assert not untagged, untagged


def test_the_tags_are_explained_before_the_first_entry():
    text = INDEX.read_text(encoding="utf-8")
    legend = text.find("starts with its status")
    assert 0 <= legend < text.find("\n- `")
    for tag in TAGS:
        assert f"`{tag}`" in text[legend:legend + 600]


def test_every_tagged_link_target_exists():
    missing = []
    for ln in entries():
        for target in re.findall(r"\]\(([^)#]+)", ln):
            if not (ROOT / target).exists():
                missing.append(target)
    assert not missing, missing
