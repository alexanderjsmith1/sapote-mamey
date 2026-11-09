"""rank_clusterblast_phylo_candidates: NaN, infinity and out-of-range identity/coverage/score rows are
left out of the ranking and listed in rejected_hit_rows.tsv; inventory rows skipped for a missing
BGC ID, contig or region are listed in inventory_skipped_rows.tsv; a present nonnumeric region stops."""
import csv
import importlib.util
import json
import pathlib
import sys
import zipfile

import pytest

TOOL = pathlib.Path(__file__).parents[1] / "tools" / "rank_clusterblast_phylo_candidates.py"
SPEC = importlib.util.spec_from_file_location("rcpc_464r3", TOOL)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

HEAD = "Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"


def _block(rank, ref, rows):
    return (f"\n>>\n{rank}. {ref}\nSource: Organism one\nType: NRPS\n"
            "Number of proteins with BLAST hits to this cluster: 1\nCumulative BLAST score: 100.0\n\n"
            + HEAD + "".join(rows))


def test_parser_rejects_nonfinite_and_out_of_range():
    rows = ["q1\ts1\tnan\t100\t90\t1e-20\n", "q2\ts2\t80\t100\tinf\t1e-20\n",
            "q3\ts3\t180\t100\t90\t1e-20\n", "q4\ts4\t80\t-inf\t90\t1e-20\n",
            "q5\ts5\t80\t100\t90\t1e-20\n"]
    rejected = []
    hits = mod.parse_hit_rows(_block(1, "NZ_REF1", rows), rejected)
    assert [h["query_gene"] for h in hits] == ["q5"]
    assert [r["reason"].split()[0] for r in rejected] == ["identity", "coverage", "identity", "BLAST"]


def _inputs(tmp_path, inventory_text):
    z = tmp_path / "EXAMPLE-1.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("input/EXAMPLE-1.fna", ">a\nAAAACCCC\n")
        zf.writestr("clusterblast/ctgA_c1.txt", "ClusterBlast scores for ctgA\n" +
                    _block(1, "NZ_REF1", ["q1\ts1\tnan\t100\t90\t1e-20\n", "q2\ts2\t75\t100\t90\t1e-20\n"]))
    inv = tmp_path / "inventory.csv"
    inv.write_text(inventory_text)
    man = tmp_path / "manifest.tsv"
    man.write_text("strain_id\tcohort\tantismash_zip\tassembly_member\tbgc_inventory_csv\tmamey_clusterblast_csv\n"
                   f"EXAMPLE-1\tPUBLIC\t{z}\tinput/EXAMPLE-1.fna\t{inv}\t\n")
    return man


def _tsv(p):
    return list(csv.DictReader(p.open(), delimiter="\t"))


def test_build_lists_rejected_and_skipped_rows(tmp_path):
    man = _inputs(tmp_path, "BGC_ID,Contig,Region\nBGC001,ctgA,1\n,ctgB,2\nBGC003,,3\n")
    receipt = mod.build(man, tmp_path / "out")
    out = tmp_path / "out"
    rej = _tsv(out / "rejected_hit_rows.tsv")
    assert len(rej) == 1 and rej[0]["bgc_id"] == "BGC001" and "identity" in rej[0]["reason"]
    hits = _tsv(out / "clusterblast_gene_hits.tsv")
    assert all(h["query_gene"] != "q1" for h in hits)
    skipped = _tsv(out / "inventory_skipped_rows.tsv")
    assert [(r["line"], r["reason"]) for r in skipped] == [("3", "missing BGC_ID"), ("4", "missing Contig")]
    assert receipt["rejected_hit_rows"] == 1 and receipt["inventory_skipped_rows"] == 2


def test_present_nonnumeric_region_stops_the_run(tmp_path):
    man = _inputs(tmp_path, "BGC_ID,Contig,Region\nBGC001,ctgA,one\n")
    assert mod.main([str(man), str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()
