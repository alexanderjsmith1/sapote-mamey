"""Static unexecuted 4D writer controls; no rescue analysis is invoked."""
import csv
from pathlib import Path
import pytest
from mamey import rescue_two_proof as tool, packaging

def _row():
    return {"contig_a": "synthetic_a", "contig_b": "synthetic_b", "verdict": "WEAK"}

@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_predictable_foreign_temp_is_never_written_or_removed(tmp_path, kind):
    out = tmp_path / "out.csv"; fixed = tmp_path / "out.csv.tmp"
    protected = tmp_path / "protected"; protected.write_text("source bytes")
    if kind == "file": fixed.write_text("foreign temporary bytes")
    else: fixed.symlink_to(protected)
    before = fixed.read_bytes()
    assert tool.write_4d_csv([_row()], out, "SYN-WRITER") == str(out)
    assert fixed.read_bytes() == before
    assert protected.read_text() == "source bytes"

def test_failed_serialization_retains_old_target_and_foreign_temp(tmp_path):
    out = tmp_path / "out.csv"; out.write_text("prior output")
    fixed = tmp_path / "out.csv.tmp"; fixed.write_text("foreign temporary")
    with pytest.raises(KeyError): tool.write_4d_csv([{}], out, "SYN-WRITER")
    assert out.read_text() == "prior output"
    assert fixed.read_text() == "foreign temporary"

def test_failed_replace_retains_prior_target_and_foreign_temp(tmp_path, monkeypatch):
    out = tmp_path / "out.csv"; out.write_text("prior output")
    fixed = tmp_path / "out.csv.tmp"; fixed.write_text("foreign temporary")
    def failed(*a, **k): raise OSError("synthetic replace failure")
    monkeypatch.setattr(packaging.os, "replace", failed)
    with pytest.raises(OSError): tool.write_4d_csv([_row()], out, "SYN-WRITER")
    assert out.read_text() == "prior output"
    assert fixed.read_text() == "foreign temporary"

def test_payload_order_policy_and_version_are_preserved(tmp_path):
    out = tmp_path / "out.csv"
    tool.write_4d_csv([_row()], out, "SYN-WRITER")
    with out.open() as f: row = list(csv.DictReader(f))[0]
    assert row["verdict"] == "WEAK"
    assert row["two_proof_logic_version"] == tool.TWO_PROOF_LOGIC_VERSION
    assert row["rule_policy"] == "ks_clade_v2"
    assert "NOT a merge" in row["claim_note"]
