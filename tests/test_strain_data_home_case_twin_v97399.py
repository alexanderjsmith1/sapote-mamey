"""Case-twin regression for mamey.strain_data_home (v9.7.399, Black Cherry-4 finding).

Verified field failure (sealed v9.7.398, macOS APFS, 2026-09-01): with the house-rule
``MAMEY_PACKAGE_HOMES="MAMEY COMPLETE"`` environment set, the built-in ``Mamey Complete*``
glob and the case-variant env home resolved the SAME physical directory under two path
strings; ``_package_zip_index`` walked it twice, and the duplicated newest package landed
in ``superseded_packages`` (shipped freshness test: 7 passed env-unset, 1 failed env-set).
``os.path.realpath`` does not canonicalize case, so the fix dedups by inode identity.

On case-sensitive filesystems (Linux CI) the case-variant env home simply does not exist,
so no twin can form and these tests pass trivially — the defect is macOS-shaped, the
invariant is universal. All strain IDs are synthetic, runtime-constructed; fixtures live
in tmp_path only.
"""
from __future__ import annotations

import os
import zipfile

from mamey.strain_data_home import resolve_mamey_package, strain_data_home

STRAIN = "AS-" + str(9900 + 7)


def _write_package_zip(dirpath, bundle_version, engine="1.9.142"):
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


def test_case_variant_env_home_does_not_case_twin_superseded(tmp_path, monkeypatch):
    """Env home differing only by case from an on-disk home must not duplicate packages."""
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "Mamey Complete", STRAIN), "9.7.397")
    new = _write_package_zip(os.path.join(root, "Mamey Complete", STRAIN), "9.7.398")
    monkeypatch.setenv("MAMEY_PACKAGE_HOMES", "MAMEY COMPLETE")
    _clear_cache()
    try:
        home = strain_data_home(STRAIN, root=root)
    finally:
        _clear_cache()  # never leave an env-keyed walk cached for later tests
    assert home["mamey_package"] == new
    sup_names = [os.path.basename(p) for p in home["superseded_packages"]]
    assert os.path.basename(new) not in sup_names, (
        "newest package case-twinned into superseded_packages: %r" % sup_names
    )
    assert sup_names == [os.path.basename(old)]


def test_duplicate_env_home_string_is_indexed_once(tmp_path, monkeypatch):
    """Even an exact-duplicate env home entry must not double-index (inode dedup)."""
    root = str(tmp_path)
    old = _write_package_zip(os.path.join(root, "mamey_packages"), "9.7.397")
    new = _write_package_zip(os.path.join(root, "mamey_packages"), "9.7.398")
    monkeypatch.setenv(
        "MAMEY_PACKAGE_HOMES", os.pathsep.join(["mamey_packages", "mamey_packages"])
    )
    _clear_cache()
    try:
        home = strain_data_home(STRAIN, root=root)
    finally:
        _clear_cache()
    assert home["mamey_package"] == new
    assert [os.path.basename(p) for p in home["superseded_packages"]] == [
        os.path.basename(old)
    ]
