"""Card 458_k01_left_margin_from_labels: K01 sizes its left margin from the measured labels.

The defect: a fixed left margin (0.30 of the width) let a bracketed row note run into the genus band label at a 6.0 in
print width ("AS-103 (Sciscionella sp.)" over "Pseudonocardiaceae (n = 2)"). Synthetic census tables only.
"""
import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chitin_k01_margin", ROOT / "tools/chitin_isolate_vs_references.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

COLS = ["genus", "role", "strain_id", "Glyco_hydro_18", "Glyco_hydro_19", "LPMO_10", "CBM_5_12", "cds_searched"]


def put(path, header, rows):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(header)
        w.writerows(rows)
    return path


ROWS = [("AS-971", "Pseudonocardia"), ("AS-972", "Pseudonocardia"), ("AS-975", "Pseudonocardia"),
        ("AS-976", "Pseudonocardia"), ("AS-977", "Kribbella"), ("AS-978", "Amycolatopsis"),
        ("AS-973", "Pseudonocardiaceae"), ("AS-974", "Streptomyces")]
GENERA = sorted({g for _, g in ROWS})


def world(tmp, notes):
    """Eight rows in six bands, the height of the Attine panel; one band is a two-reference family like its
    "Pseudonocardiaceae (n = 2)"."""
    iso = put(tmp / "iso.tsv", COLS, [[g, "isolate", s, 3 * (i % 3), i % 2, i % 4, 0, 6000 + 100 * i]
                                      for i, (s, g) in enumerate(ROWS)])
    refs = [["Pseudonocardiaceae", "reference", f"REF_F{i}", 14 + i, 0, 1, 2, 7000] for i in range(2)]
    refs += [[g, "reference", f"REF_{g[:3]}{i}", i % 9, i % 3, 1 + i % 4, i % 2, 6000]
             for g in GENERA if g != "Pseudonocardiaceae" for i in range(12)]
    ref = put(tmp / "ref.tsv", COLS, refs)
    gen = put(tmp / "genomes.tsv", ["strain", "genus", "row_note"], [[s, g, notes.get(s, "")] for s, g in ROWS])
    return iso, ref, gen


def render(tmp, monkeypatch, width, notes):
    """Run the tool and keep the figure it draws (plt.close is intercepted)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    kept = []
    real_close = plt.close
    monkeypatch.setattr(plt, "close", lambda fig=None: kept.append(fig))
    iso, ref, gen = world(tmp, notes)
    out = tmp / "out"
    assert m.main(["--genomes", str(gen), "--isolates", str(iso), "--references", str(ref), "--out", str(out),
                   "--dpi", "100", "--print-width", str(width)]) == 0
    fig = kept[0]
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    texts = fig.axes[0].texts
    rows = [t for t in texts if t.get_text().startswith("AS-")]
    bands = [t for t in texts if "(n = " in t.get_text()]
    assert len(rows) == len(ROWS) and len(bands) == 5
    boxes = ([t.get_window_extent(rend) for t in rows], [t.get_window_extent(rend) for t in bands])
    x0 = fig.axes[0].get_position().x0
    sizes = [t.get_fontsize() for t in rows + bands]
    from matplotlib.text import Text
    ticks, drawn = set(), []                                  # tick labels: only those inside the view are drawn
    for ax in fig.axes:
        lo, hi = sorted(ax.get_xlim())
        for tk in ax.xaxis.get_major_ticks() + ax.yaxis.get_major_ticks():
            ticks.add(id(tk.label1))
            if ax.axison and ax.xaxis.get_visible() and tk in ax.xaxis.get_major_ticks() and lo <= tk.get_loc() <= hi:
                drawn.append(tk.label1)
    every = [(t.get_text(), t.get_window_extent(rend)) for t in fig.findobj(Text)
             if t.get_visible() and t.get_text().strip() and (id(t) not in ticks or t in drawn)]
    page = fig.bbox
    real_close(fig)
    render.every, render.page = every, page
    return boxes, x0, sizes


NOTE = r"$\it{Sciscionella}$ sp."


@pytest.mark.needs_arial  # 6 in fit depends on real Arial widths; Liberation Sans on CI is wider
def test_long_row_note_does_not_touch_the_band_label_at_6in(tmp_path, monkeypatch):
    (rows, bands), _, sizes = render(tmp_path, monkeypatch, 6.0, {"AS-973": NOTE})
    hits = [(i, j) for i, r in enumerate(rows) for j, b in enumerate(bands) if r.overlaps(b)]
    assert hits == [], f"row label / band label overlaps: {hits}"
    assert min(sizes) >= m.MIN_PT


@pytest.mark.needs_arial  # 6 in fit depends on real Arial widths; Liberation Sans on CI is wider
def test_no_text_run_touches_another_or_leaves_the_page_at_6in(tmp_path, monkeypatch):
    """Moving the panels right must not push panel titles into each other or into the right-hand column."""
    render(tmp_path, monkeypatch, 6.0, {"AS-973": NOTE})
    every, page = render.every, render.page
    hits = [(a[0], b[0]) for i, a in enumerate(every) for b in every[i + 1:] if a[1].overlaps(b[1])]
    assert hits == [], f"text overlaps: {hits}"
    out = [t for t, bb in every if bb.x0 < page.x0 - 0.5 or bb.x1 > page.x1 + 0.5 or bb.y0 < page.y0 - 0.5 or bb.y1 > page.y1 + 0.5]
    assert out == [], f"text outside the page: {out}"


@pytest.mark.parametrize("width", [pytest.param(6.0, marks=pytest.mark.needs_arial), 7.2])
def test_figures_without_notes_keep_their_layout(tmp_path, monkeypatch, width):
    (rows, bands), x0, _ = render(tmp_path, monkeypatch, width, {})
    assert abs(x0 - 0.30) < 0.005                      # the left edge of the panels stays where it was
    assert not any(r.overlaps(b) for r in rows for b in bands)


def test_a_note_too_long_for_the_width_is_refused(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="labels need"):
        render(tmp_path, monkeypatch, 3.5, {"AS-973": NOTE + " isolated from a very long description of a host"})
