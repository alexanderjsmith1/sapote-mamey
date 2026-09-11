"""Regression test — v97395: tools/repo_health.py's CLI_TOOL_EXCLUDE_FILES is missing
phylo_place.py, its direct sibling's own list already includes.

Not a Black Cherry finding — this synthesizes a fix independently reached by two other lanes
this same cut cycle:
  - Aquarius (Claude lane), composing the earlier v97395 pool: "print_calls 1638 > ceiling 1635.
    Attribution is exact: tools/phylo_place.py 15 -> 18 prints (Amber's reference-dedup patch).
    Recommendation: add phylo_place.py to CLI_TOOL_EXCLUDE_FILES ... That list exists for
    'operator CLI tools whose stdout IS the deliverable' and already contains
    phylo_place.py's direct siblings phylo_preflight.py and phylo_postflight.py."
  - Codex, independently, in CODEX_395_COMBINED_REPO_HEALTH_CLI_OUTPUT_CLASSIFICATION_REPAIR.patch
    (tests/test_repo_health_cli_output_classification_v97395.py):
    "assert 'phylo_place.py' in repo_health.CLI_TOOL_EXCLUDE_FILES"

This card exists so the fix is stageable and independently verifiable inside the Claude-side
v97395 pool without pulling in Codex's larger, separately-staged gene-first-portability patch
(which the combined Codex patch above is bundled with and depends on).
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import repo_health


def test_phylo_place_is_an_explicit_cli_output_exclusion_v97395():
    assert "phylo_place.py" in repo_health.CLI_TOOL_EXCLUDE_FILES, (
        "phylo_place.py is the direct sibling of phylo_preflight.py/phylo_postflight.py "
        "(both already excluded as operator CLI launchers whose stdout IS the deliverable) "
        "but was never added"
    )


def test_existing_exclusions_are_not_disturbed_v97395():
    for f in ("render_all.py", "phylo_preflight.py", "phylo_postflight.py",
              "relabel_and_render.py", "render_clean_tree.py", "validate_portfolio_registry.py"):
        assert f in repo_health.CLI_TOOL_EXCLUDE_FILES
