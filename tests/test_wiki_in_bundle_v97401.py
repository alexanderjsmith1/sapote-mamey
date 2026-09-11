"""Regression test — v97401: the in-bundle wiki/ page set (repackaged AMBER_400_wiki_in_bundle).
Asserts the drift-kill invariants: core pages present, sidebar carries a version stamp, and no
workspace locators / personal identifiers ship in the payload (public_release_audit discipline)."""
import pathlib
import re

WIKI = pathlib.Path(__file__).resolve().parents[1] / "wiki"


def test_core_pages_present_v97401():
    for page in ("Home.md", "_Sidebar.md", "Quick-Guide.md", "User-Manual.md", "Glossary.md",
                 "Claim-Safety.md", "Versioning.md"):
        assert (WIKI / page).is_file(), f"wiki/{page} missing"
    assert len(list(WIKI.glob("*.md"))) >= 30


def test_sidebar_version_stamped_and_current_v97401():
    """The stamp must match the LIVE engine versions, not merely exist — a stale sidebar fails
    the suite at cut time until it is bumped (or until sync_version adopts wiki/_Sidebar.md,
    the named follow-on, which retires this manual step). Currentness flag: .401 review."""
    import mamey
    s = (WIKI / "_Sidebar.md").read_text(encoding="utf-8")
    assert f"v{mamey.BUNDLE_VERSION}" in s, \
        f"sidebar bundle stamp is stale — expected v{mamey.BUNDLE_VERSION} in wiki/_Sidebar.md"
    assert mamey.__version__ in s, \
        f"sidebar engine stamp is stale — expected {mamey.__version__} in wiki/_Sidebar.md"


def test_no_workspace_locators_v97401():
    bad = re.compile(r"AS Strain Master|Claude_Alex_2026|alexander" r"smith")
    hits = [p.name for p in WIKI.glob("*.md") if bad.search(p.read_text(encoding="utf-8", errors="replace"))]
    assert not hits, f"workspace locators/personal identifiers in: {hits}"


def test_no_cohort_strain_ids_v97401():
    """Pins the CORRECTION-WIKI-REVIEW-BC repair (2026-09-02): cohort strain IDs are
    banned from wiki content (public_release_audit caught a real cohort ID in
    Fungal-Phylogenetics.md — receipt in the AMBER card).
    Case studies use neutral labels ("the founding isolate"), never cohort IDs."""
    bad = re.compile(r"\bAS-\d+\b|\bSID\d{3,}\b|\bAJS-\d+\b")
    hits = {}
    for p in WIKI.glob("*.md"):
        m = bad.findall(p.read_text(encoding="utf-8", errors="replace"))
        if m:
            hits[p.name] = sorted(set(m))
    assert not hits, f"cohort strain IDs in wiki payload: {hits}"
