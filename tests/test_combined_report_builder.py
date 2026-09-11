from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "mamey" / "combined_report_builder.py"
SPEC = importlib.util.spec_from_file_location("candidate_combined_report_builder", MODULE)
assert SPEC and SPEC.loader
CRB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CRB
SPEC.loader.exec_module(CRB)

ASSEMBLY = "a" * 64
EVIDENCE_SHA = "b" * 64
IDENTITY = {
    "subject_id": "SAMPLE-001",
    "assembly_sha256": ASSEMBLY,
    "node_id": "NODE_7_length_42000_cov_44.500000",
    "region_id": "region001",
    "exact_region_key": "REGION_GENERIC_001",
    "source_alias": "BGC007",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start) + len(start))].rstrip() + "\n"


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_fixture(root: Path, excluded: bool = False, foreign_second_card: bool = False) -> tuple[dict, dict[str, Path]]:
    source = root / "source"
    source.mkdir()
    current_report = source / "base_report.md"
    current_text = (
        "# P357-015 fixture\n\n"
        f"## Locus 1: `{IDENTITY['node_id']} / {IDENTITY['region_id']}`\n\n"
        "- Exact region key: `REGION_GENERIC_001`\n"
        "- Exact current architecture: two biosynthetic blocks require separate interpretation.\n\n"
        "### Exact gene and domain architecture\n\n"
        "`geneA` contains a current MGT/glycosyltransferase-family domain.\n\n"
        "## Literature evidence\n\nNone selected.\n"
    )
    current_report.write_text(current_text, encoding="utf-8")
    identity_ledger = source / "exact_identity_ledger.tsv"
    write_tsv(identity_ledger, [
        "region_key", "strain", "assembly_sha256", "node_id", "source_region_ids", "identity_state"
    ], [{
        "region_key": IDENTITY["exact_region_key"], "strain": IDENTITY["subject_id"],
        "assembly_sha256": ASSEMBLY, "node_id": IDENTITY["node_id"],
        "source_region_ids": IDENTITY["region_id"], "identity_state": "EXACT_SEQUENCE_COORDINATE_BOUND",
    }])
    base_manifest = source / "report_manifest.json"
    base_manifest.write_text(json.dumps({
        "schema_version": "sapote_refreshable_bgc_report_v1",
        "strain": IDENTITY["subject_id"],
        "region_keys": [IDENTITY["exact_region_key"]],
        "outputs": [
            {"path": current_report.name, "sha256": digest(current_report), "bytes": current_report.stat().st_size},
            {"path": identity_ledger.name, "sha256": digest(identity_ledger), "bytes": identity_ledger.stat().st_size},
        ],
    }, indent=2) + "\n", encoding="utf-8")

    locus_map = source / "locus_map.svg"
    locus_map.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="120">'
        '<rect width="700" height="120" fill="#fffaf0"/><path d="M40 60h250l25-15v30l-25-15" fill="#0f766e"/>'
        '<path d="M350 60h250l25-15v30l-25-15" fill="#d4a72c"/><text x="40" y="25">Exact generic locus map</text></svg>\n',
        encoding="utf-8",
    )
    v7 = source / "v7.md"
    v7_text = "# V7 fixture\n\n## Preserved literature context\n\nFamily-level literature context remains hypothesis-generating.\n\n## V7 provenance\n"
    v7.write_text(v7_text, encoding="utf-8")
    mode_b = source / "mode_b.md"
    mode_b_text = (
        "# Preliminary Mode B fixture\n\n"
        f"## Exact occurrence {IDENTITY['node_id']} / {IDENTITY['region_id']}\n\n"
        "## Retained scientific assessment\n\n"
        "The inherited card called geneA a RiPP maturation protein; current structured evidence supersedes that role.\n"
    )
    if foreign_second_card:
        mode_b_text += "\n## Foreign compact card NODE_99_length_9999_cov_9.000000 / region002\n"
    mode_b_text += "\n## Mode B provenance\n"
    mode_b.write_text(mode_b_text, encoding="utf-8")

    channel_fields = [
        "assembly_sha256", "node_id", "region_id", "exact_region_key", "gene_id", "channel",
        "top_hit_label", "accession", "pct_identity", "query_coverage", "evidence_state",
        "sequence_binding_state", "source_logical_uri", "source_sha256",
    ]
    nr = source / "nr.tsv"
    clustered = source / "clusterednr.tsv"
    common = {
        "assembly_sha256": ASSEMBLY, "node_id": IDENTITY["node_id"],
        "region_id": IDENTITY["region_id"], "exact_region_key": IDENTITY["exact_region_key"],
        "gene_id": "geneA", "pct_identity": "72.4", "query_coverage": "98.0",
        "evidence_state": "OBSERVED_RESULT", "sequence_binding_state": "BOUND_EXACT_SUBMITTED_QUERY_SHA256",
        "source_logical_uri": "evidence://blastp-run/geneA", "source_sha256": EVIDENCE_SHA,
    }
    write_tsv(nr, channel_fields, [{**common, "channel": "nr", "top_hit_label": "glycosyltransferase", "accession": "NR_A"}])
    write_tsv(clustered, channel_fields, [{**common, "channel": "ClusteredNR", "top_hit_label": "MGT family protein", "accession": "CNR_A"}])

    role = source / "roles.tsv"
    role_fields = [
        "assembly_sha256", "node_id", "region_id", "exact_region_key", "gene_id",
        "current_role", "inherited_role", "disposition", "support_state", "claim_ceiling",
    ]
    write_tsv(role, role_fields, [{
        "assembly_sha256": ASSEMBLY, "node_id": IDENTITY["node_id"], "region_id": IDENTITY["region_id"],
        "exact_region_key": IDENTITY["exact_region_key"], "gene_id": "geneA",
        "current_role": "MGT/glycosyltransferase-family", "inherited_role": "RiPP maturation protein",
        "disposition": "SUPERSEDED", "support_state": "CURRENT_STRUCTURED_DOMAIN_SUPPORT",
        "claim_ceiling": "capacity only",
    }])

    overmerge = source / "overmerge.tsv"
    over_fields = [
        "assembly_sha256", "node_id", "region_id", "exact_region_key", "system_count_state",
        "system_count", "block_id", "block_class", "boundary_start_gene", "boundary_end_gene",
        "boundary_start_nt", "boundary_end_nt", "evidence_state", "reason_code",
        "source_logical_uri", "source_sha256",
    ]
    base_over = {
        "assembly_sha256": ASSEMBLY, "node_id": IDENTITY["node_id"], "region_id": IDENTITY["region_id"],
        "exact_region_key": IDENTITY["exact_region_key"], "system_count_state": "OBSERVED_STRUCTURED",
        "system_count": "2", "evidence_state": "CURRENT_STRUCTURED_BOUNDARIES",
        "reason_code": "TWO_DOMAIN_ARCHITECTURE_BLOCKS", "source_logical_uri": "evidence://overmerge/generic",
        "source_sha256": EVIDENCE_SHA,
    }
    write_tsv(overmerge, over_fields, [
        {**base_over, "block_id": "BLOCK_A", "block_class": "phenazine-like capacity", "boundary_start_gene": "geneA", "boundary_end_gene": "geneB", "boundary_start_nt": "100", "boundary_end_nt": "12000"},
        {**base_over, "block_id": "BLOCK_B", "block_class": "glycosylated-polyketide-like capacity", "boundary_start_gene": "geneC", "boundary_end_gene": "geneD", "boundary_start_nt": "15000", "boundary_end_nt": "39000"},
    ])

    rescue = source / "rescue.tsv"
    rescue_fields = [
        "left_assembly_sha256", "left_node_id", "left_region_id", "left_exact_region_key",
        "right_assembly_sha256", "right_node_id", "right_region_id", "right_exact_region_key",
        "candidate_family", "rggmci_state", "comparator_evidence_state", "expert_adjudication_state",
        "physical_join_state", "claim_ceiling", "source_logical_uri", "source_sha256",
    ]
    write_tsv(rescue, rescue_fields, [{
        "left_assembly_sha256": ASSEMBLY, "left_node_id": IDENTITY["node_id"],
        "left_region_id": IDENTITY["region_id"], "left_exact_region_key": IDENTITY["exact_region_key"],
        "right_assembly_sha256": ASSEMBLY, "right_node_id": "NODE_11_length_18000_cov_45.000000",
        "right_region_id": "region001", "right_exact_region_key": "REGION_GENERIC_002",
        "candidate_family": "generic glycosylated aromatic rescue candidate", "rggmci_state": "PAIR_CANDIDATE",
        "comparator_evidence_state": "CLASS_LEVEL_CONVERGENCE", "expert_adjudication_state": "CANDIDATE_SUPPORTED",
        "physical_join_state": "PHYSICAL_JOIN_NOT_ESTABLISHED", "claim_ceiling": "family candidate only",
        "source_logical_uri": "evidence://rescue/generic", "source_sha256": EVIDENCE_SHA,
    }])
    policy = source / "policy.json"
    policy.write_text(json.dumps({
        "schema_version": "sapote-combined-report-owner-policy-v1",
        "excluded_subjects": [IDENTITY["subject_id"]] if excluded else [],
        "single_file_event_bytes": 100_000_000,
        "cumulative_event_bytes": 500_000_000,
    }, indent=2) + "\n", encoding="utf-8")

    items: list[tuple[str, str, Path, str, dict]] = [
        ("base_manifest", "P357015_REPORT_MANIFEST", base_manifest, "ADMITTED_EXACT_CURRENT", {}),
        ("base_report", "P357015_REPORT_MARKDOWN", current_report, "ADMITTED_EXACT_CURRENT", {
            "start_anchor": f"## Locus 1: `{IDENTITY['node_id']} / {IDENTITY['region_id']}`",
            "end_anchor": "## Literature evidence",
            "selected_sha256": hashlib.sha256(selected(current_text, f"## Locus 1: `{IDENTITY['node_id']} / {IDENTITY['region_id']}`", "## Literature evidence").encode()).hexdigest(),
        }),
        ("identity", "P357015_EXACT_IDENTITY_LEDGER", identity_ledger, "ADMITTED_EXACT_CURRENT", {}),
        ("map", "LOCUS_MAP_ASSET", locus_map, "ADMITTED_EXACT_CURRENT", {}),
        ("v7", "V7_MARKDOWN", v7, "PRESERVED_HISTORICAL", {
            "start_anchor": "## Preserved literature context", "end_anchor": "## V7 provenance",
            "selected_sha256": hashlib.sha256(selected(v7_text, "## Preserved literature context", "## V7 provenance").encode()).hexdigest(),
        }),
        ("modeb", "MODE_B_MARKDOWN", mode_b, "PRESERVED_HISTORICAL", {
            "start_anchor": f"## Exact occurrence {IDENTITY['node_id']} / {IDENTITY['region_id']}",
            "end_anchor": "## Mode B provenance",
            "selected_sha256": hashlib.sha256(selected(mode_b_text, f"## Exact occurrence {IDENTITY['node_id']} / {IDENTITY['region_id']}", "## Mode B provenance").encode()).hexdigest(),
        }),
        ("nr", "PER_GENE_CHANNEL_TABLE", nr, "STRUCTURED_CURRENT", {"channel": "nr"}),
        ("clustered", "PER_GENE_CHANNEL_TABLE", clustered, "STRUCTURED_CURRENT", {"channel": "ClusteredNR"}),
        ("roles", "GENE_ROLE_DISPOSITIONS", role, "STRUCTURED_CURRENT", {}),
        ("overmerge", "OVERMERGE_SPLIT_EVIDENCE", overmerge, "STRUCTURED_CURRENT", {}),
        ("rescue", "CROSS_CONTIG_RESCUE_EVIDENCE", rescue, "STRUCTURED_CURRENT", {}),
    ]
    sources = []
    for source_id, role_name, path, state, extra in items:
        sources.append({
            "source_id": source_id, "role": role_name, "root_id": "FIXTURE",
            "relative_path": path.relative_to(source).as_posix(),
            "logical_uri": f"evidence://fixture/{source_id}", "sha256": digest(path),
            "bytes": path.stat().st_size, "admission_state": state, "identity": IDENTITY, **extra,
        })
    sources.append({
        "source_id": "policy", "role": "OWNER_POLICY", "root_id": "FIXTURE",
        "relative_path": policy.name, "logical_uri": "evidence://fixture/policy",
        "sha256": digest(policy), "bytes": policy.stat().st_size, "admission_state": "OWNER_POLICY_CURRENT",
    })
    job = {
        "schema_version": "sapote-combined-v7-modeb-job-v1",
        "identity": IDENTITY,
        "report_name": "SAMPLE-001_combined_v7_modeb_report.md",
        "sources": sources,
    }
    return job, {"FIXTURE": source}


class CombinedReportBuilderTests(unittest.TestCase):
    def test_combines_map_channels_roles_overmerge_and_rescue(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job, roots = make_fixture(root)
            out = root / "out"
            manifest = CRB.build(job, roots, out)
            report = (out / "SAMPLE-001_combined_v7_modeb_report.md").read_text(encoding="utf-8")
            self.assertEqual(manifest["semantic_state"], "MIXED_MULTI_SYSTEM_BUT_CLASS_CONSISTENT")
            self.assertEqual((out / "assets/locus_map.svg").read_bytes(), (roots["FIXTURE"] / "locus_map.svg").read_bytes())
            self.assertIn("| `nr` | `geneA` |", report)
            self.assertIn("| `ClusteredNR` | `geneA` |", report)
            self.assertIn("MGT/glycosyltransferase-family", report)
            self.assertIn("`SUPERSEDED`", report)
            self.assertIn("`BLOCK_A`", report)
            self.assertIn("`BLOCK_B`", report)
            self.assertIn("PHYSICAL_JOIN_NOT_ESTABLISHED", report)
            self.assertIn("## Preserved V7 literature and context", report)
            self.assertIn("## Retained Mode B scientific sections", report)

    def test_exact_locator_mismatch_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job, roots = make_fixture(root)
            job["sources"][0]["identity"] = {**IDENTITY, "node_id": "NODE_7_length_42000_cov_44"}
            out = root / "out"
            with self.assertRaisesRegex(ValueError, "Exact locator mismatch"):
                CRB.build(job, roots, out)
            self.assertFalse(out.exists())

    def test_second_mode_b_card_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job, roots = make_fixture(root, foreign_second_card=True)
            out = root / "out"
            with self.assertRaisesRegex(ValueError, "MODE_B_REQUIRES_EXACTLY_ONE_LOCATOR_HEADING"):
                CRB.build(job, roots, out)
            self.assertFalse(out.exists())

    def test_owner_exclusion_emits_no_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job, roots = make_fixture(root, excluded=True)
            out = root / "out"
            receipt = CRB.build(job, roots, out)
            self.assertEqual(receipt["status"], "EXCLUDED_NO_OUTPUT")
            self.assertFalse(out.exists())


def emit_example(destination: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        job, roots = make_fixture(root)
        CRB.build(job, roots, destination)


if __name__ == "__main__":
    example = os.environ.get("COMBINED_REPORT_EXAMPLE_ROOT")
    if example:
        emit_example(Path(example))
    unittest.main()

