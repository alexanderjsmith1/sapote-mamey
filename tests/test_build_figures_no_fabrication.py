"""test_build_figures_no_fabrication.py — fail-closed guard against fabricated data in
`tools/build_figures.py` (AMBER_TH1, .353 candidate).

Three checks, all fail-closed (they FAIL on the pre-fix .352 code):

  (a) LINT — the source of tools/build_figures.py contains NO 'SID-XXX' placeholder
      literal and no hardcoded "Mode B confirmed" enediyne row (`'value':2}`).
  (b) FIXTURE — feed a tiny synthetic banked cohort into data_chemistry() and assert the
      "enediyne (genuine)" class-prevalence bar equals the count of DISTINCT strains in the
      real genuine-candidate set (2 here), not the placeholder-set collapse value of 1, and
      that the fabricated "Mode B confirmed" enediyne_stage row is gone.
  (c) RESCUE (banks) — _rescue_from_banks() sets is_classA following the real tier rule
      (rtier(0,efls)=='A'); with no n50 in the banks, is_classA is honestly 0 for every
      strain — including a strain literally named 'SID-XXX', which the pre-fix placeholder
      set would have flagged is_classA==1.
  (d) RESCUE (workbook) — data_rescue() reads is_classA from the sheet's real Tier column
      (== 'A'), not a placeholder set: a Tier-'A' row is flagged, a Tier-'D' row (including
      one named 'SID-XXX') is not.

These three builders — data_chemistry, _rescue_from_banks, data_rescue — are exactly the
three that carried fabricated placeholder data in .352.

stdlib + pytest + openpyxl (a shipped dep, used only by the (d) workbook fixture).
"""
import importlib.util
import json
import os
import sys

import pytest


# ── locate tools/build_figures.py (walk up from this test looking for tools/) ──────────
def _find_build_figures():
    env = os.environ.get("MAMEY_TOOLS_DIR")
    if env and os.path.isfile(os.path.join(env, "build_figures.py")):
        return os.path.join(env, "build_figures.py")
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "tools", "build_figures.py")
        if os.path.isfile(cand):
            return cand
        here = os.path.dirname(here)
    return None


_BF_PATH = _find_build_figures()
pytestmark = pytest.mark.skipif(_BF_PATH is None, reason="tools/build_figures.py not locatable")


def _load_build_figures():
    tools_dir = os.path.dirname(_BF_PATH)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)  # build_figures needs its sibling _wbio importable
    spec = importlib.util.spec_from_file_location("build_figures_under_test", _BF_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── (a) LINT: no fabricated literals survive in the source ─────────────────────────────
def test_lint_no_placeholder_literals_in_source():
    src = open(_BF_PATH, encoding="utf-8").read()
    assert "SID-XXX" not in src, "fabricated 'SID-XXX' placeholder literal is still present"
    assert "'value':2}" not in src, "hardcoded 'Mode B confirmed' enediyne row (value:2) still present"
    assert "'label':'Mode B confirmed'" not in src, "fabricated 'Mode B confirmed' row still present"


# ── synthetic banked cohort (minimal, enough for data_chemistry + _rescue_from_banks) ──
def _write_banks(tmp_path):
    bgc_data = {
        "strains": {"SID-A": {}, "SID-B": {}, "SID-C": {}, "SID-XXX": {}},
        "bgcs": [
            # SID-A / SID-B: genuine enediyne candidates (no hglE veto)
            {"sid": "SID-A", "bgc_id": "SID-A_BGC1", "products": "NRPS",
             "edge_status": "Interior", "length_kb": 40},
            {"sid": "SID-B", "bgc_id": "SID-B_BGC1", "products": "T1PKS",
             "edge_status": "Edge", "length_kb": 30},
            # SID-C: enediyne signal but hglE present -> vetoed (false, goes to fl)
            {"sid": "SID-C", "bgc_id": "SID-C_BGC1", "products": "hglE-KS enediyne",
             "edge_status": "Interior", "length_kb": 50},
            # SID-XXX: name collides with the pre-fix placeholder set; no enediyne marker
            {"sid": "SID-XXX", "bgc_id": "SID-XXX_BGC1", "products": "terpene",
             "edge_status": "Full-contig", "length_kb": 20},
        ],
    }
    bgc_markers = {
        "SID-A": {"SID-A_BGC1": {"cctt": ["enediyne"], "tigrfam": []}},
        "SID-B": {"SID-B_BGC1": {"cctt": [], "tigrfam": ["enediyne"]}},
        "SID-C": {"SID-C_BGC1": {"cctt": ["enediyne"], "tigrfam": []}},
    }
    (tmp_path / "bgc_data.json").write_text(json.dumps(bgc_data), encoding="utf-8")
    (tmp_path / "bgc_markers.json").write_text(json.dumps(bgc_markers), encoding="utf-8")
    return str(tmp_path)


# ── (b) FIXTURE: genuine-enediyne prevalence = real distinct strains, Mode B row gone ──
def test_data_chemistry_genuine_enediyne_is_real_not_placeholder(tmp_path):
    bf = _load_build_figures()
    banked = _write_banks(tmp_path)
    rows, cols = bf.data_chemistry(banked)

    # the fabricated "Mode B confirmed" row must be gone
    labels = [r["label"] for r in rows]
    assert "Mode B confirmed" not in labels, "fabricated 'Mode B confirmed' row is still emitted"

    # genuine-enediyne prevalence = distinct strains in the real candidate set.
    # Real candidates here: SID-A, SID-B (SID-C is hglE-vetoed) -> 2 distinct strains.
    gen_rows = [r for r in rows
                if r["panel"] == "class_prevalence" and r["label"] == "enediyne (genuine)"]
    assert len(gen_rows) == 1, "expected exactly one 'enediyne (genuine)' class-prevalence row"
    value = gen_rows[0]["value"]
    assert value == 2, f"genuine-enediyne prevalence should be the real count 2, got {value}"
    # the pre-fix placeholder set {'SID-XXX','SID-XXX'} collapses to 1 — explicitly rule it out
    assert value != 1, "prevalence collapsed to 1 -> placeholder set is still in use"

    # sanity: the enediyne_stage counts are derived from the fixture, not hardcoded
    stage = {r["label"]: r["value"] for r in rows if r["panel"] == "enediyne_stage"}
    assert stage["candidate (no hglE)"] == 2
    assert stage["hglE false (vetoed)"] == 1
    assert stage["raw signal"] == 3


# ── (c) RESCUE: is_classA follows the real tier rule, never a placeholder membership ───
def test_rescue_is_classA_follows_real_tier_rule(tmp_path):
    bf = _load_build_figures()
    banked = _write_banks(tmp_path)
    out = bf._rescue_from_banks(banked)
    by_strain = {r["strain"]: r for r in out}

    # No n50 in banks -> tier 'A' can never be assigned -> is_classA is 0 for EVERY strain.
    for r in out:
        assert int(r["is_classA"]) == 0, f"{r['strain']} flagged class-A with no tier-A source"
        assert r["tier"] != "A", f"{r['strain']} got tier A from banks (no n50 present)"

    # The killer: the pre-fix placeholder set contained 'SID-XXX', so pre-fix code set
    # is_classA==1 for a strain named 'SID-XXX'. Post-fix it must be 0 (real tier rule).
    assert "SID-XXX" in by_strain
    assert int(by_strain["SID-XXX"]["is_classA"]) == 0, \
        "SID-XXX is class-A -> the placeholder tierA set is still driving is_classA"

    # tier follows rtier(0, efls): efls==0 (<20) -> 'D' for all fixture strains
    for r in out:
        assert r["tier"] == "D", f"{r['strain']} tier {r['tier']} != expected 'D' (efls<20)"


# ── (d) RESCUE (workbook): is_classA from the real Tier column, not a placeholder ──────
def test_data_rescue_workbook_is_classA_from_tier_column(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    bf = _load_build_figures()
    wb_path = tmp_path / "master.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fragment_Rescue_Tiers"
    ws.append(["strain", "EFLS_Pairs", "Frag_Loss", "FLBR_Megasynth", "Tier"])
    ws.append(["SID-A", 700, 1.0, 2, "A"])      # genuine tier-A -> is_classA 1
    ws.append(["SID-B", 5, 0.5, 0, "D"])         # tier-D -> is_classA 0
    ws.append(["SID-XXX", 5, 0.5, 0, "D"])       # pre-fix placeholder member; must be 0 post-fix
    wb.save(str(wb_path))

    out, headers = bf.data_rescue(str(wb_path))
    by_strain = {r["strain"]: r for r in out}

    assert int(by_strain["SID-A"]["is_classA"]) == 1, "Tier 'A' row not flagged is_classA"
    assert int(by_strain["SID-B"]["is_classA"]) == 0, "Tier 'D' row wrongly flagged is_classA"
    # the killer: SID-XXX is Tier 'D' -> post-fix 0; the pre-fix placeholder set forced it to 1
    assert int(by_strain["SID-XXX"]["is_classA"]) == 0, \
        "SID-XXX (Tier 'D') flagged class-A -> placeholder set still driving data_rescue"
