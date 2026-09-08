from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from mamey.interactive_figures import bigscape_extension as module  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE run (id INTEGER PRIMARY KEY,label TEXT,config_hash TEXT,cutoffs TEXT,input_dir TEXT,output_dir TEXT,mibig_version TEXT);
        CREATE TABLE gbk (id INTEGER PRIMARY KEY,path TEXT,organism TEXT,description TEXT);
        CREATE TABLE bgc_record (id INTEGER PRIMARY KEY,gbk_id INTEGER,product TEXT);
        CREATE TABLE family (id INTEGER PRIMARY KEY,cutoff REAL,bin_label TEXT,run_id INTEGER);
        CREATE TABLE bgc_record_family (record_id INTEGER,family_id INTEGER);
        INSERT INTO run VALUES (1,'selected','cfg-one','0.3,0.5,0.7','in','out','3.1');
        INSERT INTO run VALUES (2,'other','cfg-two','0.5','in2','out2',NULL);
        INSERT INTO gbk VALUES (1,'/job/AS-74_NODE_1.region001.gbk','.', 'NODE_1');
        INSERT INTO gbk VALUES (2,'/job/AS-747_NODE_2.region001.gbk','.', 'NODE_2');
        INSERT INTO gbk VALUES (3,'/refs/BGC0000001.gbk','MIBiG','reference');
        INSERT INTO gbk VALUES (4,'/job/AS-74_NODE_3.region001.gbk','.', 'NODE_3');
        INSERT INTO bgc_record VALUES (1,1,'NRPS');
        INSERT INTO bgc_record VALUES (2,2,'NRPS');
        INSERT INTO bgc_record VALUES (3,3,'NRPS');
        INSERT INTO bgc_record VALUES (4,4,'terpene');
        INSERT INTO family VALUES (10,0.5,'NRPS',1);
        INSERT INTO family VALUES (11,0.7,'other',1);
        INSERT INTO family VALUES (20,0.5,'other',2);
        INSERT INTO bgc_record_family VALUES (1,10);
        INSERT INTO bgc_record_family VALUES (2,10);
        INSERT INTO bgc_record_family VALUES (3,10);
        INSERT INTO bgc_record_family VALUES (4,11);
        INSERT INTO bgc_record_family VALUES (4,20);
        """
    )
    connection.commit()
    connection.close()


def _bridge(path: Path) -> None:
    path.write_text(
        "strain\tbgc_id\tlocator\tbgc_class\tboundary_state\thost_cohort\n"
        "AS-74\tBGC001\tNODE_1.region001\tNRPS\tInterior\tbee\n"
        "AS-747\tBGC002\tNODE_2.region001\tNRPS\tEdge\twasp\n"
        "AS-74\tBGC003\tNODE_3.region001\tterpene\tFull-contig\tbee\n",
        encoding="utf-8",
    )


def _leads(path: Path) -> None:
    path.write_text(
        "strain\tbgc_id\tlocator\tlead_state\n"
        "AS-74\tBGC001\tNODE_1.region001\tDECLARED_LEAD\n",
        encoding="utf-8",
    )


class BigscapeFigureFactoryExtensionTests(unittest.TestCase):
  def setUp(self):
    self._temporary = tempfile.TemporaryDirectory()
    self.tmp_path = Path(self._temporary.name)

  def tearDown(self):
    self._temporary.cleanup()

  def test_sqlite_eight_family_render_is_read_only_and_exact(self):
    tmp_path = self.tmp_path
    database = tmp_path / "fixture.db"
    _db(database)
    bridge = tmp_path / "bridge.tsv"
    ledger = tmp_path / "leads.tsv"
    _bridge(bridge)
    _leads(ledger)
    before = _hash(database)
    receipt = module.render_bigscape_extension(
        tmp_path / "out", bigscape_db=database, bigscape_run="1",
        bigscape_cutoffs="0.5,0.7", bgc_bridge=bridge, lead_ledger=ledger,
    )
    self.assertEqual(_hash(database), before)
    self.assertEqual(receipt["status"], "PASS")
    self.assertEqual(receipt["extension_ids"], list(module.EXTENSION_IDS))
    self.assertEqual(receipt["core_registry_contract"], "UNCHANGED_200")
    self.assertEqual(len(receipt["figures"]), 8)
    self.assertEqual(len({item["svg_sha256"] for item in receipt["figures"]}), 8)
    self.assertEqual(receipt["reconciliation"]["exact_bridge_matches"], 3)
    self.assertEqual(receipt["reconciliation"]["exact_lead_matches"], 1)
    text = (tmp_path / "out" / "gcf-str_plotted_data.csv").read_text()
    self.assertIn("AS-74", text)
    self.assertIn("AS-747", text)
    self.assertIn("AS-74,", text)  # AS-74 remains separate; it is not selected from AS-747.
    source = json.loads((tmp_path / "out" / "gcf-ovr_source.json").read_text())
    self.assertEqual(source["run_receipt"]["database_run_pk"], 1)
    self.assertEqual(source["run_receipt"]["sqlite_mode"], "mode=ro; PRAGMA query_only=ON")


  def test_anchor_state_is_exact_run_and_never_calls_mibig_absence_novel(self):
    tmp_path = self.tmp_path
    database = tmp_path / "fixture.db"
    _db(database)
    source = module.load_bigscape_db(database, run_id="1", cutoffs=(0.5, 0.7))
    family10 = [m for m in source.memberships if m.family_id == "10"]
    family11 = [m for m in source.memberships if m.family_id == "11"]
    self.assertTrue(family10 and all(m.mibig_anchor_state == "EXACT_RUN_MIBIG_PRESENT" for m in family10))
    self.assertTrue(family11 and all(m.mibig_anchor_state == "NO_EXACT_RUN_MIBIG_ANCHOR" for m in family11))
    self.assertNotIn("NOVEL", json.dumps([m.__dict__ for m in source.memberships]))


  def test_missing_cutoff_and_ambiguous_run_fail_closed(self):
    tmp_path = self.tmp_path
    database = tmp_path / "fixture.db"
    _db(database)
    with self.assertRaisesRegex(ValueError, "cutoffs absent"):
        module.load_bigscape_db(database, run_id="1", cutoffs=(0.3,))
    with self.assertRaisesRegex(ValueError, "RUN_ID_INVALID"):
        module.load_bigscape_db(database, run_id="selected", cutoffs=(0.5,))


  def test_portable_table_requires_matching_manifest_and_preserves_unavailable(self):
    tmp_path = self.tmp_path
    table = tmp_path / "families.tsv"
    table.write_text(
        "cutoff\tfamily_id\trun_id\tnormalized_cutoff\tqualified_family_id\tgcf_namespace\tn_strains\tstrains\tn_members\tbin\tdominant_product\tcontains_MIBiG\tmembers_locators\n"
        "0.5\t10\t1\t0.5\tbigscape-gcf:v1/run/1/cutoff/0.5/family/10\trun_id=1;cutoff=0.5\t2\tAS-74,AS-747\t2\tNRPS\tNRPS\tno\tAS-74:NODE_1.region001;AS-747:NODE_2.region001\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "RUN_MANIFEST.json"
    manifest.write_text(json.dumps({
        "run_id": "1", "configuration": {"gcf_cutoffs": "0.3,0.5,0.7"},
        "inputs": {"input_set_sha256": "abc"}, "tool": {"id": "bigscape"},
    }), encoding="utf-8")
    with self.assertRaisesRegex(ValueError, "RUN_ID_MISMATCH"):
        module.load_portable_table(table, run_id="2", cutoffs=(0.5,), run_manifest=manifest)
    receipt = module.render_bigscape_extension(
        tmp_path / "out", bigscape_tsv=table, bigscape_run="1",
        bigscape_cutoffs="0.5", run_manifest=manifest,
    )
    availability = (tmp_path / "out" / "gcf-avl_plotted_data.csv").read_text()
    boundary = (tmp_path / "out" / "gcf-bnd_plotted_data.csv").read_text()
    self.assertIn("UNPLACED_DENOMINATOR_UNAVAILABLE", availability)
    self.assertIn("UNAVAILABLE_NO_EXACT_BRIDGE", boundary)
    self.assertEqual(receipt["reconciliation"]["exact_bridge_matches"], 0)


  def test_bridge_requires_full_exact_key_and_is_one_to_one(self):
    tmp_path = self.tmp_path
    bad = tmp_path / "bad.tsv"
    bad.write_text("strain\tlocator\nAS-74\tNODE_1.region001\n", encoding="utf-8")
    with self.assertRaisesRegex(ValueError, "missing required exact-key"):
        module._bridge(bad)
    duplicate = tmp_path / "dup.tsv"
    duplicate.write_text(
        "strain\tbgc_id\tlocator\tbgc_class\tboundary_state\thost_cohort\n"
        "AS-74\tBGC001\tNODE_1.region001\tNRPS\tInterior\tbee\n"
        "AS-74\tBGC999\tNODE_1.region001\tNRPS\tEdge\tbee\n",
        encoding="utf-8",
    )
    with self.assertRaisesRegex(ValueError, "not one-to-one"):
        module._bridge(duplicate)


  def test_every_figure_has_data_caption_source_and_checksum_sidecars(self):
    tmp_path = self.tmp_path
    database = tmp_path / "fixture.db"
    _db(database)
    out = tmp_path / "out"
    receipt = module.render_bigscape_extension(
        out, bigscape_db=database, bigscape_run="1", bigscape_cutoffs="0.5,0.7",
    )
    for figure in receipt["figures"]:
        for key in ("svg", "plotted_data", "caption_methods", "source_sidecar"):
            self.assertTrue((out / figure[key]).is_file())
    checksums = (out / "SHA256SUMS.tsv").read_text()
    self.assertIn("BIGSCAPE_EXTENSION_QA_RECEIPT.json", checksums)
    self.assertTrue((out / receipt["visual_qa_entry_point"]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
