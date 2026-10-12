"""Actual relative front-door paths must remain valid after the renderer child changes cwd."""
from pathlib import Path
import shutil

import pytest
from tools import phylo_place as native
from .test_trees_432_color_strips_report_deliverable import _fixture
from .test_m5_placement_metadata_children import strip_args, fake_renderer


@pytest.mark.parametrize("relative_out", [".", "relative result directory"])
def test_relative_strip_output_and_spaced_selected_executable_are_anchored_before_child_cwd(tmp_path, monkeypatch, relative_out):
    _fixture(tmp_path)
    calls = fake_renderer(tmp_path, monkeypatch)
    original_fake = native.subprocess.run
    monkeypatch.chdir(tmp_path)
    output_root = Path(relative_out).absolute()
    output_root.mkdir(exist_ok=True)
    # A configured relative invocation can be returned by which; it must remain that
    # invocation's executable rather than being interpreted relative to the child cwd.
    monkeypatch.setattr(shutil, "which", lambda command: "selected Rscript")
    def observe(argv, **kwargs):
        child = Path(kwargs["cwd"])
        executable, script = Path(argv[0]), Path(argv[1])
        assert child.is_absolute() and executable.is_absolute() and script.is_absolute()
        assert executable == tmp_path/"selected Rscript" and executable.is_file()
        assert script.parent == child and script.is_file()
        assert child.is_relative_to(output_root)
        return original_fake(argv, **kwargs)
    monkeypatch.setattr(native.subprocess, "run", observe)
    args = strip_args(tmp_path); args.rscript = "./selected Rscript"
    result = native._color_strips_deliverable(args, relative_out, "Genus", "tree.newick", "labelmap.tsv")
    assert result["state"] == "RENDERED_WITH_OMISSIONS" and len(calls) == 2
    assert Path(result["receipt"]).is_absolute()
    for child in result["variants"]:
        assert child["state"] == "RENDERED"
        assert Path(child["receipt"]).is_absolute()
        assert all(Path(item["path"]).is_absolute() for item in child["artifacts"])
