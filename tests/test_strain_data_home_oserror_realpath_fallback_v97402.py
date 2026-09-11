"""OSError→realpath-fallback regression for mamey.strain_data_home (v9.7.402, Black Cherry-4).

Roster seed #7 (ROSTER_401 carried seed — the one good extra from the superseded .399
convergent case-dup card): ``_package_zip_index`` keys its estate dedup on inode identity
``(st_dev, st_ino)``, but when ``os.stat`` raises OSError (a permission blip, a racing
rename, an unreadable network mount) it drops the home directory or package ZIP from the
index ENTIRELY. A transiently unstat-able package then resolves as missing — or worse, an
older seal silently wins freshness — which is a wrong resolution, not a degraded one.

The fix degrades to ``os.path.realpath`` string identity for exactly the entries whose
inode identity is unavailable. Worst case of the fallback is a rare case-twin double-walk
of one unstat-able entry (the cosmetic .399 failure shape); the pre-fix worst case is a
silently absent package (a wrong answer). Inode dedup remains the primary key for every
stat-able entry, so the .399 case-twin fix is untouched.

All strain IDs are synthetic, runtime-constructed; fixtures live in tmp_path only.
"""
from __future__ import annotations

import os
import zipfile

from mamey.strain_data_home import resolve_mamey_package, strain_data_home

STRAIN = "AS-" + str(9900 + 42)


def _write_package_zip(dirpath, bundle_version, engine="1.9.143"):
    os.makedirs(dirpath, exist_ok=True)
    name = "%s_SapoteMamey_v%s_engine%s_Complete_Package.zip" % (STRAIN, bundle_version, engine)
    path = os.path.join(dirpath, name)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("package/manifest.json", "{}")
    return path


def _clear_cache():
    # Bind through the resolver's own __globals__ (suite tests purge mamey.* from
    # sys.modules; a fresh import could reach an orphaned module instance).
    resolve_mamey_package.__globals__["clear_strain_data_cache"]()


def _stat_raising_for(paths, real_stat):
    """An os.stat stand-in raising PermissionError for exactly *paths* (realpath-keyed)."""
    blocked = {os.path.realpath(p) for p in paths}

    def fake_stat(path, *args, **kwargs):
        if isinstance(path, (str, bytes)) and os.path.realpath(os.fsdecode(path)) in blocked:
            raise PermissionError(13, "stat blocked by test", os.fsdecode(path))
        return real_stat(path, *args, **kwargs)

    return fake_stat


def test_unstatable_package_zip_still_indexed(tmp_path, monkeypatch):
    """A ZIP whose os.stat fails must stay in the index (realpath key), not vanish."""
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "mamey_packages"), "9.7.400")
    new = _write_package_zip(os.path.join(root, "mamey_packages", "newer"), "9.7.401")
    real_stat = os.stat
    monkeypatch.setattr(os, "stat", _stat_raising_for([new], real_stat))
    _clear_cache()
    try:
        resolved = resolve_mamey_package(STRAIN, root=root)
    finally:
        _clear_cache()
    assert resolved == new, (
        "unstat-able newest package was dropped from the estate index; "
        "resolver answered %r (silent stale-seal win)" % resolved
    )


def test_unstatable_home_dir_still_walked(tmp_path, monkeypatch):
    """A home dir whose os.stat fails must still be walked (realpath key), not skipped."""
    root = str(tmp_path)
    home_dir = os.path.join(root, "mamey_packages")
    new = _write_package_zip(home_dir, "9.7.401")
    real_stat = os.stat
    real_isdir = os.path.isdir
    monkeypatch.setattr(os, "stat", _stat_raising_for([home_dir], real_stat))
    # os.path.isdir consults os.stat; keep it truthful for the blocked dir so the test
    # isolates the _package_zip_index stat call (the dir genuinely exists).
    monkeypatch.setattr(
        os.path,
        "isdir",
        lambda p: True if os.path.realpath(os.fsdecode(p)) == os.path.realpath(home_dir) else real_isdir(p),
    )
    _clear_cache()
    try:
        resolved = resolve_mamey_package(STRAIN, root=root)
    finally:
        _clear_cache()
    assert resolved == new, (
        "unstat-able package home was skipped entirely; resolver answered %r" % resolved
    )


def test_fallback_still_dedups_duplicate_home_strings(tmp_path, monkeypatch):
    """Realpath fallback must keep exact-duplicate env homes single-indexed."""
    root = str(tmp_path)
    home_dir = os.path.join(root, "mamey_packages")
    old = _write_package_zip(home_dir, "9.7.400")
    new = _write_package_zip(home_dir, "9.7.401")
    monkeypatch.setenv(
        "MAMEY_PACKAGE_HOMES", os.pathsep.join(["mamey_packages", "mamey_packages"])
    )
    real_stat = os.stat
    real_isdir = os.path.isdir
    monkeypatch.setattr(os, "stat", _stat_raising_for([home_dir], real_stat))
    monkeypatch.setattr(
        os.path,
        "isdir",
        lambda p: True if os.path.realpath(os.fsdecode(p)) == os.path.realpath(home_dir) else real_isdir(p),
    )
    _clear_cache()
    try:
        home = strain_data_home(STRAIN, root=root)
    finally:
        _clear_cache()
    assert home["mamey_package"] == new
    assert [os.path.basename(p) for p in home["superseded_packages"]] == [
        os.path.basename(old)
    ], "duplicate home strings double-indexed under the realpath fallback"


def test_statable_estate_unchanged(tmp_path):
    """No-regression: a fully stat-able estate resolves exactly as before."""
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "mamey_packages"), "9.7.400")
    new = _write_package_zip(os.path.join(root, "mamey_packages"), "9.7.401")
    _clear_cache()
    try:
        home = strain_data_home(STRAIN, root=root)
    finally:
        _clear_cache()
    assert home["mamey_package"] == new
    assert [os.path.basename(p) for p in home["superseded_packages"]] == [
        os.path.basename(old)
    ]
