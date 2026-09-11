"""Read-only finished-review request coupling; synthetic identities only."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

from mamey.mode_b_receipt import (
    validate_finished_review_request,
    validate_finished_review_request_command,
)


IDENTITY = "SYNTH-001 / NODE_7_length_12345_cov_20.500000 / region001 / BGC007"
SHA = "a" * 64


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return {"locator": path.relative_to(path.parents[1]).as_posix(), "sha256": _sha(path)}


def _fixture(tmp_path: Path):
    pkg = tmp_path / "package"
    root = tmp_path / "packet"
    pkg.mkdir()
    root.mkdir()
    manifest = {
        "strain_id": "SYNTH-001",
        "bgcs": [{"bgc_id": "BGC007", "contig": "NODE_7_length_12345_cov_20.500000",
                  "antismash_region": "region001"}],
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    from mamey.modeb_structure_gate import load_contract
    from mamey.mode_b.gene_first_stage_v2 import ROSTER_FIELDS, query_roster_sha256
    from tests.test_modeb_publication_quality_v9_7_372 import _card
    card_text = f"# {IDENTITY}\n\nFINISHED_FULL48_CURRENT_EVIDENCE\n\n" + _card()
    for section in load_contract()["sections"]:
        card_text = card_text.replace(
            f"## §{section['number']} Section {section['number']}",
            f"## §{section['number']} {section['title']}",
        )
        # This positive fixture must clear the live strict-depth gate rather
        # than relying on self-asserted PASS receipts.  The paragraph is tied
        # to the synthetic exact query gene and names the section purpose, so
        # it is not evidence-free generic padding.
        marker = f"## §{section['number']} {section['title']}\n"
        depth = (
            f"For synthetic gate testing, §{section['number']} ({section['title']}) "
            "is evaluated against the exact ctg1_1 query roster and the sealed "
            "package binding. The observation remains a bounded workflow fixture; "
            "ctg1_1 does not establish product identity, activity, expression, or "
            "biological function for any real locus.\n\n"
        )
        card_text = card_text.replace(marker, marker + depth, 1)
    card_text = card_text.replace(
        "#### Complete named-match, channel-separated table\n"
        "| locus | nr accession | matched protein | organism | identity |\n"
        "|---|---|---|---|---|\n"
        "| ctg1_1 | WP_1 | enzyme | Nocardia testii | 90% |",
        "#### Complete named-match, channel-separated table\n"
        "| Gene | aa | NCBI nr accession + matched protein | nr id/pos/qcov | NCBI ClusteredNR accession + matched protein | ClusteredNR id/pos/qcov | local Swiss-Prot accession + matched protein | Swiss-Prot id/pos/qcov |\n"
        "|---|---:|---|---|---|---|---|---|\n"
        "| `ctg1_1` | 100 | WP_000001 — synthase [Streptomyces examplei] | 91.2% id / 95.0% positives / qcov 100.0% | WP_000002 — synthase [Streptomyces examplei] | 88.0% id / 92.0% positives / qcov 99.0% | P00001 — Reviewed synthase [Streptomyces examplei] | 42.0% id / 61.0% positives / query coverage 88.0% |",
    )
    card = root / "card.md"
    card.write_text(card_text)
    roster = root / "gene_roster.tsv"
    gene_first_identity = {
        "strain": "SYNTH-001",
        "full_node": "NODE_7_length_12345_cov_20.500000",
        "region": "region001",
        "bgc_alias": "BGC007",
        "exact_identity": IDENTITY,
    }
    roster_row = {
        **gene_first_identity,
        "membership": "EXACT_REGION",
        "locus_tag": "ctg1_1",
        "gene_order": "1",
        "cds_start": "100",
        "cds_end": "400",
        "strand": "+",
        "protein_length_aa": "100",
        "protein_sha256": SHA,
        "antismash_role": "biosynthetic",
        "gene_kind": "CDS",
        "partial_state": "COMPLETE",
        "boundary_proximity": "INTERIOR",
        "source_locator": "regions/synthetic.gbk",
        "source_sha256": "9" * 64,
    }
    roster.write_text(
        "\t".join(ROSTER_FIELDS) + "\n"
        + "\t".join(str(roster_row[field]) for field in ROSTER_FIELDS) + "\n"
    )
    package_sha = _sha(pkg / "manifest.json")
    card_sha = _sha(card)
    roster_digest = query_roster_sha256(gene_first_identity, [roster_row])
    common = {
        "exact_identity": IDENTITY, "card_sha256": card_sha,
        "package_manifest_sha256": package_sha, "query_roster_sha256": roster_digest,
    }
    structure = _write_json(root / "receipts" / "structure.json", {
        **common, "status": "PASS", "profile": "FINISHED_FULL48_CURRENT_EVIDENCE",
    })
    quality = _write_json(root / "receipts" / "quality.json", {
        **common, "status": "PASS", "substantive_quality_v2": True,
    })
    score = _write_json(root / "receipts" / "score.json", {
        **common, "route": "PASS_TO_HUMAN_REVIEW",
        "rubric_sha256": "c" * 64, "scorer_sha256": "d" * 64,
    })
    channels = {}
    for channel, char in (("nr", "e"), ("clustered_nr", "f"),
                          ("local_swissprot", "1")):
        channels[channel] = _write_json(root / "receipts" / f"{channel}.json", {
            "exact_identity": IDENTITY, "package_manifest_sha256": package_sha,
            "query_roster_sha256": roster_digest, "channel": channel,
            "producer_state": "COMPLETE", "database_sha256": char * 64,
            "output_sha256": "2" * 64,
        })
    request = {
        "schema_version": "mode-b-finished-review-request-1.0",
        "intent": "REQUEST_FINISHED_FULL48_REVIEW",
        "structure_override_used": False,
        "identity": {"strain": "SYNTH-001", "full_node_or_contig": "NODE_7_length_12345_cov_20.500000",
                     "region": "region001", "bgc_alias": "BGC007", "display": IDENTITY},
        "package_manifest_sha256": package_sha,
        "card": {"locator": "card.md", "sha256": card_sha},
        "roster": {"locator": "gene_roster.tsv", "sha256": _sha(roster),
                   "query_roster_sha256": roster_digest},
        "verification_receipts": {"structure": structure, "substantive_quality_v2": quality,
                                  "blinded_score": score},
        "channel_producer_receipts": channels,
    }
    request_path = root / "request.json"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return pkg, root, request_path, request


def _snapshot(root: Path):
    return {p.relative_to(root).as_posix(): (_sha(p), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def _upgrade_to_v3(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True) -> dict:
    """Upgrade the synthetic v1.0 request to the explicit v1.1 profile."""
    if structure_card:
        from tests.test_modeb_semantic_sections_10_12_17_24_v97410 import _structured_card
        from mamey.modeb_structure_gate import extract_section_bodies
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        structured_bodies = extract_section_bodies(_structured_card())
        for section in (10, 12, 17, 24):
            card_text = re.sub(
                rf"(^## §{section}\b[^\n]*\n).*?(?=^## §\d+\b|\Z)",
                lambda match, body=structured_bodies[section]: match.group(1) + "\n" + body + "\n\n",
                card_text, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.1"
    request["quality_profile"] = "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3"
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    semantic = _write_json(root / "receipts" / "semantic_v3.json", {
        **common, "status": "PASS", "semantic_sections_v3": True,
    })
    request["verification_receipts"]["semantic_sections_v3"] = semantic
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v4(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True) -> dict:
    """Upgrade through v1.1, then bind the explicit v1.2 semantic-v4 profile."""
    _upgrade_to_v3(pkg, root, request_path, request)
    if structure_card:
        from tests.test_modeb_semantic_comparators_v4_v97410 import _structured_card
        from mamey.modeb_structure_gate import extract_section_bodies
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        structured_bodies = extract_section_bodies(_structured_card())
        for section in (6, 45, 46, 47):
            card_text = re.sub(
                rf"(^## §{section}\b[^\n]*\n).*?(?=^## §\d+\b|\Z)",
                lambda match, body=structured_bodies[section]: match.group(1) + "\n" + body + "\n\n",
                card_text, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.2"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4"
    )
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    semantic = _write_json(root / "receipts" / "semantic_v4.json", {
        **common, "status": "PASS", "semantic_comparators_v4": True,
    })
    request["verification_receipts"]["semantic_comparators_v4"] = semantic
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v5(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True) -> dict:
    """Upgrade through v1.2, then bind the explicit v1.3 semantic-v5 profile."""
    _upgrade_to_v4(pkg, root, request_path, request)
    source_common = {
        "exact_identity": IDENTITY,
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
    }
    missing_state = _write_json(root / "receipts" / "section15_missing_state.json", {
        **source_common, "receipt_role": "SECTION_15_MISSING_EVIDENCE_STATE",
        "status": "COMPLETE",
    })
    rggmci = _write_json(root / "receipts" / "section43_rggmci_run.json", {
        **source_common, "receipt_role": "SECTION_43_RGGMCI_RUN", "status": "COMPLETE",
    })
    request["section_evidence_receipts"] = {
        "section15_missing_evidence_state": [missing_state],
        "section43_rggmci_run": rggmci,
    }
    if structure_card:
        from tests.test_modeb_semantic_sections_15_19_29_31_43_v97410 import _structured_card
        from mamey.modeb_structure_gate import extract_section_bodies
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        structured_bodies = extract_section_bodies(_structured_card())
        replacements = {
            15: missing_state["sha256"],
            31: request["roster"]["query_roster_sha256"],
            43: rggmci["sha256"],
        }
        for section in (15, 19, 29, 31, 43):
            body = structured_bodies[section]
            if section in replacements:
                body = body.replace(SHA, replacements[section])
            card_text = re.sub(
                rf"(^## §{section}\b[^\n]*\n).*?(?=^## §\d+\b|\Z)",
                lambda match, body=body: match.group(1) + "\n" + body + "\n\n",
                card_text, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.3"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
        "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5"
    )
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    semantic = _write_json(root / "receipts" / "semantic_v5.json", {
        **common, "status": "PASS", "semantic_sections_v5": True,
    })
    request["verification_receipts"]["semantic_sections_v5"] = semantic
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v6(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True) -> dict:
    """Upgrade through v1.3, then bind the explicit v1.4 semantic-v6 profile."""
    _upgrade_to_v5(pkg, root, request_path, request)
    from tests.test_modeb_semantic_decision_chains_v6_v97410 import (
        ROWS, SECTIONS, _structured_card,
    )
    from mamey.modeb_structure_gate import extract_section_bodies

    source_common = {
        "exact_identity": IDENTITY,
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
    }
    decision_receipts = {}
    replacements = {}
    for section in SECTIONS:
        typed_state = ROWS[section].split("|")[1].strip()
        spec = _write_json(root / "receipts" / f"decision_chain_s{section}.json", {
            **source_common,
            "receipt_role": "MODEB_SEMANTIC_DECISION_CHAIN_EVIDENCE",
            "section_number": section,
            "typed_state": typed_state,
            "status": "COMPLETE",
        })
        decision_receipts[f"section{section}"] = [spec]
        replacements[section] = spec["sha256"]
    request["semantic_decision_chain_evidence_receipts"] = decision_receipts
    if structure_card:
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        structured_bodies = extract_section_bodies(_structured_card())
        for section in SECTIONS:
            body = structured_bodies[section].replace(SHA, replacements[section])
            card_text = re.sub(
                rf"(^## §{section}\b[^\n]*\n).*?(?=^## §\d+\b|\Z)",
                lambda match, body=body: match.group(1) + "\n" + body + "\n\n",
                card_text, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.4"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
        "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
        "SEMANTIC_DECISION_CHAINS_V6"
    )
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    semantic = _write_json(root / "receipts" / "semantic_v6.json", {
        **common, "status": "PASS", "semantic_decision_chains_v6": True,
    })
    request["verification_receipts"]["semantic_decision_chains_v6"] = semantic
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v7(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True) -> dict:
    """Upgrade through v1.4 and bind all four v1.5 claim-model sources."""
    _upgrade_to_v6(pkg, root, request_path, request)
    from tests.test_modeb_semantic_claim_models_v7_v97410 import ROWS, SECTIONS, _structured_card
    from mamey.modeb_structure_gate import extract_section_bodies

    source_common = {
        "exact_identity": IDENTITY,
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
    }
    claim_receipts = {}
    replacements = {}
    for section in SECTIONS:
        typed_state = ROWS[section].split("|")[1].strip()
        spec = _write_json(root / "receipts" / f"claim_model_s{section}.json", {
            **source_common, "receipt_role": "MODEB_SEMANTIC_CLAIM_MODEL_EVIDENCE",
            "section_number": section, "typed_state": typed_state, "status": "COMPLETE",
        })
        claim_receipts[f"section{section}"] = [spec]
        replacements[section] = spec["sha256"]
    request["semantic_claim_model_evidence_receipts"] = claim_receipts
    if structure_card:
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        bodies = extract_section_bodies(_structured_card())
        for section in SECTIONS:
            body = bodies[section].replace("b" * 64, replacements[section])
            card_text = re.sub(
                rf"(^## §{section}\b[^\n]*\n).*?(?=^## §\d+\b|\Z)",
                lambda match, body=body: match.group(1) + "\n" + body + "\n\n",
                card_text, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.5"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4_PLUS_"
        "SEMANTIC_SECTIONS_V5_PLUS_SEMANTIC_DECISION_CHAINS_V6_PLUS_SEMANTIC_CLAIM_MODELS_V7"
    )
    common = {**source_common, "card_sha256": request["card"]["sha256"],
              "quality_profile": request["quality_profile"]}
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request["verification_receipts"]["semantic_claim_models_v7"] = _write_json(
        root / "receipts" / "semantic_v7.json",
        {**common, "status": "PASS", "semantic_claim_models_v7": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v8(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True) -> dict:
    """Upgrade through v1.5 and bind all six v1.6 inventory sources."""
    _upgrade_to_v7(pkg, root, request_path, request)
    from tests.test_modeb_inventory_reconciliation_v8_v97410 import ROWS, SECTIONS, _structured_card
    from mamey.modeb_structure_gate import extract_section_bodies

    source_common = {
        "exact_identity": IDENTITY,
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
    }
    inventory_receipts = {}
    replacements = {}
    for section in SECTIONS:
        cells = [cell.strip() for cell in ROWS[section].split("|")[1:-1]]
        spec = _write_json(root / "receipts" / f"inventory_s{section}.json", {
            **source_common,
            "receipt_role": "MODEB_INVENTORY_RECONCILIATION_EVIDENCE",
            "section_number": section,
            "typed_state": cells[0],
            "exact_member_or_typed_zero": cells[1],
            "section_specific_role": cells[2],
            "declared_denominator": int(cells[4]),
            "evidence_state": cells[5],
            "status": "COMPLETE",
        })
        inventory_receipts[f"section{section}"] = [spec]
        replacements[section] = spec["sha256"]
    request["inventory_reconciliation_evidence_receipts"] = inventory_receipts
    if structure_card:
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        bodies = extract_section_bodies(_structured_card())
        for section in SECTIONS:
            body = bodies[section].replace("c" * 64, replacements[section])
            card_text = re.sub(
                rf"(^## §{section}\b[^\n]*\n).*?(?=^## §\d+\b|\Z)",
                lambda match, body=body: match.group(1) + "\n" + body + "\n\n",
                card_text, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.6"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4_PLUS_"
        "SEMANTIC_SECTIONS_V5_PLUS_SEMANTIC_DECISION_CHAINS_V6_PLUS_"
        "SEMANTIC_CLAIM_MODELS_V7_PLUS_INVENTORY_RECONCILIATION_V8"
    )
    common = {**source_common, "card_sha256": request["card"]["sha256"],
              "quality_profile": request["quality_profile"]}
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request["verification_receipts"]["inventory_reconciliation_v8"] = _write_json(
        root / "receipts" / "inventory_v8.json",
        {**common, "status": "PASS", "inventory_reconciliation_v8": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v9(pkg: Path, root: Path, request_path: Path, request: dict,
                   *, structure_card: bool = True,
                   single_candidate: bool = False) -> dict:
    """Upgrade through v1.6 and bind the v1.7 section-2 selection source."""
    _upgrade_to_v8(pkg, root, request_path, request)
    from tests.test_modeb_selection_process_v9_v97410 import (
        HEADER, ROW, TERMINAL, SELECTED, SHA as SELECTION_SHA,
    )

    card_row = (TERMINAL if single_candidate else ROW).replace(SELECTED, IDENTITY, 1)
    cells = [cell.strip() for cell in card_row.split("|")[1:-1]]
    source_common = {
        "exact_identity": IDENTITY,
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
    }
    selection = _write_json(root / "receipts" / "selection_process.json", {
        **source_common,
        "receipt_role": "MODEB_SELECTION_PROCESS_EVIDENCE",
        "section_number": 2,
        "selection_state": cells[0],
        "selected_exact_identity": cells[1],
        "comparator_exact_identity_or_terminal_state": cells[2],
        "candidate_set_denominator": int(cells[3]),
        "selected_observed_metrics": cells[5],
        "comparator_metrics_or_terminal_basis": cells[6],
        "predeclared_selection_rule": cells[7],
        "rule_evaluation": cells[8],
        "status": "COMPLETE",
    })
    request["selection_process_evidence_receipt"] = selection
    if structure_card:
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        body = (HEADER + card_row).replace(SELECTION_SHA, selection["sha256"])
        card_text = re.sub(
            r"(^## §2\b[^\n]*\n).*?(?=^## §3\b)",
            lambda match: match.group(1) + "\n" + body + "\n\n",
            card_text, count=1, flags=re.MULTILINE | re.DOTALL,
        )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.7"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4_PLUS_"
        "SEMANTIC_SECTIONS_V5_PLUS_SEMANTIC_DECISION_CHAINS_V6_PLUS_"
        "SEMANTIC_CLAIM_MODELS_V7_PLUS_INVENTORY_RECONCILIATION_V8_PLUS_"
        "SELECTION_PROCESS_V9"
    )
    common = {**source_common, "card_sha256": request["card"]["sha256"],
              "quality_profile": request["quality_profile"]}
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request["verification_receipts"]["selection_process_v9"] = _write_json(
        root / "receipts" / "selection_v9.json",
        {**common, "status": "PASS", "selection_process_v9": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _upgrade_to_v10(pkg: Path, root: Path, request_path: Path, request: dict,
                    *, structure_card: bool = True) -> dict:
    """Upgrade through v1.7 and bind canonical locus-map-v8 plus visual review."""
    _upgrade_to_v9(pkg, root, request_path, request)
    (pkg / "SYNTH-001_4_triage_board.csv").write_text(
        "BGC_ID,Node_ID,Contig,antiSMASH_Region,Products,Corrected_rank\n"
        "BGC007,NODE_7_length_12345_cov_20.500000,NODE_7_length_12345_cov_20.500000,region001,NRPS,1\n"
    )
    (pkg / "SYNTH-001_gene_by_gene_all_bgcs.csv").write_text(
        "bgc_id,locus_tag,order,start,end,strand,length_aa,product,gene_functions,sec_met_domains\n"
        "BGC007,ctg1_1,1,100,400,+,100,synthetic synthase,biosynthetic,AMP-binding\n"
    )
    from mamey.locus_map_v8 import render_bgc_v8
    map_dir = root / "locus_map"
    map_receipt = render_bgc_v8(
        pkg, "BGC007", out_dir=map_dir, strain_id="SYNTH-001",
        node="NODE_7_length_12345_cov_20.500000", region="region001",
    )
    map_path = map_dir / "BGC007_locus_map_v8_receipt.json"
    map_spec = {"locator": map_path.relative_to(root).as_posix(), "sha256": _sha(map_path)}
    checks = {name: False for name in (
        "clipped_arrows", "overlapping_labels", "unreadable_type", "missing_legend",
        "hidden_suppression", "ambiguous_identity", "absent_companion_data",
    )}
    visual_spec = _write_json(root / "receipts" / "locus_map_visual_review.json", {
        "receipt_role": "MODEB_LOCUS_MAP_VISUAL_REVIEW",
        "exact_identity": IDENTITY,
        "locus_map_v8_receipt_sha256": map_spec["sha256"],
        "visual_review_state": "PASS_OWNER_REVIEWED",
        "checks": checks,
        "png_sha256": map_receipt["output_integrity"]["png"]["sha256"],
        "svg_sha256": map_receipt["output_integrity"]["svg"]["sha256"],
    })
    request["locus_map_v8_receipt"] = map_spec
    request["locus_map_visual_review_receipt"] = visual_spec
    if structure_card:
        card_path = root / request["card"]["locator"]
        card_text = card_path.read_text()
        body = (
            "#### Figure specification\n"
            "| Figure state | Exact plotted identity | Plotted interval | Locus-map v8 receipt | Rendered formats | Evidence-state encoding | Uncertainty labels | Provenance footer | Lossless sidecar | Visual-review receipt | Visual-review state |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            f"| FIGURE_RENDERED_REVIEWED | {IDENTITY} | 100-400 bp | {map_spec['sha256']} | PNG+SVG+CSV | "
            "ENCODED_WITH_EXPLICIT_MISSING | boundary uncertainty and missing coverage labels remain visibly explicit | "
            f"PRESENT_PACKAGE_RELATIVE_SOURCES | VERIFIED_ALL_GENES | {visual_spec['sha256']} | PASS_OWNER_REVIEWED |"
        )
        card_text = re.sub(
            r"(^## §18\b[^\n]*\n).*?(?=^## §19\b)",
            lambda match: match.group(1) + "\n" + body + "\n\n",
            card_text, count=1, flags=re.MULTILINE | re.DOTALL,
        )
        card_path.write_text(card_text)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.8"
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4_PLUS_"
        "SEMANTIC_SECTIONS_V5_PLUS_SEMANTIC_DECISION_CHAINS_V6_PLUS_"
        "SEMANTIC_CLAIM_MODELS_V7_PLUS_INVENTORY_RECONCILIATION_V8_PLUS_"
        "SELECTION_PROCESS_V9_PLUS_FIGURE_SPEC_V10"
    )
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request["verification_receipts"]["figure_spec_v10"] = _write_json(
        root / "receipts" / "section18_v10.json",
        {**common, "status": "PASS", "figure_spec_v10": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    return request


def _mutate_visual_receipt_and_rebind(root: Path, request_path: Path,
                                      request: dict, **changes) -> None:
    spec = request["locus_map_visual_review_receipt"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt.update(changes)
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(root, request_path, request, old, spec["sha256"])


def test_v18_section18_profile_is_bound_rerun_and_read_only(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.8"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v18_fake_pass_cannot_replace_live_section18_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request, structure_card=False)
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in codes


def test_v17_rejects_v18_receipt_fields(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request)
    request["locus_map_v8_receipt"] = {"locator": "none.json", "sha256": "0" * 64}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_FIGURE_SPEC_RECEIPTS_NOT_ALLOWED" in codes


def test_v18_requires_exact_profile_and_true_verification(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    request["quality_profile"] = "FIGURE_SPEC_V10"
    spec = request["verification_receipts"]["figure_spec_v10"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["figure_spec_v10"] = False
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in codes
    assert "REVIEW_FIGURE_V10_RECEIPT_NOT_PASS" in codes


def test_v18_detects_map_output_tamper(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    map_path = root / request["locus_map_v8_receipt"]["locator"]
    receipt = json.loads(map_path.read_text())
    (map_path.parent / receipt["outputs"]["svg"]).write_text("tampered")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_LOCUS_MAP_V8_INVALID" in codes


def test_v18_detects_package_source_tamper(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    source = pkg / "SYNTH-001_gene_by_gene_all_bgcs.csv"
    source.write_text(source.read_text() + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_LOCUS_MAP_SOURCE_INTEGRITY_MISMATCH" in codes


def test_v18_detects_card_interval_mismatch(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    card = root / request["card"]["locator"]
    card.write_text(card.read_text().replace("100-400 bp", "101-400 bp", 1))
    request["card"]["sha256"] = _sha(card)
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt["card_sha256"] = request["card"]["sha256"]
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_FIGURE_SPEC_CARD_BINDING_MISMATCH" in codes


def test_v18_detects_visual_defect_even_after_rebinding(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    path = root / request["locus_map_visual_review_receipt"]["locator"]
    receipt = json.loads(path.read_text())
    checks = dict(receipt["checks"])
    checks["clipped_arrows"] = True
    _mutate_visual_receipt_and_rebind(root, request_path, request, checks=checks)
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_LOCUS_MAP_VISUAL_DEFECT_PRESENT" in codes


def test_v18_detects_visual_render_hash_mismatch(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    _mutate_visual_receipt_and_rebind(root, request_path, request, png_sha256="0" * 64)
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_LOCUS_MAP_VISUAL_RENDER_MISMATCH" in codes


def test_v18_requires_one_map_hash_and_one_visual_hash_in_card(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    card = root / request["card"]["locator"]
    visual_sha = request["locus_map_visual_review_receipt"]["sha256"]
    card.write_text(card.read_text().replace(visual_sha, visual_sha + " " + visual_sha, 1))
    request["card"]["sha256"] = _sha(card)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_FIGURE_SPEC_CARD_VISUAL_HASH_COUNT_MISMATCH" in codes


def _mutate_selection_receipt_and_rebind(root: Path, request_path: Path,
                                         request: dict, **changes) -> None:
    spec = request["selection_process_evidence_receipt"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt.update(changes)
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(
        root, request_path, request, old, spec["sha256"])


def test_v17_selection_profile_is_bound_rerun_and_read_only(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.7"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v17_single_candidate_terminal_is_bound_and_ready(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request, single_candidate=True)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"


def test_v17_fake_pass_cannot_replace_live_selection_process(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v17_requires_exact_profile_and_true_verification(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request)
    request["quality_profile"] = "SELECTION_PROCESS_V9"
    spec = request["verification_receipts"]["selection_process_v9"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["selection_process_v9"] = False
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in codes
    assert "REVIEW_SELECTION_V9_RECEIPT_NOT_PASS" in codes


def test_v16_rejects_v17_selection_field(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    request["selection_process_evidence_receipt"] = {
        "locator": "receipts/none.json", "sha256": "0" * 64}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SELECTION_EVIDENCE_RECEIPT_NOT_ALLOWED" in result["finding_codes"]


def test_v17_rejects_cross_binding_role_section_selected_state_and_status(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request)
    _mutate_selection_receipt_and_rebind(
        root, request_path, request,
        package_manifest_sha256="0" * 64, receipt_role="WRONG",
        section_number=3, selected_exact_identity="wrong", selection_state="lowercase",
        status="PARTIAL")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert {"REVIEW_SELECTION_EVIDENCE_BINDING_MISMATCH",
            "REVIEW_SELECTION_EVIDENCE_ROLE_MISMATCH",
            "REVIEW_SELECTION_EVIDENCE_SECTION_MISMATCH",
            "REVIEW_SELECTION_SELECTED_IDENTITY_MISMATCH",
            "REVIEW_SELECTION_EVIDENCE_STATE_INVALID",
            "REVIEW_SELECTION_EVIDENCE_NOT_COMPLETE"}.issubset(codes)


def test_v17_rejects_card_metric_rule_or_state_mismatch(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request)
    _mutate_selection_receipt_and_rebind(
        root, request_path, request,
        selected_observed_metrics="different observed score 7",
        predeclared_selection_rule="different predeclared rule selects higher score",
        rule_evaluation="RULE_NOT_MET_HELD")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SELECTION_CARD_RECEIPT_BINDING_MISMATCH" in result["finding_codes"]


def test_v17_rejects_multiple_card_candidate_set_hashes(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v9(pkg, root, request_path, request)
    digest = request["selection_process_evidence_receipt"]["sha256"]
    _rewrite_card_and_rebind_verification(
        root, request_path, request, digest, digest + " " + digest)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SELECTION_CARD_RECEIPT_HASH_COUNT_MISMATCH" in result["finding_codes"]


def _mutate_inventory_receipt_and_rebind(root: Path, request_path: Path,
                                         request: dict, section: int, **changes) -> None:
    spec = request["inventory_reconciliation_evidence_receipts"][f"section{section}"][0]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt.update(changes)
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(
        root, request_path, request, old, spec["sha256"])


def test_v16_inventory_profile_is_bound_rerun_and_read_only(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.6"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v16_fake_pass_cannot_replace_live_inventory_tables(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v16_requires_exact_profile_and_true_verification(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    request["quality_profile"] = "INVENTORY_RECONCILIATION_V8"
    spec = request["verification_receipts"]["inventory_reconciliation_v8"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["inventory_reconciliation_v8"] = False
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in codes
    assert "REVIEW_INVENTORY_V8_RECEIPT_NOT_PASS" in codes


def test_v15_rejects_v16_inventory_field(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    request["inventory_reconciliation_evidence_receipts"] = {}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_INVENTORY_EVIDENCE_RECEIPTS_NOT_ALLOWED" in result["finding_codes"]


def test_v16_rejects_missing_empty_and_duplicate_inventory_sources(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    del request["inventory_reconciliation_evidence_receipts"]["section38"]
    request["inventory_reconciliation_evidence_receipts"]["section32"] *= 2
    request["inventory_reconciliation_evidence_receipts"]["section33"] = []
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_INVENTORY_RECEIPT_SET_MISMATCH" in codes
    assert "REVIEW_INVENTORY_RECEIPT_DUPLICATE" in codes
    assert "REVIEW_INVENTORY_RECEIPT_SET_EMPTY" in codes


def test_v16_rejects_cross_binding_role_section_state_and_status(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    _mutate_inventory_receipt_and_rebind(
        root, request_path, request, 34,
        exact_identity="SYNTH-002 / NODE_8_length_1_cov_1 / region002 / BGC008",
        receipt_role="WRONG", section_number=35, typed_state="lowercase", status="PARTIAL")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert {"REVIEW_INVENTORY_EVIDENCE_BINDING_MISMATCH",
            "REVIEW_INVENTORY_EVIDENCE_ROLE_MISMATCH",
            "REVIEW_INVENTORY_EVIDENCE_SECTION_MISMATCH",
            "REVIEW_INVENTORY_EVIDENCE_STATE_INVALID",
            "REVIEW_INVENTORY_EVIDENCE_NOT_COMPLETE"}.issubset(codes)


def test_v16_rejects_card_role_denominator_or_state_mismatch(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    _mutate_inventory_receipt_and_rebind(
        root, request_path, request, 37,
        section_specific_role="different accessory partner role",
        declared_denominator=2, evidence_state="UNRESOLVED_SOURCE_BOUND")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_INVENTORY_CARD_RECEIPT_BINDING_MISMATCH" in result["finding_codes"]


def test_v16_rejects_multiple_card_receipt_hashes(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v8(pkg, root, request_path, request)
    digest = request["inventory_reconciliation_evidence_receipts"]["section32"][0]["sha256"]
    _rewrite_card_and_rebind_verification(
        root, request_path, request, digest, digest + " " + digest)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_INVENTORY_CARD_EVIDENCE_HASH_COUNT_MISMATCH" in result["finding_codes"]


def _mutate_claim_receipt_and_rebind(root: Path, request_path: Path,
                                     request: dict, section: int, **changes) -> None:
    spec = request["semantic_claim_model_evidence_receipts"][f"section{section}"][0]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt.update(changes)
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(root, request_path, request, old, spec["sha256"])


def test_v15_claim_model_profile_is_bound_rerun_and_read_only(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.5"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v15_fake_pass_cannot_replace_live_claim_models(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v15_requires_exact_profile_and_true_verification(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    request["quality_profile"] = "SEMANTIC_CLAIM_MODELS_V7"
    spec = request["verification_receipts"]["semantic_claim_models_v7"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["semantic_claim_models_v7"] = False
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in codes
    assert "REVIEW_SEMANTIC_V7_RECEIPT_NOT_PASS" in codes


def test_v14_rejects_v15_claim_receipt_field(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    request["semantic_claim_model_evidence_receipts"] = {}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_CLAIM_MODEL_EVIDENCE_RECEIPTS_NOT_ALLOWED" in result["finding_codes"]


def test_v15_rejects_missing_empty_and_duplicate_claim_sources(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    del request["semantic_claim_model_evidence_receipts"]["section44"]
    request["semantic_claim_model_evidence_receipts"]["section8"] *= 2
    request["semantic_claim_model_evidence_receipts"]["section11"] = []
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_CLAIM_MODEL_RECEIPT_SET_MISMATCH" in codes
    assert "REVIEW_CLAIM_MODEL_RECEIPT_DUPLICATE" in codes
    assert "REVIEW_CLAIM_MODEL_RECEIPT_SET_EMPTY" in codes


def test_v15_rejects_cross_identity_role_section_state_and_status(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    _mutate_claim_receipt_and_rebind(
        root, request_path, request, 11,
        exact_identity="SYNTH-002 / NODE_8_length_1_cov_1 / region002 / BGC008",
        receipt_role="WRONG", section_number=13, typed_state="lowercase", status="PARTIAL",
    )
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert {"REVIEW_CLAIM_MODEL_EVIDENCE_BINDING_MISMATCH",
            "REVIEW_CLAIM_MODEL_EVIDENCE_ROLE_MISMATCH",
            "REVIEW_CLAIM_MODEL_EVIDENCE_SECTION_MISMATCH",
            "REVIEW_CLAIM_MODEL_EVIDENCE_STATE_INVALID",
            "REVIEW_CLAIM_MODEL_EVIDENCE_NOT_COMPLETE"}.issubset(codes)


def test_v15_rejects_card_receipt_or_typed_state_mismatch(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    _mutate_claim_receipt_and_rebind(root, request_path, request, 13,
                                     typed_state="ACTIVITY_EVIDENCE_UNAVAILABLE_TYPED")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_CLAIM_MODEL_CARD_RECEIPT_BINDING_MISMATCH" in result["finding_codes"]


def test_v15_rejects_zero_or_multiple_card_receipt_hashes(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v7(pkg, root, request_path, request)
    digest = request["semantic_claim_model_evidence_receipts"]["section8"][0]["sha256"]
    _rewrite_card_and_rebind_verification(root, request_path, request, digest, digest + " " + digest)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_CLAIM_MODEL_CARD_EVIDENCE_HASH_COUNT_MISMATCH" in result["finding_codes"]


def _rewrite_card_and_rebind_verification(
        root: Path, request_path: Path, request: dict, old: str, new: str) -> None:
    """Change card bytes while keeping only the verification receipt bindings coherent."""
    card_path = root / request["card"]["locator"]
    card_path.write_text(card_path.read_text().replace(old, new, 1))
    request["card"]["sha256"] = _sha(card_path)
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt["card_sha256"] = request["card"]["sha256"]
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")


def _mutate_decision_receipt_and_rebind(
        root: Path, request_path: Path, request: dict, section: int, **changes) -> None:
    spec = request["semantic_decision_chain_evidence_receipts"][f"section{section}"][0]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt.update(changes)
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(
        root, request_path, request, old, spec["sha256"])


def test_ready_request_is_read_only_and_never_claims_promotion(tmp_path):
    pkg, root, request_path, _ = _fixture(tmp_path)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["mutation_performed"] is False
    assert "does not mean card acceptance" in result["authority_ceiling"]
    assert "Hashes prove byte consistency" in result["authenticity_ceiling"]
    assert _snapshot(tmp_path) == before


def test_v11_semantic_profile_is_independently_rerun_and_ready(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v3(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.1"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v11_fake_semantic_pass_cannot_bypass_live_v3_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v3(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "HOLD_FINISHED_REVIEW_REQUEST"
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v12_semantic_v4_profile_is_independently_rerun_and_ready(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v4(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.2"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v12_fake_semantic_pass_cannot_bypass_live_v4_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v4(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "HOLD_FINISHED_REVIEW_REQUEST"
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v13_semantic_v5_profile_is_independently_rerun_and_ready(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.3"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v13_fake_semantic_pass_cannot_bypass_live_v5_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "HOLD_FINISHED_REVIEW_REQUEST"
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v14_semantic_v6_profile_is_bound_rerun_and_read_only(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.4"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v14_reasoned_terminal_state_is_also_receipt_bound(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    _mutate_decision_receipt_and_rebind(
        root, request_path, request, 16, typed_state="ANALYSIS_NOT_RUN_TYPED")
    card_path = root / request["card"]["locator"]
    old_basis = re.search(
        r"measured 71% identity and 88% query coverage in receipt sha-256 [0-9a-f]{64}",
        card_path.read_text(),
    ).group(0)
    _rewrite_card_and_rebind_verification(
        root, request_path, request, "RESULT_MEASURED", "ANALYSIS_NOT_RUN_TYPED")
    bound = request["semantic_decision_chain_evidence_receipts"]["section16"][0]["sha256"]
    _rewrite_card_and_rebind_verification(
        root, request_path, request, old_basis,
        f"analysis not run because the sealed source receipt is unavailable; denominator 0 and receipt {bound}",
    )
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"


def test_v14_fake_semantic_pass_cannot_bypass_live_v6_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request, structure_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "HOLD_FINISHED_REVIEW_REQUEST"
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v14_requires_semantic_v6_receipt_and_exact_profile(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    del request["verification_receipts"]["semantic_decision_chains_v6"]
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
        "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5"
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in result["finding_codes"]
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v14_rejects_self_reported_v6_failure(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    spec = request["verification_receipts"]["semantic_decision_chains_v6"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["semantic_decision_chains_v6"] = False
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SEMANTIC_V6_RECEIPT_NOT_PASS" in result["finding_codes"]


def test_v13_rejects_mixed_v6_receipt_and_evidence_fields(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    request["verification_receipts"]["semantic_decision_chains_v6"] = _write_json(
        root / "receipts" / "semantic_v6.json",
        {**common, "status": "PASS", "semantic_decision_chains_v6": True},
    )
    request["semantic_decision_chain_evidence_receipts"] = {}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]
    assert "REVIEW_DECISION_CHAIN_EVIDENCE_RECEIPTS_NOT_ALLOWED" in result["finding_codes"]


def test_v14_requires_exact_decision_chain_section_keys(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    del request["semantic_decision_chain_evidence_receipts"]["section41"]
    request["semantic_decision_chain_evidence_receipts"]["section42"] = []
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_RECEIPT_SET_MISMATCH" in result["finding_codes"]
    assert "REVIEW_DECISION_CHAIN_RECEIPT_SET_EMPTY" in result["finding_codes"]


def test_v14_rejects_empty_and_duplicate_decision_receipt_sets(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    specs = request["semantic_decision_chain_evidence_receipts"]["section16"]
    specs.append(dict(specs[0]))
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_RECEIPT_DUPLICATE" in result["finding_codes"]
    request["semantic_decision_chain_evidence_receipts"]["section16"] = []
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_RECEIPT_SET_EMPTY" in result["finding_codes"]


def test_v14_rejects_same_receipt_hash_under_second_locator(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    specs = request["semantic_decision_chain_evidence_receipts"]["section16"]
    duplicate = root / "receipts" / "decision_chain_s16_duplicate.json"
    duplicate.write_bytes((root / specs[0]["locator"]).read_bytes())
    specs.append({
        "locator": "receipts/decision_chain_s16_duplicate.json",
        "sha256": specs[0]["sha256"],
    })
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_RECEIPT_DUPLICATE" in result["finding_codes"]


def test_v14_decision_receipt_root_escape_and_tamper_are_held(tmp_path):
    for index, mode in enumerate(("escape", "tamper")):
        case_root = tmp_path / str(index)
        case_root.mkdir()
        pkg, root, request_path, request = _fixture(case_root)
        _upgrade_to_v6(pkg, root, request_path, request)
        spec = request["semantic_decision_chain_evidence_receipts"]["section16"][0]
        if mode == "escape":
            spec["locator"] = "../outside.json"
        else:
            (root / spec["locator"]).write_text("{}\n")
        request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
        result = validate_finished_review_request(pkg, request_path, root)
        code = "REVIEW_MEMBER_LOCATOR_UNSAFE" if mode == "escape" else "REVIEW_MEMBER_SHA256_MISMATCH"
        assert code in result["finding_codes"]


def test_v14_decision_receipt_cross_identity_is_held_after_rehash(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    _mutate_decision_receipt_and_rebind(
        root, request_path, request, 16,
        exact_identity="SYNTH-999 / NODE_X / region999 / BGC999",
    )
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_EVIDENCE_BINDING_MISMATCH" in result["finding_codes"]


def test_v14_decision_receipt_role_section_and_completion_are_typed(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    _mutate_decision_receipt_and_rebind(
        root, request_path, request, 16,
        receipt_role="OTHER", section_number=21, status="PENDING",
    )
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_EVIDENCE_ROLE_MISMATCH" in result["finding_codes"]
    assert "REVIEW_DECISION_CHAIN_EVIDENCE_SECTION_MISMATCH" in result["finding_codes"]
    assert "REVIEW_DECISION_CHAIN_EVIDENCE_NOT_COMPLETE" in result["finding_codes"]


def test_v14_card_state_must_equal_bound_receipt_state(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    _mutate_decision_receipt_and_rebind(
        root, request_path, request, 16, typed_state="ANALYSIS_NOT_RUN_TYPED")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_CARD_RECEIPT_BINDING_MISMATCH" in result["finding_codes"]


def test_v14_card_hash_must_equal_bound_receipt_hash(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v6(pkg, root, request_path, request)
    old = request["semantic_decision_chain_evidence_receipts"]["section16"][0]["sha256"]
    _rewrite_card_and_rebind_verification(root, request_path, request, old, "b" * 64)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_DECISION_CHAIN_CARD_RECEIPT_BINDING_MISMATCH" in result["finding_codes"]


def test_v14_card_requires_exactly_one_evidence_receipt_hash_per_row(tmp_path):
    for index, replacement in enumerate(("receipt unavailable", f"receipts {SHA} and {'b' * 64}")):
        case_root = tmp_path / str(index)
        case_root.mkdir()
        pkg, root, request_path, request = _fixture(case_root)
        _upgrade_to_v6(pkg, root, request_path, request)
        bound = request["semantic_decision_chain_evidence_receipts"]["section16"][0]["sha256"]
        _rewrite_card_and_rebind_verification(root, request_path, request, bound, replacement)
        result = validate_finished_review_request(pkg, request_path, root)
        assert "REVIEW_DECISION_CHAIN_CARD_EVIDENCE_HASH_COUNT_MISMATCH" in result["finding_codes"]


def test_v13_requires_semantic_v5_receipt_and_exact_profile(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    del request["verification_receipts"]["semantic_sections_v5"]
    request["quality_profile"] = (
        "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4"
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in result["finding_codes"]
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v13_rejects_self_reported_v5_failure(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    spec = request["verification_receipts"]["semantic_sections_v5"]
    receipt_path = root / spec["locator"]
    receipt = json.loads(receipt_path.read_text())
    receipt["semantic_sections_v5"] = False
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(receipt_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SEMANTIC_V5_RECEIPT_NOT_PASS" in result["finding_codes"]


def test_v13_binds_all_three_card_receipt_columns_to_packet_evidence(tmp_path):
    cases = [
        (lambda request: request["section_evidence_receipts"]["section15_missing_evidence_state"][0]["sha256"],
         "REVIEW_SECTION15_RECEIPT_BINDING_MISMATCH"),
        (lambda request: request["roster"]["query_roster_sha256"],
         "REVIEW_SECTION31_ROSTER_DIGEST_MISMATCH"),
        (lambda request: request["section_evidence_receipts"]["section43_rggmci_run"]["sha256"],
         "REVIEW_SECTION43_RECEIPT_BINDING_MISMATCH"),
    ]
    for index, (get_old, code) in enumerate(cases):
        case_root = tmp_path / str(index)
        case_root.mkdir()
        pkg, root, request_path, request = _fixture(case_root)
        _upgrade_to_v5(pkg, root, request_path, request)
        old = get_old(request)
        _rewrite_card_and_rebind_verification(root, request_path, request, old, "a" * 64)
        result = validate_finished_review_request(pkg, request_path, root)
        assert code in result["finding_codes"]


def test_v13_requires_exact_section_evidence_receipt_keys(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    del request["section_evidence_receipts"]["section43_rggmci_run"]
    request["section_evidence_receipts"]["unexpected"] = {"locator": "x", "sha256": SHA}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION_EVIDENCE_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v13_rejects_empty_and_duplicate_section15_receipt_set(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    spec = request["section_evidence_receipts"]["section15_missing_evidence_state"][0]
    request["section_evidence_receipts"]["section15_missing_evidence_state"].append(dict(spec))
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION15_RECEIPT_DUPLICATE" in result["finding_codes"]
    request["section_evidence_receipts"]["section15_missing_evidence_state"] = []
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION15_RECEIPT_SET_EMPTY" in result["finding_codes"]


def test_v13_rejects_same_section15_receipt_hash_under_second_locator(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    spec = request["section_evidence_receipts"]["section15_missing_evidence_state"][0]
    duplicate = root / "receipts" / "section15_duplicate.json"
    duplicate.write_bytes((root / spec["locator"]).read_bytes())
    request["section_evidence_receipts"]["section15_missing_evidence_state"].append({
        "locator": "receipts/section15_duplicate.json", "sha256": spec["sha256"],
    })
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION15_RECEIPT_DUPLICATE" in result["finding_codes"]


def test_v13_section_receipt_root_escape_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    request["section_evidence_receipts"]["section15_missing_evidence_state"][0]["locator"] = "../outside.json"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_MEMBER_LOCATOR_UNSAFE" in result["finding_codes"]


def test_v13_section_receipt_byte_tamper_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    spec = request["section_evidence_receipts"]["section43_rggmci_run"]
    (root / spec["locator"]).write_text("{}\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_MEMBER_SHA256_MISMATCH" in result["finding_codes"]


def test_v13_section_receipt_cross_identity_is_held_even_after_rehash(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    spec = request["section_evidence_receipts"]["section43_rggmci_run"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["exact_identity"] = "SYNTH-999 / NODE_X / region999 / BGC999"
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(root, request_path, request, old, spec["sha256"])
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION_EVIDENCE_BINDING_MISMATCH" in result["finding_codes"]


def test_v13_section_receipt_role_and_completion_are_typed(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v5(pkg, root, request_path, request)
    spec = request["section_evidence_receipts"]["section43_rggmci_run"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["receipt_role"] = "OTHER"
    receipt["status"] = "PENDING"
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    old = spec["sha256"]
    spec["sha256"] = _sha(path)
    _rewrite_card_and_rebind_verification(root, request_path, request, old, spec["sha256"])
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION_EVIDENCE_ROLE_MISMATCH" in result["finding_codes"]
    assert "REVIEW_SECTION_EVIDENCE_NOT_COMPLETE" in result["finding_codes"]


def test_v12_rejects_section_evidence_receipts_field(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v4(pkg, root, request_path, request)
    request["section_evidence_receipts"] = {}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SECTION_EVIDENCE_RECEIPTS_NOT_ALLOWED" in result["finding_codes"]


def test_v12_rejects_mixed_v5_receipt(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v4(pkg, root, request_path, request)
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    request["verification_receipts"]["semantic_sections_v5"] = _write_json(
        root / "receipts" / "semantic_v5.json",
        {**common, "status": "PASS", "semantic_sections_v5": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v12_requires_semantic_v4_receipt_and_exact_profile(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v4(pkg, root, request_path, request)
    del request["verification_receipts"]["semantic_comparators_v4"]
    request["quality_profile"] = "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in result["finding_codes"]
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v12_rejects_self_reported_v4_failure(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v4(pkg, root, request_path, request)
    spec = request["verification_receipts"]["semantic_comparators_v4"]
    receipt_path = root / spec["locator"]
    receipt = json.loads(receipt_path.read_text())
    receipt["semantic_comparators_v4"] = False
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(receipt_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_SEMANTIC_V4_RECEIPT_NOT_PASS" in result["finding_codes"]


def test_v11_rejects_mixed_v4_receipt(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v3(pkg, root, request_path, request)
    common = {
        "exact_identity": IDENTITY,
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": request["quality_profile"],
    }
    request["verification_receipts"]["semantic_comparators_v4"] = _write_json(
        root / "receipts" / "semantic_v4.json",
        {**common, "status": "PASS", "semantic_comparators_v4": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v11_requires_semantic_receipt_and_exact_profile(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v3(pkg, root, request_path, request)
    del request["verification_receipts"]["semantic_sections_v3"]
    request["quality_profile"] = "SUBSTANTIVE_V2"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in result["finding_codes"]
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in result["finding_codes"]


def test_v10_rejects_mixed_v3_fields(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    request["quality_profile"] = "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_REQUEST_QUALITY_PROFILE_NOT_ALLOWED" in result["finding_codes"]


def test_command_emits_machine_receipt_and_ready_exit(tmp_path, capsys):
    pkg, root, request_path, _ = _fixture(tmp_path)
    rc = validate_finished_review_request_command(SimpleNamespace(
        package=str(pkg), request=str(request_path), artifact_root=str(root)
    ))
    result = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["mutation_performed"] is False


def test_tampered_card_is_held(tmp_path):
    pkg, root, request_path, _ = _fixture(tmp_path)
    (root / "card.md").write_text("tampered\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "HOLD_FINISHED_REVIEW_REQUEST"
    assert "REVIEW_CARD_SHA256_MISMATCH" in result["finding_codes"]


def test_self_consistent_fake_pass_receipts_do_not_bypass_live_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    card_path = root / request["card"]["locator"]
    text = card_path.read_text()
    start = text.index("## §9 Alternative hypotheses")
    body_start = text.index("\n", start) + 1
    next_start = text.index("## §10 Fragmentation and co-capture risks", body_start)
    card_path.write_text(text[:body_start] + "Reasoned.\n\n" + text[next_start:])
    new_card_sha = _sha(card_path)
    request["card"]["sha256"] = new_card_sha
    for spec in request["verification_receipts"].values():
        receipt_path = root / spec["locator"]
        receipt = json.loads(receipt_path.read_text())
        receipt["card_sha256"] = new_card_sha
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(receipt_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_missing_required_channel_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    del request["channel_producer_receipts"]["clustered_nr"]
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_CHANNEL_SET_MISMATCH" in result["finding_codes"]


def test_self_consistent_invented_roster_digest_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    invented = "b" * 64
    request["roster"]["query_roster_sha256"] = invented
    for spec in request["verification_receipts"].values():
        receipt_path = root / spec["locator"]
        receipt = json.loads(receipt_path.read_text())
        receipt["query_roster_sha256"] = invented
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(receipt_path)
    for spec in request["channel_producer_receipts"].values():
        receipt_path = root / spec["locator"]
        receipt = json.loads(receipt_path.read_text())
        receipt["query_roster_sha256"] = invented
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(receipt_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_ROSTER_DIGEST_MISMATCH" in result["finding_codes"]


def test_truncated_display_roster_cannot_replace_canonical_roster(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    roster_path = root / request["roster"]["locator"]
    roster_path.write_text("gene_order\tlocus_tag\tprotein_sha256\n1\tctg1_1\t" + SHA + "\n")
    request["roster"]["sha256"] = _sha(roster_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_ROSTER_CONTENT_INVALID" in result["finding_codes"]


def test_blinded_score_hold_route_cannot_be_worked_around(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    spec = request["verification_receipts"]["blinded_score"]
    score_path = root / spec["locator"]
    score = json.loads(score_path.read_text())
    score["route"] = "HOLD_FOR_REWRITE"
    score_path.write_text(json.dumps(score, sort_keys=True) + "\n")
    spec["sha256"] = _sha(score_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_BLINDED_SCORE_ROUTE_HOLD" in result["finding_codes"]


def test_structure_override_cannot_request_finished_review(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    request["structure_override_used"] = True
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_STRUCTURE_OVERRIDE_FORBIDDEN" in result["finding_codes"]


def test_absolute_or_traversing_member_locator_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    request["card"]["locator"] = "/tmp/outside.md"
    request["roster"]["locator"] = "../outside.tsv"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_MEMBER_LOCATOR_UNSAFE" in result["finding_codes"]


def test_package_exact_locus_conflict_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["bgcs"][0]["contig"] = "NODE_8_length_12345_cov_20.500000"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    request["package_manifest_sha256"] = _sha(manifest_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_PACKAGE_EXACT_LOCUS_NOT_UNIQUE" in result["finding_codes"]


def test_package_strain_conflict_is_held(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["strain_id"] = "SYNTH-002"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    request["package_manifest_sha256"] = _sha(manifest_path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_PACKAGE_STRAIN_MISMATCH" in result["finding_codes"]
