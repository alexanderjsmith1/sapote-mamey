import json
import os
from pathlib import Path
import pytest
from mamey.assembly_line import run

def source_package(tmp_path, strain="SYN-A", sealed=False):
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text(json.dumps({"strain": strain}))
    (package / "SYN-A_domains.csv").write_text("bgc_id,feature_type,domain,start,substrate\nBGC001,aSDomain,PKS_KS,1,\n")
    if sealed: (package / "checksums_sha256.txt").write_text("synthetic marker only; no sealing performed")
    return package

@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("kind", ["parent", "absolute", "windows"])
def test_manifest_strain_cannot_change_output_destination(tmp_path, sealed, kind):
    strain = {"parent": "../escape", "absolute": str(tmp_path / "outside"), "windows": "C:\\outside"}[kind]
    package = source_package(tmp_path, strain, sealed)
    before = {p: p.read_bytes() for p in package.iterdir()}
    with pytest.raises(ValueError):run(package, tmp_path / "output")
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not (tmp_path / "outside_assembly_lines.csv").exists()

@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("kind", ["hardlink", "symlink", "existing", "directory_symlink"])
def test_existing_or_aliased_outputs_are_not_overwritten(tmp_path, kind, sealed):
    package = source_package(tmp_path, sealed=sealed)
    output = tmp_path / "output"
    output.mkdir()
    protected = tmp_path / "protected.csv"
    protected.write_text("original evidence")
    folder = output / "ASSEMBLY_LINES"
    if kind == "directory_symlink":
        external = tmp_path / "external"
        external.mkdir()
        folder.symlink_to(external, target_is_directory=True)
    else:
        folder.mkdir()
        target = folder / "SYN-A_assembly_lines.csv"
        if kind == "hardlink": os.link(protected, target)
        elif kind == "symlink": target.symlink_to(protected)
        else: target.write_text("existing evidence")
    with pytest.raises((ValueError, FileExistsError)):run(package, output)
    assert protected.read_text() == "original evidence"

def test_fresh_ordinary_strain_keeps_output_and_report_identity(tmp_path):
    package = source_package(tmp_path)
    result = run(package, tmp_path / "output")
    assert result["status"] == "ok" and result["strain"] == "SYN-A"
    assert Path(result["out"]).name == "SYN-A_assembly_lines.csv"
    assert Path(result["out"]).is_file()
