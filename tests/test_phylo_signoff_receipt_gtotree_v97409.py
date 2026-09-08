"""CLAUDE_409_phylo_signoff_receipt — a completed GToTree cohort tree can emit a sign-off
receipt the phylogeny arm accepts.

Two blocks previously stopped ``phylo_evidence.produce_phylo_evidence_receipt`` from ever
succeeding on the real, already-built cohort tree, so the phylogeny Figure Factory arm could
never proceed on a GToTree tree even though the tree exists:

  1. The completed-tree location gate hard-coded the ``amber_phylo`` path token. Nothing in the
     bundle produces an ``amber_phylo`` directory; the real GToTree cohort output lives under
     ``workspace/cohort/phylo_tree/gtotree_out/``. So the producer refused the real tree with
     ``PHYLO_TREE_LOCATION_INVALID``.
  2. ``_support`` only recognised IQ-TREE's slash-joined ``)SH-aLRT/UFBoot:`` form. GToTree
     annotates each node with ONE support value (``)1.000:``), so the producer refused the real
     tree with ``PHYLO_SUPPORT_MISSING``.

These tests bind an already-built (approved) tree under ``phylo_tree/`` carrying single-value
GToTree support, prove a valid PASS receipt is emitted, and prove
``phylogeny_figure_factory.validate_signoff`` admits it (the phylogeny arm proceeds). The producer
still builds no tree and spends no CPU — the tree-approval gate is untouched.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mamey.phylo_evidence import (
    PHYLO_EVIDENCE_SCHEMA,
    PhyloEvidenceError,
    produce_phylo_evidence_receipt,
    _support,
)
from mamey.phylogeny_figure_factory import json_object, validate_signoff


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path, *, support: str = "0.98"):
    # The real completed cohort tree lives under phylo_tree/, NOT amber_phylo/.
    run = tmp_path / "cohort" / "phylo_tree" / "gtotree_out"
    run.mkdir(parents=True)
    tree = run / "gtotree_out.tre"
    # GToTree single-value branch support (")0.98:"), not IQ-TREE's ")90/99:".
    tree.write_text(
        "(('Nocardia farcinica QUERY-01':0.1,'Nocardia nova DSM-44481':0.1)"
        + support
        + ":0.2,Rhodococcus_erythropolis_GCF_017656525.1:0.3);\n"
    )
    alignment = run / "Aligned_SCGs.faa"
    alignment.write_text(
        ">Nocardia_farcinica_QUERY-01\nAAAA\n>Nocardia_nova_DSM-44481\nAAAA\n"
        ">Rhodococcus_erythropolis_GCF_017656525.1\nAAAA\n"
    )
    gtotree = _write_json(run / "gtotree.json", {
        "tool_name": "GToTree", "tool_version": "1.8.6", "tool_sha256": "1" * 64})
    iqtree = _write_json(run / "iqtree.json", {
        "tool_name": "IQ-TREE", "tool_version": "2.3.6", "tool_sha256": "2" * 64})
    marker = _write_json(run / "marker.json", {
        "name": "Actinobacteria", "count": 138, "sha256": "3" * 64})
    registry = run / "outgroup_registry.tsv"
    registry.write_text(
        "tree_scope\tingroup_taxon\tfamily\toutgroup_genus\toutgroup_species_strain\t"
        "assembly_accession\tstatus\trationale\n"
        "genus\tNocardia\tNocardiaceae\tRhodococcus\tRhodococcus erythropolis\t"
        "GCF_017656525.1\tLOCKED\tsister genus\n")
    dedup = run / "reference_dedup.tsv"
    dedup.write_text("action\tspecies\nkept\tnocardia farcinica\nkept\tnocardia nova\n")
    flags = run / "assembly_quality_flags.tsv"
    flags.write_text(
        "tree_tip\tassembly_quality_flag\tdetail\n"
        "Nocardia farcinica QUERY-01\tPASS\tcomplete\n"
        "Nocardia nova DSM-44481\tPASS\tcomplete\n"
        "Rhodococcus_erythropolis_GCF_017656525.1\tPASS\ttype reference\n")
    package = run / "packages" / "query"
    package.mkdir(parents=True)
    manifest = package / "manifest.json"
    manifest.write_text(json.dumps({"strain_id": "QUERY-01"}), encoding="utf-8")
    hosts = run / "hosts.tsv"
    hosts.write_text("strain_id\thost\nQUERY-01\tActinomadura macrotermitis host\n", encoding="utf-8")
    crosswalk = run / "package_tree_crosswalk.tsv"
    crosswalk.write_text(
        "tree_tip\trole\tstrain_id\tpackage_manifest\tpackage_manifest_sha256\t"
        "host_label\thost_provenance\n"
        f"Nocardia farcinica QUERY-01\tPACKAGE\tQUERY-01\tpackages/query/manifest.json\t{_sha(manifest)}\t\t\n"
        "Nocardia nova DSM-44481\tREFERENCE\tDSM-44481\t\t\t\t\n"
        "Rhodococcus erythropolis GCF 017656525.1\tREFERENCE\tGCF 017656525.1\t\t\t\t\n")
    return {"tree": tree, "alignment": alignment, "gtotree_receipt": gtotree,
            "iqtree_receipt": iqtree, "marker_set_receipt": marker,
            "outgroup_tip": "Rhodococcus_erythropolis_GCF_017656525.1",
            "outgroup_registry": registry, "ingroup_taxon": "Nocardia", "tree_scope": "genus",
            "reference_dedup": dedup, "assembly_quality_flags": flags,
            "package_tree_crosswalk": crosswalk, "host_table": hosts}


def test_completed_gtotree_tree_under_phylo_tree_emits_receipt_the_arm_admits(tmp_path):
    """End to end: a completed tree under phylo_tree/ with single-value support yields a valid
    PASS receipt AND validate_signoff admits it, so the phylogeny arm proceeds."""
    values = _fixture(tmp_path)
    receipt_path = produce_phylo_evidence_receipt(**values)  # no PHYLO_TREE_LOCATION_INVALID
    receipt = json.loads(receipt_path.read_text())
    assert receipt["schema_version"] == PHYLO_EVIDENCE_SCHEMA
    assert receipt["status"] == "PASS"
    assert receipt["tree_sha256"] == _sha(values["tree"])
    # GToTree single-value support was accepted and summarised (no slash-pair fabricated).
    assert receipt["support"]["support_format"] == "GTOTREE_SINGLE_VALUE"
    assert receipt["support"]["node_count"] == 1
    assert receipt["support"]["support_min"] == 0.98
    assert receipt["support"]["support_scale"] == "UNIT_0_1"
    assert receipt["support"]["weak_node_count"] == 0
    # The phylogeny arm's admission gate accepts the receipt.
    validated = validate_signoff(
        json_object(receipt_path, "signoff"), values["tree"], values["alignment"],
        values["outgroup_tip"], "signoff")
    assert validated["status"] == "PASS"
    assert validated["n_tips"] == 3
    assert validated["gtotree"]["name"] == "GToTree"


def test_support_regex_accepts_gtotree_single_value_and_scales():
    """The support parser accepts a single value on either scale and stays claim-safe."""
    unit = _support("((A:0.1,B:0.1)0.72:0.2,C:0.3);")
    assert unit["support_format"] == "GTOTREE_SINGLE_VALUE"
    assert unit["support_scale"] == "UNIT_0_1"
    assert unit["support_min"] == 0.72
    assert unit["weak_node_count"] == 1  # 0.72 < 0.80

    percent = _support("((A:0.1,B:0.1)88:0.2,(C:0.1,D:0.1)97:0.2);")
    assert percent["support_scale"] == "PERCENT_0_100"
    assert percent["node_count"] == 2
    assert percent["support_min"] == 88.0
    assert percent["weak_node_count"] == 1  # 88 < 95, 97 passes


def test_iqtree_slash_pair_support_still_wins_and_is_unchanged():
    """Regression: a slash-joined IQ-TREE tree still produces the SH-aLRT/UFBoot summary."""
    pair = _support("(('N f Q':0.1,'N n D':0.1)90/99:0.2,'R e G':0.3);")
    assert pair == {"label": "SH-aLRT/UFBoot", "node_count": 1,
                    "sh_alrt_min": 90.0, "ufboot_min": 99.0, "weak_node_count": 0}


def test_no_support_at_all_still_fails_closed(tmp_path):
    """A tree with no support annotation whatsoever is still refused."""
    with pytest.raises(PhyloEvidenceError) as caught:
        _support("(A:0.1,B:0.2,C:0.3);")
    assert caught.value.code == "PHYLO_SUPPORT_MISSING"

    values = _fixture(tmp_path, support="")  # ")" immediately followed by ":" -> no support token
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_SUPPORT_MISSING"


def test_tree_outside_a_completed_run_directory_is_still_refused(tmp_path):
    """The location gate still rejects an arbitrary path (no amber_phylo/ or phylo_tree/ token)."""
    values = _fixture(tmp_path)
    stray = tmp_path / "loose" / "gtotree_out.tre"
    stray.parent.mkdir(parents=True)
    stray.write_text(values["tree"].read_text(), encoding="utf-8")
    values["tree"] = stray
    with pytest.raises(PhyloEvidenceError) as caught:
        produce_phylo_evidence_receipt(**values)
    assert caught.value.code == "PHYLO_TREE_LOCATION_INVALID"
