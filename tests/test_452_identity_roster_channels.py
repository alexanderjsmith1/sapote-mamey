"""Static unexecuted public-roster regression drafts; synthetic package files."""
import csv
import pytest
from mamey.roster_v2 import build_gene_roster

def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

@pytest.mark.parametrize("reverse", [False, True])
def test_independent_overlay_channels(tmp_path, reverse):
    rows=[dict(query_bgc="BGC001", locus_tag="ctg1_1", channel=c,
               blastp_accession=a, pct_identity="70")
          for c,a in [("nr","NR"),("clustered_nr","CNR")]]
    write(tmp_path/"blastp_online/BGC001_online_blastp.csv", list(reversed(rows)) if reverse else rows)
    m=build_gene_roster(tmp_path, strain_id="SYNTHETIC")
    ch=m["bgcs"][0]["genes"][0]["channels"]
    assert ch["nr"]["acc"]=="NR" and ch["clustered_nr"]["acc"]=="CNR"

@pytest.mark.parametrize("channel", ["nr","clustered_nr","swissprot","ebi"])
def test_untagged_overlay_cannot_suppress_typed_store(tmp_path, channel):
    write(tmp_path/"blastp_online/BGC001_online_blastp.csv", [dict(query_bgc="BGC001",locus_tag="ctg1_1",channel="",blastp_accession="UNKNOWN")])
    write(tmp_path/f"blastp_{channel}/BGC001_top10.csv", [dict(bgc_id="BGC001",gene="ctg1_1",subject_acc="TYPED",pct_identity="60")])
    m=build_gene_roster(tmp_path, strain_id="SYNTHETIC")
    assert m["bgcs"][0]["genes"][0]["channels"][channel]["acc"]=="TYPED"
    assert m["channels_present"]==[channel]
