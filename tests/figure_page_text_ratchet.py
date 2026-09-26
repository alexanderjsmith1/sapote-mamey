"""Check the text drawn on every matplotlib figure a test saves.

The rule: no claim wording on the page (`mamey.figure_policy.FIGURE_BANNED_TEXT`). The shared
save path (`mamey/figure_save.py`) enforces it, but most bundle renderers call `Figure.savefig`
directly and never pass through that check. This module wraps `Figure.savefig` for the test
session, so the check has a caller wherever a test renders a figure.

A renderer that draws banned wording fails the test that rendered it, unless its site is listed
in `fixtures/figure_page_text_known_sites.txt`. That list is the backlog. It may only shrink: a
new site fails at once, and a listed site that renders clean is reported at the end of the run so
its line can be deleted.

A site is `<path relative to the bundle root>::<function>` of the innermost bundle frame that
called `savefig`. Function names survive line edits; line numbers do not.

Not covered: SVG written by hand (no matplotlib figure), R renderers, and tests skipped in the
run (slow-marked tests need --run-slow).
"""
from __future__ import annotations

import traceback
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent.parent
KNOWN_SITES_FILE = Path(__file__).resolve().parent / "fixtures" / "figure_page_text_known_sites.txt"
# Shared save helpers are skipped so the site names the renderer that called them.
SHARED_HELPERS = {"mamey/figure_theme.py::save_figure_pair"}
# Admission ceiling for the initial known-site backlog. The editable file may
# remove entries as renderers are fixed, but cannot exempt a new renderer.
FROZEN_KNOWN_SITES = frozenset({
    "mamey/bigscape_figures.py::gcf_network",
    "mamey/cohort_class_heatmap.py::render_cohort_class_heatmap",
    "mamey/collection_figures.py::_save",
    "mamey/cross_strain_figures.py::_save",
    "mamey/cross_strain_threads.py::render_threads_figure",
    "mamey/figures_extra.py::fig_class_distribution",
    "mamey/kcb_locusmap.py::render_region",
    "mamey/locus_map.py::render_locus_map",
    "mamey/locus_map_v8.py::render_bgc_v8",
    "mamey/master_figure_atlas.py::_save",
    "mamey/render_brief.py::_text_page",
    "mamey/render_brief.py::fig_landscape",
    "mamey/render_brief.py::new_page",
    "tools/cluster_alignment.py::render",
})


def load_known_sites(path: Path = KNOWN_SITES_FILE) -> set[str]:
    if not path.is_file():
        return set()
    known = {line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines()
             if line.split("#", 1)[0].strip()}
    added = known - FROZEN_KNOWN_SITES
    if added:
        raise ValueError(f"new figure page text exception(s) are forbidden: {sorted(added)}")
    return known


def calling_site(stack: list[traceback.FrameSummary]) -> str:
    """Return the innermost bundle frame outside tests/ as `relpath::function`, or ""."""
    tests_dir = BUNDLE_ROOT / "tests"
    for frame in reversed(stack):
        if frame.filename.startswith("<"):
            continue  # <stdin>, <string>, <frozen ...>: not a file, and resolve() would put it in cwd
        path = Path(frame.filename).resolve()
        if not path.is_relative_to(BUNDLE_ROOT) or path.is_relative_to(tests_dir):
            continue
        if path.name == "figure_save.py":
            return ""  # the shared save path runs the same check itself
        site = f"{path.relative_to(BUNDLE_ROOT).as_posix()}::{frame.name}"
        if site not in SHARED_HELPERS:
            return site
    return ""


class PageTextRatchet:
    def __init__(self, known: set[str]):
        self.known = known
        self.seen_dirty: set[str] = set()
        self.seen_clean: set[str] = set()

    def check(self, fig, site: str) -> None:
        from mamey.figure_policy import FigureTextRefusal, figure_text_violations, matplotlib_visible_text

        if not site:
            return
        found = figure_text_violations(matplotlib_visible_text(fig))
        if not found:
            self.seen_clean.add(site)
            return
        self.seen_dirty.add(site)
        if site not in self.known:
            raise FigureTextRefusal(
                f"FIGURE_TEXT_BANNED: {site} draws {sorted(set(found))} on the figure. "
                "Move the wording to the receipt, caption file or methods text. "
                "Do not add the site to figure_page_text_known_sites.txt; that list only shrinks.")

    def cleared_sites(self) -> list[str]:
        """Listed sites that rendered at least once in this run and never drew banned text."""
        return sorted((self.known & self.seen_clean) - self.seen_dirty)


def install(ratchet: PageTextRatchet):
    """Wrap Figure.savefig for this process. Returns the original so a caller can restore it."""
    from matplotlib.figure import Figure

    original = Figure.savefig

    def savefig(self, *args, **kwargs):
        ratchet.check(self, calling_site(traceback.extract_stack()[:-1]))
        return original(self, *args, **kwargs)

    savefig.page_text_ratchet = ratchet
    Figure.savefig = savefig
    return original
