"""build_lead_detail never replaces an earlier lead_detail.json (default or --out).

Before: the default output inside the package, or any existing --out file that was not an input
alias, was replaced.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lead_464r3", ROOT / "tools/build_lead_detail.py")
lead = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lead)


def _setup(tmp_path):
    pkg, gbks = tmp_path / "package", tmp_path / "gbks"
    pkg.mkdir(); gbks.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "FIXTURE", "bgcs": [
        {"bgc_id": "BGC001", "contig": "c", "notes": ["source_gbk=s.region001.gbk"]}]}))
    (gbks / "s.region001.gbk").write_text("LOCUS       S\nORIGIN\n//\n")
    return pkg, gbks


@pytest.mark.parametrize("where", ["default", "explicit"])
def test_existing_output_is_kept(tmp_path, monkeypatch, where):
    pkg, gbks = _setup(tmp_path)
    prior = pkg / "lead_detail.json" if where == "default" else tmp_path / "result.json"
    prior.write_text("previous generated output")
    argv = ["build_lead_detail.py", "--package", str(pkg), "--gbk-dir", str(gbks), "--leads", "BGC001"]
    if where == "explicit":
        argv += ["--out", str(prior)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        lead.main()
    assert exc.value.code == 2
    assert prior.read_text() == "previous generated output"
