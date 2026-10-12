"""v9.7.450: an unclosed run lock surfaced as an RG-GMCI intake diagnostic.

The cut's final suite failed once on test_rggmci_shared_invocation: a `.mamey.lock` handle left by an earlier
in-process run was garbage-collected while RG-GMCI read its source, and the ResourceWarning was recorded as
SOURCE_INTAKE_WARNING. The lock is now held by a holder that closes it, and intake does not record ResourceWarnings.
"""
import gc
import warnings
from pathlib import Path

from mamey import cli, parsers

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "tests/fixtures/rggmci_public_VWPH00000000.1_subset.zip"


def test_package_lock_closes_without_resource_warning(tmp_path):
    (tmp_path / "S1").mkdir()
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        lock = cli._acquire_package_lock(tmp_path, "S1")
        assert lock is not None
        del lock
        gc.collect()
    assert not [w for w in seen if issubclass(w.category, ResourceWarning)]


def test_released_lock_can_be_taken_again(tmp_path):
    (tmp_path / "S1").mkdir()
    first = cli._acquire_package_lock(tmp_path, "S1")
    del first
    gc.collect()
    assert cli._acquire_package_lock(tmp_path, "S1") is not None


def test_resource_warning_during_read_is_not_a_source_diagnostic(monkeypatch):
    real = parsers.read_genbank_records

    def noisy(*args, **kwargs):
        warnings.warn("unclosed file <stray handle>", ResourceWarning)
        return real(*args, **kwargs)

    monkeypatch.setattr(parsers, "read_genbank_records", noisy)
    diagnostics = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        list(parsers.iter_region_core_inputs(PUBLIC, intake_diagnostics=diagnostics))
    assert not [d for d in diagnostics if "stray handle" in d["message"]]


def test_other_source_warnings_are_still_recorded(monkeypatch):
    real = parsers.read_genbank_records

    def noisy(*args, **kwargs):
        warnings.warn("malformed locus line", UserWarning)
        return real(*args, **kwargs)

    monkeypatch.setattr(parsers, "read_genbank_records", noisy)
    diagnostics = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        list(parsers.iter_region_core_inputs(PUBLIC, intake_diagnostics=diagnostics))
    assert any(d["code"] == "SOURCE_INTAKE_WARNING" and "malformed locus line" in d["message"] for d in diagnostics)
