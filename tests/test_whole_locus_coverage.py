import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("coverage", Path(__file__).parents[1] / "tools" / "whole_locus_coverage.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
IDENTITY = "DEMO / NODE_1_length_5000_cov_20 / region001 / BGC001"


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "saved_alignment.txt"
        self.source.write_text("operator supplied test evidence\n")
        self.genes = [{"identity": IDENTITY, "locus_tag": str(i), "protein_sha256": str(i) * 64,
                       "source_role": "biosynthetic" if i == 1 else ""} for i in (1, 2)]

    def edge(self, gene="1", **kwargs):
        return {"identity": IDENTITY, "locus_tag": gene, "protein_sha256": gene * 64,
                "state": "MATCHED", "scope": "FOCAL_REGION", "reference_id": "R1", "reference_gene_id": "r1",
                "evidence_path": str(self.source), "evidence_sha256": mod.sha(self.source), **kwargs}

    def test_no_evidence_is_unexamined_not_no_hit(self):
        _, s = mod.audit(self.genes)
        self.assertEqual(s["evidence_states"], {"UNEXAMINED": 2})
        self.assertIsNone(s["reference_genes_denominator"])

    def test_missing_supplied_table_is_missing(self):
        _, s = mod.audit(self.genes, evidence_requested=True)
        self.assertEqual(s["evidence_states"], {"MISSING_EVIDENCE": 2})

    def test_distinct_query_and_reference_denominators(self):
        _, s = mod.audit(self.genes, [self.edge(), self.edge(), self.edge(reference_gene_id="r2")],
                         [{"reference_id": "R1", "reference_gene_id": "r" + str(i)} for i in (1, 2, 3)])
        self.assertEqual(s["references"]["R1"], {"distinct_supplied_AS_genes_matched": 1,
            "distinct_reference_genes_matched": 2, "supplied_reference_gene_denominator": 3})
        self.assertEqual(s["evidence_states"], {"MATCHED": 1, "UNEXAMINED": 1})

    def test_split_external_candidates_never_count_as_focal_matches(self):
        _, s = mod.audit(self.genes, [self.edge(scope="SPLIT_CANDIDATE"), self.edge(scope="OUTSIDE_REGION_CANDIDATE")])
        self.assertEqual(s["evidence_states"], {"CANDIDATE_ONLY": 1, "UNEXAMINED": 1})
        self.assertEqual(s["distinct_supplied_matched_reference_genes"], 0)
        with self.assertRaises(ValueError):
            mod.audit(self.genes, [self.edge(scope="SPLIT_CANDIDATE", state="SEARCHED_NO_HIT")])

    def test_explicit_searched_no_hit(self):
        _, s = mod.audit(self.genes, [self.edge(state="SEARCHED_NO_HIT", reference_id="", reference_gene_id="")])
        self.assertEqual(s["evidence_states"]["SEARCHED_NO_HIT"], 1)

    def test_conflicting_states_hold(self):
        _, s = mod.audit(self.genes, [self.edge(), self.edge(state="SEARCHED_NO_HIT")])
        self.assertEqual(s["evidence_states"]["EVIDENCE_HOLD"], 1)
        self.assertEqual(s["distinct_supplied_matched_reference_genes"], 0)

    def test_changed_evidence_bytes_hold(self):
        e = self.edge()
        self.source.write_text("changed")
        rows, s = mod.audit(self.genes, [e])
        self.assertEqual(rows[0]["evidence_state"], "EVIDENCE_HOLD")
        self.assertIn("SOURCE_HASH_HOLD", rows[0]["reason"])

    def test_missing_evidence_not_no_hit(self):
        e = self.edge()
        self.source.unlink()
        rows, s = mod.audit(self.genes, [e])
        self.assertEqual(rows[0]["evidence_state"], "MISSING_EVIDENCE")

    def test_changed_protein_hold(self):
        rows, _ = mod.audit(self.genes, [self.edge(protein_sha256="x" * 64)])
        self.assertEqual(rows[0]["evidence_state"], "EVIDENCE_HOLD")

    def test_malformed_matching_pins_never_admit_match(self):
        for malformed in ("x", "x" * 64, "a" * 63, "a" * 65, "", "a" * 63 + " "):
            with self.subTest(malformed=malformed):
                genes = [{**self.genes[0], "protein_sha256": malformed}]
                rows, s = mod.audit(genes, [self.edge(protein_sha256=malformed)])
                self.assertEqual(rows[0]["evidence_state"], "EVIDENCE_HOLD")
                self.assertEqual(s["distinct_supplied_matched_reference_genes"], 0)
        rows, _ = mod.audit(self.genes, [self.edge(evidence_sha256="x" * 64)])
        self.assertIn("SOURCE_HASH_HOLD", rows[0]["reason"])

    def test_malformed_region_and_unknown_alias_hold(self):
        for region in ("regionblah", "region1", "region001extra", "region001 "):
            bad_identity = IDENTITY.replace("region001", region)
            with self.subTest(region=region), self.assertRaisesRegex(ValueError, "IDENTITY_HOLD"):
                mod.audit([{**self.genes[0], "identity": bad_identity}])
        for alias in ("BGCunknown", "BGC", "BGC001extra"):
            with self.subTest(alias=alias), self.assertRaisesRegex(ValueError, "IDENTITY_HOLD"):
                mod.audit([{**self.genes[0], "identity": IDENTITY.replace("BGC001", alias)}])

    def test_identity_and_duplicate_inventory_fail(self):
        with self.assertRaises(ValueError): mod.audit(self.genes + [self.genes[0]])
        with self.assertRaises(ValueError): mod.audit([{**self.genes[0], "identity": "AS-1 / BGC001"}])

    def test_unknown_gene_and_reference_fail_closed(self):
        with self.assertRaises(ValueError): mod.audit(self.genes, [self.edge(gene="3")])
        rows, _ = mod.audit(self.genes, [self.edge()], [{"reference_id": "R1", "reference_gene_id": "different"}])
        self.assertEqual(rows[0]["evidence_state"], "EVIDENCE_HOLD")

    def test_exclusion_requires_reason_and_is_visible(self):
        with self.assertRaises(ValueError): mod.audit(self.genes, [self.edge(state="EXCLUDED")])
        rows, _ = mod.audit(self.genes, [self.edge(state="EXCLUDED", reason="producer filter")])
        self.assertEqual(rows[0]["evidence_state"], "EXCLUDED")


if __name__ == "__main__": unittest.main()
