import csv
import hashlib
import json
import sqlite3

import pytest

from mamey.mode_b.mibig_evidence_adapter import (
    MANIFEST_SCHEMA, MibigExtensionHold, gene_first_rows, load_protein_roster, main, open_bound_extension,
    write_gene_first_index,
)


def _database(tmp_path):
    path = tmp_path / "extension.sqlite"
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
    INSERT INTO metadata VALUES ('schema_version','current_mibig_convergence_extension_v1');
    CREATE TABLE reference_dependency(locator TEXT,sha256 TEXT,bytes INTEGER,schema_state TEXT,bulk_rows_copied INTEGER);
    INSERT INTO reference_dependency VALUES ('reference.sqlite','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',1,'EXTERNAL',0);
    CREATE TABLE evidence_state_vocabulary(state TEXT PRIMARY KEY,definition TEXT);
    CREATE TABLE locus(locus_key TEXT PRIMARY KEY,strain TEXT,full_contig TEXT,region TEXT,bgc_alias TEXT);
    INSERT INTO locus VALUES ('l1','TEST-1','NODE_1_length_100_cov_1.1','region001','BGC001');
    INSERT INTO locus VALUES ('l2','TEST-1-ALT','NODE_1_length_100_cov_1.1','region001','BGC001');
    CREATE TABLE gene(gene_key TEXT PRIMARY KEY,locus_key TEXT,locus_tag TEXT,gene_order INTEGER,protein_sha256 TEXT);
    INSERT INTO gene VALUES ('g1','l1','edge_left',1,'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb');
    INSERT INTO gene VALUES ('g2','l1','edge_right',2,'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc');
    CREATE TABLE gene_channel_state(gene_key TEXT,locus_key TEXT,state TEXT,hit_row_count INTEGER);
    INSERT INTO gene_channel_state VALUES ('g1','l1','MIBIG_HIT_OBSERVED',2);
    INSERT INTO gene_channel_state VALUES ('g2','l1','NO_MIBIG_HIT_REPORTED_IN_CURRENT_PACKAGE',0);
    CREATE TABLE mibig_hit(gene_key TEXT,reference_binding_state TEXT);
    INSERT INTO mibig_hit VALUES ('g1','BOUND_EXISTING_REFERENCE_PRODUCT');
    INSERT INTO mibig_hit VALUES ('g1','OBSERVED_UNBOUND_ALIGNMENT_NOT_IN_REFERENCE_PRODUCT');
    """)
    con.executemany("INSERT INTO evidence_state_vocabulary VALUES (?,?)", [(x, x) for x in ("OBSERVED","MISSING","NOT_RUN","UNBOUND","PARSE_FAILED","TESTED_NO_CALL")])
    con.commit(); con.close()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = tmp_path / "dependency.json"
    manifest.write_text(json.dumps({"schema": MANIFEST_SCHEMA, "extension_sha256": digest,
                                    "reference_dependency_sha256": "a" * 64}))
    return path, manifest


def test_boundary_genes_and_missing_state_export(tmp_path):
    db, manifest = _database(tmp_path); con, digest = open_bound_extension(db, manifest)
    rows = gene_first_rows(con, digest, strain="TEST-1", full_node="NODE_1_length_100_cov_1.1",
                           region="region001", bgc_alias="BGC001",
                           protein_roster={"edge_left": "b" * 64, "edge_right": "c" * 64})
    assert [row["gene"] for row in rows] == ["edge_left", "edge_right"]
    assert [row["evidence_state"] for row in rows] == ["BOUND", "MISSING"]
    out = write_gene_first_index(tmp_path / "index.tsv", rows)
    with out.open() as handle:
        assert len(list(csv.DictReader(handle, delimiter="\t"))) == 2


def test_wrong_assembly_fails(tmp_path):
    db, manifest = _database(tmp_path); con, digest = open_bound_extension(db, manifest)
    with pytest.raises(MibigExtensionHold, match="locus does not resolve"):
        gene_first_rows(con, digest, strain="TEST-1", full_node="WRONG", region="region001",
                        bgc_alias="BGC001", protein_roster={})


def test_wrong_protein_fails(tmp_path):
    db, manifest = _database(tmp_path); con, digest = open_bound_extension(db, manifest)
    with pytest.raises(MibigExtensionHold, match="protein hash mismatch"):
        gene_first_rows(con, digest, strain="TEST-1", full_node="NODE_1_length_100_cov_1.1",
                        region="region001", bgc_alias="BGC001",
                        protein_roster={"edge_left": "0" * 64, "edge_right": "c" * 64})


def test_tampered_database_fails(tmp_path):
    db, manifest = _database(tmp_path)
    with db.open("ab") as handle: handle.write(b"tamper")
    with pytest.raises(MibigExtensionHold, match="extension hash mismatch"):
        open_bound_extension(db, manifest)


def test_changed_reference_dependency_fails(tmp_path):
    db, manifest = _database(tmp_path)
    data = json.loads(manifest.read_text()); data["reference_dependency_sha256"] = "d" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(MibigExtensionHold, match="reference hash mismatch"):
        open_bound_extension(db, manifest)


def test_mixed_run_identity_is_not_collapsed(tmp_path):
    db, manifest = _database(tmp_path); con, digest = open_bound_extension(db, manifest)
    with pytest.raises(MibigExtensionHold, match="protein roster gene set mismatch"):
        gene_first_rows(con, digest, strain="TEST-1-ALT", full_node="NODE_1_length_100_cov_1.1",
                        region="region001", bgc_alias="BGC001", protein_roster={"edge_left": "b" * 64})


def test_duplicate_roster_label_cannot_be_hidden(tmp_path):
    roster = tmp_path / "roster.tsv"
    roster.write_text("gene\tprotein_sha256\nedge_left\t" + "b" * 64 + "\nedge_left\t" + "b" * 64 + "\n")
    with pytest.raises(MibigExtensionHold, match="duplicate roster gene"):
        load_protein_roster(roster)


def test_real_cli_entrypoint(tmp_path):
    db, manifest = _database(tmp_path)
    roster = tmp_path / "roster.tsv"
    roster.write_text("gene\tprotein_sha256\nedge_left\t" + "b" * 64 + "\nedge_right\t" + "c" * 64 + "\n")
    out = tmp_path / "index.tsv"
    assert main(["--database", str(db), "--dependency-manifest", str(manifest),
                 "--strain", "TEST-1", "--full-node", "NODE_1_length_100_cov_1.1",
                 "--region", "region001", "--bgc-alias", "BGC001",
                 "--protein-roster", str(roster), "--output", str(out)]) == 0
    assert out.is_file()
