import json
import pytest
from mamey import blastp_evidence_store as mod

@pytest.mark.parametrize("failure", ["missing", "parse", "source_alias"])
def test_invalid_update_preserves_retained_round(tmp_path, monkeypatch, failure):
    store = tmp_path / "store"
    raw = store / "raw_ncbi_downloads/round1"
    parsed = store / "parsed_rounds/round1"
    raw.mkdir(parents=True)
    parsed.mkdir(parents=True)
    (raw / "original.csv").write_text("unique source")
    (parsed / "table.csv").write_text("unique parsed")
    (store / "BLASTP_round_manifest.jsonl").write_text(json.dumps({"round_id": "round1"}) + "\n")
    before = {str(p.relative_to(store)): p.read_bytes() for p in store.rglob("*") if p.is_file()}
    source = tmp_path / "replacement.csv"
    if failure == "parse":
        source.write_text("invalid")
        def reject(*args):
            raise ValueError("bad input")
        monkeypatch.setattr(mod, "parse_hit_table_csv", reject)
    elif failure == "source_alias":
        source = raw / "original.csv"
    with pytest.raises((FileNotFoundError, ValueError)):
        mod.ingest_blastp_round(store, strain="SYN-A", round_id="round1", hit_table_csv=source, allow_update=True)
    assert {str(p.relative_to(store)): p.read_bytes() for p in store.rglob("*") if p.is_file()} == before
