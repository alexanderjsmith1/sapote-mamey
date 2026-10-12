"""Small nonbiological ZIP inputs exercise the shared RG-GMCI read/refusal boundary."""
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
from mamey import parsers, rggmci


BAD = "clusterblast/SYNTHETIC_REFUSED.txt"
GOOD = "clusterblast/SYNTHETIC_ADMITTED.txt"


def archive(path, mixed=False):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if mixed:
            zf.writestr(GOOD, "synthetic admitted reference marker")
        zf.writestr(BAD, "X" * 4096)
    return path


def limits(monkeypatch, kind):
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "256" if kind == "size" else "8192")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "10000" if kind == "size" else "2")


@pytest.mark.parametrize("kind", ["size", "ratio"])
def test_text_preflight_refuses_before_open_or_whole_read(tmp_path, monkeypatch, kind):
    path = archive(tmp_path / "SYNTHETIC.zip")
    limits(monkeypatch, kind)
    opened, read = [], []
    original_open = zipfile.ZipFile.open
    def tracked_open(zf, member, *args, **kwargs):
        opened.append(member)
        return original_open(zf, member, *args, **kwargs)
    def forbidden_read(zf, member, *args, **kwargs):
        read.append(member)
        raise AssertionError("unbounded ZIP whole-member read is forbidden")
    monkeypatch.setattr(zipfile.ZipFile, "open", tracked_open)
    monkeypatch.setattr(zipfile.ZipFile, "read", forbidden_read)
    with zipfile.ZipFile(path) as zf:
        with pytest.raises(parsers.GbkSizeGuardRefusal) as error:
            rggmci._read_text(zf, BAD)
    assert error.value.member == BAD
    assert ("MAMEY_GBK_MAX_BYTES" if kind == "size" else "MAMEY_GBK_MAX_RATIO") in error.value.reason
    assert str(error.value).startswith("GBK_SIZE_GUARD_REFUSED:")
    assert opened == read == []


def test_text_stream_overflow_uses_cap_plus_one(monkeypatch):
    limits(monkeypatch, "size")
    requested = []
    class Stream(io.BytesIO):
        def read(self, size=-1):
            requested.append(size)
            return super().read(size)
    class DeclaredSmall:
        def getinfo(self, name):
            return SimpleNamespace(file_size=1, compress_size=1)
        def open(self, name):
            return Stream(b"X" * 4096)
        def read(self, *args):
            raise AssertionError("whole read forbidden")
    with pytest.raises(parsers.GbkSizeGuardRefusal, match="streamed size"):
        rggmci._read_text(DeclaredSmall(), BAD)
    assert requested == [257]


def admitted_reference(name):
    return rggmci.ClusterBlastReference(
        bgc_id="SYNTHETIC_REFERENCE", contig="SYNTHETIC_CONTIG", region_number=1,
        region_key="SYNTHETIC_CONTIG_c1", ref="SYNTHETIC_REFERENCE", source="synthetic fixture",
        reference_type="synthetic", rank=1, nprot=None, cumulative_score=None,
        mean_identity=None, interval_start=None, interval_end=None, source_file=name)


@pytest.mark.parametrize("mixed", [False, True])
def test_reference_map_refusal_cannot_be_null_or_partial_pass(tmp_path, monkeypatch, mixed):
    path = archive(tmp_path / "SYNTHETIC.zip", mixed)
    limits(monkeypatch, "size")
    parsed = []
    def parse(name, text, keys):
        parsed.append(name)
        return [admitted_reference(name)]
    monkeypatch.setattr(rggmci, "_parse_clusterblast_refs_from_text", parse)
    with pytest.raises(parsers.GbkSizeGuardRefusal) as error:
        rggmci.parse_clusterblast_reference_map(path, [])
    assert error.value.member == BAD
    assert parsed == ([GOOD] if mixed else [])
    called = []
    def forbidden_compute(*args, **kwargs):
        called.append(True)
        raise AssertionError("resource refusal must precede computation/completion")
    monkeypatch.setattr(rggmci, "compute_rggmci", forbidden_compute)
    with pytest.raises(parsers.GbkSizeGuardRefusal):
        rggmci.run_rggmci(path, [], reference_completion="off")
    assert called == []


def test_small_text_and_true_empty_map_remain_distinct(tmp_path, monkeypatch):
    limits(monkeypatch, "size")
    path = tmp_path / "SYNTHETIC_EMPTY.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("notes.txt", b"synthetic \xff marker")
    with zipfile.ZipFile(path) as zf:
        assert rggmci._read_text(zf, "notes.txt") == "synthetic \ufffd marker"
    result = rggmci.parse_clusterblast_reference_map(path, [])
    assert result["status"] == "NULL_NO_CLUSTERBLAST_REFERENCES_PARSED"
    assert result["parse_error_count"] == 0 and result["reference_records"] == []


@pytest.mark.parametrize("reader", ["_glycosyltransferase_bgcs", "_contig_edge_bgcs"])
def test_shared_gbk_wrapper_refusal_propagates(tmp_path, monkeypatch, reader):
    limits(monkeypatch, "size")
    member = "SYNTHETIC_CONTIG.region001.gbk"
    path = tmp_path / "SYNTHETIC_GBK.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, "X" * 4096)
    bgc = SimpleNamespace(source_gbk=member, bgc_id="SYNTHETIC_REFERENCE", edge_status="Edge")
    with pytest.raises(parsers.GbkSizeGuardRefusal) as error:
        getattr(rggmci, reader)(path, [bgc])
    assert error.value.member == member


def test_builder_optional_guard_import_zero_one_duplicate():
    path = Path(__file__).resolve().parents[1] / "packaging/rggmci/build_rggmci_package.py"
    spec = importlib.util.spec_from_file_location("synthetic_guard_builder", path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    old = "from .parsers import GbkSizeGuardRefusal, _safe_read_text\n"
    new = "from ._parsers import GbkSizeGuardRefusal, _safe_read_text\n"
    assert builder._rewrite_optional_guard_import("# older synthetic core\n") == "# older synthetic core\n"
    assert builder._rewrite_optional_guard_import(old) == new
    with pytest.raises(SystemExit, match="IMPORT_REWRITE_FAILED"):
        builder._rewrite_optional_guard_import(old + old)
