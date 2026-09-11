"""Tests for fetch_reference_cluster (v9.7.302) — synthetic sqlite DB, no network.

Builds a tiny BiG-SCAPE-shaped DB (gbk/cds/hsp), reconstructs a cluster GBK, and checks that
CDS + Pfam-derived /gene labels come through (the annotation improvement over hand reconstruction).
"""
import importlib.util, sqlite3
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "fetch_reference_cluster.py"


def _load():
    pytest.importorskip("Bio")
    spec = importlib.util.spec_from_file_location("frc", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _make_db(path):
    c = sqlite3.connect(path)
    c.executescript(
        "CREATE TABLE gbk(id INTEGER PRIMARY KEY, path TEXT);"
        "CREATE TABLE cds(id INTEGER PRIMARY KEY, gbk_id INT, nt_start INT, nt_stop INT,"
        " strand INT, aa_seq TEXT, orf_num INT);"
        "CREATE TABLE hsp(id INTEGER PRIMARY KEY, cds_id INT, accession TEXT, bit_score REAL);")
    c.execute("INSERT INTO gbk(id,path) VALUES(1,'/x/BGC0000877.gbk')")
    seqs = ["MKTAYIAKQRQISFVKSHFS", "MPQLAFDIGFFAELPKLQPPV", "MSDNKQTLVRALKAGDLTAAE"]
    for i, aa in enumerate(seqs, 1):
        c.execute("INSERT INTO cds(id,gbk_id,nt_start,nt_stop,strand,aa_seq,orf_num) "
                  "VALUES(?,1,?,?,1,?,?)", (i, i * 1000, i * 1000 + 60, aa, i))
    # gene 1 -> radical SAM (PF04055), gene 2 -> aminotransferase (PF00155), gene 3 -> unknown Pfam
    c.execute("INSERT INTO hsp(cds_id,accession,bit_score) VALUES(1,'PF04055',200)")
    c.execute("INSERT INTO hsp(cds_id,accession,bit_score) VALUES(2,'PF00155',180)")
    c.execute("INSERT INTO hsp(cds_id,accession,bit_score) VALUES(3,'PF99999',150)")
    c.commit(); c.close()


def test_ref_from_db_reconstructs_with_pfam_labels(tmp_path):
    m = _load()
    db = tmp_path / "syn.db"; _make_db(db)
    genes = m.ref_from_db(str(db), "BGC0000877", "polyoxin")
    assert len(genes) == 3
    assert genes[0]["gene"] == "radical_SAM"        # PF04055 mapped
    assert genes[1]["gene"] == "aminotransferase"   # PF00155 mapped
    assert genes[2]["gene"] == "PF99999"            # unmapped -> raw accession (never blank)
    assert all(g["aa"] for g in genes)


def test_genes_to_gbk_writes_labelled_gbk(tmp_path):
    m = _load()
    db = tmp_path / "syn.db"; _make_db(db)
    genes = m.ref_from_db(str(db), "BGC0000877", "polyoxin")
    p, n, n_annot = m.genes_to_gbk(genes, "polyoxin", str(tmp_path))
    assert n == 3 and n_annot == 3
    txt = Path(p).read_text()
    assert 'gene="radical_SAM"' in txt
    assert 'locus_tag="polyoxin_1"' in txt


def test_missing_accession_raises(tmp_path):
    m = _load()
    db = tmp_path / "syn.db"; _make_db(db)
    with pytest.raises(KeyError):
        m.ref_from_db(str(db), "NOT_IN_DB", "x")
