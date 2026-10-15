import os
import pytest
from mamey import npatlas_provision as library
from tools import npatlas_provision as front

@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink", "temporary"])
def test_subset_writer_preserves_source_aliases(tmp_path, alias):
    source = tmp_path / "source.json"
    source.write_text("{\"compounds\": []}")
    out = tmp_path / "subset.json"
    if alias == "direct":out = source
    elif alias == "symlink":out.symlink_to(source)
    elif alias == "hardlink":os.link(source, out)
    else:(tmp_path / "subset.json.tmp").symlink_to(source)
    before = source.read_bytes()
    with pytest.raises(library.NpatlasProvisionError):library.provision(str(source),str(out),[])
    assert source.read_bytes() == before

@pytest.mark.parametrize("mode", ["inspect", "receipt"])
def test_front_door_refuses_receipt_source_alias_before_processing(tmp_path, monkeypatch, mode):
    source = tmp_path / "source.json"
    source.write_text("original")
    monkeypatch.setattr(front, "inspect_source", lambda *a, **k: {})
    monkeypatch.setattr(front, "provision", lambda *a, **k: None)
    args = ["inspect", "--source", str(source), "--out-json", str(source)] if mode == "inspect" else ["provision", "--source", str(source), "--out", str(tmp_path / "subset.json"), "--out-receipt", str(source)]
    assert front.main(args) == 1
    assert source.read_text() == "original"
