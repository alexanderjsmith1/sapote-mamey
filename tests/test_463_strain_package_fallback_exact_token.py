"""The package fallback matches the strain as the file's leading token, not as a substring.

`resolve_antismash_zip` fell back to `strain in basename` over the package homes. A request for
TST-1 matched the TST-10 package and returned another genome as the ZIP of record. On the
operator workstation, 2 of 296 package strain names are contained in another strain's
package name.
"""
import os
import zipfile

from mamey import strain_data_home as sdh


def _package(dirpath, strain, version):
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, f"{strain}_SapoteMamey_v{version}_engine1.9.178_loose_Complete_Package.zip")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("input/antismash/" + strain + ".json", '{"records": []}')
        zf.writestr("package/" + strain + "_results.json", "{}")
    return path


def test_short_id_does_not_take_a_longer_ids_package(tmp_path, monkeypatch):
    monkeypatch.delenv("MAMEY_PACKAGE_HOMES", raising=False)
    monkeypatch.delenv("SAPOTE_STRAIN_MASTER", raising=False)
    sdh._ESTATE_CACHE.clear()
    root = str(tmp_path)
    longer = _package(os.path.join(root, "mamey_packages"), "TST-10", "9.7.462")
    assert sdh.resolve_antismash_zip("TST-1", root) is None
    own = _package(os.path.join(root, "mamey_packages"), "TST-1", "9.7.440")
    sdh._ESTATE_CACHE.clear()
    # the older own package still wins over the newer foreign one
    assert sdh.resolve_antismash_zip("TST-1", root) == own
    assert sdh.resolve_antismash_zip("TST-10", root) == longer


def test_leading_token_rule():
    assert sdh._names_strain("TST-1_SapoteMamey_v9.7.462_Complete_Package.zip", "TST-1")
    assert sdh._names_strain("TST-1.zip", "TST-1")
    assert not sdh._names_strain("TST-10_SapoteMamey_v9.7.462_Complete_Package.zip", "TST-1")
    assert not sdh._names_strain("Genus_specie_conviva_x.zip", "Genus_specie_conviv")
    assert not sdh._names_strain("old_TST-1_copy.zip", "TST-1")
