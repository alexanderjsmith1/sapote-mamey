"""16S admission keeps deposited geography on each tip; the ten-value list is a display field only.

`tools/phylo_sequence_admission.py` refused any geography outside a ten-value list, so a roster had to
carry continent bins instead of the deposited text. The house rule is to report geography as deposited
and never bin, infer or fix it. A tip with no deposited geography stays blank and is omitted from
figures, listed by full name.
"""
import csv
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_admission_fixture_459g", ROOT / "tests" / "test_phylo_sequence_admission_v97429.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
_tool = importlib.util.spec_from_file_location("phylo_sequence_admission_459g", ROOT / "tools" / "phylo_sequence_admission.py")
adm = importlib.util.module_from_spec(_tool)
_tool.loader.exec_module(adm)

SEQ = "A" * 1400
TEN = ("US", "Canada", "North America (other)", "South America", "Europe",
       "Asia", "Africa", "Oceania", "Antarctica", "Indian Ocean")


def _one(geography, **kw):
    result = adm.validate([_fx.row("R1", SEQ, geography=geography, **kw)], {"R1": SEQ})
    assert result["status"] == "ADMISSION_PASS"
    (tip,) = result["tips"]
    return result, tip


def test_deposited_value_outside_the_list_is_admitted_unchanged():
    result, tip = _one("Panama: Barro Colorado Island")
    assert tip["tip"] == "R1"
    assert tip["geography"] == "Panama: Barro Colorado Island"
    assert result["figure_omissions"] == []


def test_former_refusal_example_is_admitted_unchanged():
    _, tip = _one("Yunnan Province")
    assert tip["geography"] == "Yunnan Province"
    assert (tip["geography_region"], tip["geography_region_basis"]) == ("", "NOT_DERIVED")


@pytest.mark.parametrize("deposited, region, basis", [
    ("Panama: Barro Colorado Island", "North America (other)", "COUNTRY_TABLE"),
    ("USA: Wisconsin, Madison", "US", "COUNTRY_TABLE"),
    ("United States of America: Iowa", "US", "COUNTRY_TABLE"),
    ("Mexico: Oaxaca", "North America (other)", "COUNTRY_TABLE"),
    ("Canada: Ontario", "Canada", "LIST_VALUE"),
    ("China: Yunnan", "Asia", "COUNTRY_TABLE"),
    ("Brazil: Amazonas", "South America", "COUNTRY_TABLE"),
    ("Asia", "Asia", "LIST_VALUE"),
    ("Indian Ocean: Maldives", "Indian Ocean", "LIST_VALUE"),
    ("Antarctica", "Antarctica", "LIST_VALUE"),
    # a guess would be needed: blank, never binned
    ("North America", "", "NOT_DERIVED"),
    ("USSR", "", "NOT_DERIVED"),
    ("Pacific Ocean", "", "NOT_DERIVED"),
    ("Yunnan Province", "", "NOT_DERIVED"),
])
def test_display_region_is_derived_only_without_guessing(deposited, region, basis):
    _, tip = _one(deposited)
    assert tip["geography"] == deposited               # deposited text is never overwritten
    assert tip["geography_region"] == region
    assert tip["geography_region_basis"] == basis
    assert tip["geography_region"] in TEN + ("",)


@pytest.mark.parametrize("missing", ["", "unknown", "missing: lab stock", "not collected"])
def test_missing_geography_stays_missing_and_is_listed_for_omission(missing):
    result, tip = _one(missing, organism="Saccharopolyspora erythraea NRRL 2338", accession="NR_000002.1")
    assert tip["geography"] == missing                 # nothing inferred or filled in
    assert (tip["geography_region"], tip["geography_region_basis"]) == ("", "NOT_RECORDED")
    assert result["figure_omissions"] == [{"tip": "R1", "name": "Saccharopolyspora erythraea NRRL 2338",
                                           "accession": "NR_000002.1", "reason": "NO_DEPOSITED_GEOGRAPHY"}]


def test_missing_isolation_source_is_still_refused():
    with pytest.raises(ValueError, match="METADATA_INCOMPLETE: R1 field=isolation_source"):
        adm.validate([_fx.row("R1", SEQ, isolation_source="")], {"R1": SEQ})


def test_ten_value_list_is_kept_as_the_display_list():
    assert tuple(adm.GEOGRAPHY_REGIONS) == TEN


def test_cli_receipt_carries_deposited_geography_per_tip(tmp_path):
    row = _fx.row("R1", SEQ, geography="Panama: Barro Colorado Island")
    roster = tmp_path / "roster.tsv"
    with open(roster, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(row), delimiter="\t")
        w.writeheader()
        w.writerow(row)
    fasta = tmp_path / "seqs.fasta"
    fasta.write_text(f">R1\n{SEQ}\n")
    out = tmp_path / "receipt.json"
    assert adm.main(["--roster", str(roster), "--fasta", str(fasta), "--json", str(out)]) == 0
    receipt = json.loads(out.read_text())
    assert receipt["status"] == "ADMISSION_PASS"
    assert receipt["tips"][0]["geography"] == "Panama: Barro Colorado Island"
    assert receipt["tips"][0]["geography_region"] == "North America (other)"
    assert receipt["geography_note"] == adm.GEOGRAPHY_NOTE


def test_receipt_states_deposited_text_is_the_record_and_region_is_display_only():
    result, tip = _one("Panama: Barro Colorado Island")
    note = result["geography_note"]
    assert note == adm.GEOGRAPHY_NOTE
    assert "deposited text" in note and "the record" in note and "display-only" in note
    assert "never written back" in note
    assert tip["geography"] == "Panama: Barro Colorado Island"   # the region did not replace it
