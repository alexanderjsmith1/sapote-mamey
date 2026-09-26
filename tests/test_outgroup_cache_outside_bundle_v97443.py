"""v9.7.443: the outgroup cache refuses to sit inside the code bundle.

CACHE defaults to workspace_root(), which falls back to the current directory. Run from the
bundle root with no SAPOTE_WORKSPACE_ROOT or OUTGROUP_CACHE, the 16S and genome caches landed in
the sealed bundle. Both write sites now go through _cache_dir(), which raises
RegistryAuthorityError; the CLI and every library caller already report that cleanly.
"""
import argparse
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(monkeypatch, cache):
    monkeypatch.setenv("OUTGROUP_CACHE", str(cache))
    spec = importlib.util.spec_from_file_location("outgroup_registry_cache_v97443",
                                                  ROOT / "tools" / "outgroup_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bundle_is_recognisable():
    assert (ROOT / "BUILD_STAMP.txt").exists()


def test_cache_inside_the_bundle_is_refused_and_nothing_is_created(monkeypatch):
    inside = ROOT / "OFFICIAL_DATA" / "outgroup_cache_test_v97443"
    mod = _load(monkeypatch, inside)
    with pytest.raises(mod.RegistryAuthorityError, match="OUTPUT_INSIDE_BUNDLE"):
        mod._cache_dir("16S")
    assert not inside.exists()


def test_cache_outside_the_bundle_is_created(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path / "cache")
    d = mod._cache_dir("16S")
    assert Path(d) == tmp_path / "cache" / "16S" and Path(d).is_dir()


def test_genome_fetch_script_refuses_an_in_bundle_cache(monkeypatch):
    inside = ROOT / "OFFICIAL_DATA" / "outgroup_cache_test_v97443"
    mod = _load(monkeypatch, inside)
    monkeypatch.setattr(mod, "find_row", lambda g, s: {
        "outgroup_genus": "Kitasatospora", "outgroup_species_strain": "setae KM-6054",
        "assembly_accession": "GCF_000269985.1", "status": "LOCKED"})
    a = argparse.Namespace(genus="Streptomyces", scope="genus", fetch=True)
    with pytest.raises(mod.RegistryAuthorityError, match="OUTPUT_INSIDE_BUNDLE"):
        mod.cmd_genome(a)
    assert not inside.exists()
