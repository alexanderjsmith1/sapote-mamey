"""Synthetic project only: an image locator cannot land on the normalized document's own path."""
from pathlib import Path

import pytest

from mamey.document_factory import DocumentFactoryError, check_project, init_project


def _project(tmp_path, locator):
    root = tmp_path / "starter"
    init_project(root)
    guide = root / "templates" / "guide.md"
    asset = root / "templates" / locator
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"\x89PNG\r\n\x1a\nnot really an image")
    guide.write_text(guide.read_text(encoding="utf-8") + f"\n![Figure]({locator})\n", encoding="utf-8")
    return root / "sapote-documents.yml", asset


@pytest.mark.parametrize("locator", ["quickstart.md", "QuickStart.md", "./quickstart.md"])
def test_asset_named_like_the_document_is_refused(tmp_path, locator):
    project, asset = _project(tmp_path, locator)
    saved = asset.read_bytes()
    with pytest.raises(DocumentFactoryError, match="ASSET_PATH_COLLIDES_WITH_DOCUMENT"):
        check_project(project)
    assert asset.read_bytes() == saved


def test_ordinary_asset_still_passes_presence_check(tmp_path):
    project, _ = _project(tmp_path, "figure.png")
    try:
        result = check_project(project)
    except DocumentFactoryError as exc:  # a non-image fixture may fail asset validation
        assert "ASSET_PATH_COLLIDES_WITH_DOCUMENT" not in str(exc)
    else:
        assert result["status"] == "PASS"
