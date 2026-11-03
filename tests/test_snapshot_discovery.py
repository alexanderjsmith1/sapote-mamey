import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[1]/"tools/build_deep_data.py"
spec=importlib.util.spec_from_file_location("snapshot_discovery_candidate",PATH);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

def write(root,relative):
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text("{}")
    return path

def test_distinct_duplicate_ids_fail(tmp_path,monkeypatch):
    write(tmp_path,"a/SID1_Project_Memory_Snapshot.json");write(tmp_path,"b/SID1_Project_Memory_Snapshot.json")
    monkeypatch.setenv("MAMEY_PACKAGES",str(tmp_path))
    with pytest.raises(ValueError,match="SNAPSHOT_AMBIGUOUS"):tool.find_snaps()

def test_incomplete_directory_fails(tmp_path,monkeypatch):
    write(tmp_path,"a/SID1_Project_Memory_Snapshot.json");hidden=tmp_path/"blocked";hidden.mkdir()
    monkeypatch.setenv("MAMEY_PACKAGES",str(tmp_path));real=tool.os.scandir
    def denied(path):
        if Path(path)==hidden:raise PermissionError("synthetic denied")
        return real(path)
    monkeypatch.setattr(tool.os,"scandir",denied)
    with pytest.raises(ValueError,match="SNAPSHOT_DISCOVERY_HOLD"):tool.find_snaps()

def test_missing_root_fails(tmp_path,monkeypatch):
    monkeypatch.setenv("MAMEY_PACKAGES",str(tmp_path/"missing"))
    with pytest.raises(ValueError,match="SNAPSHOT_DISCOVERY_HOLD"):tool.find_snaps()

def test_unique_nested_paths_and_hidden_convention(tmp_path,monkeypatch):
    chosen=write(tmp_path,"nest/SID1_Project_Memory_Snapshot.json");write(tmp_path,".hidden/SID2_Project_Memory_Snapshot.json");monkeypatch.setenv("MAMEY_PACKAGES",str(tmp_path))
    assert tool.find_snaps()=={"SID1":str(chosen)}

def test_cycle_fails_instead_of_looping(tmp_path,monkeypatch):
    (tmp_path/"loop").symlink_to(tmp_path,target_is_directory=True);monkeypatch.setenv("MAMEY_PACKAGES",str(tmp_path))
    with pytest.raises(ValueError,match="SNAPSHOT_DISCOVERY_HOLD"):tool.find_snaps()
