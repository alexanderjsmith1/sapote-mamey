"""Index admission over ZIP-name metadata only; payload validity is outside scope."""
import pytest

from tools import family_rarity_by_window as tool


@pytest.fixture
def metadata_zip(monkeypatch):
    reads = []
    class MetadataZip:
        def __init__(self, path):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def namelist(self):
            return ["software_first.region001.gbk", "software_second.region002.gbk"]
        def read(self, name):
            reads.append(name)
            return b""
    monkeypatch.setattr(tool.zipfile, "ZipFile", MetadataZip)
    return reads


@pytest.mark.parametrize("index", [-1, 2, 99])
def test_outside_index_refuses_before_any_payload_read(metadata_zip, index):
    with pytest.raises(tool.Refusal, match="region-index"):
        tool.read_regions("unused-metadata-locator", only=index)
    assert metadata_zip == []


@pytest.mark.parametrize("index, expected", [(None, [0, 1]), (0, [0]), (1, [1])])
def test_valid_selection_preserves_sorted_indices(metadata_zip, index, expected):
    rows = tool.read_regions("unused-metadata-locator", only=index)
    assert [row["index"] for row in rows] == expected
    assert len(metadata_zip) == len(expected)
