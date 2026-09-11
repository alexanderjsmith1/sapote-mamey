"""B2 Phase 2 structured evaluator framework tests.

The first batch converts selected manual cassette concepts into deterministic
support/caution evaluators while keeping global Phase 2 backends inactive.
"""
from pathlib import Path
import csv
import re

from mamey.b2_structured_evaluators import (
    FIRST_BATCH_IDS,
    calls_to_dicts,
    caution_calls,
    evaluate_structured_cassettes,
    read_annotation_rows_csv,
    support_calls,
    write_structured_evaluator_report,
)
from mamey.registry_detector import ACTIVE_DETECTORS, PHASE2_DETECTORS


FIX = Path(__file__).resolve().parent / "fixtures" / "tiny_public" / "b2_structured_evaluators"


def _fixture_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _rows_for(path, fixture):
    return [r for r in _fixture_rows(path) if r["fixture"] == fixture]


def _by_id(calls):
    return {c.cassette_id: c for c in calls}


def test_phase2_backends_are_not_globally_activated():
    assert ACTIVE_DETECTORS == frozenset({"regex", "motif"})
    assert {"pfam", "tigrfam", "hmm", "diamond", "blastp"} <= PHASE2_DETECTORS


def test_first_batch_ids_are_expected():
    assert FIRST_BATCH_IDS == ("SMC-001", "SMC-002", "SMC-004", "SMC-009", "SMC-013", "SMC-016")


def test_positive_fixture_supports_each_first_batch_cassette():
    positives = FIX / "positive_cassette_rows.csv"
    expectations = {
        "nucleoside_positive": "SMC-001",
        "phosphonate_positive": "SMC-002",
        "aminocyclitol_positive": "SMC-004",
        "tetronate_positive": "SMC-009",
        "thioamitide_positive": "SMC-013",
        "self_protection_positive": "SMC-016",
    }
    for fixture, cid in expectations.items():
        calls = _by_id(evaluate_structured_cassettes(_rows_for(positives, fixture)))
        assert calls[cid].status == "SUPPORT"
        assert calls[cid].support_flags == [f"{cid}_SUPPORT"]
        assert calls[cid].claim_ceiling
        assert calls[cid].evidence_loci


def test_negative_fixtures_block_or_caution_correctly():
    negatives = FIX / "negative_guard_rows.csv"

    calls = _by_id(evaluate_structured_cassettes(_rows_for(negatives, "nucleoside_missing_marker")))
    assert calls["SMC-001"].status == "ABSENT"

    calls = _by_id(evaluate_structured_cassettes(_rows_for(negatives, "phosphonate_missing_pepm")))
    assert calls["SMC-002"].status == "ABSENT"

    calls = _by_id(evaluate_structured_cassettes(_rows_for(negatives, "aph_aac_sugar_context_negative")))
    assert calls["SMC-004"].status == "CAUTION"
    assert calls["SMC-016"].status == "CAUTION"

    calls = _by_id(evaluate_structured_cassettes(_rows_for(negatives, "tetronate_mobile_caution")))
    assert calls["SMC-009"].status == "SUPPORT_WITH_CAUTION"
    assert calls["SMC-009"].support_flags
    assert calls["SMC-009"].caution_flags

    calls = _by_id(evaluate_structured_cassettes(_rows_for(negatives, "thioamitide_ycao_only_negative")))
    assert calls["SMC-013"].status == "ABSENT"

    calls = _by_id(evaluate_structured_cassettes(_rows_for(negatives, "self_protection_mobile_negative")))
    assert calls["SMC-016"].status == "CAUTION"


def test_report_writer_outputs_claim_ceiling_and_flags(tmp_path):
    rows = _rows_for(FIX / "positive_cassette_rows.csv", "tetronate_positive")
    calls = evaluate_structured_cassettes(rows)
    out = write_structured_evaluator_report(calls, tmp_path / "structured_calls.csv")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "SMC-009" in text
    assert "claim_ceiling" in text
    assert "SMC-009_SUPPORT" in text


def test_public_fixtures_have_no_private_strain_literals():
    private_strain_re = re.compile(r"\bA" + r"S-\d{3,}\b")
    hits = []
    for path in FIX.rglob("*"):
        if path.is_file() and private_strain_re.search(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(str(path.relative_to(FIX)))
    assert not hits


def test_structured_calls_are_serializable():
    rows = _rows_for(FIX / "positive_cassette_rows.csv", "nucleoside_positive")
    calls = evaluate_structured_cassettes(rows)
    payload = calls_to_dicts(calls)
    assert isinstance(payload, list)
    assert any(r["cassette_id"] == "SMC-001" and r["status"] == "SUPPORT" for r in payload)
    assert support_calls(calls)
    assert not caution_calls(calls)
