import csv, importlib.util, json
from pathlib import Path
import pytest

SCRIPT=Path(__file__).parents[1]/"tools"/"init_project_data_home.py"
spec=importlib.util.spec_from_file_location("project_home", SCRIPT)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_creates_complete_pointer_home(tmp_path):
    root=tmp_path/"research-home"
    mod.create_home(root,"example-project")
    assert set(mod.DIRS) <= {p.name for p in root.iterdir() if p.is_dir()}
    data=json.loads((root/"PROJECT_HOME.json").read_text())
    assert data["storage_model"] == "pointer-first"
    for rel, header in mod.REGISTERS.items():
        rows=list(csv.reader((root/rel).open(),delimiter="\t"))
        assert rows == [list(header)]

def test_refuses_existing_target(tmp_path):
    root=tmp_path/"exists"; root.mkdir(); marker=root/"keep"; marker.write_text("safe")
    with pytest.raises(FileExistsError): mod.create_home(root,"example")
    assert marker.read_text()=="safe"

def test_shipped_files_have_no_personal_workspace_paths():
    for path in (SCRIPT, Path(__file__).parents[1]/"docs"/"PROJECT_DATA_HOME.md"):
        text=path.read_text()
        assert "/Users/" not in text
        assert "Claude_Alex" not in text
        assert "Codex Alex" not in text
