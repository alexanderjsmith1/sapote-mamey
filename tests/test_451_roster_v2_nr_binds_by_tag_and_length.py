"""deliverable_tools/roster_v2.py binds an nr row to a gene only by tag and protein length within the current BGC.

nr top-hit files name the gene by locus tag and the BGC by the number of the run they came from. In some results the
tag is the gene's position inside its region, written with the contig prefix, and BGC numbers can come from an older
engine. Joining by BGC number and tag alone then shows another gene's hit. Rows that do not bind are held and counted.

Strain IDs are synthetic and runtime-constructed; fixtures live in tmp_path only.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os

_SPEC = importlib.util.spec_from_file_location(
    "deliverable_tools_roster_v2_bind",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deliverable_tools", "roster_v2.py"),
)
roster_v2 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(roster_v2)

STRAIN = "AS-" + str(9900 + 7)


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _fixture(root):
    pkg = os.path.join(root, "Mamey Complete", STRAIN, "package")
    _csv(os.path.join(pkg, f"{STRAIN}_2_inventory.csv"), ["BGC_ID", "Products", "KCB_top", "Node_ID", "antiSMASH_Region"],
         [["BGC001", "NRPS", "", "NODE_1", "region001"]])
    _csv(os.path.join(pkg, "locus_maps", "BGC001_NODE_1_locus_data.csv"),
         ["locus_tag", "length_aa", "order", "start", "end", "strand", "role", "gene_functions"],
         [["ctg1_1", "289", "1", "1", "870", "+", "", ""], ["ctg1_2", "300", "2", "900", "1800", "+", "", ""],
          ["ctg1_3", "310", "3", "1900", "2830", "+", "", ""]])
    nr_hdr = ["strain", "bgc_id", "gene", "aa_length", "hit_rank", "subject_acc", "subject_organism", "subject_def",
              "pct_identity"]
    _csv(os.path.join(root, "strain_data", STRAIN, "blastp_nr_1", f"{STRAIN}_nr_top_hit_per_gene_1.csv"), nr_hdr, [
        [STRAIN, "BGC001", "ctg1_2", "300", "1", "WP_BOUND", "Org", "bound hit", "88.0"],      # tag and length match
        [STRAIN, "BGC001", "ctg1_1", "1275", "1", "WP_OTHER", "Org", "another gene's hit", "93.6"],  # length differs
        [STRAIN, "BGC001", "ctg1_9", "300", "1", "WP_ABSENT", "Org", "tag not here", "70.0"],     # tag not in BGC
        [STRAIN, "BGC007", "ctg1_2", "300", "1", "WP_OLDNUM", "Org", "old BGC number", "65.0"],   # no locus data
        [STRAIN, "BGC001", "ctg1_3", "", "1", "WP_NOLEN", "Org", "no length", "60.0"],        # length not recorded
        [STRAIN, "BGC002", "ctg1_2", "300", "1", "WP_NOBGC", "Org", "unknown BGC", "61.0"],   # no locus data
    ])
    gm = os.path.join(root, "strain_data", "ClusterBlast_Gene_Master", "CLUSTERBLAST_GENE_MASTER.csv")
    _csv(gm, ["strain", "bgc_id", "query_gene", "pct_identity"], [])
    return gm


def test_nr_rows_bind_by_tag_and_length_and_the_rest_are_held(tmp_path, monkeypatch):
    root = str(tmp_path)
    gm = _fixture(root)
    monkeypatch.setattr(roster_v2, "ROOT", root)
    monkeypatch.setattr(roster_v2, "GMASTER", gm)
    out = os.path.join(root, "out")
    summary, err = roster_v2.build_strain(STRAIN, out)
    assert err is None, err
    model = json.load(open(summary["path"]))
    genes = {(b["bgc_id"], g["locus_tag"]): g for b in model["bgcs"] for g in b["genes"]}
    assert genes[("BGC001", "ctg1_2")]["channels"]["nr"]["acc"] == "WP_BOUND"
    assert genes[("BGC001", "ctg1_1")]["channels"]["nr"] is None            # the 1,275 aa hit is not shown on 289 aa
    assert ("BGC001", "ctg1_9") not in genes                                 # no phantom gene from an unbound tag
    assert not any(g["channels"]["nr"] for (b, _t), g in genes.items() if b in ("BGC007", "BGC002"))
    assert genes[("BGC001", "ctg1_3")]["channels"]["nr"] is None
    assert model["held_nr"] == {"length differs": 1, "tag not in this BGC": 1, "length not recorded": 1,
                                "no locus data for this BGC": 2}
    assert summary["nr"] == 1
