"""Portable regression for the flavor-aware resolver (BC4's CLAUDE_399 patch; test authored
by Black Cherry at composition — the patch shipped receipt-verified but test-less).

Asserts the card's documented semantics: a flavor request returns ONLY a package/ZIP of that
flavor (honest ``None`` otherwise, never a silent other-flavor substitute); ``flavor=None``
keeps the flavor-agnostic newest-wins behavior. Synthetic runtime-constructed strain IDs.
"""
from __future__ import annotations

import os
import zipfile

from mamey.strain_data_home import (
    resolve_antismash_zip,
    resolve_mamey_package,
    strain_data_home,
)

STRAIN = "AS-" + str(9900 + 13)


def _pkg(dirpath, bundle_version, flavor=None, engine="1.9.142"):
    os.makedirs(dirpath, exist_ok=True)
    tok = ("_" + flavor) if flavor else ""
    name = "%s_SapoteMamey_v%s_engine%s%s_Complete_Package.zip" % (
        STRAIN, bundle_version, engine, tok)
    path = os.path.join(dirpath, name)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("package/manifest.json", "{}")
    return path


def _canonical_zip(root, flavor):
    d = os.path.join(root, "_ANTISMASH_CANONICAL", flavor)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, STRAIN + ".zip")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(STRAIN + ".json", "{}")
    return path


def _clear_cache():
    resolve_mamey_package.__globals__["clear_strain_data_cache"]()


def test_flavor_request_returns_only_that_flavor(tmp_path):
    root = str(tmp_path)
    home = os.path.join(root, "Mamey Complete", STRAIN)
    loose = _pkg(home, "9.7.398", "loose")
    relaxed = _pkg(home, "9.7.398", "relaxed")
    _clear_cache()
    try:
        assert resolve_mamey_package(STRAIN, root=root, flavor="loose") == loose
        assert resolve_mamey_package(STRAIN, root=root, flavor="relaxed") == relaxed
        assert resolve_mamey_package(STRAIN, root=root, flavor="strict") is None, (
            "a flavor request must NEVER return a different flavor's package")
    finally:
        _clear_cache()


def test_flavorless_packages_never_satisfy_a_flavor_request(tmp_path):
    root = str(tmp_path)
    pre398 = _pkg(os.path.join(root, "Mamey Complete", STRAIN), "9.7.376")
    _clear_cache()
    try:
        assert resolve_mamey_package(STRAIN, root=root, flavor="loose") is None, (
            "a pre-.398 flavor-less package cannot prove its flavor from the name")
        assert resolve_mamey_package(STRAIN, root=root) == pre398
    finally:
        _clear_cache()


def test_antismash_flavor_resolves_only_from_canonical_home(tmp_path):
    root = str(tmp_path)
    loose_zip = _canonical_zip(root, "loose")
    _clear_cache()
    try:
        assert resolve_antismash_zip(STRAIN, root=root, flavor="loose") == loose_zip
        assert resolve_antismash_zip(STRAIN, root=root, flavor="relaxed") is None
        home = strain_data_home(STRAIN, root=root, flavor="loose")
        assert home["antismash_zip"] == loose_zip
    finally:
        _clear_cache()
