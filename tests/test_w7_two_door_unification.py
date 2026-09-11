"""W7 — two-door lint unification: verify-modeb and ingest/record must evaluate the
SAME context. Pins door symmetry BY CONSTRUCTION (full tctx merge, whitelist retired).
"""
from __future__ import annotations

import json
import pathlib

from tests._modeb_card_fixtures import valid_modeb_card_stub


def _mk_pkg(tmp_path: pathlib.Path, strain_id: str = "AS-XXX") -> pathlib.Path:
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain_id}))
    (pkg / "manifest_short.json").write_text(json.dumps({"strain_id": strain_id}))
    # triage board with a high-priority roll-up surface + one BGC
    (pkg / f"{strain_id}_4_triage_board.csv").write_text(
        "BGC_ID,Products,Corrected_rank,Standing_rule,Lead_tier_auto\n"
        "BGC001,NRPS,1,,HIGH\n"
        "BGC002,NRPS,2,,HIGH\n"
        "BGC003,terpene,3,,HIGH\n"
        "BGC004,terpene,4,,HIGH\n")
    # modules table so module_count binds for BGC001
    (pkg / f"{strain_id}_3_antismash_modules.csv").write_text(
        "bgc_id,feature_type\nBGC001,aSModule\nBGC001,aSModule\n")
    return pkg


def test_every_triage_ctx_key_reaches_the_verify_door(tmp_path):
    """The structural pin: NO whitelist — every key the triage builder computes must be
    visible to the verify door's ctx (authored values may override, but the KEY exists)."""
    from mamey.mode_b_receipt import _bgc_context_from_triage
    from mamey.authored_verify import _bgc_context_from_package

    pkg = _mk_pkg(tmp_path)
    tctx = _bgc_context_from_triage(pkg, "BGC001")
    vctx = _bgc_context_from_package(pkg, "BGC001")
    assert tctx, "fixture must produce a triage ctx"
    missing = [k for k in tctx if k not in vctx]
    assert not missing, (
        f"triage-ctx keys invisible at the verify door (whitelist regression): {missing}")


def test_predicate_inputs_agree_across_doors(tmp_path):
    """module_count / strain_high_priority_count computed once, seen identically."""
    from mamey.mode_b_receipt import _bgc_context_from_triage
    from mamey.authored_verify import _bgc_context_from_package

    pkg = _mk_pkg(tmp_path)
    tctx = _bgc_context_from_triage(pkg, "BGC001")
    vctx = _bgc_context_from_package(pkg, "BGC001")
    assert tctx.get("module_count") == 2
    assert vctx.get("module_count") == 2
    assert tctx.get("strain_high_priority_count") == 4
    assert vctx.get("strain_high_priority_count") == 4


def test_both_doors_same_verdict_on_underauthored_card(tmp_path):
    """A §1–§30 card for a MEASURED-assembly-line BGC (2 aSModule) must draw
    MISSING_CONDITIONAL_SECTION §32–§34 at BOTH doors — not just ingest."""
    from mamey.mode_b_receipt import _bgc_context_from_triage
    from mamey.authored_verify import _bgc_context_from_package
    from mamey import modeb_structure_gate as g

    pkg = _mk_pkg(tmp_path)
    card = valid_modeb_card_stub("BGC001", strain_id="AS-XXX")

    def missing_conditionals(ctx):
        f = g.lint_card(card, bgc_context=ctx)
        return sorted(x["section"] for x in f
                      if x.get("code") == "MISSING_CONDITIONAL_SECTION")

    ingest = missing_conditionals(_bgc_context_from_triage(pkg, "BGC001"))
    verify = missing_conditionals(_bgc_context_from_package(pkg, "BGC001"))
    assert ingest == verify, f"door divergence: ingest={ingest} verify={verify}"
    assert set(ingest) >= {32, 33, 34}, (
        "measured assembly line (2 aSModule) must require §32–§34")


def test_authored_values_keep_precedence(tmp_path):
    """The merge must not clobber richer package-derived values with raw triage strings."""
    from mamey.authored_verify import _bgc_context_from_package

    pkg = _mk_pkg(tmp_path)
    vctx = _bgc_context_from_package(pkg, "BGC001")
    # products/is_ripp/boundary are authored-door derivations; they must remain the
    # authored-door types (products lower-cased by that door), not the raw triage row's.
    assert vctx.get("bgc_id") == "BGC001"
    if "products" in vctx:
        assert vctx["products"] == vctx["products"].lower()


def test_no_triage_board_still_degrades_cleanly(tmp_path):
    """Missing triage board: verify door falls back exactly as before (no raise, ctx built)."""
    from mamey.authored_verify import _bgc_context_from_package

    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX", "bgcs": []}))
    vctx = _bgc_context_from_package(pkg, "BGC001")
    assert vctx.get("bgc_id") == "BGC001"
