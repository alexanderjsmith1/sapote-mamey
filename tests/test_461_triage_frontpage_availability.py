"""Missing front-page source and an available empty result must remain distinct."""
import pytest
from argparse import Namespace
from mamey.kcb_frontpage import frontpage_command
from mamey.raw_antismash_triage import explore_strain, render_explore_report_md


def test_missing_frontpage_source_is_unavailable(tmp_path):
    source = tmp_path / "partial input"; source.mkdir()
    result = explore_strain(source, bundle_root=tmp_path, run_bgc_walk=False)
    state = result["steps"]["kcb_frontpage"]
    assert state["status"] == "SOURCE_UNAVAILABLE"
    assert state["n_hits"] is None
    md = render_explore_report_md(result, "PUBLIC")
    assert "regions.js" in md and "not a negative result" in md


def test_available_empty_frontpage_keeps_zero(tmp_path):
    source = tmp_path / "available input"; source.mkdir()
    (source / "regions.js").write_text("var resultsData = {};\n")
    result = explore_strain(source, bundle_root=tmp_path, run_bgc_walk=False)
    state = result["steps"]["kcb_frontpage"]
    assert state["status"] == "RAN" and state["n_hits"] == 0


@pytest.mark.parametrize("text", ["var unrelated = {};\n", "var resultsData = {broken};\n"])
def test_invalid_frontpage_source_is_an_error(tmp_path, text):
    source = tmp_path / "invalid input"; source.mkdir()
    (source / "regions.js").write_text(text)
    result = explore_strain(source, bundle_root=tmp_path, run_bgc_walk=False)
    state = result["steps"]["kcb_frontpage"]
    assert state["status"] == "ERRORED"
    assert state.get("n_hits") is None


def test_standalone_frontpage_cli_refuses_missing_source(tmp_path, capsys):
    assert frontpage_command(Namespace(strain_dir=str(tmp_path))) == 1
    captured = capsys.readouterr()
    assert "FRONTPAGE_SOURCE_UNAVAILABLE" in captured.err
    assert "No KnownClusterBlast hits" not in captured.out
