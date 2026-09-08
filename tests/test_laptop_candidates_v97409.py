"""v9.7.409 — regression tests for the new-laptop scratch candidates (A1–A11, N1, B1–B3, CS-2, V1).

Each test names the finding it guards. The finding numbering follows
`EVAL_new_laptop_scratch_candidates_2026-09-04.md` (Black Cherry lane). Synthetic inputs only.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


# ── A1 / RUN-1: the CLI must import (so `doctor`, `--help`, `--version` run) without openpyxl ──
def test_a1_cli_imports_with_openpyxl_absent():
    code = ("import sys; sys.modules['openpyxl'] = None; import mamey.cli; print('IMPORT_OK')")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                       env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    assert "IMPORT_OK" in r.stdout, r.stderr[-800:]


def test_a1_master_workbook_not_imported_at_cli_module_level():
    src = (ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    assert not re.search(r"^from \.master_workbook import", src, re.M)


# ── A2: Low ranks strictly above Inventory in the activity lead report ──
def test_a2_tier_order_low_above_inventory():
    from mamey.activity_lead_report import TIER_ORDER
    assert TIER_ORDER["low"] > TIER_ORDER["inventory"]
    assert TIER_ORDER["medium"] > TIER_ORDER["low"]


# ── A3: deliverables_registry render path no longer calls str(content, end="") ──
def test_a3_registry_render_stdout_path_is_valid_python_call():
    from mamey import deliverables_registry as dr
    import ast
    tree = ast.parse((ROOT / "mamey" / "deliverables_registry.py").read_text(encoding="utf-8"))
    bad = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "str"
           and any(k.arg == "end" for k in n.keywords)]
    assert not bad, "str(..., end=...) call still present"
    assert hasattr(dr, "render_menu")


# ── A5: shipped schema names the field the emitter writes ──
def test_a5_citation_compact_schema_matches_emitter_field():
    schema = json.loads((ROOT / "schemas" / "lead_record_citation_compact_v1.schema.json").read_text())
    assert "interpretation_scope" in schema["required"]
    assert "interpretation_scope" in schema["properties"]
    assert "claim_scope" not in json.dumps(schema)


# ── A6 / G4: lead-page predicate fails CLOSED when the exclusion check cannot import ──
def test_a6_lead_predicate_fails_closed_on_import_failure(monkeypatch):
    from mamey import lead_pages
    monkeypatch.setitem(sys.modules, "mamey.scoring", None)
    assert lead_pages._is_lead({"Lead_tier_auto": "High"}) is False


# ── A7 / G3: both receipt paths treat an import-unavailable structure gate as UNVERIFIED ──
def test_a7_receipt_import_unavailable_branch_is_fail_closed_at_both_sites():
    src = (ROOT / "mamey" / "mode_b_receipt.py").read_text(encoding="utf-8")
    assert src.count('raise ImportError("modeb_structure_gate import failed")') == 2


# ── A8 / SF-1 / G2: a card whose lint crashes is structurally invalid, not silently valid ──
def test_a8_compilation_gate_counts_lint_crash_as_invalid(monkeypatch):
    sys.path.insert(0, str(ROOT / "tools"))
    import compilation_gate as cg
    import mamey.modeb_structure_gate as sg
    monkeypatch.setattr(cg, "_split_cards", lambda md: [("BGC001", "card text")])
    def boom(*a, **k):
        raise RuntimeError("synthetic lint crash")
    monkeypatch.setattr(sg, "lint_card", boom)
    ok, messages, _n = cg.g2_modeb_coverage("# whatever", 1)
    assert ok is False
    assert any("lint-crash" in m for m in messages), messages


# ── A9 / G1: an unreadable XML makes the zero-alignment audit PARTIAL (exit 3), never a clean bill ──
def test_a9_zero_alignment_audit_partial_on_unreadable_xml(tmp_path):
    (tmp_path / "batch1.xml").write_text("<not really xml", encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "audit_blastp_zero_alignment.py"),
                        "--xml", str(tmp_path)], capture_output=True, text=True,
                       env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    assert r.returncode == 3, (r.returncode, r.stdout, r.stderr)
    assert "PARTIAL" in r.stderr
    assert "genuine tested-negatives" not in r.stdout


# ── A10: timing_breakdown receipts are excluded from the checksum set by suffix ──
def test_a10_timing_breakdown_excluded_from_checksums(tmp_path):
    from mamey.packaging import MUTABLE_RECEIPT_SUFFIXES, write_checksums
    assert "_timing_breakdown.json" in MUTABLE_RECEIPT_SUFFIXES
    assert "_timing_breakdown.csv" in MUTABLE_RECEIPT_SUFFIXES
    assert "_judgment_register.json" in MUTABLE_RECEIPT_SUFFIXES
    (tmp_path / "TEST-01_timing_breakdown.json").write_text("{}", encoding="utf-8")
    (tmp_path / "TEST-01_timing_breakdown.csv").write_text("a,b\n", encoding="utf-8")
    (tmp_path / "TEST-01_1_intake.json").write_text("{}", encoding="utf-8")
    write_checksums(tmp_path)
    listed = (tmp_path / "checksums_sha256.txt").read_text(encoding="utf-8")
    assert "TEST-01_1_intake.json" in listed
    assert "timing_breakdown" not in listed


def test_a10_validate_uses_the_same_suffix_tuple():
    src = (ROOT / "mamey" / "validate.py").read_text(encoding="utf-8")
    assert "endswith('_judgment_register.json')" not in src
    assert 'endswith("_judgment_register.json")' not in src
    assert "mutable_suffixes = ('_judgment_register.json',)" not in src


# ── A11: the zero-byte tool is gone ──
def test_a11_zero_byte_tool_removed():
    assert not (ROOT / "tools" / "wac_validation_genelevel.py").exists()


# ── B1: validate honours claim_safety_status FAIL, waivable by FILE only ──
def test_b1_claim_safety_status_blocks(tmp_path):
    from mamey.validate import claim_safety_status_blocks, CLAIM_SAFETY_WAIVER_NAME
    (tmp_path / "manifest.json").write_text(json.dumps({"claim_safety_status": "FAIL"}), encoding="utf-8")
    assert claim_safety_status_blocks(tmp_path) == (True, "FAIL")
    (tmp_path / CLAIM_SAFETY_WAIVER_NAME).write_text("{}", encoding="utf-8")
    assert claim_safety_status_blocks(tmp_path) == (False, "FAIL_WAIVED")
    (tmp_path / "manifest.json").write_text(json.dumps({"claim_safety_status": "PASS"}), encoding="utf-8")
    assert claim_safety_status_blocks(tmp_path) == (False, "PASS")
    (tmp_path / "manifest.json").write_text(json.dumps({}), encoding="utf-8")
    assert claim_safety_status_blocks(tmp_path) == (False, "ABSENT")


def test_b1_validate_chain_reads_claim_safety_before_gold_completeness():
    src = (ROOT / "mamey" / "validate.py").read_text(encoding="utf-8")
    i_cs = src.index("    elif _cs_blocks:")
    i_gold = src.index('    elif result.get("gold_completeness") == "FAIL":')
    assert i_cs < i_gold


# ── B2: finished-profile verify promotes CLAIM_SAFETY to blocking; export refuses overclaims ──
def test_b2_verify_modeb_parser_has_force_flag():
    from mamey.cli import build_parser  # noqa
    p = build_parser()
    ns = p.parse_args(["verify-modeb", "card.md", "--force"])
    assert ns.force is True


def test_b2_export_refuses_overclaiming_card_unless_forced(tmp_path):
    from mamey.modeb_export import export_card, claim_safety_findings_for_export
    md = "# BGC001\n\n## §1 Boundary\n\nThis cluster produces streptomycin.\n"
    assert claim_safety_findings_for_export(md), "probe phrase must be flagged by the structure gate"
    card = tmp_path / "TEST-01_BGC001_mode_b.md"
    card.write_text(md, encoding="utf-8")
    res = export_card(card, outdir=tmp_path, formats=("docx",))
    assert res["status"] == "REFUSED_CLAIM_SAFETY"
    assert res["docx"]["status"] == "REFUSED_CLAIM_SAFETY"
    assert not list(tmp_path.glob("*.docx"))
    from mamey.modeb_export import _print_result
    assert _print_result(res) == 1
    forced = export_card(card, outdir=tmp_path, formats=("docx",), force=True)
    assert forced.get("status") != "REFUSED_CLAIM_SAFETY"


# ── B3 / SF-2: a crashed bioactivity check is a finding, never a silent pass ──
def test_b3_lint_text_reports_linter_unavailable(monkeypatch):
    from mamey import claim_safety_gate as g
    monkeypatch.setitem(sys.modules, "claim_safety_linter", None)
    out = g.lint_text("The BGC001 cluster shows antibacterial activity against Staphylococcus aureus.")
    assert any("CLAIM_SAFETY_LINTER_UNAVAILABLE" in f for f in out), out


# ── CS-2 (receipt-gated): the three verbs with zero false positives over 1,559 finished cards ──
@pytest.mark.parametrize("verb", ["assembles", "elaborates", "secretes"])
def test_cs2_zero_fp_verbs_are_now_production_verbs(verb):
    from mamey.claim_safety_gate import lint_text
    assert lint_text(f"BGC001 {verb} streptomycin."), verb


def test_cs2_capacity_phrasing_still_clean():
    from mamey.claim_safety_gate import lint_text
    assert lint_text("BGC001 encodes a polyketide synthase with capacity consistent with a macrolide class.") == []


# ── V1: the vacuous inventory test is gone (a test that cannot fail is not a gate) ──
def test_v1_vacuous_inventory_test_removed():
    src = (ROOT / "tests" / "test_no_unpublished_ids_in_public_tier.py").read_text(encoding="utf-8")
    assert "def test_as_mention_inventory" not in src
    import ast
    bare = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assert)
            and isinstance(n.test, ast.Constant) and n.test.value is True]
    assert not bare, "a bare `assert True` statement is still present"
