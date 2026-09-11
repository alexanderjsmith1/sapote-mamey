"""Tests for the .343 card-verdict surfacing patch (card_verdicts.py + the four
per-BGC emitters). Self-contained: builds a tiny synthetic sealed package in tmp so
the test does not depend on any on-disk run.

What it locks in:
  1. triage_verdict reads the engine's Arch_Capacity/Class_Conf/Novelty for a BGC.
  2. rescue_for_bgc collects the Diagnostic-Rescue rows a BGC participates in.
  3. render_block surfaces a claim-safe "Engine capacity read" block.
  4. an all-DEMOTED rescue set is reported as "evaluated, NOT supported" — never as a
     live/supported hypothesis (the honesty fix); a SUPPORTED tiling is reported as such.
  5. the block carries the claim ceiling (no contig-join / no product-identity).
  6. empty package -> empty block (cards stay clean).
  7. the primary emitter (modeb_template_emitter) prints the block in §2.
"""
import csv
import os
from pathlib import Path

import pytest

from mamey import card_verdicts as cv


def _write_pkg(tmp: Path, rescue_rows):
    tri = tmp / "AS-TEST_4_triage_board.csv"
    with tri.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Arch", "Arch_Capacity", "Class_Conf", "Novelty_auto",
                    "Concordance", "Misanchor_Flag", "Standing_rule", "Primary_metab_flag"])
        w.writerow(["BGC013", "modular-PKS", "unresolved (capacity not architecture-classifiable)",
                    "LOW", "38.0", "indeterminate", "", "", ""])
        w.writerow(["BGC099", "", "", "", "", "", "", "", ""])
    resc = tmp / "AS-TEST_4B_Diagnostic_Rescue_Leads.csv"
    cols = ["pair", "rescue_tier", "kcb_concordance", "core_bgc", "core_triggers",
            "core_kcb_family", "arm_bgc", "arm_roles", "arm_kcb_family", "shared_scaffold",
            "tiling_verdict", "rggmci_gate", "safe_claim", "claim_ceiling"]
    with resc.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rescue_rows:
            w.writerow(r)
    return tmp


def _demoted_row(pair, arm):
    return {"pair": pair, "rescue_tier": "DIAGNOSTIC_RESCUE_MODERATE",
            "kcb_concordance": "indeterminate", "core_bgc": "BGC013",
            "core_triggers": "T43-IDC", "core_kcb_family": "indolocarbazole",
            "arm_bgc": arm, "arm_roles": "saccharide", "arm_kcb_family": "saccharide",
            "shared_scaffold": "NZ_KB913030",
            "tiling_verdict": "RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI",
            "rggmci_gate": "DEMOTED_TO_LOW_shared_reference_only_no_geometry_no_split_signal",
            "safe_claim": "reconstruction hypothesis only", "claim_ceiling": "not a contig join"}


def test_triage_verdict_reads_capacity(tmp_path):
    _write_pkg(tmp_path, [])
    tv = cv.triage_verdict(tmp_path, "BGC013")
    assert tv["arch_capacity"].startswith("unresolved")
    assert tv["class_conf"] == "LOW"
    assert tv["novelty_auto"] == "38.0"


def test_rescue_collects_involvement(tmp_path):
    _write_pkg(tmp_path, [_demoted_row("BGC013+BGC052", "BGC052"),
                          _demoted_row("BGC013+BGC041", "BGC041")])
    rc = cv.rescue_for_bgc(tmp_path, "BGC013")
    assert len(rc) == 2
    assert all(r["role"] == "core" for r in rc)


def test_all_demoted_is_reported_not_supported(tmp_path):
    _write_pkg(tmp_path, [_demoted_row("BGC013+BGC052", "BGC052"),
                          _demoted_row("BGC013+BGC041", "BGC041")])
    block = cv.render_block(tmp_path, "BGC013")
    assert "Engine capacity read" in block
    assert "evaluated, NOT supported" in block
    # must NOT present demoted candidates as engine-supported
    assert "engine-SUPPORTED" not in block.replace("NOT supported", "")
    # claim ceiling present
    assert "NOT a nucleotide contig join" in block or "not a contig join" in block.lower()


def test_supported_tiling_is_surfaced(tmp_path):
    row = _demoted_row("BGC013+BGC052", "BGC052")
    row["tiling_verdict"] = "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY"
    row["rggmci_gate"] = "HIGH_RG_GMCI"
    _write_pkg(tmp_path, [row])
    block = cv.render_block(tmp_path, "BGC013")
    assert "engine-SUPPORTED" in block
    assert "BGC013+BGC052" in block


def test_empty_when_no_data(tmp_path):
    # BGC099 has blank triage fields and no rescue rows -> empty block
    _write_pkg(tmp_path, [])
    assert cv.render_block(tmp_path, "BGC099") == ""


def test_accepts_str_and_none(tmp_path):
    _write_pkg(tmp_path, [_demoted_row("BGC013+BGC052", "BGC052")])
    # str path
    assert "Engine capacity read" in cv.render_block(str(tmp_path), "BGC013")
    # None pkg with pre-read data still renders
    tv = {"arch_capacity": "RiPP", "class_conf": "LOW", "novelty_auto": "53"}
    assert "RiPP" in cv.render_block(None, "BGC013", triage=tv, rescues=[])


def test_primary_emitter_prints_block(tmp_path):
    # minimal package the template emitter can render a card from
    _write_pkg(tmp_path, [_demoted_row("BGC013+BGC052", "BGC052")])
    from mamey import modeb_template_emitter as em
    card = em.emit_card_template(tmp_path, "BGC013")
    assert "Engine capacity read" in card
    assert "## §2" in card
