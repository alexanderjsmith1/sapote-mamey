"""Full-nr runner lanes reach the hits store as ncbi_nr; other top-10 CSVs keep their channel rule.

nr_rid_runner writes `_STRAINGAP_SINGLE_NR_*/results/**/*_blastp_top10.csv` when RID_DATABASE=nr.
Those CSVs have no channel column. The ingest tool used to skip the lane; the suffix and the lane
folder now imply ncbi_nr / nr. Synthetic CSVs only; never runs BLAST.
"""
import csv
import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import pytest
from mamey.blastp_ingest import BLASTP_HITS_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rollup_full_nr_463", ROOT / "tools/ingest_blastp_rollups.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
FIELDS = ["strain", "gene", "bgc_id", "hit_rank", "subject_acc", "subject_def"]
NR_LANE = "Blastp RESULTS/_STRAINGAP_SINGLE_NR_SOFTWARE/results/SOFTWARE/geneA/geneA_blastp_top10.csv"
OTHER = "Blastp RESULTS/_SOMEWHERE_ELSE/results/SOFTWARE/geneA/geneA_blastp_top10.csv"


def make_store(root):
    db = root / "software.sqlite"
    columns = ",".join(name + " " + kind + (" NOT NULL" if required else "") for name, kind, required in BLASTP_HITS_SCHEMA)
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE hits (" + columns + ")")
    return db


def write_lane(root, relative):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=FIELDS)
    writer.writeheader()
    for rank in (1, 2):
        writer.writerow(dict(strain="SOFTWARE", gene="geneA", bgc_id="software_identity", hit_rank=rank,
                             subject_acc=f"ACC{rank}", subject_def=f"hit {rank}, comma-bearing"))
    path.write_text(text.getvalue(), encoding="utf-8")
    return path


def test_implied_channel_needs_the_nr_lane_folder():
    assert tool._implied_channel(Path(NR_LANE)) == ("ncbi_nr", "nr")
    assert tool._implied_channel(Path(OTHER)) is None
    assert tool._implied_channel(Path("x/_STRAINGAP_SINGLE_CLNR_S/results/g_blastp_top10_clustered.csv")) == (
        "ncbi_clustered_nr", "nr_cluster_seq")


def test_full_nr_lane_rows_are_admitted_as_ncbi_nr(tmp_path, capsys):
    db = make_store(tmp_path)
    path = write_lane(tmp_path, NR_LANE)
    assert tool.main(["--root", str(tmp_path), "--db", str(db), "--execute", "--source-workspace", "software-import"]) == 0
    assert capsys.readouterr().err == ""
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT hit_rank,channel,subject_db,source_file FROM hits ORDER BY hit_rank").fetchall()
    rel = os.path.relpath(path, tmp_path)
    assert rows == [(1, "ncbi_nr", "nr", rel), (2, "ncbi_nr", "nr", rel)]


def test_top10_csv_outside_nr_lane_is_not_globbed(tmp_path, capsys):
    db = make_store(tmp_path)
    write_lane(tmp_path, OTHER)
    assert tool.main(["--root", str(tmp_path), "--db", str(db)]) == 0
    assert "rows to add: 0" in capsys.readouterr().out
