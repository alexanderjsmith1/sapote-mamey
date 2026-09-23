"""Exercise the real scoping command against pre-existing sidecar symlinks."""
import json
import pytest
from tests.test_scope_cluster import _load, _merged_region
from mamey.path_safety import UnsafeOutputLabel


def prepare(tmp_path):
    module = _load()
    from Bio import SeqIO
    gbk = tmp_path / "input.gbk"
    SeqIO.write(_merged_region(), gbk, "genbank")
    out = tmp_path / "out"
    out.mkdir()
    args = ["--gbk", str(gbk), "--category", "nucleoside", "--label", "sample", "--outdir", str(out)]
    return module, out, args


@pytest.mark.parametrize("exists", [True, False])
def test_external_sidecar_symlink_is_rejected_before_any_output(tmp_path, exists):
    module, out, args = prepare(tmp_path)
    target = tmp_path / "external.json"
    if exists:
        target.write_text("preserve this content")
    (out / "sample_nucleoside_scope.json").symlink_to(target)
    with pytest.raises(UnsafeOutputLabel, match="OUTPUT_PATH_ESCAPES_OUTDIR"):
        module.main(args)
    assert not (out / "sample_nucleoside_scoped.gbk").exists()
    if exists:
        assert target.read_text() == "preserve this content"
    else:
        assert not target.exists()


def test_normal_scoped_outputs_remain_available(tmp_path):
    module, out, args = prepare(tmp_path)
    assert module.main(args) == 0
    report = json.loads((out / "sample_nucleoside_scope.json").read_text())
    assert report["boundary"] == [0, 20000]
    assert report["n_kept"] == 2
    assert (out / "sample_nucleoside_scoped.gbk").is_file()
