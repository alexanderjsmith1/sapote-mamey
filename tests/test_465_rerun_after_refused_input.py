"""A rerun after a refused input must not be refused as "already holds a package".

A run refused at input leaves <outdir>/<strain>/package/ with two receipt files. The next run into
the same --outdir used to be refused as if a real package were there.
"""
from mamey import cli


def _stub(tmp_path, names):
    pkg = tmp_path / "out" / "S1" / "package"
    pkg.mkdir(parents=True)
    for name in names:
        (pkg / name).write_text("{}", encoding="utf-8")
    return tmp_path / "out", pkg


def test_refused_run_stub_is_moved_aside_and_kept(tmp_path):
    outdir, pkg = _stub(tmp_path, ["project_registry_status.json", "run_phase_receipts.jsonl"])
    assert cli._refuse_occupied_package(str(outdir), "S1") is False
    assert not pkg.exists()
    moved = pkg.parent / "package_refused_1"
    assert sorted(p.name for p in moved.iterdir()) == ["project_registry_status.json", "run_phase_receipts.jsonl"]


def test_a_second_stub_gets_the_next_number(tmp_path):
    outdir, pkg = _stub(tmp_path, ["run_phase_receipts.jsonl"])
    (pkg.parent / "package_refused_1").mkdir()
    assert cli._refuse_occupied_package(str(outdir), "S1") is False
    assert (pkg.parent / "package_refused_2").is_dir()


def test_a_real_package_is_still_refused(tmp_path):
    outdir, pkg = _stub(tmp_path, ["run_phase_receipts.jsonl", "manifest.json"])
    assert cli._refuse_occupied_package(str(outdir), "S1") is True
    assert pkg.exists() and (pkg / "manifest.json").exists()


def test_a_sealed_zip_beside_a_stub_is_still_refused(tmp_path):
    outdir, pkg = _stub(tmp_path, ["run_phase_receipts.jsonl"])
    (pkg.parent / "S1_Complete_Package.zip").write_bytes(b"PK")
    assert cli._refuse_occupied_package(str(outdir), "S1") is True
    assert pkg.exists()
