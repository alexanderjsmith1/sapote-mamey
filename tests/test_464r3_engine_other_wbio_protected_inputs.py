"""tools/_wbio.py: opt-in refusals for an output that aliases an input or already exists.

Before: every writer replaced any existing regular file, so a tool that passed its own input path
as an output (for example `--out-json counts.tsv`) replaced that input. The default stays the same
for the existing callers; new callers pass `protected=` and `refuse_existing=True`.
"""
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import _wbio


def _writers():
    class _Book:
        def save(self, path):
            pathlib.Path(path).write_text("book")

    def _open(path, **kw):
        with _wbio.atomic_open(path, **kw) as fh:
            fh.write("streamed")

    return {
        "text": lambda path, **kw: _wbio.atomic_write_text(path, "new", **kw),
        "json": lambda path, **kw: _wbio.atomic_dump_json({"new": 1}, path, **kw),
        "save": lambda path, **kw: _wbio.atomic_save(_Book(), path, **kw),
        "open": _open,
        "owned": lambda path, **kw: _wbio.atomic_dump_json_owned(
            {"new": 1}, path, owner_dir=os.path.dirname(os.path.abspath(path)), **kw),
    }


@pytest.mark.parametrize("name", sorted(_writers()))
def test_protected_input_is_refused_and_left_unchanged(tmp_path, name):
    source = tmp_path / "counts.tsv"
    source.write_text("original input")
    with pytest.raises(_wbio.AtomicWriteRefused):
        _writers()[name](str(source), protected=[str(source)])
    assert source.read_text() == "original input"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["counts.tsv"]


@pytest.mark.parametrize("name", sorted(_writers()))
def test_protected_input_reached_through_a_symlink_is_refused(tmp_path, name):
    source = tmp_path / "tree.nwk"
    source.write_text("(a,b);")
    link = tmp_path / "report.json"
    link.symlink_to(source)
    with pytest.raises(_wbio.AtomicWriteRefused):
        _writers()[name](str(link), protected=(str(source),))
    assert source.read_text() == "(a,b);" and link.is_symlink()


@pytest.mark.parametrize("name", sorted(_writers()))
def test_refuse_existing_keeps_an_earlier_output(tmp_path, name):
    earlier = tmp_path / "receipt.json"
    earlier.write_text("earlier receipt")
    with pytest.raises(_wbio.AtomicWriteRefused):
        _writers()[name](str(earlier), refuse_existing=True)
    assert earlier.read_text() == "earlier receipt"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["receipt.json"]


@pytest.mark.parametrize("name", sorted(_writers()))
def test_refuse_existing_writes_a_fresh_destination(tmp_path, name):
    fresh = tmp_path / "fresh.out"
    _writers()[name](str(fresh), refuse_existing=True, protected=[str(tmp_path / "input.tsv")])
    assert fresh.is_file() and fresh.read_text()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["fresh.out"]


@pytest.mark.parametrize("name", sorted(_writers()))
def test_default_still_replaces_an_existing_file(tmp_path, name):
    target = tmp_path / "out.txt"
    target.write_text("old")
    _writers()[name](str(target))
    assert target.read_text() != "old"


def test_owned_writer_refusal_keeps_its_own_exception_type(tmp_path):
    target = tmp_path / "x.json"
    target.write_text("{}")
    with pytest.raises(_wbio.AtomicJsonWriteRefused):
        _wbio.atomic_dump_json_owned({}, str(target), owner_dir=str(tmp_path), refuse_existing=True)
    assert issubclass(_wbio.AtomicJsonWriteRefused, RuntimeError)
