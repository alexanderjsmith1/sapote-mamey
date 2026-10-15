import csv
import pytest
from tools.check_bgc_naming import crosswalk

@pytest.mark.parametrize("kind", ["blank_node", "blank_region", "zero_region", "malformed_region", "blank_alias", "ancestor_only", "duplicate_alias", "equivalent_alias", "duplicate_locus", "row_conflict"])
def test_incomplete_or_conflicting_identity_never_publishes_rename_keys(tmp_path, kind):
    folder = tmp_path / "AS-972"
    folder.mkdir()
    source = folder / ("inventory.csv" if kind == "ancestor_only" else "AS-971_2_inventory.csv")
    node = "" if kind == "blank_node" else "contig1"
    region = {"blank_region": "", "zero_region": "0", "malformed_region": "notes2"}.get(kind, "1")
    alias = "" if kind == "blank_alias" else "BGC001"
    rows = [[alias, node, region, "AS-972" if kind == "row_conflict" else ""]]
    if kind == "duplicate_alias": rows.append([alias, "contig2", "2", ""])
    if kind == "equivalent_alias": rows.append(["BGC_1", "contig2", "2", ""])
    if kind == "duplicate_locus": rows.append(["BGC002", node, region, ""])
    with source.open("w") as out:
        from mamey.csv_safety import SafeWriter
        writer = SafeWriter(out)
        writer.writerow(["bgc_id", "node_id", "region", "strain"])
        writer.writerows(rows)
    before = source.read_bytes()
    output = tmp_path / "crosswalk.tsv"
    with pytest.raises(ValueError):crosswalk(str(source), str(output))
    assert not output.exists() and source.read_bytes() == before

def test_full_wgs_contig_version_and_positive_region_are_preserved(tmp_path):
    source = tmp_path / "AS-971_2_inventory.csv"
    source.write_text("bgc_id,node_id,region\nBGC001,JAGDQQ010000001.1,region001\n")
    output = tmp_path / "crosswalk.tsv"
    assert crosswalk(str(source), str(output)) == 0
    row = next(csv.DictReader(output.open(), delimiter="\t"))
    assert row["strain"] == "AS-971"
    assert row["canonical_exact_locus_prefix"] == "AS-971__JAGDQQ010000001.1__region001__BGC001"
