"""Freshness/correctness regression tests for mamey.strain_data_home (v9.7.397 review finding).

Two verified field failures motivated this card (2026-09-01, engine 1.9.142 workspace):
  * resolve_mamey_package returned a v9.7.339 package while a v9.7.376 seal existed in the
    workspace's current per-strain home ``MAMEY COMPLETE/`` (home missing from the search list).
  * resolve_antismash_zip returned a v9.7.335 Complete_Package ZIP (alphabetically first
    package fallback) while the raw antiSMASH result ZIP existed one directory deep under
    ``Antismash/``.

All strain IDs here are synthetic and constructed at runtime; no real cohort identifier
appears as a literal. Fixture trees are built in tmp_path; nothing outside it is touched.
"""
from __future__ import annotations

import os
import zipfile

import pytest

from mamey.strain_data_home import (
    resolve_antismash_zip,
    resolve_mamey_package,
    strain_data_home,
)

# Runtime-constructed synthetic strain id (never a literal cohort id).
STRAIN = "AS-" + str(9900 + 1)


def _write_antismash_zip(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(STRAIN + ".json", "{}")
        zf.writestr("input/" + STRAIN + ".gbk", "LOCUS")


def _write_package_zip(dirpath, bundle_version, engine="1.9.129"):
    os.makedirs(dirpath, exist_ok=True)
    name = "%s_SapoteMamey_v%s_engine%s_Complete_Package.zip" % (STRAIN, bundle_version, engine)
    path = os.path.join(dirpath, name)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("package/manifest.json", "{}")
        zf.writestr("package/" + STRAIN + "_results.json", "{}")
    return path


def test_package_resolver_searches_current_home_and_prefers_newest(tmp_path):
    """A newer seal in ``MAMEY COMPLETE/`` must beat an older one in ``Mamey Complete v*/``."""
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "Mamey Complete v9.7.339"), "9.7.339")
    new = _write_package_zip(os.path.join(root, "Mamey Complete", STRAIN), "9.7.376")
    got = resolve_mamey_package(STRAIN, root=root)
    assert got == new, "resolver preferred %r over newer %r" % (got, new)
    assert got != old


def test_antismash_resolver_finds_zip_one_level_under_antismash_home(tmp_path):
    """A raw result ZIP at ``Antismash/<subdir>/<strain>.zip`` must beat any package fallback."""
    root = str(tmp_path)
    raw = os.path.join(root, "Antismash", "cohort analysis", STRAIN + ".zip")
    _write_antismash_zip(raw)
    _write_package_zip(os.path.join(root, "Mamey Complete v9.7.335"), "9.7.335")
    got = resolve_antismash_zip(STRAIN, root=root)
    assert got == raw, "resolver returned %r instead of the raw antiSMASH zip %r" % (got, raw)


def test_antismash_package_fallback_prefers_newest_not_alphabetical(tmp_path):
    """With only package ZIPs on disk, the fallback must pick the highest version, not the
    alphabetically-first path (v9.7.335 must lose to v9.7.339)."""
    root = str(tmp_path)
    older = _write_package_zip(os.path.join(root, "Mamey Complete v9.7.335"), "9.7.335")
    newer = _write_package_zip(os.path.join(root, "Mamey Complete v9.7.339"), "9.7.339")
    # Make both valid antiSMASH-bearing zips per zip_has_antismash_json.
    got = resolve_antismash_zip(STRAIN, root=root)
    assert got == newer, "package fallback returned %r instead of newest %r" % (got, older)


def test_canonical_strain_data_home_still_wins(tmp_path):
    """Regression guard: the canonical ``strain_data/<strain>/antiSMASH/`` home keeps top priority."""
    root = str(tmp_path)
    canonical = os.path.join(root, "strain_data", STRAIN, "antiSMASH", STRAIN + ".zip")
    _write_antismash_zip(canonical)
    _write_antismash_zip(os.path.join(root, "Antismash", STRAIN + ".zip"))
    _write_package_zip(os.path.join(root, "Mamey Complete", STRAIN), "9.7.376")
    assert resolve_antismash_zip(STRAIN, root=root) == canonical


def test_strain_data_home_reports_superseded_packages(tmp_path):
    """The descriptor must name the older seals it skipped, newest excluded."""
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "Mamey Complete v9.7.339"), "9.7.339")
    new = _write_package_zip(os.path.join(root, "Mamey Complete", STRAIN), "9.7.376")
    home = strain_data_home(STRAIN, root=root)
    assert home["mamey_package"] == new
    assert "superseded_packages" in home, "descriptor lacks the superseded_packages receipt"
    assert home["superseded_packages"] == [old]


def test_resolvers_still_return_none_when_nothing_exists(tmp_path):
    root = str(tmp_path)
    assert resolve_antismash_zip(STRAIN, root=root) is None
    assert resolve_mamey_package(STRAIN, root=root) is None
    home = strain_data_home(STRAIN, root=root)
    assert home["mamey_package"] is None and home["antismash_zip"] is None
    assert home["superseded_packages"] == []


def test_estate_cache_semantics(tmp_path):
    """The package-home walk is cached per root: a ZIP added after the first resolve is
    invisible until clear_strain_data_cache() — documented behavior, not a bug.

    The clear() MUST operate on the very globals the resolver reads: suite tests
    purge mamey.* from sys.modules (e.g. test_cli_parser_no_biopython) and re-import,
    so this file's top-level bindings can point at an ORPHANED module instance whose
    cache a fresh import (or sys.modules lookup) can no longer reach. Bind clear
    through the resolver function's own __globals__ — exact by construction."""
    clear_strain_data_cache = resolve_mamey_package.__globals__["clear_strain_data_cache"]
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "Mamey Complete v9.7.339"), "9.7.339")
    assert resolve_mamey_package(STRAIN, root=root) == old
    new = _write_package_zip(os.path.join(root, "Mamey Complete", STRAIN), "9.7.376")
    assert resolve_mamey_package(STRAIN, root=root) == old  # cached walk
    clear_strain_data_cache()
    assert resolve_mamey_package(STRAIN, root=root) == new
