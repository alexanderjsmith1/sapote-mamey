"""v9.7.213 AUDIT: no NEW dangling tools/-name reference may enter the live docs.

Mirrors tests/test_no_dangling_examples_refs_v9795.py. The v9.7.213 tools/ duplication audit found doc
references to `.py`/`.sh` names that don't exist in the tree (retired shims, renamed modules, one
fabricated script). Most were fixed; 6 remain, all in deep API-doc subsections of
docs/reference/03_Plumbing_Reference.md (+ one first_pass module-vs-tool distinction) that need real
module-tracing archaeology before they can be corrected. This guard FREEZES that known set as a
baseline and fails the moment a reference to a NEW (non-baselined) missing tool name appears.

Detector: tools/check_dangling_refs.py::scan_tools (single source of truth).
"""
from __future__ import annotations
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_dangling_refs import scan_tools  # noqa: E402

# Known-remaining dangling tool/module refs as of v9.7.213-audit (see the duplication-audit report §2.4/2.5).
# Tracked, not accepted as correct — each needs consolidation-era module tracing to fix.
DANGLING_BASELINE = frozenset({
    "cohort_figure_captions.py",
    "cohort_figures_bridge.py",
    "cohort_figures_d.py",
    "cohort_figures_g.py",
    "first_pass_scans.py",
    "package_addons_html.py",
    "wac_validation_genelevel.py",  # v9.7.409 A11: 0-byte tool deleted; docs/working/GATE_AND_DATA_INTEGRITY_AUDIT.md is a dated audit that named it
    "COMMAND.sh",  # CODEX16: governed-workspace per-run artifact name (RUN_MANIFEST.json/COMMAND.sh/EVENTS.jsonl), not a shipped tools/ script
})


def test_no_new_dangling_tool_refs():
    current = set(scan_tools(ROOT).keys())
    new = current - DANGLING_BASELINE
    assert not new, (
        "NEW dangling tools/ reference(s) introduced (the named .py/.sh does not exist; ship it or fix "
        "the reference): " + ", ".join(sorted(new))
    )
