"""Tests for Gap 1 — cohort_cards orchestrator (v9.7.116).

The full orchestration tests need the 24 per-strain packages (/data/mamey-local/cohort_runs), absent in
this build; they're guarded and skip cleanly. The injection logic + the real-master prevalence join
are unit-testable and run here.
"""
import os
import sys
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
from mamey.cohort_cards import (run_cohort_cards, inject_cross_strain, _RANK_RE)  # noqa: E402
from mamey.cross_strain_card_context import load_prevalence, registry_size  # noqa: E402

MASTER = str(_ROOT / "private" / "cohort_fixtures" / "_cohort_master_v2.xlsx")
COHORT = "/data/mamey-local/cohort_runs"

_have_master = os.path.exists(MASTER)
_have_cohort = os.path.isdir(COHORT)


# --- pure injection logic (no packages needed) ---

def test_inject_is_idempotent():
    """Running injection twice must not double-add §X blocks."""
    md = "## Rank 1: NODE_x (BGC001) -- RiPP\nbody\n"
    prev = {"crocagin": {"n_strains": 1, "band": "RARE", "informative": True}}
    once = inject_cross_strain(md, "AS-X", {"BGC001": ["crocagin"]}, prev, 24)
    twice = inject_cross_strain(once, "AS-X", {"BGC001": ["crocagin"]}, prev, 24)
    assert once.count("§X. Cross-strain context") == 1
    assert twice.count("§X. Cross-strain context") == 1


def test_empty_prevalence_no_injection():
    md = "## Rank 1: NODE_x (BGC001) -- RiPP\nbody\n"
    out = inject_cross_strain(md, "AS-X", {"BGC001": ["crocagin"]}, {}, 0)
    assert "§X" not in out


def test_rank_split_matches_at_string_start():
    """The fixed regex must match a '## Rank' header with NO preamble (string start), not only
    after a newline — the bug caught during the analysis-chat build."""
    md = "## Rank 1: NODE_x (BGC001) -- RiPP\nbody\n"   # card begins immediately, no preamble
    prev = {"crocagin": {"n_strains": 1, "band": "RARE", "informative": True}}
    out = inject_cross_strain(md, "AS-X", {"BGC001": ["crocagin"]}, prev, 24)
    assert "§X. Cross-strain context" in out  # the first (and only) card got annotated


def test_rank_re_extracts_bgc_id():
    m = _RANK_RE.search("## Rank 3: NODE_12 (BGC028) -- NRPS")
    assert m and m.group(1) == "BGC028"


# --- real-master injection (master present, packages not needed) ---

@pytest.mark.skipif(not _have_master, reason="scored master fixture absent in this tier")
def test_injection_against_real_master_flags_unique():
    """Inject §X into a synthetic card for a real cohort-unique capacity, using the real prevalence
    sheet — crocagin is cohort-unique (1/24), so the block must flag COHORT-UNIQUE."""
    prev = load_prevalence(MASTER)
    n = registry_size(MASTER)
    assert n == 24
    md = "## Rank 1: NODE_20 (BGC015) -- RiPP;crocagin\nbody text\n"
    out = inject_cross_strain(md, "AS-900", {"BGC015": ["RiPP", "crocagin"]}, prev, n)
    assert "§X. Cross-strain context" in out
    assert "COHORT-UNIQUE" in out
    assert "crocagin" in out


# --- full orchestration (needs the 24 packages) ---

@pytest.mark.skipif(not (_have_cohort and _have_master),
                    reason="per-strain cohort packages absent in this tier")
def test_orchestration_annotates_all_cards(tmp_path):
    import glob
    from mamey.cohort_cards import _strain_id

    def _runner(pkg, outdir, top_n):
        sid = _strain_id(pkg)
        mds = glob.glob(f"{COHORT}/{sid}/mode_b/*_Mode_B_Top_Leads.md")
        return mds[0] if mds else None

    s = run_cohort_cards(COHORT, MASTER, tmp_path, top_n=15, mode_b_runner=_runner)
    assert s["strains"] == 24
    assert s["annotated"] == s["cards"]
    assert not s["warnings"]


def test_products_for_skips_bgc_without_id(tmp_path):
    """Bug Hunt v9.7.117: a manifest BGC entry missing 'bgc_id' must be skipped, not KeyError the
    whole cohort orchestration."""
    import json
    from mamey.cohort_cards import _products_for
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-902",
        "bgcs": [{"products": ["NRPS"]},                       # no bgc_id — must skip
                 {"bgc_id": "BGC002", "products": ["PKS"]}],
    }))
    out = _products_for(pkg)
    assert out == {"BGC002": ["PKS"]}


def test_products_for_missing_bgcs_key(tmp_path):
    import json
    from mamey.cohort_cards import _products_for
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-903"}))
    assert _products_for(pkg) == {}
