from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mamey.stage2_overlay import build, sha256_file


POLICY = {
    "expected_reviewed_loci": 1,
    "required_disposition_modules": {"PRELIMINARY_MODE_B", "V7_LITERATURE_ATLAS"},
    "allowed_review_roles": {"scientific checkpoint output"},
}


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


class Stage2OverlayTests(unittest.TestCase):
    def preflight(self, fixture: dict) -> dict:
        return fixture["source_preflight"]

    def refresh_manifest_row(self, fixture: dict, filename: str) -> None:
        with fixture["manifest"].open() as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        artifact = fixture["review"] / filename
        for row in rows:
            if row["path"] == filename:
                row["sha256"] = sha256_file(artifact)
                row["bytes"] = str(artifact.stat().st_size)
        write_tsv(fixture["manifest"], rows)

    def fixture(self, root: Path) -> dict:
        base = root / "base"; base.mkdir()
        report = base / "reports/x.md"; report.parent.mkdir(); report.write_text("# exact base\n")
        index = [{
            "strain": "AS-X", "primary_user_locator": "NODE_1 / region001",
            "source_scoped_bgc_alias": "BGC001", "assembly_sha256": "a" * 64,
            "region_key": "REGION_test", "report_path": "reports/x.md",
            "report_sha256": sha256_file(report),
        }]
        write_tsv(base / "REPORT_INDEX.tsv", index)
        write_tsv(base / "REPORT_MODULE_STATUS.tsv", [{"state": "base"}])
        (base / "REPORT_PROGRAM_MANIFEST.json").write_text(json.dumps({
            "portable_resolution_receipt": {
                "source_discovery_preflight": {
                    "status": "PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND"
                }
            }
        }) + "\n")
        profile_table = base / "tables/AS-X/NODE_1/region001/exact_region_profile_calls.tsv"
        profile_table.parent.mkdir(parents=True)
        write_tsv(profile_table, [{
            "profile": "relaxed", "region_id": "region001",
            "archive_sha256": "c" * 64, "embedded_assembly_sha256": "a" * 64,
        }])
        review = root / "review"; review.mkdir()
        analysis = review / "analysis.tsv"
        analysis_row = {
            "strain": "AS-X", "primary_user_locator": "NODE_1 / region001",
            "source_scoped_bgc_alias": "BGC001", "assembly_sha256": "a" * 64,
            "exact_region_key": "REGION_test", "current_bgc_class": "PKS",
            "current_cds_denominator": "3", "exact_profile_call_basis": "relaxed",
            "machinery_domain_architecture": "KS/AT/ACP capacity.",
            "observed_blastp_channels": "nr observed; receipt unbound.",
            "mibig_kcb_interpretation": "Family context only.",
            "clusterblast_interpretation": "Topology context only.",
            "biosynthetic_logic_and_routing_hypothesis": "PKS capacity hypothesis.",
            "alternatives_counterevidence_and_holds": "Product unresolved.",
            "paragraph_disposition_recommendation": "REVISE named product.",
            "claim_ceiling": "Similarity is not identity; capacity is not production.",
        }
        write_tsv(analysis, [analysis_row])
        disposition = review / "disposition.tsv"
        disposition_row = {
            "strain": "AS-X", "primary_user_locator": "NODE_1 / region001",
            "source_scoped_bgc_alias": "BGC001", "assembly_sha256": "a" * 64,
            "exact_region_key": "REGION_test", "module": "PRELIMINARY_MODE_B",
            "disposition": "REVISE", "recommendation": "Remove product identity.",
            "claim_ceiling": analysis_row["claim_ceiling"],
        }
        v7_row = dict(disposition_row)
        v7_row.update({"module": "V7", "recommendation": "Retain comparator context only."})
        write_tsv(disposition, [disposition_row, v7_row])
        artifact = review / "children.tsv"; artifact.write_text("query\tsubject\nq\ts\n")
        target = review / "target.tsv"
        write_tsv(target, [{
            "strain": "AS-X", "primary_user_locator": "NODE_1 / region001",
            "source_scoped_bgc_alias": "BGC001",
            "module_type": "MIBIG_KCB_COMPARATOR_CHILDREN",
            "module_state": "PRELIMINARY_SOURCE_BOUND_QUERY_AND_RUN_RECEIPTS_UNBOUND",
            "artifact_path": "children.tsv", "artifact_sha256": sha256_file(artifact),
            "claim_ceiling": analysis_row["claim_ceiling"],
        }])
        manifest = review / "ARTIFACT_MANIFEST.tsv"
        rows = []
        for path in [analysis, disposition, artifact]:
            rows.append({
                "path": path.name, "role": "scientific checkpoint output",
                "sha256": sha256_file(path), "bytes": str(path.stat().st_size),
                "status": "PRESENT_HASH_BOUND",
            })
        write_tsv(manifest, rows)
        catalog = review / "source_catalog.json"
        catalog.write_text(json.dumps({
            "schema_version": "sapote-source-discovery-catalog-v1",
            "status": "PASS_COMPLETE",
            "root_id": "REVIEW_ROOT",
            "collections": [{
                "collection_id": "COLLECTION_REVIEW",
                "collection_type": "SCIENTIFIC_REVIEW",
                "relative_path": ".",
                "strain_keys_observed": ["AS-X"],
            }],
        }) + "\n")
        decisions = review / "source_decisions.tsv"
        write_tsv(decisions, [{
            "collection_id": "COLLECTION_REVIEW", "decision": "CONSUME",
            "reason": "", "evidence_receipt": "",
        }])
        source_preflight = {
            "source_discovery_catalog": catalog,
            "expected_source_discovery_catalog_sha256": sha256_file(catalog),
            "source_discovery_decisions": decisions,
            "expected_source_discovery_decisions_sha256": sha256_file(decisions),
            "required_collection_types": {"SCIENTIFIC_REVIEW"},
        }
        return {"base": base, "review": review, "analysis": analysis,
                "disposition": disposition, "target": target, "manifest": manifest,
                "source_preflight": source_preflight}

    def test_builds_additive_locator_first_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            result = build(
                base_report_root=f["base"], target_ledger=f["target"],
                expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                **POLICY, **self.preflight(f),
            )
            self.assertEqual(result["reviewed_loci"], 1)
            module = out / "modules/AS-X/NODE_1/region001/scientific_reconciliation.md"
            self.assertIn("NODE_1 / region001", module.read_text())
            self.assertIn("Similarity is not identity", module.read_text())
            with (out / "MODULE_STATE_DELTA.tsv").open() as handle:
                delta = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual({row["module_type"] for row in delta}, {
                "MIBIG_KCB_COMPARATOR_CHILDREN", "PARAGRAPH_DISPOSITION",
            })
            self.assertEqual(json.loads((out / "OVERLAY_MANIFEST.json").read_text())["counts"]["reviewed_loci"], 1)
            self.assertIn("NODE_1 / region001", (out / "INDEX.md").read_text())
            with (out / "REVIEW_INDEX.tsv").open() as handle:
                review_index = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(review_index[0]["base_report_sha256"], sha256_file(f["base"] / "reports/x.md"))
            self.assertEqual(review_index[0]["reconciliation_state"], "PROPOSAL_SOURCE_BOUND_NOT_ACCEPTED")
            self.assertTrue((out / review_index[0]["profile_table_link"]).resolve().is_file())
            with (out / "MODULE_STATE_DELTA.tsv").open() as handle:
                portable_delta = list(csv.DictReader(handle, delimiter="\t"))
            self.assertTrue(all((out / row["artifact_link"]).resolve().is_file() for row in portable_delta))
            counts = json.loads((out / "OVERLAY_MANIFEST.json").read_text())["counts"]
            self.assertEqual(counts["overlay_coverage_state"], "PARTIAL_1_OF_1")

    def test_upstream_base_without_source_preflight_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            (f["base"] / "REPORT_PROGRAM_MANIFEST.json").write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "UPSTREAM_BASE_PREFLIGHT_UNBOUND"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]],
                    out_root=out, **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_alias_mismatch_is_held_metadata_not_a_second_locus(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["analysis"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["source_scoped_bgc_alias"] = "BGC999"
            write_tsv(f["analysis"], rows)
            self.refresh_manifest_row(f, "analysis.tsv")
            result = build(
                base_report_root=f["base"], target_ledger=f["target"],
                expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]],
                out_root=out, **POLICY, **self.preflight(f),
            )
            self.assertEqual(result["reviewed_loci"], 1)
            with (out / "REVIEW_INDEX.tsv").open() as handle:
                review = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(
                review[0]["source_alias_relation_state"],
                "SOURCE_ALIAS_MISMATCH_HELD_METADATA_ONLY",
            )

    def test_assembly_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            with f["analysis"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["assembly_sha256"] = "c" * 64; write_tsv(f["analysis"], rows)
            # Keep the source manifest truthful so the identity gate is the failure.
            with f["manifest"].open() as handle:
                mrows = list(csv.DictReader(handle, delimiter="\t"))
            for row in mrows:
                if row["path"] == "analysis.tsv":
                    row["sha256"] = sha256_file(f["analysis"])
                    row["bytes"] = str(f["analysis"].stat().st_size)
            write_tsv(f["manifest"], mrows)
            with self.assertRaisesRegex(ValueError, "Assembly mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]],
                    out_root=Path(tmp) / "out", **POLICY, **self.preflight(f),
                )

    def test_source_manifest_drift_fails_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            f["analysis"].write_text(f["analysis"].read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "(?:byte|hash) mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_unmanifested_review_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            unbound = f["review"] / "unbound-analysis.tsv"
            unbound.write_bytes(f["analysis"].read_bytes())
            with self.assertRaisesRegex(ValueError, "not admitted by source manifest"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[unbound], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_base_report_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            (f["base"] / "reports/x.md").write_text("# drifted base\n")
            with self.assertRaisesRegex(ValueError, "Base report hash mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_coverage_above_100_requires_explicit_hold_and_blank_usable_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            artifact = f["review"] / "children.tsv"
            write_tsv(artifact, [{
                "query": "q", "subject": "s", "pct_coverage": "120.6",
                "usable_pct_coverage": "120.6", "coverage_state": "OBSERVED",
            }])
            with f["target"].open() as handle:
                targets = list(csv.DictReader(handle, delimiter="\t"))
            targets[0]["artifact_sha256"] = sha256_file(artifact); write_tsv(f["target"], targets)
            with f["manifest"].open() as handle:
                manifest = list(csv.DictReader(handle, delimiter="\t"))
            for row in manifest:
                if row["path"] == "children.tsv":
                    row["sha256"] = sha256_file(artifact); row["bytes"] = str(artifact.stat().st_size)
            write_tsv(f["manifest"], manifest)
            with self.assertRaisesRegex(ValueError, "Coverage above 100 is not quarantined"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_usable_coverage_above_100_fails_even_when_raw_coverage_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            artifact = f["review"] / "children.tsv"
            write_tsv(artifact, [{
                "query": "q", "subject": "s", "pct_coverage": "99",
                "usable_pct_coverage": "120", "coverage_state": "OBSERVED",
            }])
            with f["target"].open() as handle:
                targets = list(csv.DictReader(handle, delimiter="\t"))
            targets[0]["artifact_sha256"] = sha256_file(artifact); write_tsv(f["target"], targets)
            self.refresh_manifest_row(f, "children.tsv")
            with self.assertRaisesRegex(ValueError, "Usable coverage above 100"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_disposition_assembly_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["disposition"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["assembly_sha256"] = "d" * 64; write_tsv(f["disposition"], rows)
            self.refresh_manifest_row(f, "disposition.tsv")
            with self.assertRaisesRegex(ValueError, "Disposition assembly mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_disposition_region_key_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["disposition"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["exact_region_key"] = "REGION_wrong"; write_tsv(f["disposition"], rows)
            self.refresh_manifest_row(f, "disposition.tsv")
            with self.assertRaisesRegex(ValueError, "Disposition exact region-key mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_direct_named_production_prose_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["analysis"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["biosynthetic_logic_and_routing_hypothesis"] = "The strain produces vancomycin."
            write_tsv(f["analysis"], rows); self.refresh_manifest_row(f, "analysis.tsv")
            with self.assertRaisesRegex(ValueError, "Claim-unsafe or foreign structural content"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_second_locator_heading_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["analysis"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["paragraph_disposition_recommendation"] += "\n## NODE_2 / region001"
            write_tsv(f["analysis"], rows); self.refresh_manifest_row(f, "analysis.tsv")
            with self.assertRaisesRegex(ValueError, "Claim-unsafe or foreign structural content"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_missing_required_disposition_module_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["disposition"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            write_tsv(f["disposition"], rows[:1])
            with f["manifest"].open() as handle:
                manifest = list(csv.DictReader(handle, delimiter="\t"))
            for row in manifest:
                if row["path"] == "disposition.tsv":
                    row["sha256"] = sha256_file(f["disposition"])
                    row["bytes"] = str(f["disposition"].stat().st_size)
            write_tsv(f["manifest"], manifest)
            with self.assertRaisesRegex(ValueError, "Required disposition module set mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_manifested_input_with_unapproved_role_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["manifest"].open() as handle:
                manifest = list(csv.DictReader(handle, delimiter="\t"))
            for row in manifest:
                if row["path"] == "analysis.tsv":
                    row["role"] = "untrusted prose"
            write_tsv(f["manifest"], manifest)
            with self.assertRaisesRegex(ValueError, "Review input role is not allowed"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_declared_reviewed_locus_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            policy = dict(POLICY); policy["expected_reviewed_loci"] = 2
            with self.assertRaisesRegex(ValueError, "Reviewed-locus count mismatch"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **policy, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_foreign_compact_card_in_review_content_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["analysis"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["paragraph_disposition_recommendation"] += "\n### 3.9 BGC999 — foreign card"
            write_tsv(f["analysis"], rows)
            with f["manifest"].open() as handle:
                manifest = list(csv.DictReader(handle, delimiter="\t"))
            for row in manifest:
                if row["path"] == "analysis.tsv":
                    row["sha256"] = sha256_file(f["analysis"])
                    row["bytes"] = str(f["analysis"].stat().st_size)
            write_tsv(f["manifest"], manifest)
            with self.assertRaisesRegex(ValueError, "Claim-unsafe or foreign structural content"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())

    def test_raw_mode_b_template_marker_in_review_content_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp)); out = Path(tmp) / "out"
            with f["analysis"].open() as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["paragraph_disposition_recommendation"] += (
                "\n<!-- MODE B TEMPLATE | bgc: BGC999 | node: NODE_999 | strain: AS-Y -->"
            )
            write_tsv(f["analysis"], rows)
            with f["manifest"].open() as handle:
                manifest = list(csv.DictReader(handle, delimiter="\t"))
            for row in manifest:
                if row["path"] == "analysis.tsv":
                    row["sha256"] = sha256_file(f["analysis"])
                    row["bytes"] = str(f["analysis"].stat().st_size)
            write_tsv(f["manifest"], manifest)
            with self.assertRaisesRegex(ValueError, "Claim-unsafe or foreign structural content"):
                build(
                    base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **self.preflight(f),
                )
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
