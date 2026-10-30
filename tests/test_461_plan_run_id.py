"""A run identifier must not redirect writes outside the workspace run folder."""
from pathlib import Path
import pytest
from tools import plan_gtotree_iqtree as planner

@pytest.mark.parametrize("run_id", ["../escaped", "/absolute_run", "nested/run"])
def test_run_id_refused_before_inputs_or_probes(monkeypatch, tmp_path, run_id):
    args = planner.build_parser().parse_args([
        "plan", "--panel-tsv", str(tmp_path / "panel.tsv"),
        "--workspace", str(tmp_path / "workspace"), "--run-id", run_id,
        "--hmm", str(tmp_path / "set.hmm"),
    ])
    calls = []
    def must_not_read(*args, **kwargs):
        calls.append("read")
        pytest.fail("invalid run ID reached input reading")
    monkeypatch.setattr(planner, "read_panel", must_not_read)
    with pytest.raises(ValueError, match="run-id"):
        planner.plan(args)
    assert not calls
    assert not (tmp_path / "workspace").exists()
