"""prepare_biosynthetic_tree_inputs: a repeated FASTA identifier is refused, and an RRE row without
valid in-range coordinates is held instead of falling back to the full protein."""
import csv
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).parents[1] / "tools" / "prepare_biosynthetic_tree_inputs.py"
PROT = "ACDEFGHIKLMNPQRSTVWY" * 6  # 120 aa


def _csv(path, fields, rows):
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _fixture(root, faa_text, rre_rows):
    inv = root / "inventory.csv"
    _csv(inv, ["BGC_ID", "Products"], [{"BGC_ID": "BGC002", "Products": "RiPP;lassopeptide"}])
    rre = root / "rre.csv"
    _csv(rre, ["bgc_id", "locus_tag", "mapping_status", "rre_family", "protein_start", "protein_end"], rre_rows)
    faa = root / "proteins.faa"
    faa.write_text(faa_text)
    man = root / "sources.tsv"
    man.write_text(f"strain_id\tinventory_csv\trrefinder_csv\tproteins_faa\nEXAMPLE-1\t{inv}\t{rre}\t{faa}\n")
    return man


def _run(root, man):
    return subprocess.run([sys.executable, str(TOOL), str(man), str(root / "out"), "--track", "ripp-rre",
                           "--family", "lassopeptide"], text=True, capture_output=True, cwd=root)


def _ledger(root):
    with (root / "out" / "sequence_ledger.tsv").open() as h:
        return {r["locus_tag"]: r for r in csv.DictReader(h, delimiter="\t")}


def test_repeated_fasta_identifier_is_refused(tmp_path):
    man = _fixture(tmp_path, f">p1\n{PROT}\n>p1\n{PROT[:60]}\n",
                   [{"bgc_id": "BGC002", "locus_tag": "p1", "mapping_status": "MAPPED", "rre_family": "lassopeptide",
                     "protein_start": "1", "protein_end": "60"}])
    r = _run(tmp_path, man)
    assert r.returncode != 0
    assert "appears more than once" in r.stderr
    assert not (tmp_path / "out").exists()


def test_rre_without_valid_coordinates_is_held(tmp_path):
    faa = "".join(f">p{i}\n{PROT}\n" for i in range(1, 6))
    base = {"bgc_id": "BGC002", "mapping_status": "MAPPED", "rre_family": "lassopeptide"}
    rows = [dict(base, locus_tag="p1", protein_start="", protein_end=""),
            dict(base, locus_tag="p2", protein_start="x", protein_end="50"),
            dict(base, locus_tag="p3", protein_start="10", protein_end="500"),
            dict(base, locus_tag="p4", protein_start="11", protein_end="60")]
    r = _run(tmp_path, _fixture(tmp_path, faa, rows))
    assert r.returncode == 0, r.stderr
    led = _ledger(tmp_path)
    assert (led["p1"]["status"], led["p1"]["reason"]) == ("HOLD", "RRE_COORDINATES_MISSING")
    assert (led["p2"]["status"], led["p2"]["reason"]) == ("HOLD", "RRE_COORDINATES_NOT_INTEGER")
    assert (led["p3"]["status"], led["p3"]["reason"]) == ("HOLD", "RRE_COORDINATES_OUTSIDE_PROTEIN")
    for k in ("p1", "p2", "p3"):
        assert led[k]["aa_length"] == "" and led[k]["sequence_sha256"] == ""
    assert led["p4"]["status"] == "ELIGIBLE" and led["p4"]["aa_length"] == "50"
    receipt = json.loads((tmp_path / "out" / "receipt.json").read_text())
    assert receipt["counts"]["eligible_sequences"] == 1


def test_repeated_inventory_bgc_id_is_refused(tmp_path):
    man = _fixture(tmp_path, f">p1\n{PROT}\n",
                   [{"bgc_id": "BGC002", "locus_tag": "p1", "mapping_status": "MAPPED", "rre_family": "lassopeptide",
                     "protein_start": "1", "protein_end": "60"}])
    inv = tmp_path / "inventory.csv"
    inv.write_text("BGC_ID,Products\nBGC002,RiPP;lassopeptide\nBGC002,NRPS\n")
    r = _run(tmp_path, man)
    assert r.returncode != 0
    assert "BGC_ID 'BGC002' appears more than once" in r.stderr
    assert not (tmp_path / "out").exists()
