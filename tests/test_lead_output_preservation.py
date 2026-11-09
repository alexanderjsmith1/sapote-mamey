"""Source/output alias controls, with synthetic software-only input records."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lead_candidate", ROOT / "tools/build_lead_detail.py")
lead = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lead)


def setup(tmp_path):
    pkg = tmp_path / "package"
    gbks = tmp_path / "gbks"
    pkg.mkdir()
    gbks.mkdir()
    manifest = pkg / "manifest.json"
    manifest.write_text(json.dumps({"strain_id": "SOFTWARE-FIXTURE", "bgcs": [{"bgc_id": "BGC001", "contig": "software_contig", "notes": ["source_gbk=software.region001.gbk"]}]}))
    pairs = pkg / "SOFTWARE-FIXTURE_RGGMCI_full.json"
    pairs.write_text(json.dumps({"ranked_pairs": []}))
    gbk = gbks / "software.region001.gbk"
    gbk.write_text("LOCUS       SOFTWARE_FIXTURE\nORIGIN\n//\n")
    return pkg, gbks, dict(manifest=manifest, pairs=pairs, gbk=gbk)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def invoke(monkeypatch, pkg, gbks, out=None):
    args = ["build_lead_detail.py", "--package", str(pkg), "--gbk-dir", str(gbks), "--leads", "BGC001"]
    if out is not None:
        args += ["--out", str(out)]
    monkeypatch.setattr(sys, "argv", args)
    lead.main()


@pytest.mark.parametrize("source", ["manifest", "pairs", "gbk"])
@pytest.mark.parametrize("kind", ["direct", "symlink", "hardlink", "parent_symlink"])
def test_alias_refused_and_sources_preserved(tmp_path, monkeypatch, source, kind):
    pkg, gbks, inputs = setup(tmp_path)
    path = inputs[source]
    if kind == "direct":
        out = path
    elif kind == "parent_symlink":
        alias = tmp_path / "alias_dir"
        alias.symlink_to(path.parent, target_is_directory=True)
        out = alias / path.name
    else:
        out = tmp_path / "alias.json"
        out.symlink_to(path) if kind == "symlink" else os.link(path, out)
    before = snapshot(tmp_path)
    refused = False
    try:
        invoke(monkeypatch, pkg, gbks, out)
    except SystemExit as error:
        assert error.code == 2
        refused = True
    after = snapshot(tmp_path)
    assert refused and before == after, {"refused": refused, "changed_paths": [p for p in before if before.get(p) != after.get(p)], "new_paths": sorted(after.keys() - before.keys())}


@pytest.mark.parametrize("destination", ["default", "new"])
def test_nonalias_output_retains_existing_behavior(tmp_path, monkeypatch, destination):
    pkg, gbks, inputs = setup(tmp_path)
    before = {key: path.read_bytes() for key, path in inputs.items()}
    out = None if destination == "default" else tmp_path / "result.json"
    invoke(monkeypatch, pkg, gbks, out)
    result = json.loads((out or pkg / "lead_detail.json").read_text())
    assert result["strain_id"] == "SOFTWARE-FIXTURE"
    assert len(result["leads"]) == 1
    assert all(path.read_bytes() == before[key] for key, path in inputs.items())
