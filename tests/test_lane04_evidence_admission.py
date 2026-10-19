"""Evidence freshness and MIBiG admission regressions using synthetic observations."""
import sqlite3
import unittest
from mamey.mode_b import availability
from mamey.mode_b import mibig_evidence_adapter as adapter


class AvailabilityFreshness(unittest.TestCase):
    def observation(self, binding, freshness, source):
        return availability.EvidenceObservation(
            channel="blastp_per_gene", source_label="synthetic", source_path=source,
            source_sha256="a" * 64, source_bytes=1, strain="TEST-1", bgc="BGC001",
            full_node="ctg1", region="region001", binding_state=binding,
            freshness_state=freshness,
        )

    def test_current_unbound_does_not_refresh_stale_exact(self):
        rows = [self.observation("EXACT_LOCUS", "STALE", "old"),
                self.observation("UNBOUND", "CURRENT", "conflicting")]
        self.assertEqual(availability._best_state(rows), ("EXACT_LOCUS", 2, "STALE"))

    def test_promotion_held_for_stale_bound_plus_current_conflict(self):
        locus = availability.InventoryLocus("TEST-1", "BGC001", "ctg1", "region001",
                                            "TEST-1 / ctg1 / region001 / BGC001")
        rows = [self.observation("EXACT_LOCUS", "STALE", "old"),
                self.observation("UNBOUND", "CURRENT", "conflicting")]
        result, _, _ = availability.build_availability([locus], rows, availability.load_contract())
        self.assertEqual(result[0]["promotion_gate"], "HOLD_BLASTP_FRESHNESS_UNVERIFIED")

    def test_current_alias_cannot_refresh_exact_cohort(self):
        rows = [self.observation("EXACT_LOCUS", "STALE", "old"),
                self.observation("ALIAS_BOUND", "CURRENT", "alias")]
        self.assertEqual(availability._best_state(rows), ("EXACT_LOCUS", 2, "STALE"))

    def test_current_at_same_binding_still_eligible(self):
        for binding in ("EXACT_LOCUS", "ALIAS_BOUND"):
            with self.subTest(binding=binding):
                rows = [self.observation(binding, "STALE", "old"),
                        self.observation(binding, "CURRENT", "current")]
                self.assertEqual(availability._best_state(rows), (binding, 2, "CURRENT"))

    def test_no_source_and_unknown_freshness_stay_unknown(self):
        self.assertEqual(availability._best_state([]), ("ABSENT", 0, "UNVERIFIED"))
        self.assertEqual(availability._best_state([
            self.observation("EXACT_LOCUS", "UNVERIFIED", "unknown")
        ]), ("EXACT_LOCUS", 1, "UNVERIFIED"))


class MibigChannelIntegrity(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        self.con.executescript("""
        CREATE TABLE locus(locus_key TEXT,strain TEXT,full_contig TEXT,region TEXT,bgc_alias TEXT);
        INSERT INTO locus VALUES ('l1','TEST-1','ctg1','region001','BGC001');
        CREATE TABLE gene(gene_key TEXT,locus_key TEXT,locus_tag TEXT,gene_order INTEGER,protein_sha256 TEXT);
        CREATE TABLE gene_channel_state(gene_key TEXT,locus_key TEXT,state TEXT,hit_row_count INTEGER);
        CREATE TABLE mibig_hit(gene_key TEXT,reference_binding_state TEXT);
        INSERT INTO gene VALUES ('g1','l1','gene1',1,'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb');
        INSERT INTO gene VALUES ('g2','l1','gene2',2,'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc');
        INSERT INTO gene_channel_state VALUES ('g1','l1','MIBIG_HIT_OBSERVED',1);
        INSERT INTO gene_channel_state VALUES ('g2','l1','NO_MIBIG_HIT_REPORTED_IN_CURRENT_PACKAGE',0);
        INSERT INTO mibig_hit VALUES ('g1','BOUND_EXISTING_REFERENCE_PRODUCT');
        """)

    def tearDown(self):
        self.con.close()

    def read(self, roster=None):
        return adapter.gene_first_rows(
            self.con, "a" * 64, strain="TEST-1", full_node="ctg1", region="region001",
            bgc_alias="BGC001", protein_roster=roster if roster is not None else
            {"gene1": "b" * 64, "gene2": "c" * 64},
        )

    def test_valid_observed_and_missing_preserved(self):
        rows = self.read()
        self.assertEqual([row["evidence_state"] for row in rows], ["BOUND", "MISSING"])
        self.assertIn("not biological absence", rows[1]["note"])
        self.assertIn("not exact product identity", rows[0]["note"])

    def test_unbound_reference_hit_retained_as_qualified_observation(self):
        self.con.execute("UPDATE mibig_hit SET reference_binding_state='OBSERVED_UNBOUND_ALIGNMENT_NOT_IN_REFERENCE_PRODUCT'")
        row = self.read()[0]
        self.assertEqual(row["evidence_state"], "BOUND")
        self.assertIn('"OBSERVED_UNBOUND_ALIGNMENT_NOT_IN_REFERENCE_PRODUCT": 1', row["note"])
        self.assertIn("not exact product identity", row["note"])

    def test_failed_search_never_becomes_missing(self):
        self.con.execute("UPDATE gene_channel_state SET state='PARSE_FAILED' WHERE gene_key='g2'")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "channel state"):
            self.read()

    def test_unrun_search_never_becomes_missing(self):
        self.con.execute("UPDATE gene_channel_state SET state='NOT_RUN' WHERE gene_key='g2'")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "channel state"):
            self.read()

    def test_positive_count_without_hits_never_becomes_bound(self):
        self.con.execute("DELETE FROM mibig_hit")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "hit count"):
            self.read()

    def test_zero_count_with_hits_never_becomes_missing(self):
        self.con.execute("UPDATE gene_channel_state SET hit_row_count=0 WHERE gene_key='g1'")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "hit count"):
            self.read()

    def test_negative_count_rejected(self):
        self.con.execute("UPDATE gene_channel_state SET hit_row_count=-1 WHERE gene_key='g2'")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "hit count"):
            self.read()

    def test_missing_state_row_cannot_hide_gene(self):
        self.con.execute("DELETE FROM gene_channel_state WHERE gene_key='g2'")
        with self.assertRaises(adapter.MibigExtensionHold):
            self.read({"gene1": "b" * 64})

    def test_missing_state_with_complete_roster_held(self):
        self.con.execute("DELETE FROM gene_channel_state WHERE gene_key='g2'")
        with self.assertRaises(adapter.MibigExtensionHold):
            self.read()

    def test_duplicate_state_cannot_duplicate_gene(self):
        self.con.execute("INSERT INTO gene_channel_state SELECT * FROM gene_channel_state WHERE gene_key='g1'")
        with self.assertRaises(adapter.MibigExtensionHold):
            self.read()

    def test_channel_state_wrong_locus_held(self):
        self.con.execute("UPDATE gene_channel_state SET locus_key='other' WHERE gene_key='g1'")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "channel locus"):
            self.read()

    def test_contradictory_observation_state_held(self):
        self.con.execute("UPDATE gene_channel_state SET state='NO_MIBIG_HIT_REPORTED_IN_CURRENT_PACKAGE' WHERE gene_key='g1'")
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "channel state"):
            self.read()

    def test_protein_hash_mismatch_held(self):
        with self.assertRaisesRegex(adapter.MibigExtensionHold, "protein hash"):
            self.read({"gene1": "d" * 64, "gene2": "c" * 64})


