import csv
from pathlib import Path

import pytest

from mamey import card_verdicts as CV
from mamey.report_card import render_report_cards


RESCUE_HEADERS = "core_bgc,arm_bgc,pair,tiling_verdict\n"


class _CSVFailureSource:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def __iter__(self): return self
    def __next__(self): raise csv.Error("bad CSV")


def _fail_path_open(monkeypatch, source, error):
    real_open = Path.open
    def fail_source(self, *args, **kwargs):
        if self == source:
            if isinstance(error, OSError):
                raise error
            return _CSVFailureSource()
        return real_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_source)


def _report_package(tmp_path):
    (tmp_path / "TEST-STRAIN_4_triage_board.csv").write_text(
        "Rank,Corrected_rank,BGC_ID,Contig,antiSMASH_Region,Products,KCB_score,"
        "Novelty_auto,AB_auto,AF_auto\n"
        "1,1,BGC001,NODE_1,region001,NRPS,0,0,0,0\n",
        encoding="utf-8",
    )
    return tmp_path


def _render(tmp_path):
    return render_report_cards(str(tmp_path))["markdown"]


@pytest.mark.parametrize("error", [OSError("source unreadable"), csv.Error("bad CSV")])
def test_report_consumer_types_rescue_read_failures(tmp_path, monkeypatch, error):
    _report_package(tmp_path)
    rescue = tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv"
    rescue.write_text(RESCUE_HEADERS, encoding="utf-8")
    _fail_path_open(monkeypatch, rescue, error)
    text = _render(tmp_path)
    expected = "UNREADABLE" if isinstance(error, OSError) else "INVALID_CSV"
    assert f"Diagnostic-Rescue source: {expected}" in text
    assert "evidence unresolved, not absent" in text


def test_report_consumer_types_invalid_rescue_schema(tmp_path):
    _report_package(tmp_path)
    (tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv").write_text(
        "arbitrary,columns\na,b\n", encoding="utf-8"
    )
    text = _render(tmp_path)
    assert "Diagnostic-Rescue source: INVALID_SCHEMA (MissingColumns)" in text
    assert "evidence unresolved, not absent" in text


@pytest.mark.parametrize("source", ["ABSENT", "VALID_EMPTY"])
def test_report_consumer_preserves_absent_and_valid_empty_rescue_states(tmp_path, source):
    _report_package(tmp_path)
    if source == "VALID_EMPTY":
        (tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv").write_text(
            RESCUE_HEADERS, encoding="utf-8"
        )
    text = _render(tmp_path)
    assert "Diagnostic-Rescue source:" not in text
    assert "evidence unresolved, not absent" not in text


@pytest.mark.parametrize("failure", ["OSERROR", "CSV", "SCHEMA"])
def test_render_block_types_triage_source_failures(tmp_path, monkeypatch, failure):
    triage = tmp_path / "TEST-STRAIN_4_triage_board.csv"
    triage.write_text("BGC_ID,Arch_Capacity\nBGC001,RiPP\n", encoding="utf-8")
    if failure == "SCHEMA":
        triage.write_text("arbitrary,columns\na,b\n", encoding="utf-8")
    else:
        error = OSError("source unreadable") if failure == "OSERROR" else csv.Error("bad CSV")
        _fail_path_open(monkeypatch, triage, error)
    text = CV.render_block(tmp_path, "BGC001")
    expected = {"OSERROR": "UNREADABLE", "CSV": "INVALID_CSV", "SCHEMA": "INVALID_SCHEMA"}[failure]
    assert f"triage source status:** {expected}" in text
    assert "evidence is unresolved, not absent" in text


def test_legacy_readers_remain_dict_and_list(tmp_path):
    _report_package(tmp_path)
    (tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv").write_text(
        RESCUE_HEADERS + "BGC001,BGC002,pair-1,RECONSTRUCTION_SUPPORTED_COMPLEMENTARY\n",
        encoding="utf-8",
    )
    assert isinstance(CV.triage_verdict(tmp_path, "BGC001"), dict)
    assert isinstance(CV.rescue_for_bgc(tmp_path, "BGC001"), list)
    assert CV.triage_verdict_status(tmp_path, "BGC001").status == "VALID"
    assert CV.rescue_for_bgc_status(tmp_path, "BGC001").status == "VALID"


def test_modeb_template_consumer_preserves_rescue_read_failure(tmp_path, monkeypatch):
    _report_package(tmp_path)
    rescue = tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv"
    rescue.write_text(RESCUE_HEADERS, encoding="utf-8")
    _fail_path_open(monkeypatch, rescue, OSError("source unreadable"))
    from mamey import modeb_template_emitter as emitter
    card = emitter.emit_card_template(tmp_path, "BGC001")
    assert "Diagnostic-Rescue source status:** UNREADABLE" in card
    assert "evidence is unresolved, not absent" in card
