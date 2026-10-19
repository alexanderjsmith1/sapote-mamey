"""Unexecuted controlled source replacement at the real byte-read boundary."""
import hashlib
from pathlib import Path
import pytest
from mamey.gold_bgc_identity import load_gold_identity_context,GoldBGCIdentityError
from tests._gold_identity_fixture import bind_synthetic_gold_package

def test_inventory_records_match_hashed_buffer_despite_later_replacement(tmp_path,monkeypatch):
    fixture=bind_synthetic_gold_package(tmp_path/"package","SYNTHETIC",deep={"bgc_profile":[{"bgc_id":"BGC001"}]})
    pkg=Path(fixture["pkg"]);inv=pkg/"SYNTHETIC_2_inventory.csv"
    original=Path.read_bytes;raw=original(inv)
    def replaced(path):
        data=original(path)
        if path==inv: path.write_text("corrupted replacement\n",encoding="utf-8")
        return data
    monkeypatch.setattr(Path,"read_bytes",replaced)
    context = None
    refusal = None
    try:
        context = load_gold_identity_context(pkg, "SYNTHETIC")
    except GoldBGCIdentityError as exc:
        refusal = str(exc)
    assert context is not None, f"Already-read inventory buffer must still bind; got {refusal!r}"
    assert context["receipt"]["inventory_sha256"]==hashlib.sha256(raw).hexdigest()
    assert context["records"][0]["exact_locus"]==fixture["context"]["records"][0]["exact_locus"]
    with pytest.raises(GoldBGCIdentityError):load_gold_identity_context(pkg,"SYNTHETIC")
