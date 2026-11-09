"""Family-verdict outputs are fresh per run and cutoff; ingest opens the database read-only; card wording."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


def _load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verdicts_refuse_reused_output_pair_and_database_alias(tmp_path):
    from test_452_bigscape_family_verdicts_run_id import _db
    bfv = _load("tools/bigscape_family_verdicts.py", "_bfv_464r3")
    db = _db(tmp_path)
    out = tmp_path / "verdicts_c0.3.tsv"
    assert bfv.main([str(db), str(out), "--cutoff", "0.3", "--run-id", "2"]) == 0
    first = out.read_bytes(), Path(str(out) + ".placement.tsv").read_bytes()
    with pytest.raises(SystemExit) as caught:
        bfv.main([str(db), str(out), "--cutoff", "0.5", "--run-id", "2"])
    assert caught.value.code == 2
    assert (out.read_bytes(), Path(str(out) + ".placement.tsv").read_bytes()) == first
    db_bytes = db.read_bytes()
    with pytest.raises(SystemExit):
        bfv.main([str(db), str(db), "--cutoff", "0.3", "--run-id", "2"])
    assert db.read_bytes() == db_bytes
    # a stale sidecar alone also blocks the pair
    stale = tmp_path / "new.tsv.placement.tsv"
    stale.write_text("earlier\n")
    with pytest.raises(SystemExit):
        bfv.main([str(db), str(tmp_path / "new.tsv"), "--cutoff", "0.3", "--run-id", "2"])
    assert stale.read_text() == "earlier\n" and not (tmp_path / "new.tsv").exists()


def test_ingest_dry_run_with_missing_database_creates_no_file(tmp_path):
    triage = tmp_path / "triage.csv"
    triage.write_text("Strain,BGC,Contig,antiSMASH_Region\nSYN-1,1,NODE_1_length_9000_cov_1.0,1\n")
    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "SYN-1_BGC001_ModeB.md").write_text("# card\n")
    missing = tmp_path / "missing.db"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "bigscape_ingest_to_mamey.py"), "--db", str(missing),
                        "--run-id", "1", "--triage", str(triage), "--cards-dir", str(cards), "--dry-run"],
                       capture_output=True, text=True, env=dict(os.environ))
    assert r.returncode != 0
    assert "not an existing BiG-SCAPE database" in r.stderr
    assert not missing.exists()


def test_ingest_gcf_context_refuses_missing_path_directly(tmp_path):
    tm = _load("tools/bigscape_ingest_to_mamey.py", "_bim_464r3")
    with pytest.raises(FileNotFoundError):
        tm.gcf_context(str(tmp_path / "absent.db"), "0.5", {}, run_id="1")
    assert not (tmp_path / "absent.db").exists()


def test_card_block_does_not_call_distance_zero_identical():
    tm = _load("tools/bigscape_ingest_to_mamey.py", "_bim_464r3_words")
    ctx = {"status": "KNOWN", "family_id": None, "mibig": [], "nearest_mibig": ("BGC0000001", "x", 0.0),
           "cross_strain_members": None}
    block = tm.render_block(ctx)
    assert "0 identical" not in block
    assert "distance 0 does not show identical sequences" in block
