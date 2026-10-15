"""M5_452_overlap_check_columns: tools/_min_text_check.py pdf_text_boxes() joined text runs on one baseline whose gap was anywhere in
-0.5 em .. +0.5 em, so two separate labels running INTO each other (negative gap) became one "line" and pdf_text_overlaps() never
compared them (Nocardia 16S figure v1, 13 Oct 2026: a two-column key whose long left lines ran into the right column passed).
Fix: join only runs that do not overlap (gap >= -0.25 pt). Synthetic PDFs only."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mtc", ROOT / "tools" / "_min_text_check.py"); mtc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mtc)


def _page(tmp_path, name, second_x):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "pdf.fonttype": 42})
    fig = plt.figure(figsize=(7.2, 1.0)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 7.2); ax.set_ylim(0, 1)
    ax.text(0.1, 0.5, "SYN-01  moss; Moss; Place A, synthetic location; 2000-01", fontsize=8, va="center")
    ax.text(second_x, 0.5, "SYN-02  bee/wasp; Bumblebee; Place B; 2000-01", fontsize=8, va="center")
    p = tmp_path / name; fig.savefig(p); plt.close(fig); return p


def test_labels_running_into_each_other_on_one_baseline_are_reported(tmp_path):
    p = _page(tmp_path, "touching.pdf", 2.94)   # the left label ends at 2.97 in (8 pt Arial): ~2 pt overlap, under the old 0.5 em window
    hits = mtc.pdf_text_overlaps(p)
    assert hits and "SYN-01" in hits[0] and "SYN-02" in hits[0]


def test_separate_labels_with_clear_space_are_not_reported(tmp_path):
    p = _page(tmp_path, "clear.pdf", 4.2)
    assert mtc.pdf_text_overlaps(p) == []


def test_two_column_key_fixture_is_reported():
    """Synthetic copy of the failing two-column key (13 Oct 2026): same layout and font size; labels SYN-01..SYN-18, places
    Place A/B/C, date 2000-01. Two left lines run about 2 pt into the right column; the old check found 0.
    Generator: fixtures/make_m5_452_overlap_two_column_key_v2.py."""
    hits = mtc.pdf_text_overlaps(ROOT / "tests" / "fixtures" / "m5_452_overlap_two_column_key_v2.pdf")
    assert len(hits) == 2 and all("Place A" in h for h in hits)
