import sys
import pytest
from tools import check_tier_parity as mod

def test_parity_receipt_cannot_replace_selected_archive(tmp_path, monkeypatch):
    archive = tmp_path / "candidate.zip"
    archive.write_bytes(b"archive evidence")
    monkeypatch.setattr(sys, "argv", ["check_tier_parity", "--zips", str(archive), "--receipt-out", str(archive)])
    monkeypatch.setattr(mod, "inspect", lambda *args: pytest.fail("archive must not be consumed before admission"))
    with pytest.raises(ValueError, match="aliases"):mod.main()
    assert archive.read_bytes() == b"archive evidence"
