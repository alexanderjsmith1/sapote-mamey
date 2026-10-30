"""A missing source directory is unavailable evidence, not a successful empty scan."""
from argparse import Namespace
import pytest
from mamey import raw_antismash_triage as triage


@pytest.mark.parametrize("kind", ["absent", "file"])
def test_directory_unavailable_refused_before_scan(tmp_path, monkeypatch, capsys, kind):
    source = tmp_path / "antiSMASH input"
    if kind == "file": source.write_text("not a directory\n")
    out = tmp_path / "report.md"
    monkeypatch.setattr(triage, "explore_strain", lambda *a, **k: pytest.fail("unavailable directory must not be scanned"))
    args = Namespace(strain_dir=str(source), input_zip=None, no_walk=True, top_n=1, out=str(out), json=False, strain="PUBLIC")
    assert triage.explore_command(args) == 1
    assert "TRIAGE_SOURCE_UNAVAILABLE" in capsys.readouterr().err
    assert not out.exists()
