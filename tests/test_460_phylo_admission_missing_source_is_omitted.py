"""16S admission: a missing isolation source is admitted and listed for omission, not refused.

Owner ruling (.460): isolation source follows the geography omission rule. Before, one row without
a deposited isolation source refused the whole roster with METADATA_INCOMPLETE. The house rule is
that a tip with no deposited source is left out of figures and listed by full name, and the rest of
the roster still builds.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_admission_fixture_460s", ROOT / "tests" / "test_phylo_sequence_admission_v97429.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
_tool = importlib.util.spec_from_file_location("phylo_sequence_admission_460s", ROOT / "tools" / "phylo_sequence_admission.py")
adm = importlib.util.module_from_spec(_tool)
_tool.loader.exec_module(adm)

A, C = "A" * 1400, "C" * 1400
NAME = "Saccharopolyspora erythraea NRRL 2338"


@pytest.mark.parametrize("missing", ["", "unknown", "missing: lab stock", "not collected", "n/a"])
def test_one_missing_source_no_longer_refuses_the_roster(missing):
    rows = [_fx.row("R1", A, isolation_source=missing, organism=NAME, accession="NR_000002.1"),
            _fx.row("R2", C, accession="NR_000003.1", organism="Saccharopolyspora gamma")]
    result = adm.validate(rows, {"R1": A, "R2": C})
    assert result["status"] == "ADMISSION_PASS"
    assert result["tips"][0]["isolation_source"] == missing          # kept as given, nothing filled in
    assert result["figure_omissions"] == [{"tip": "R1", "name": NAME, "accession": "NR_000002.1",
                                           "reason": "NO_DEPOSITED_SOURCE"}]


def test_deposited_source_is_carried_unchanged_on_each_tip():
    result = adm.validate([_fx.row("R1", A, isolation_source="Rhizosphere of Theobroma cacao, wet season")], {"R1": A})
    assert result["tips"][0]["isolation_source"] == "Rhizosphere of Theobroma cacao, wet season"
    assert result["figure_omissions"] == []


def test_missing_source_and_geography_are_both_listed():
    result = adm.validate([_fx.row("R1", A, isolation_source="", geography="")], {"R1": A})
    assert sorted(o["reason"] for o in result["figure_omissions"]) == ["NO_DEPOSITED_GEOGRAPHY", "NO_DEPOSITED_SOURCE"]


def test_evidence_and_accession_are_still_required():
    for field in ("accession", "sequence_evidence", "metadata_evidence"):
        with pytest.raises(ValueError, match=f"METADATA_INCOMPLETE: R1 field={field}"):
            adm.validate([_fx.row("R1", A, **{field: ""})], {"R1": A})
