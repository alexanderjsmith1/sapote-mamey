"""Software policy admission only, opaque names and synthetic metadata."""
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

SOURCE = Path(__file__).resolve().parents[1]
SCRIPT = SOURCE / "tools/zip_hygiene_allowlist.py"
spec = importlib.util.spec_from_file_location("isolated_allowlist_parser", SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

@pytest.mark.parametrize("row", ["docs/opaque.pdf", "docs/opaque.pdf\t10"])
def test_short_noncomment_row_is_not_silently_omitted(tmp_path, row):
    p = tmp_path / "policy.tsv"; p.write_text("# policy\n" + row + "\n")
    before = p.read_bytes()
    with pytest.raises(ValueError, match="ZIP_ALLOWLIST_ROW_INVALID") as caught:
        tool.load_allowlist(p)
    assert str(p) + ":2:" in str(caught.value)
    assert p.read_bytes() == before

@pytest.mark.parametrize("failure_type", [PermissionError, OSError])
def test_inaccessible_policy_is_not_empty_policy(tmp_path, monkeypatch, failure_type):
    p = tmp_path / "policy.tsv"; p.write_text("docs/opaque.pdf\t10\treason\n")
    stat, read = os.stat, Path.read_text
    def denied_stat(path, *args, **kwargs):
        if Path(path) == p: raise failure_type("synthetic metadata unavailable")
        return stat(path, *args, **kwargs)
    def denied_read(path, *args, **kwargs):
        if path == p: raise failure_type("synthetic content unavailable")
        return read(path, *args, **kwargs)
    monkeypatch.setattr(os, "stat", denied_stat)
    monkeypatch.setattr(Path, "read_text", denied_read)
    with pytest.raises(failure_type): tool.load_allowlist(p)


def test_absent_policy_and_missing_parent_remain_optional(tmp_path):
    assert tool.load_allowlist(tmp_path / "absent.tsv") == {}
    assert tool.load_allowlist(tmp_path / "absent-parent/policy.tsv") == {}


def test_comments_blanks_and_empty_policy_are_preserved(tmp_path):
    p = tmp_path / "empty.tsv"; p.write_text("# comment\n\n  \n")
    assert tool.load_allowlist(p) == {}


def test_shipped_policy_parses_without_normalization_change():
    p = SOURCE / "tools/zip_hygiene_allowlist.tsv"
    lines = [x for x in p.read_text().splitlines() if x and not x.startswith('#')]
    expected = {x.split('\t')[0].strip(): (int(x.split('\t')[1]), x.split('\t')[2].strip()) for x in lines}
    assert tool.load_allowlist(p) == expected
    assert len(expected) == 1


def test_duplicate_precedence_is_rejected(tmp_path):
    p = tmp_path / "duplicates.tsv"
    p.write_text("docs/opaque.pdf\t10\tfirst\ndocs/opaque.pdf\t20\tsecond\n")
    with pytest.raises(ValueError, match="ZIP_ALLOWLIST_DUPLICATE"):
        tool.load_allowlist(p)


def test_extra_fields_are_retained_as_legacy_ignored_columns(tmp_path):
    p = tmp_path / "extra.tsv"; p.write_text("docs/opaque.pdf\t10\treason\textra\n")
    assert tool.load_allowlist(p) == {"docs/opaque.pdf": (10, "reason")}


def test_symlink_and_dangling_symlink_routes_preserved(tmp_path):
    p = tmp_path / "policy.tsv"; p.write_text("docs/opaque.pdf\t10\treason\n")
    link = tmp_path / "link.tsv"; link.symlink_to(p)
    dangling = tmp_path / "dangling.tsv"; dangling.symlink_to(tmp_path / "absent.tsv")
    assert tool.load_allowlist(link) == tool.load_allowlist(p)
    with pytest.raises(ValueError, match="ZIP_ALLOWLIST_UNREADABLE"):
        tool.load_allowlist(dangling)


def test_selected_directory_still_raises(tmp_path):
    with pytest.raises(IsADirectoryError): tool.load_allowlist(tmp_path)


def test_card40_wrapper_rejects_short_policy_before_metadata_scan(tmp_path, monkeypatch):
    path = SOURCE / "tools/preflight_zip_hygiene.py"
    spec = importlib.util.spec_from_file_location("parser_wrapper_integration", path)
    wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    monkeypatch.setitem(sys.modules, "zip_hygiene_allowlist", tool)
    p = tmp_path / "policy.tsv"; p.write_text("docs/opaque.pdf\t10\n")
    loader = wrapper._load_path_allowlist
    monkeypatch.setattr(wrapper, "_load_path_allowlist", lambda: loader(p))
    calls = []
    class Metadata:
        def __init__(self, path): calls.append(path)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def infolist(self): return [SimpleNamespace(filename="docs/opaque.pdf", file_size=6 * 1024 * 1024)]
    monkeypatch.setattr(wrapper.zipfile, "ZipFile", Metadata)
    with pytest.raises(ValueError, match="ZIP_HYGIENE_ALLOWLIST_HOLD") as caught:
        wrapper.scan(tmp_path / "synthetic.zip")
    assert isinstance(caught.value.__cause__, ValueError) and not calls
