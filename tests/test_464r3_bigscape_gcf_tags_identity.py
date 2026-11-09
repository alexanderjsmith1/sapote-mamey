"""build_gcf_tags rows carry contig and region from the bank and hold rows that lack an identity part."""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tag_rows_carry_full_identity_and_hold_missing_parts(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": [
        {"sid": "SYN-1", "bgc_id": "BGC001", "contig": "NODE_1_length_9000_cov_1.0", "region": "region001",
         "products": "NRPS", "closest_kcb_product": "unresolved"},
        {"sid": "SYN-1", "bgc_id": "BGC001", "contig": "NODE_9_length_7000_cov_2.0", "region": "region001",
         "products": "NRPS", "closest_kcb_product": "unresolved"},
        {"sid": "SYN-2", "bgc_id": "BGC002", "region": "region002", "products": "terpene",
         "closest_kcb_product": ""},
    ]}))
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_gcf_tags.py"), "--banked-dir", str(bank),
                        "--thesaurus", str(ROOT / "resources" / "gcf_thesaurus.json"), "--out-dir", str(out)],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    rows = list(csv.DictReader((out / "GCF_Tags.csv").open()))
    # a reused alias on two contigs stays two distinguishable rows
    assert [(x["strain"], x["contig"], x["region"], x["bgc"]) for x in rows[:2]] == [
        ("SYN-1", "NODE_1_length_9000_cov_1.0", "region001", "BGC001"),
        ("SYN-1", "NODE_9_length_7000_cov_2.0", "region001", "BGC001")]
    assert [x["identity_status"] for x in rows] == ["COMPLETE", "COMPLETE", "IDENTITY_HOLD"]
    assert rows[2]["contig"] == ""


def _run_tags(bank, out):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "build_gcf_tags.py"), "--banked-dir", str(bank),
                           "--thesaurus", str(ROOT / "resources" / "gcf_thesaurus.json"), "--out-dir", str(out)],
                          capture_output=True, text=True, cwd=str(ROOT))


def test_rerun_into_the_same_folder_is_refused_and_keeps_the_earlier_tags(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": [
        {"sid": "SYN-1", "bgc_id": "BGC001", "contig": "NODE_1", "region": "region001",
         "products": "NRPS", "closest_kcb_product": "unresolved"}]}))
    out = tmp_path / "out"
    assert _run_tags(bank, out).returncode == 0
    first = (out / "GCF_Tags.csv").read_bytes()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": []}))
    r = _run_tags(bank, out)
    assert r.returncode == 2
    assert "refusing" in r.stderr and "choose a new --out-dir" in r.stderr
    assert (out / "GCF_Tags.csv").read_bytes() == first


def test_output_may_not_be_the_bank_file(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    src = bank / "GCF_Tags.csv"          # out-dir == banked-dir; an existing file of that name is refused
    src.write_text("strain\n")
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": []}))
    assert _run_tags(bank, bank).returncode == 2
    assert src.read_text() == "strain\n"
