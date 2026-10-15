"""Card attine_452_region_edge_totals: tools/region_edge_totals.py counts regions on a contig edge with the engine's
own region intake (mamey.parsers.parse_bgcs_from_zip; Edge or Full-contig), records the mamey version, and refuses a
genome whose engine region count differs from the one-strictness region table. Public fixture only.
"""
import csv
import importlib.util
import json
from pathlib import Path

import mamey
from mamey import parsers

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/region_edge_totals.py"
FIX = ROOT / "tests/fixtures/micromonospora_humida_JAFEUC01.zip"
NAME = FIX.name[:-4]
spec = importlib.util.spec_from_file_location("region_edge_totals_t", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def genomes(tmp_path):
    g = tmp_path / "genomes.tsv"
    g.write_text(f"strain\tgenus\n{NAME}\tMicromonospora\n")
    return g


def test_edge_counts_follow_the_engine_and_record_its_version(tmp_path):
    out = tmp_path / "edge.tsv"
    assert mod.main(["--zips", str(FIX), "--genomes", str(genomes(tmp_path)), "--out", str(out)]) == 0
    row = next(csv.DictReader(out.open(), delimiter="\t"))
    statuses = [b.edge_status for b in parsers.parse_bgcs_from_zip(FIX)]
    assert int(row["regions"]) == len(statuses)
    assert int(row["contig_edge"]) == sum(s in ("Edge", "Full-contig") for s in statuses)
    assert int(row["pct_edge"]) == round(100 * int(row["contig_edge"]) / int(row["regions"]))
    info = json.loads((tmp_path / "edge_RUN_INFO.json").read_text())
    assert info["mamey_version"] == mamey.__version__ and "95%" in info["rule"] and "5 kb" in info["rule"]


def test_a_region_count_that_differs_from_the_region_table_is_refused(tmp_path):
    t = tmp_path / "table.tsv"
    t.write_text(f"strain\tregion_file\n{NAME}\tSYN.region001.gbk\n")   # one region; the engine reads more
    out = tmp_path / "edge.tsv"
    assert mod.main(["--zips", str(FIX), "--genomes", str(genomes(tmp_path)), "--region-table", str(t), "--out", str(out)]) == 2
    assert not out.exists()


def test_genome_table_must_name_every_zip(tmp_path):
    g = tmp_path / "g.tsv"
    g.write_text("strain\tgenus\nSYN-971\tSynthetica\n")
    import pytest
    with pytest.raises(ValueError, match="different strains"):
        mod.main(["--zips", str(FIX), "--genomes", str(g), "--out", str(tmp_path / "o.tsv")])
