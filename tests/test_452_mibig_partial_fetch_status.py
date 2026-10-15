import io
import tarfile
import pytest
from tools import fetch_mibig_reference as mod

@pytest.mark.parametrize("missing", [True, False])
def test_partial_reference_batch_is_non_success_and_complete_batch_still_passes(tmp_path, monkeypatch, missing):
    tar = tmp_path / "references.tar.gz"
    entries = {"BGC0000971": b"synthetic reference one"}
    if not missing:entries["BGC0000972"] = b"synthetic reference two"
    with tarfile.open(tar, "w:gz") as archive:
        for accession, payload in entries.items():
            info = tarfile.TarInfo("mibig_gbk_4.0/" + accession + ".gbk")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    monkeypatch.setattr(mod, "ensure_tarball", lambda *args, **kwargs: str(tar))
    output = tmp_path / "output"
    status = mod.main(["--acc", "BGC0000971:first", "--acc", "BGC0000972:second", "--outdir", str(output), "--cache", str(tmp_path / "cache")])
    assert status == (1 if missing else 0)
    assert (output / "first.gbk").read_bytes() == entries["BGC0000971"]
    assert (output / "second.gbk").exists() is (not missing)
