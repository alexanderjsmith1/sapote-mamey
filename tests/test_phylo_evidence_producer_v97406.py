from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mamey.phylo_evidence import (
    PHYLO_EVIDENCE_SCHEMA,
    PhyloEvidenceError,
    produce_phylo_evidence_receipt,
)
from mamey.phylogeny_figure_factory import json_object, validate_signoff


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path):
    run = tmp_path / "amber_phylo" / "demo"
    run.mkdir(parents=True)
    tree = run / "iqtree.treefile"
    tree.write_text("(('Nocardia farcinica QUERY-01':0.1,'Nocardia nova DSM-44481':0.1)90/99:0.2,Rhodococcus_erythropolis_GCF_017656525.1:0.3);\n")
    alignment = run / "Aligned_SCGs.faa"
    alignment.write_text(">Nocardia_farcinica_QUERY-01\nAAAA\n>Nocardia_nova_DSM-44481\nAAAA\n>Rhodococcus_erythropolis_GCF_017656525.1\nAAAA\n")
    gtotree = _write_json(run / "gtotree.json", {
        "tool_name": "GToTree", "tool_version": "2.0.0", "tool_sha256": "1" * 64})
    iqtree = _write_json(run / "iqtree.json", {
        "tool_name": "IQ-TREE", "tool_version": "3.1.2", "tool_sha256": "2" * 64})
    marker = _write_json(run / "marker.json", {
        "name": "Actinomycetota", "count": 92, "sha256": "3" * 64})
    registry = run / "outgroup_registry.tsv"
    registry.write_text(
        "tree_scope\tingroup_taxon\tfamily\toutgroup_genus\toutgroup_species_strain\tassembly_accession\tstatus\trationale\n"
        "genus\tNocardia\tNocardiaceae\tRhodococcus\tRhodococcus erythropolis\tGCF_017656525.1\tLOCKED\tsister genus\n")
    dedup = run / "reference_dedup.tsv"
    dedup.write_text("action\tspecies\nkept\tnocardia farcinica\nkept\tnocardia nova\n")
    flags = run / "assembly_quality_flags.tsv"
    flags.write_text(
        "tree_tip\tassembly_quality_flag\tdetail\n"
        "Nocardia farcinica QUERY-01\tPASS\tcomplete\nNocardia nova DSM-44481\tWARN\tfragmented\n"
        "Rhodococcus_erythropolis_GCF_017656525.1\tPASS\ttype reference\n")
    package = run / "packages" / "query"
    package.mkdir(parents=True)
    manifest = package / "manifest.json"
    manifest.write_text(json.dumps({"strain_id": "QUERY-01"}), encoding="utf-8")
    hosts = run / "hosts.tsv"
    hosts.write_text("strain_id\thost\nQUERY-01\tgoverned synthetic host\n", encoding="utf-8")
    crosswalk = run / "package_tree_crosswalk.tsv"
    crosswalk.write_text(
        "tree_tip\trole\tstrain_id\tpackage_manifest\tpackage_manifest_sha256\thost_label\thost_provenance\n"
        f"Nocardia farcinica QUERY-01\tPACKAGE\tQUERY-01\tpackages/query/manifest.json\t{_sha(manifest)}\t\t\n"
        "Nocardia nova DSM-44481\tREFERENCE\tDSM-44481\t\t\t\t\n"
        "Rhodococcus erythropolis GCF 017656525.1\tREFERENCE\tGCF 017656525.1\t\t\t\t\n")
    return {"tree": tree, "alignment": alignment, "gtotree_receipt": gtotree,
            "iqtree_receipt": iqtree, "marker_set_receipt": marker,
            "outgroup_tip": "Rhodococcus_erythropolis_GCF_017656525.1",
            "outgroup_registry": registry, "ingroup_taxon": "Nocardia", "tree_scope": "genus",
            "reference_dedup": dedup, "assembly_quality_flags": flags,
            "package_tree_crosswalk": crosswalk, "host_table": hosts}


def test_producer_and_consumer_share_schema_and_exact_hashes(tmp_path):
    values = _fixture(tmp_path)
    receipt_path = produce_phylo_evidence_receipt(**values)
    receipt = json.loads(receipt_path.read_text())
    assert receipt["schema_version"] == PHYLO_EVIDENCE_SCHEMA
    assert receipt["tree_sha256"] == _sha(values["tree"])
    assert receipt["alignment_sha256"] == _sha(values["alignment"])
    assert receipt["reference_dedup"]["state"] == "ONE_PER_SPECIES"
    assert receipt["package_tree_join"]["rows"][0]["canonical_tip"] == "Nocardia farcinica QUERY-01"
    assert receipt["package_tree_join"]["rows"][0]["host_provenance"] == "AUTHORITATIVE_TABLE"
    assert receipt["support"] == {"label": "SH-aLRT/UFBoot", "node_count": 1,
                                  "sh_alrt_min": 90.0, "ufboot_min": 99.0,
                                  "weak_node_count": 0}
    validated = validate_signoff(
        json_object(receipt_path, "signoff"), values["tree"], values["alignment"],
        values["outgroup_tip"], "signoff")
    assert validated["n_tips"] == 3
    assert validated["gtotree"]["version"] == "2.0.0"
    assert validated["package_tree_join"]["row_count"] == 3
    assert validated["package_tree_join"]["package_count"] == 1


def test_producer_builds_no_tree_and_refuses_overwrite(tmp_path):
    values = _fixture(tmp_path)
    before = values["tree"].read_bytes()
    produce_phylo_evidence_receipt(**values)
    assert values["tree"].read_bytes() == before
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_EVIDENCE_RECEIPT_EXISTS"


def test_missing_support_and_incomplete_assembly_flags_fail_closed(tmp_path):
    values = _fixture(tmp_path)
    values["tree"].write_text("('Nocardia farcinica QUERY-01':0.1,Rhodococcus_erythropolis_GCF_017656525.1:0.3);\n")
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_SUPPORT_MISSING"

    values = _fixture(tmp_path / "second")
    values["assembly_quality_flags"].write_text("tree_tip\tassembly_quality_flag\nQuery\tPASS\n")
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_ASSEMBLY_FLAGS_INCOMPLETE"


def test_join_types_pi_word_only_and_rejects_noncanonical_or_ambiguous_tips(tmp_path):
    values = _fixture(tmp_path)
    values["host_table"].write_text("strain_id\thost\nOTHER-01\tsynthetic host\n", encoding="utf-8")
    text = values["package_tree_crosswalk"].read_text(encoding="utf-8")
    values["package_tree_crosswalk"].write_text(
        text.replace("\t\t\nNocardia nova", "\tPI supplied synthetic host\tPI_WORD_ONLY\nNocardia nova", 1),
        encoding="utf-8",
    )
    receipt = json.loads(produce_phylo_evidence_receipt(**values).read_text(encoding="utf-8"))
    assert receipt["package_tree_join"]["rows"][0]["host_provenance"] == "PI_WORD_ONLY"

    values = _fixture(tmp_path / "bad")
    values["tree"].write_text("((QUERY-01:0.1,'Nocardia nova DSM-44481':0.1)90/99:0.2,Rhodococcus_erythropolis_GCF_017656525.1:0.3);\n")
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_TIP_LABEL_INVALID"


def test_xlsx_duplicate_headers_require_explicit_column_selector(tmp_path):
    from openpyxl import Workbook

    values = _fixture(tmp_path)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Host schema"
    sheet.append(["Strain Name", "Strain Name", "Source Species"])
    sheet.append(["legacy-name", "QUERY-01", "governed synthetic host"])
    host_xlsx = values["host_table"].with_suffix(".xlsx")
    workbook.save(host_xlsx)
    values["host_table"] = host_xlsx
    values["host_sheet"] = "Host schema"
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_HOST_TABLE_AMBIGUOUS"

    values["host_strain_column"] = "B"
    values["host_value_column"] = "C"
    receipt = json.loads(produce_phylo_evidence_receipt(**values).read_text(encoding="utf-8"))
    assert receipt["package_tree_join"]["rows"][0]["host_label"] == "governed synthetic host"


def test_no_reference_dedup_supplied_is_not_recorded_and_does_not_hold(tmp_path):
    # BC2-407: --reference-dedup is the one optional producer input (main()'s argparse
    # never marks it required). Before this test, neither dedup branch that matters for
    # claim-safety -- "no dedup file at all" and "a dedup file that fails to establish
    # one-per-species" -- had ANY test coverage, on a module whose whole reason to exist
    # is closing exactly this class of gap (see memory: phylo-dedup-verify-species-column,
    # a real prior incident in this project -- "one-per-species silently no-op'd"). This
    # pins the CURRENT, intentional behavior as tested fact rather than an unverified
    # assumption: omitting the dedup file entirely is NOT_RECORDED (a scope decision --
    # the operator chose not to run dedup verification for this tree), and NOT_RECORDED
    # does not hold the receipt. If a future reviewer decides NOT_RECORDED should also
    # HOLD, that is a claim-safety policy call for Alex, not something to change quietly
    # by editing this test.
    values = _fixture(tmp_path)
    values["reference_dedup"] = None
    receipt = json.loads(produce_phylo_evidence_receipt(**values).read_text(encoding="utf-8"))
    assert receipt["reference_dedup"] == {
        "state": "NOT_RECORDED", "species_column": "", "rows": 0, "source_sha256": None,
    }
    assert receipt["status"] == "PASS"
    assert "hold_code" not in receipt
    assert receipt["comparator_provenance"]["reference_dedup_state"] == "NOT_RECORDED"


def test_dedup_not_verified_holds_the_receipt(tmp_path):
    # BC2-407: the other, previously-unexercised half of the same gap -- a dedup file
    # that IS supplied but fails to establish the one-per-species invariant (here: no
    # species column at all) must actually HOLD the receipt, not silently PASS. This is
    # the safety-critical branch; before this test it had never been proven to fire.
    values = _fixture(tmp_path)
    values["reference_dedup"].write_text("action\nkept\nkept\n")
    receipt = json.loads(produce_phylo_evidence_receipt(**values).read_text(encoding="utf-8"))
    assert receipt["reference_dedup"]["state"] == "DEDUP_NOT_VERIFIED"
    assert receipt["reference_dedup"]["reason"] == "species_column_missing"
    assert receipt["status"] == "HOLD"
    assert receipt["hold_code"] == "DEDUP_NOT_VERIFIED"
    assert receipt["comparator_provenance"]["reference_dedup_state"] == "DEDUP_NOT_VERIFIED"
