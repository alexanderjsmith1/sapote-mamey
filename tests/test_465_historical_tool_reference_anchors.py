"""Historical tool-reference section links resolve to real headings or explicit anchors."""
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/history/TOOLS_REFERENCE_v9_7_460.md"
TARGETS = re.findall(r"\[[^\]]*\]\(([^)\n]+\.md#[^)\n]+)\)", SOURCE.read_text())


@pytest.mark.parametrize("target", TARGETS)
def test_historical_tool_reference_section_exists(target):
    relative, fragment = target.split("#", 1)
    destination = SOURCE.parent / unquote(relative)
    assert destination.is_file(), str(destination)
    headings = re.findall(r"^#{1,6}\s+(.+?)(?:\s+#+)?$", destination.read_text(), re.M)
    ids = {re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-") for heading in headings}
    ids.update(re.findall(r"""\b(?:id|name)=["']([^"']+)["']""", destination.read_text()))
    assert unquote(fragment) in ids, f"{target}: no matching heading; available={sorted(ids)}"
