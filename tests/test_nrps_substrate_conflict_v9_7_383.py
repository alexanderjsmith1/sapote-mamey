"""v9.7.383: retain antiSMASH consensus/Stachelhaus conflicts end to end."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

from mamey.modeb_template_emitter import _section_body, _substrate_display
from mamey.nrps_predictions import extract_adomain_rows


def _record(consensus="Gly", stachelhaus="Ala", score=0.8):
    matches = []
    if stachelhaus:
        matches = [{
            "substrates": [{"short": stachelhaus, "long": stachelhaus}],
            "aa10_score": score,
        }]
    return {
        "id": "NODE_50_length_54152_cov_56.710735",
        "modules": {
            "antismash.modules.nrps_pks": {
                "consensus": {"nrpspksdomains_ctg50_45_AMP-binding.1": consensus},
                "domain_predictions": {
                    "nrpspksdomains_ctg50_45_AMP-binding.1": {
                        "nrpys": {
                            "aa10": "DIVQVGGVYK",
                            "stachelhaus_matches": matches,
                            "physiochemical_class": {
                                "name": "hydrophobic-aliphatic",
                                "substrates": [
                                    {"short": "Ala"}, {"short": "Gly"}, {"short": "Val"}
                                ],
                            },
                        }
                    }
                },
            }
        },
    }


def test_conflicting_predictors_are_both_preserved():
    row = extract_adomain_rows([_record()])[0]
    assert row["consensus_substrate"] == "Gly"
    assert row["stachelhaus_substrate"] == "Ala"
    assert row["substrate"] == "Ala"  # backward compatibility
    assert row["prediction_agreement_state"] == "SUBSTRATE_PREDICTION_CONFLICT"
    assert row["prediction_disposition"] == "RETAIN_BOTH_CALLS_SUBSTRATE_UNRESOLVED"


def test_concordance_and_one_stream_states_are_typed():
    concordant = extract_adomain_rows([_record("Gly", "Gly")])[0]
    assert concordant["prediction_agreement_state"] == "SUBSTRATE_PREDICTION_CONCORDANT"

    resolves_x = extract_adomain_rows([_record("X", "Ala")])[0]
    assert resolves_x["prediction_agreement_state"] == "STACHELHAUS_RESOLVES_UNINFORMATIVE_CONSENSUS"

    consensus_only = extract_adomain_rows([_record("Gly", "")])[0]
    assert consensus_only["prediction_agreement_state"] == "CONSENSUS_ONLY_STACHELHAUS_UNRESOLVED"

    neither = extract_adomain_rows([_record("X", "")])[0]
    assert neither["prediction_agreement_state"] == "BOTH_SUBSTRATE_PREDICTIONS_UNINFORMATIVE"


def test_pks_at_rows_are_explicitly_not_applicable():
    rec = {
        "id": "NODE_1",
        "modules": {"antismash.modules.nrps_pks": {"domain_predictions": {
            "nrpspksdomains_ctg1_2_PKS_AT.1": {
                "minowa_at": {"predictions": [["mal", 90], ["mmal", 20]]},
                "signature": {"predictions": {"mal": [0, 0, 8]}},
            }
        }}},
    }
    row = extract_adomain_rows([rec])[0]
    assert row["domain_class"] == "PKS_AT"
    assert row["prediction_agreement_state"] == "NOT_APPLICABLE_NRPS_CONFLICT_CHECK"
    assert row["prediction_disposition"] == "MINOWA_AT_SIGNATURE_SIMILARITY_LEVEL"


def test_modeb_sections_display_conflict_without_selecting_a_winner():
    row = {
        "locus_tag": "ctg50_45",
        "domain": "AMP-binding.1",
        "substrate": "Ala",
        "consensus_substrate": "Gly",
        "stachelhaus_substrate": "Ala",
        "prediction_agreement_state": "SUBSTRATE_PREDICTION_CONFLICT",
        "confidence": "high",
        "stachelhaus_signature": "DIVQVGGVYK",
    }
    assert _substrate_display(row) == "**CONFLICT:** consensus Gly; Stachelhaus Ala"
    section16 = _section_body(16, {"pc_substrates": [row]}, {})
    section21 = _section_body(21, {"pc_substrates": [row]}, {})
    assert "CONFLICT" in section16 and "consensus Gly" in section16 and "Stachelhaus Ala" in section16
    assert "retain conflicts" in section21


def test_modeb_legacy_rows_remain_supported():
    row = {
        "locus_tag": "ctg1_5",
        "domain": "AMP-binding.1",
        "substrate": "Gln",
        "confidence": "high",
        "stachelhaus_signature": "DAWQCATIDK",
    }
    assert _substrate_display(row) == "Gln"
    assert "LEGACY_STACHELHAUS_ONLY" in _section_body(16, {"pc_substrates": [row]}, {})


def test_cohort_precompute_preserves_additive_fields(tmp_path):
    package = tmp_path / "TEST-1"
    package.mkdir()
    with (package / "TEST-1_nrps_prediction.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "record_id", "locus_tag", "domain_id", "signature", "substrate",
            "consensus_substrate", "stachelhaus_substrate", "prediction_agreement_state",
            "prediction_disposition", "confidence", "class_or_alternatives",
        ])
        writer.writeheader()
        writer.writerow({
            "record_id": "NODE_50", "locus_tag": "ctg50_45", "domain_id": "AMP-binding.1",
            "signature": "DIVQVGGVYK", "substrate": "Ala", "consensus_substrate": "Gly",
            "stachelhaus_substrate": "Ala", "prediction_agreement_state": "SUBSTRATE_PREDICTION_CONFLICT",
            "prediction_disposition": "RETAIN_BOTH_CALLS_SUBSTRATE_UNRESOLVED", "confidence": "high",
            "class_or_alternatives": "hydrophobic-aliphatic",
        })
    with (package / "TEST-1_antismash_module_summary_by_bgc.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["BGC_ID", "Assembly_Locator", "module_domains"])
        writer.writeheader()
        writer.writerow({"BGC_ID": "BGC001", "Assembly_Locator": "NODE_50 region001",
                         "module_domains": "nrpspksdomains_ctg50_45_AMP-binding.1"})

    tool_path = Path(__file__).resolve().parents[1] / "tools" / "build_cohort_precompute.py"
    spec = importlib.util.spec_from_file_location("build_cohort_precompute", tool_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    out = tmp_path / "cohort.csv"
    assert module.build_nrps([str(package)], str(out)) == 1
    emitted = list(csv.DictReader(out.open(encoding="utf-8")))[0]
    assert emitted["consensus_substrate"] == "Gly"
    assert emitted["stachelhaus_substrate"] == "Ala"
    assert emitted["prediction_agreement_state"] == "SUBSTRATE_PREDICTION_CONFLICT"
    assert emitted["prediction_disposition"] == "RETAIN_BOTH_CALLS_SUBSTRATE_UNRESOLVED"
