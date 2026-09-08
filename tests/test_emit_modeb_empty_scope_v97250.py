"""P-emit-01 (docs lineage v9.7.243, merged at the v9.7.250 consolidation).

`emit-modeb-template --batch --scope leads` exited 0 when no BGC carried
`Lead_tier_auto` in {HIGH, PRIORITY_ISO, HIGH_SEQ}. W3 of the Sapote workflow checks for the
`mode_b_templates/` directory; an exit-0 with an empty directory reads as PASS while producing no
templates, so W4 (cards authored + verified) blocks with no stated cause.

Exit 3 names the condition. `--fail-on-empty` generalises it to any scope.
"""
from __future__ import annotations
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.mode_b_receipt import emit_modeb_template_command  # noqa: E402


def _args(scope, pkg, fail_on_empty=False):
    return argparse.Namespace(package=str(pkg), bgc=None, batch=True, scope=scope,
                              top_n=None, out=None, fail_on_empty=fail_on_empty)


def _board(pkg, tier):
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "STRAIN_4_triage_board.csv").write_text(
        "Rank,BGC_ID,Lead_tier_auto,Corrected_rank,Standing_rule,Primary_metab_flag\r\n"
        f"1,BGC001,{tier},1,,\r\n"
    )
    return pkg


def test_scope_leads_exits_3_when_no_high_bgcs(tmp_path):
    rc = emit_modeb_template_command(_args("leads", _board(tmp_path / "pkg", "Medium")))
    assert rc == 3, f"expected exit 3 for --scope leads on a Medium-only package, got {rc}"


def test_scope_leads_exits_3_on_inventory_only(tmp_path):
    rc = emit_modeb_template_command(_args("leads", _board(tmp_path / "inv", "Inventory")))
    assert rc == 3, f"expected exit 3 for --scope leads on an Inventory-only package, got {rc}"


def test_scope_all_never_exits_3_when_a_bgc_exists(tmp_path):
    rc = emit_modeb_template_command(_args("all", _board(tmp_path / "all", "Medium")))
    assert rc != 3, f"--scope all emits whatever is present; should not exit 3, got {rc}"


def test_fail_on_empty_does_not_fire_when_something_is_emitted(tmp_path):
    rc = emit_modeb_template_command(_args("all", _board(tmp_path / "fe", "Inventory"), fail_on_empty=True))
    assert rc != 3, f"--fail-on-empty with 1 template emitted must not exit 3, got {rc}"


def test_scope_leads_does_not_exit_3_when_a_high_bgc_is_present(tmp_path):
    rc = emit_modeb_template_command(_args("leads", _board(tmp_path / "hi", "High")))
    assert rc != 3, f"--scope leads with a HIGH BGC must not exit 3, got {rc}"


def test_missing_triage_board_is_exit_1_not_exit_3(tmp_path):
    """A missing board is an error (1), not an empty scope (3). The codes must stay distinct."""
    pkg = tmp_path / "empty"; pkg.mkdir()
    rc = emit_modeb_template_command(_args("leads", pkg))
    assert rc == 1, f"missing triage board should exit 1 (skipped_reason), got {rc}"
