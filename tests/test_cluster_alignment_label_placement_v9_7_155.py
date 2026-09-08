"""PATCH-006 regression: cluster_alignment track labels must not overlap connector
lines, and the two bottom legends must not be squeezed into overlap by tight_layout.

Original bug (patch list PATCH-006): the four track-title `ax.text()` calls were drawn
at x=0 (left-aligned) with a +0.22/+0.12 y-offset, placing them inside the [0, TRACK]
x-span and the y-band that connector lines cross en route between fragment and reference
tracks — so lines visibly ran through the label text. Separately, `plt.tight_layout()`
(with bbox_inches="tight") re-derived the axes width from content on every call, shrinking
it to fit the labels and squeezing the two fixed-size bottom legends until they overlapped.

Fix: labels moved into the left margin (right-aligned, ending at x=-0.02, wrapped to <=2
lines); tight_layout()/bbox_inches replaced with fixed subplots_adjust margins.

These tests assert the invariants structurally (artist inspection), not by pixel diff.
"""
import importlib.util
import os

import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _load():
    spec = importlib.util.spec_from_file_location(
        "cluster_alignment", os.path.join(TOOLS, "cluster_alignment.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture(ca):
    ref_subjects = [f"BGC0000469_{i}" for i in range(1, 6)]
    ref_role = {s: ("core", f"g{i}") for i, s in enumerate(ref_subjects)}
    locs = [f"ctg1_{i}" for i in range(1, 5)]
    hits = {locs[i]: {"s": ref_subjects[i], "id": 80 - i * 10, "score": 200, "cov": 90}
            for i in range(4)}
    frags = [{
        "name": "BGC0000469 - a very long reference cluster label that would previously "
                "overlap the diagonal connector lines running through it",
        "sub": "4 genes -> BGC0000469 · class corroborated by 12 MIBiG + 8 genome refs",
        "genes": locs, "roles": {l: ("core", f"q{i}") for i, l in enumerate(locs)},
        "hits": hits, "side": "top", "synteny": True,
    }]
    return frags, ref_subjects, ref_role


def test_all_track_labels_sit_in_left_margin(tmp_path):
    """Every bold track title must be right-aligned at a negative x (in the margin),
    clear of the connector zone at x>=0."""
    ca = _load()
    frags, ref_subjects, ref_role = _fixture(ca)
    out = str(tmp_path / "aln")
    ca.render(frags, ref_subjects, ref_role, "BGC0000469", "testref",
              "title", "subtitle", out)
    assert os.path.exists(out + ".png")

    # Re-render capturing the axes so we can inspect text artists.
    import matplotlib.pyplot as plt
    figs_before = set(map(id, map(plt.figure, [])))  # noop to keep import used
    # The render closes its figure; instead assert via a fresh render into a live fig.
    # Simpler: monkeypatch savefig to capture the current axes' texts.
    captured = {}
    _orig_savefig = plt.savefig

    def _cap_savefig(*a, **k):
        ax = plt.gca()
        captured["labels"] = [
            (t.get_position()[0], t.get_ha(), t.get_text())
            for t in ax.texts if t.get_fontweight() == "bold"
        ]
        return _orig_savefig(*a, **k)

    plt.savefig = _cap_savefig
    try:
        ca.render(frags, ref_subjects, ref_role, "BGC0000469", "testref",
                  "title", "subtitle", str(tmp_path / "aln2"))
    finally:
        plt.savefig = _orig_savefig

    bold = captured.get("labels", [])
    # There must be at least the reference + one fragment title.
    title_labels = [(x, ha, txt) for (x, ha, txt) in bold
                    if "BGC0000469" in txt or "reference operon" in txt]
    assert title_labels, f"no track titles found among bold texts: {bold}"
    for x, ha, txt in title_labels:
        assert x < 0, f"track label at x={x} is not in the left margin (should be <0): {txt!r}"
        assert ha == "right", f"track label not right-aligned (ha={ha}): {txt!r}"


def test_no_tight_layout_in_source():
    """tight_layout()/bbox_inches='tight' re-derive axes width from content and squeeze
    the fixed-size legends. The fix uses explicit subplots_adjust instead. (Check for the
    actual calls, ignoring comment lines that document what was replaced.)"""
    lines = open(os.path.join(TOOLS, "cluster_alignment.py"), encoding="utf-8").read().splitlines()
    code = "\n".join(l for l in lines if not l.lstrip().startswith("#"))
    assert "plt.tight_layout()" not in code, "tight_layout() reintroduced — legends will overlap"
    assert 'bbox_inches="tight"' not in code, "bbox_inches='tight' reintroduced — undoes fixed margins"
    assert "subplots_adjust(" in code, "explicit fixed margins (subplots_adjust) missing"


def test_wrap_label_shortens_long_titles():
    ca = _load()
    short = "BGC0000469 - streptophenazine"
    assert ca._wrap_label(short) == short, "short label should be unchanged"
    long = ("BGC0002010 - streptophenazine B/C/F/G/H (BGC0002010.4) top fragment "
            "reconstruction with a great many extra words to force wrapping")
    wrapped = ca._wrap_label(long)
    assert "\n" in wrapped, "long label should wrap to multiple lines"
    assert len(wrapped.split("\n")) <= 2, "should wrap to at most 2 lines"
