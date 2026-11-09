"""Synthetic banks only: assembly QC keeps unchecked roster strains visible and never overwrites inputs."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "assembly_qc_check.py"


def _bank(tmp_path, strains=("S1", "S2")):
    bank = tmp_path / "cohort"
    bank.mkdir()
    (bank / "strains.json").write_text(json.dumps([{"sid": s, "organism": "Streptomyces sp."} for s in strains]))
    (bank / "bgc_data.json").write_text(json.dumps({"bgcs": [
        {"sid": "S1", "contig": "c1", "edge_status": "Interior"},
        {"sid": "S1", "contig": "c2", "edge_status": "Edge"}]}))
    return bank


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, timeout=120)


def test_roster_strain_without_bgc_rows_is_not_checked(tmp_path):
    bank = _bank(tmp_path)
    out = tmp_path / "qc.json"
    result = _run("--banked-dir", str(bank), "--out", str(out))
    assert result.returncode == 0, result.stderr
    data = json.loads(out.read_text())
    rows = {r["strain"]: r for r in data["strains"]}
    assert set(rows) == {"S1", "S2"}
    assert rows["S2"]["status"] == "NOT_CHECKED"
    assert rows["S2"]["raw_bgcs"] is None and rows["S2"]["contigs"] is None
    assert data["not_checked"] == ["S2"] and "S2" not in data["held_qc"]
    assert "1 NOT_CHECKED" in result.stdout


def test_output_aliasing_an_input_is_refused_even_with_replace(tmp_path):
    bank = _bank(tmp_path)
    saved = (bank / "bgc_data.json").read_bytes()
    for extra in ([], ["--replace"]):
        result = _run("--banked-dir", str(bank), "--out", str(bank / "bgc_data.json"), *extra)
        assert result.returncode == 2 and "REFUSED" in result.stderr
    assert (bank / "bgc_data.json").read_bytes() == saved


def test_existing_output_needs_replace(tmp_path):
    bank = _bank(tmp_path)
    out = tmp_path / "qc.json"
    out.write_text("EARLIER")
    result = _run("--banked-dir", str(bank), "--out", str(out))
    assert result.returncode == 2 and out.read_text() == "EARLIER"
    result = _run("--banked-dir", str(bank), "--out", str(out), "--replace")
    assert result.returncode == 0 and json.loads(out.read_text())["gate"] == "assembly_qc"


def test_repeated_roster_strain_is_refused(tmp_path):
    bank = _bank(tmp_path, strains=("S1", "S1"))
    out = tmp_path / "qc.json"
    result = _run("--banked-dir", str(bank), "--out", str(out))
    assert result.returncode == 2 and "more than once" in result.stderr
    assert not out.exists()


def test_repeated_snapshot_strain_is_refused(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps([{"strain": "S1", "assembly": {}}, {"strain": "S1", "assembly": {}}]))
    out = tmp_path / "qc.json"
    result = _run("--snapshot", str(snap), "--out", str(out))
    assert result.returncode == 2 and not out.exists()
