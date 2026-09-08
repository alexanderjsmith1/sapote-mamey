"""Static contract tests for v9.7.148 patches.

Tests:
  - PATCH-MODEB-BLASTP-AUTO: modeb_blastp module interface
  - PATCH-AUTO-FIGURES: gold figure triggers in cli.py
  - PATCH-COMPILED-OUTPUT: execution slice sections 12-13
  - PATCH-MYCO-DISAMBIGUATION: mycofactocin rule in execution slice
"""
from pathlib import Path
import sys, tempfile, types

ROOT = Path(__file__).resolve().parents[1]


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── PATCH-MODEB-BLASTP-AUTO ───────────────────────────────────────────────────

def test_modeb_blastp_module_exists():
    assert (ROOT / "mamey" / "modeb_blastp.py").exists()


def test_modeb_blastp_exports_emit_for_bgc():
    src = text("mamey/modeb_blastp.py")
    assert "def emit_for_bgc(" in src
    assert "def command(" in src
    assert "BlastpBatchEmitter" in src


def test_modeb_blastp_cli_subcommand_registered():
    cli = text("mamey/cli.py")
    assert '"modeb-blastp"' in cli
    assert "--package" in cli
    assert "--bgc" in cli
    assert "--start-batch" in cli
    assert "modeb_blastp" in cli


def test_modeb_blastp_nonblocking_returns_manifest():
    """emit_for_bgc must return a dict with status key, never raise."""
    sys.path.insert(0, str(ROOT))
    from mamey.modeb_blastp import emit_for_bgc
    with tempfile.TemporaryDirectory() as d:
        result = emit_for_bgc(d, "BGC999")
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ("OK", "SKIPPED", "ERROR")


def test_modeb_blastp_skips_cleanly_on_missing_panel():
    sys.path.insert(0, str(ROOT))
    from mamey.modeb_blastp import emit_for_bgc
    with tempfile.TemporaryDirectory() as d:
        result = emit_for_bgc(d, "BGC044")
    assert result["status"] == "SKIPPED"
    assert result["batch_count"] == 0
    assert "note" in result


# ── PATCH-AUTO-FIGURES ────────────────────────────────────────────────────────

def test_single_strain_gold_figure_trigger_in_cli():
    cli = text("mamey/cli.py")
    assert "cohort_figures import generate as _gen_single_figs" in cli
    assert "gold_figures" in cli
    assert "GOLD_FIGURES_REQUIRE_GOLD_MODE" in cli


def test_multi_strain_gold_figure_trigger_in_cli():
    cli = text("mamey/cli.py")
    assert "cohort_figures import generate as _gen_multi_figs" in cli
    assert "cohort_figures_gold" in cli
    assert "len(_gold_pkgs) >= 2" in cli


def test_gold_figure_trigger_is_nonblocking():
    cli = text("mamey/cli.py")
    # Both triggers must be inside try/except blocks
    single_idx = cli.find("_gen_single_figs")
    multi_idx = cli.find("_gen_multi_figs")
    # Check try appears before each generate call
    assert "try:" in cli[max(0, single_idx - 300):single_idx]
    assert "try:" in cli[max(0, multi_idx - 300):multi_idx]


# ── PATCH-COMPILED-OUTPUT ─────────────────────────────────────────────────────

def test_rc1_no_figures_rendered_detection():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "NO_FIGURES_RENDERED.md" in exe
    assert "render-figures" in exe


def test_judgment_pending_banner():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "JUDGMENT PENDING" in exe
    assert "EXTRACTION COMPLETE" in exe


def test_gold_figures_in_handback():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "gold_figures/" in exe
    assert "cohort_figures_gold/" in exe


def test_compiled_report_required():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "Analysis_Report" in exe
    assert "required deliverable" in exe
    assert "Executive summary" in exe
    assert "Triage board" in exe
    assert "Fermentation and wet-lab guidance" in exe


def test_section_16_blastp_emission_rule():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "modeb-blastp" in exe
    assert "§16" in exe
    assert "FASTA files" in exe or "FASTA" in exe


# ── PATCH-MYCO-DISAMBIGUATION ─────────────────────────────────────────────────

def test_mycofactocin_disambiguation_rule():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "mycofactocin" in exe.lower()
    assert "TIGR03996" in exe
    assert "TIGR03997" in exe
    assert "TIGR03967" in exe
    assert "MftD" in exe
    assert "MftE" in exe


def test_mycofactocin_overrides_spasm():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "TIGR04085" in exe
    assert "regardless of whether TIGR04085" in exe or "SPASM" in exe


def test_mycofactocin_excluded_from_leads():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "cofactor" in exe
    assert "not an antibiotic" in exe or "Inventory / cofactor" in exe


# ── PATCH-NODE-CITATION-ENFORCEMENT ──────────────────────────────────────────

def test_node_citation_rule_in_execution_slice():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "## 15" in exe
    assert "node/contig citation" in exe.lower() or "node citation" in exe.lower()
    assert "NODE_" in exe
    assert "bare" in exe.lower()


def test_node_citation_format_specified():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    # Required format must be present
    assert "NODE_1 · r001" in exe or "NODE_" in exe
    assert "first mention" in exe
    assert "subsequent" in exe


def test_node_citation_rule_in_claude_start_here():
    src = text("CLAUDE_START_HERE.md")
    assert "node" in src.lower()
    assert "region" in src.lower()
    # Should have the strong form
    assert "never acceptable" in src or "must" in src.lower()


def test_node_citation_map_emitter_in_cli():
    cli = text("mamey/cli.py")
    assert "node_citation_map.json" in cli
    assert "W7" in cli


def test_bare_bgc_patterns_called_out():
    exe = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    # The rule must show examples of what's NOT acceptable
    assert "never acceptable" in exe or "NEVER acceptable" in exe
    assert "bare" in exe


# ── PATCH-SYNC-VERSION-SUFFIX ─────────────────────────────────────────────────

def test_sync_version_handles_letter_suffixes():
    """sync_version.py patterns must match letter-suffixed versions like 9.7.148b."""
    import re
    src = text("tools/sync_version.py")
    # The fix: [a-z]* in re.compile patterns (not [a-z]? which only consumes one letter)
    assert "[a-z]*" in src, "sync_version.py must use [a-z]* not [a-z]? for letter suffixes"
    # The PLAYBOOK patterns must also accept letters
    assert r"[\d._]+[a-z]*" in src or r"[\d._][a-z]*" in src


def test_sync_version_check_passes():
    """sync_version --check must exit 0 with current bundle version."""
    import subprocess
    import sys
    # v9.7.410: run under the interpreter executing the suite, not whatever `python3` is on PATH
    # (a system 3.9 without PyYAML turned this into a false red on every macOS laptop).
    result = subprocess.run(
        [sys.executable, "tools/sync_version.py", "--check"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"sync_version --check failed:\n{result.stdout[:500]}"
    )


def test_new_mamey_modules_have_companion_tests():
    """Guard: every module added in the 9.7.148+ arc has a companion test file.
    Prevents the session_resume.py failure mode (shipped with correctness bugs,
    no test file to catch them). Add new modules to expected_modules as they ship.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]

    # Modules introduced in 9.7.148+ arc that must have companion tests
    expected_modules = {
        'mamey/modeb_blastp.py':   'tests/test_wise_fragmented_pks_workflow_v97144.py',
        'mamey/compile_report.py': 'tests/test_compile_report.py',
        'mamey/session_resume.py': 'tests/test_session_resume.py',
        'mamey/figures_smoke.py':  'tests/test_figures_smoke.py',
        'mamey/judgment_store.py': 'tests/test_judgment_dir_split.py',
        'mamey/mode_b_receipt.py': 'tests/test_ingest_one_card.py',
        'mamey/locus_map.py':      'tests/test_locus_map_compile_integration.py',
        'mamey/modeb_structure_gate.py':  'tests/test_modeb_structure_gate.py',
        'mamey/modeb_template_emitter.py': 'tests/test_modeb_template_emitter.py',
        'mamey/render_all_figures.py':    'tests/test_render_all_figures.py',
        'mamey/mode_b/evidence_ledgers.py': 'tests/test_bunny_hop_fixes.py',
    }

    missing_tests = []
    for module, test_file in expected_modules.items():
        if (root / module).exists() and not (root / test_file).exists():
            missing_tests.append(f'{module} -> {test_file} missing')

    assert not missing_tests, (
        "These modules shipped without companion test files:\n" +
        "\n".join(missing_tests)
    )
