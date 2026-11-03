import importlib.util
from pathlib import Path
import pytest
PATH=Path(__file__).resolve().parents[1]/"tools/build_deep_data.py"
spec=importlib.util.spec_from_file_location("symlink_discovery_candidate",PATH);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

@pytest.mark.parametrize("kind",["snapshot", "evidence"])
def test_external_directory_link_refuses(tmp_path,monkeypatch,kind):
    root=tmp_path/"root";root.mkdir();external=tmp_path/"external";external.mkdir()
    name="SID1_Project_Memory_Snapshot.json" if kind=="snapshot" else "SID1_AntiSMASH_Evidence_Parse.json"
    (external/name).write_text("{}")
    (root/"outside").symlink_to(external,target_is_directory=True)
    if kind=="snapshot":
        monkeypatch.setenv("MAMEY_PACKAGES",str(root))
        with pytest.raises(ValueError,match="DISCOVERY_HOLD"):tool.find_snaps()
    else:
        with pytest.raises(ValueError,match="DISCOVERY_HOLD"):tool.admitted_evidence(str(root/"Snapshot.json"))

@pytest.mark.parametrize("kind",["snapshot", "evidence"])
def test_external_file_link_refuses(tmp_path,monkeypatch,kind):
    root=tmp_path/"root";root.mkdir();external=tmp_path/"outside.json";external.write_text("{}")
    name="SID1_Project_Memory_Snapshot.json" if kind=="snapshot" else "SID1_AntiSMASH_Evidence_Parse.json"
    (root/name).symlink_to(external)
    if kind=="snapshot":
        monkeypatch.setenv("MAMEY_PACKAGES",str(root))
        with pytest.raises(ValueError,match="DISCOVERY_HOLD"):tool.find_snaps()
    else:
        with pytest.raises(ValueError,match="DISCOVERY_HOLD"):tool.admitted_evidence(str(root/"Snapshot.json"))

def test_internal_symlink_file_still_admitted(tmp_path,monkeypatch):
    content=tmp_path/"source.txt";content.write_text("{}")
    link=tmp_path/"SID1_Project_Memory_Snapshot.json";link.symlink_to(content)
    monkeypatch.setenv("MAMEY_PACKAGES",str(tmp_path)); assert tool.find_snaps()=={"SID1":str(link)}


def test_snapshot_alias_manifest_outside_package_refuses(tmp_path):
    root=tmp_path/"root";root.mkdir();external=tmp_path/"outside.json";external.write_text('{"source_scans": {}}')
    snapshot=root/"SID1_Project_Memory_Snapshot.json";snapshot.write_text('{"alias_of": "manifest.json"}')
    (root/"manifest.json").symlink_to(external)
    with pytest.raises(ValueError,match="SNAPSHOT_ALIAS_HOLD"):tool._read_json(snapshot)


def test_unrelated_external_file_link_does_not_block_discovery(tmp_path,monkeypatch):
    root=tmp_path/"root";root.mkdir();external=tmp_path/"outside.txt";external.write_text("unused")
    (root/"unrelated.txt").symlink_to(external)
    snapshot=root/"SID1_Project_Memory_Snapshot.json";snapshot.write_text("{}")
    monkeypatch.setenv("MAMEY_PACKAGES",str(root))
    assert tool.find_snaps()=={"SID1":str(snapshot)}
    assert tool._evidence_paths(str(root)) == []
