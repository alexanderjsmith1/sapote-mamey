from pathlib import Path
import importlib.util
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_tool", ROOT / "tools/build_combined_bgc_report.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

@pytest.mark.parametrize("status, expected", [("EXCLUDED_NO_OUTPUT", 3),
                         ("DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED", 0)])
def test_builder_status_reaches_cli(tmp_path, monkeypatch, capsys, status, expected):
    import json, sys
    output = tmp_path / "output"
    manifest = {"status": status, "subject_id": "SYNTHETIC_TEST_SUBJECT"}
    def builder(job, roots, out):
        assert roots == {"TEST": tmp_path}
        assert out == output
        return manifest
    monkeypatch.setattr(tool, "build_from_path", builder)
    monkeypatch.setattr(sys, "argv", ["build_combined_bgc_report.py", "--job-spec", str(tmp_path / "job.json"),
                                     "--source-root", "TEST=" + str(tmp_path), "--out-root", str(output)])
    assert tool.main() == expected
    assert json.loads(capsys.readouterr().out) == manifest
    assert not output.exists()
