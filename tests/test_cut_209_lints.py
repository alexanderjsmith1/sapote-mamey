"""Cut v9.7.209 additions — claim-safety (#58), citation (#59) lints;
docstring/FLOORS drift guard (#8); figure-import guard (#35). Hermetic.

Matches the landed convention (test_arts_ingest.py): assertions on real function
behavior, synthetic inputs, no private-data dependency. Verified this cut against
the three real AS-XXX cards (0 false positives) — those assertions are reproduced
here as synthetic minimal cases so the suite stays hermetic.
"""
import importlib.util, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(mod, rel):
    s = importlib.util.spec_from_file_location(mod, ROOT / rel)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


# ---- #58 claim-safety lint -------------------------------------------------
def test_claim_safety_flags_produces():
    g = _load("modeb_structure_gate", "mamey/modeb_structure_gate.py")
    bad = "The strain produces daptomycin and synthesizes a polyketide."
    out = g._claim_safety_findings(bad)
    founds = {f["found"] for f in out}
    assert "produces" in founds


def test_claim_safety_allows_negated_and_conditional():
    g = _load("modeb_structure_gate", "mamey/modeb_structure_gate.py")
    # these are the real false-positive shapes found on the AS-XXX cards this cut
    safe = [
        "Cannot claim BGC039 (NODE_9 · r001) produces SapB or any named compound.",
        "If this BGC produces an active compound, an antibacterial role is plausible.",
        "Biosynthetic capacity consistent with a class-III lanthipeptide.",
    ]
    for line in safe:
        assert g._claim_safety_findings(line) == [], f"false positive on: {line}"


# ---- #59 citation lint -----------------------------------------------------
def test_citation_flags_bgc_never_located():
    g = _load("modeb_structure_gate", "mamey/modeb_structure_gate.py")
    card = "## §1\nBGC099 is discussed at length but never given a locator. observed."
    out = g._citation_findings(card)
    assert any(f["code"] == "MISSING_LOCATOR" and f["found"] == "BGC099" for f in out)


def test_citation_ok_when_located_somewhere():
    g = _load("modeb_structure_gate", "mamey/modeb_structure_gate.py")
    # prose cross-reference "BGC039/BGC027's tier" is fine as long as each is located once
    card = ("BGC039 (NODE_9 · r001) and BGC027 (NODE_59 · r001) both map here. "
            "Later, BGC039/BGC027's shared tier is noted. observed evidence.")
    out = [f for f in g._citation_findings(card) if f["code"] == "MISSING_LOCATOR"]
    assert out == [], f"prose cross-ref should not flag: {[f['found'] for f in out]}"


def test_citation_flags_missing_provenance():
    g = _load("modeb_structure_gate", "mamey/modeb_structure_gate.py")
    card = "BGC001 (NODE_1 · r001) is a lanthipeptide with no provenance words at all."
    assert any(f["code"] == "NO_PROVENANCE_TAGS" for f in g._citation_findings(card))


# ---- lint_card wiring (flags off by default, additive when on) -------------
def test_lint_card_flags_are_opt_in():
    g = _load("modeb_structure_gate", "mamey/modeb_structure_gate.py")
    bad = "## §1 Identity and node/region\nThe strain produces X. BGC099 uncited."
    off = {f["code"] for f in g.lint_card(bad)}
    assert "CLAIM_SAFETY" not in off and "MISSING_LOCATOR" not in off
    on = {f["code"] for f in g.lint_card(bad, check_claim_safety=True, check_citations=True)}
    assert "CLAIM_SAFETY" in on and "MISSING_LOCATOR" in on


# ---- #8 docstring vs FLOORS drift guard ------------------------------------
def test_gate_docstring_matches_floors():
    """The module docstring's floor numbers must equal the FLOORS dict (B17 kept drifting).
    Reads FLOORS by regex rather than importing the module, so the drift guard doesn't
    depend on the module's runtime imports (dataclass/etc.)."""
    src = (ROOT / "mamey" / "mode_b_quality_gate.py").read_text(encoding="utf-8")
    block = re.search(r"FLOORS\s*=\s*\{(.*?)\}", src, re.DOTALL)
    assert block, "FLOORS dict not found"
    floor_vals = [int(v.replace("_", "").replace(",", ""))
                  for v in re.findall(r":\s*([\d_,]+)", block.group(1))]
    assert floor_vals, "no FLOORS values parsed"
    for val in floor_vals:
        v = f"{val:,}"
        assert v in src or str(val) in src, f"FLOORS value {val} not reflected in module text"
    # the retired 6,000 fragment must be gone
    assert "10,000–6,000" not in src and "10,000-6,000" not in src


# ---- #35 figure-import guard -----------------------------------------------
def test_cohort_figures_guards_matplotlib():
    """cohort_figures must expose _HAVE_MPL and a _require_mpl that raises a clear message."""
    src = (ROOT / "mamey" / "cohort_figures.py").read_text(encoding="utf-8")
    assert "_HAVE_MPL" in src, "matplotlib import must be capability-guarded"
    assert "[figures]" in src, "the guard message should name the .[figures] extra"
    # generate() must consult the guard before doing any plotting
    assert re.search(r"def generate\(.*?_HAVE_MPL", src, re.DOTALL), \
        "generate() should check _HAVE_MPL before plotting"
