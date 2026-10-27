import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools/ranked_match_shortlist.py"
spec = importlib.util.spec_from_file_location("ranked_shortlist", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
IDENTITY = "AS-1 / NODE_1_length_12000_cov_30.5 / region001 / BGC001"


def raw(rank, ref=None, selected="False", **more):
    return {"identity": IDENTITY, "run": "/saved/runA", "selected": selected, "rank": str(rank) if rank is not None else "",
            "mibig": ref or "BGC" + str(rank).zfill(7), "name": "reference annotation", "distinct_query_genes": "4",
            "distinct_reference_genes": "5", "median_identity": "51.5", "cumulative_blast_score": "1200", **more}


class RankedMatchShortlist(unittest.TestCase):
    def rows(self, values):
        return mod.normalize(values, "SAVED_KNOWNCLUSTERBLAST")

    def project(self, rows, selected="BGC0000001", policy=None):
        return mod.project(rows, {(IDENTITY, "/saved/runA"): {"selected_reference": selected}}, policy or {})

    def test_preserves_saved_rank_not_gene_count_or_identity(self):
        records = self.rows([raw(2, distinct_query_genes="20", median_identity="99"), raw(1, selected="True", distinct_query_genes="2")])
        g = self.project(records)[0]
        self.assertEqual([r["saved_rank"] for r in g["top3"]["rows"]], [1, 2])
        self.assertEqual(g["top3"]["rows"][0]["distinct_AS_genes_matched"], 2)

    def test_same_reference_across_runs_remains_separate(self):
        records = self.rows([raw(1, selected="True"), raw(1, selected="True", run="/saved/runB")])
        groups = self.project(records)
        self.assertEqual(len(groups), 2)
        self.assertEqual([len(g["all_source_rows"]) for g in groups], [1, 1])

    def test_evidence_channels_are_in_group_identity(self):
        records = self.rows([raw(1, selected="True"), raw(2)])
        records[1]["evidence_channel"] = "SEPARATE_TEST_CHANNEL"
        self.assertEqual(len(self.project(records)), 2)

    def test_top_three_boundary_ties_retained(self):
        records = self.rows([raw(1, selected="True"), raw(2), raw(3), raw(3, ref="BGC0000999"), raw(5)])
        g = self.project(records)[0]
        self.assertEqual(len(g["top3"]["rows"]), 4)
        self.assertEqual(g["top3"]["state"], "SAVED_ORDER_WITH_BOUNDARY_TIES")
        self.assertEqual(g["top3"]["rows"][2]["same_saved_rank_count"], 2)

    def test_gene_count_tie_does_not_expand_native_rank_window(self):
        records = self.rows([raw(i, selected="True" if i == 1 else "False") for i in range(1, 8)])
        g = self.project(records)[0]
        self.assertEqual(len(g["top3"]["rows"]), 3)
        self.assertEqual(g["top3"]["rows"][0]["same_AS_gene_count_candidate_count"], 7)

    def test_original_selection_retained_outside_top_five(self):
        records = self.rows([raw(i, selected="True" if i == 7 else "False") for i in range(1, 8)])
        g = self.project(records, "BGC0000007")[0]
        self.assertEqual(g["retained_original_selection"][0]["saved_rank"], 7)
        self.assertNotIn("BGC0000007", [r["reference_id"] for r in g["top5"]["rows"]])

    def test_duplicate_ref_within_context_holds_not_silently_deduplicates(self):
        records = self.rows([raw(1, selected="True"), raw(2, ref="BGC0000001")])
        g = self.project(records)[0]
        self.assertIn("DUPLICATE_REFERENCE_ROWS_WITHIN_CONTEXT", g["holds"])
        self.assertEqual(g["top3"]["state"], "BLOCKED_BY_SOURCE_HOLD")
        self.assertEqual(len(g["all_source_rows"]), 2)

    def test_unknown_denominators_and_coverage_are_null(self):
        row = self.rows([raw(1)])[0]
        self.assertIsNone(row["query_gene_denominator"])
        self.assertIsNone(row["reference_gene_denominator"])
        self.assertIsNone(row["alignment_coverage_rule"])

    def test_missing_measurements_not_zero(self):
        row = self.rows([raw(1, distinct_query_genes="", distinct_reference_genes="", median_identity="", cumulative_blast_score="")])[0]
        for key in ["distinct_AS_genes_matched", "distinct_reference_subjects_matched", "median_identity_pct", "cumulative_BLAST_score_saved"]:
            self.assertIsNone(row[key])

    def test_unranked_evidence_retained_separately(self):
        g = self.project(self.rows([raw(None, ref="BGC0000001", selected="True")]))[0]
        self.assertEqual(g["top3"]["state"], "SAVED_RANK_UNAVAILABLE")
        self.assertEqual(len(g["unranked_rows"]), 1)

    def test_selection_metadata_disagreement_holds_shortlist(self):
        g = self.project(self.rows([raw(1, selected="True")]), "BGC0000999")[0]
        self.assertIn("ORIGINAL_SELECTION_SOURCE_MISMATCH", g["holds"])
        self.assertEqual(g["top5"]["rows"], [])

    def test_absent_original_selected_reference_not_invented(self):
        g = self.project(self.rows([raw(1)]), "BGC0000999")[0]
        self.assertIn("ORIGINAL_SELECTION_NOT_IN_SAVED_RANKING", g["holds"])
        self.assertEqual(g["original_selection_from_run_metadata"], "BGC0000999")
        self.assertEqual(g["retained_original_selection"], [])

    def test_intentional_paired_policy_kept_per_run(self):
        records = self.rows([raw(1, selected="True"), raw(2, selected="True", run="/saved/runB")])
        policy = {(IDENTITY, "/saved/runA"): {"selected_reference": "BGC0000001", "selection_policy_state": "EXPLICIT_PAIRED_COMPARATORS_IN_SOURCE_SCRIPT"}}
        groups = self.project(records, policy=policy)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["selection_policy_snapshot"]["selection_policy_state"], "EXPLICIT_PAIRED_COMPARATORS_IN_SOURCE_SCRIPT")

    def test_incomplete_locus_identity_holds(self):
        g = self.project(self.rows([raw(1, identity="AS-1 / BGC001")]))[0]
        self.assertIn("COMPLETE_LOCUS_IDENTITY_HOLD", g["holds"])

    def test_rejects_cross_channel_mislabelling(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_CHANNEL_MISMATCH"):
            self.rows([raw(1, evidence_channel="DIAMOND")])

    def test_invalid_measurements_rejected(self):
        for field, value in [("median_identity", "101"), ("rank", "0"), ("distinct_query_genes", "1.5"), ("median_identity", "nan")]:
            with self.assertRaises(ValueError):
                self.rows([raw(1, **{field: value})] if field != "rank" else [raw(value)])

    def test_duplicate_source_columns_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_COLUMNS"):
            mod.table(b"identity\tidentity\nA\tB\n", {"identity"})

    def test_source_pin_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "source.tsv"
            p.write_text("actual bytes")
            with self.assertRaisesRegex(ValueError, "SOURCE_HASH_MISMATCH"):
                mod.pinned(Path(td), {"path": p.name, "sha256": "0" * 64})

    def test_duplicate_run_metadata_rejected(self):
        row = {"identity": IDENTITY, "run": "/saved/runA"}
        with self.assertRaisesRegex(ValueError, "DUPLICATE_RUN_METADATA"):
            mod.indexed_metadata([row, row])

    def test_html_escapes_annotations_and_no_external_script(self):
        groups = self.project(self.rows([raw(1, selected="True", name='<script src="https://bad.example/x.js"></script>')]))
        rendered = mod.render({"groups": groups, "state": "TEST", "method": "saved rank only", "limits": []})
        self.assertNotIn("<script", rendered)
        self.assertIn("&lt;script", rendered)


if __name__ == "__main__":
    unittest.main()
