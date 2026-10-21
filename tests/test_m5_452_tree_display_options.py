"""m5_452_ggtree_tree_display_options: opt-in display settings for tools/ggtree_rect_heatmap.R (Paper 4 Fig. 5, M3 review 16 Oct).
GG_PAGE_TITLE=0 drops the "Page i of n" title; GG_SUPPORT_MAX leaves supports at or above it blank (100 unlabelled); GG_SUPPORT_POS=auto
puts each support number on the side of its node where it crosses no branch line; GG_SCALE_OFFSET lifts the scale-bar label off its
line. Unset, every setting draws as sealed. Synthetic tree only."""
import os, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import _min_text_check as mtc  # noqa: E402

# The Fig. 5 shape: a cherry (85) just right of an ancestor's long vertical line (70), so the sealed up-left number lands on it.
TREE = "((((X1:0.1,X2:0.1)99:0.01,((A:0.1,B:0.1)85:0.002,C:0.1)40:0.003)70:0.01,D:0.1)100:0.01,OUTGROUP_REF:0.35);"
TIPS = ["X1", "X2", "A", "B", "C", "D", "OUTGROUP_REF"]


@pytest.fixture
def render(tmp_path):
    r = shutil.which("Rscript")
    if not r:
        pytest.skip("Rscript unavailable")
    probe = subprocess.run([r, "-e", 'quit(status=if(all(sapply(c("ape","ggtree","ggplot2","aplot","treeio","patchwork"),requireNamespace,quietly=TRUE))) 0 else 1)'], capture_output=True)
    if probe.returncode:
        pytest.skip("R graphics packages not installed")
    tree = tmp_path / "t.nwk"; tree.write_text(TREE)
    meta = tmp_path / "labels.tsv"
    meta.write_text("tip\tlabel\tcategory\tcategory_raw\tsource\n" + "".join(f"{k}\t{k} strain\tplant-associated\tplant\tUS\n" for k in TIPS))

    def run(name, **env):
        out = tmp_path / name / "fig"; out.parent.mkdir()
        cp = subprocess.run([r, str(ROOT / "tools/ggtree_rect_heatmap.R"), str(tree), str(meta), str(out)], capture_output=True, text=True,
                            env=dict(os.environ, LANG="en_US.UTF-8", LC_ALL="en_US.UTF-8", SAPOTE_PYTHON=shutil.which("python3"), GG_PRINT_WIDTH="6.5", **env), timeout=180)
        assert cp.returncode == 0, cp.stdout + cp.stderr
        return cp, out.with_suffix(".pdf")
    return run


def texts(pdf):
    return [t for t, *_ in mtc.pdf_text_boxes(pdf)]


def crossings(pdf, labels, pad=0.5):
    """Text boxes among `labels` that touch a black stroke (the tree's branch lines, the scale bar)."""
    segs = mtc.pdf_stroke_segments(pdf, (0, 0, 0))
    hit = []
    for t, x0, x1, y0, y1 in mtc.pdf_text_boxes(pdf):
        if t in labels and any(max(a, c) >= x0 - pad and min(a, c) <= x1 + pad and max(b, d) >= y0 - pad and min(b, d) <= y1 + pad for a, b, c, d in segs):
            hit.append(t)
    return hit


def lines_under_numbers(bare_png, png, gap_px=6):
    """Branch-line pixels of the bare render (no support numbers) lying under or within gap_px of a support number of the other
    render (300 dpi: 6 px = 1.4 pt). The pixel truth a reader sees; PDF text boxes include descender room digits do not use."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(bare_png).convert("L")).astype(int); b = np.asarray(Image.open(png).convert("L")).astype(int)
    m = np.abs(a - b) > 30
    for _ in range(gap_px):
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    return int((m & (a < 128)).sum())


def test_defaults_draw_as_sealed(render):
    cp, pdf = render("default", GG_SUPPORT_MIN="0")
    t = texts(pdf)
    # Since .454 the page title is opt-in (GG_PAGE_TITLE=1; tests/test_tree_page_title_optin.py), so the sealed default has none.
    assert not any(x.startswith("Page ") for x in t) and {"99", "85", "40", "70", "100"} <= set(t)
    assert "SUPPORT_POS" not in cp.stdout


def test_page_title_off(render):
    _, pdf = render("notitle", GG_PAGE_TITLE="0")
    assert not any(x.startswith("Page ") for x in texts(pdf))


def test_support_max_leaves_100_blank(render):
    cp, pdf = render("max", GG_SUPPORT_MIN="0", GG_SUPPORT_MAX="100")
    t = texts(pdf)
    assert {"99", "85", "40", "70"} <= set(t) and "100" not in t
    assert "SUPPORT_LABELS: 4 nodes >= 0 and < 100" in cp.stdout


def test_support_auto_crosses_no_branch_line(render):
    """Sealed placement puts the 85 on the 70 node's vertical line (as the Fig. 5 98); auto places every number clear."""
    _, bare = render("bare")
    _, sealed = render("left", GG_SUPPORT_MIN="0", GG_SUPPORT_MAX="100")
    assert lines_under_numbers(bare.with_suffix(".png"), sealed.with_suffix(".png")) > 0
    cp, pdf = render("auto", GG_SUPPORT_MIN="0", GG_SUPPORT_MAX="100", GG_SUPPORT_POS="auto")
    assert "SUPPORT_POS auto:" in cp.stdout and "SUPPORT_LABEL_COLLISION" not in cp.stdout
    assert {"99", "85", "40", "70"} <= set(texts(pdf))
    assert lines_under_numbers(bare.with_suffix(".png"), pdf.with_suffix(".png")) == 0


def test_scale_offset_lifts_label_off_bar(render):
    _, pdf = render("scale", GG_SCALE_OFFSET="0.45")
    nums = {t for t in texts(pdf) if t.replace(".", "", 1).isdigit()}
    assert nums and crossings(pdf, nums) == []


# The shape of the Paper 4 Fig. 5 76-genome tree (topology, branch lengths and UFBoot of the try-4 IQ-TREE contree; tips renamed
# T1..T76, no names or data kept) with labels padded to the real label width (3.8 in): two numbers have no clear place at 8 pt.
CROWDED = "((((((((((((((((T1:0.00276,T2:0.001921)100:0.02194,((((T3:0.001387,T4:0.001505)100:0.009234,T5:0.007618)100:0.007871,(T6:0.008095,T7:0.01021)100:0.0121)100:0.009233,(T8:0.003209,T9:0.003432)100:0.02062)93:0.004483)100:0.01658,(T10:0.03198,T11:0.02502)100:0.01273)100:0.03527,(T12:0.005672,T13:0.009625)100:0.05723)100:0.01611,((((((T14:0.002623,T15:0.002508)100:0.009092,T16:0.01735)100:0.01267,(T17:0.02693,T18:0.02233)100:0.007976)100:0.008731,T19:0.03472)100:0.01271,((T20:0.01403,T21:0.01604)100:0.01777,T22:0.03057)100:0.01712)100:0.07389,((T23:0.03346,T24:0.02873)100:0.01293,((T25:0.0412,(T26:0.006643,T27:0.006165)100:0.03019)100:0.01472,T28:0.04362)69:0.008493)100:0.1207)100:0.03042)98:0.0241,(T29:0.06498,((T30:0.00165,(T31:0.001715,T32:0.002739)100:0.001891)100:0.04883,((T33:0.04273,(T34:0.04407,T35:0.03849)94:0.008771)100:0.009591,(T36:0.04412,(T37:0.04101,T38:0.0465)100:0.008447)100:0.00942)92:0.00792)100:0.01449)100:0.02354)86:0.008505,(((((T39:0.02437,T40:0.02434)100:0.008233,T41:0.03557)100:0.04713,T42:0.06894)100:0.0158,T43:0.05516)100:0.032,((T44:0.09706,(T45:0.04426,T46:0.0384)100:0.02649)100:0.01873,T47:0.09855)100:0.02054)100:0.01308)100:0.03881,(T48:0.07689,T49:0.09641)100:0.02542)100:0.04065,(T50:0.1202,T51:0.1102)92:0.02926)100:0.02902,((T52:0.08909,T53:0.1493)100:0.05524,((T54:0.02318,T55:0.01718)100:0.1159,T56:0.0995)100:0.1139)100:0.03583)82:0.03541,((T57:0.02023,T58:0.0149)100:0.1537,((T59:0.04207,T60:0.04306)100:0.03817,T61:0.0477)100:0.1454)82:0.03539)77:0.01323,(T62:0.1283,T63:0.1237)100:0.05388)74:0.02079,((((T64:0.06639,T65:0.06615)100:0.03779,T66:0.1744)98:0.01567,(T67:0.0842,T68:0.1002)100:0.04058)76:0.01084,T69:0.08976)100:0.05522)74:0.0232,(((T70:0.001458,T71:0.003292)100:0.0265,T72:0.04064)100:0.02617,T73:0.07644)100:0.1162)100:0.1312,(T74:0.2398,T75:0.3024)98:0.04717)100:0.09248,T76:0.3214,OUTGROUP_REF:0.7778);"


def crowded_case(tmp_path):
    (tmp_path / "t.nwk").write_text(CROWDED)
    tips = [f"T{i}" for i in range(1, 77)] + ["OUTGROUP_REF"]
    (tmp_path / "labels.tsv").write_text("tip\tlabel\tcategory\tcategory_raw\tsource\n" + "".join(
        f"{k}\t{k} synthetic label padded to width [GCA_000000000.1] [Type]\tplant-associated\tplant\tUS\n" for k in tips))


def test_unplaced_numbers_are_omitted_and_reported(render, tmp_path):
    """GG_SUPPORT_UNPLACED=omit: a number with no clear place (SUPPORT_LABEL_COLLISION) is not drawn and is reported with its
    clade as SUPPORT_NOT_DRAWN; the drawn numbers stay. Unset, the same numbers are drawn at their fewest crossings."""
    crowded_case(tmp_path)
    cp_draw, _ = render("crowded_draw", GG_SUPPORT_MIN="0", GG_SUPPORT_MAX="100", GG_SUPPORT_POS="auto")
    n_clash = cp_draw.stdout.count("SUPPORT_LABEL_COLLISION")
    assert n_clash > 0 and "SUPPORT_NOT_DRAWN" not in cp_draw.stdout
    cp, _ = render("crowded_omit", GG_SUPPORT_MIN="0", GG_SUPPORT_MAX="100", GG_SUPPORT_POS="auto", GG_SUPPORT_UNPLACED="omit")
    assert cp.stdout.count("SUPPORT_NOT_DRAWN") == n_clash and cp.stdout.count("clade from T") == n_clash
    n_all = int(cp_draw.stdout.split("SUPPORT_LABELS: ")[1].split()[0]); n_kept = int(cp.stdout.split("SUPPORT_LABELS: ")[1].split()[0])
    assert n_kept == n_all - n_clash


def test_auto_uses_the_added_places(render, tmp_path):
    """auto has five places (right, up-left, down-left, up-right, down-right); the crowded shape needs more than the first two."""
    crowded_case(tmp_path)
    cp, _ = render("crowded_auto", GG_SUPPORT_MIN="0", GG_SUPPORT_MAX="100", GG_SUPPORT_POS="auto")
    assert "right_below" in cp.stdout or "left_below" in cp.stdout or "right_above" in cp.stdout   # the added places are used


def test_scale_bar_on_last_page_only(render, tmp_path):
    """GG_SCALE_PAGES=last: a multi-page tree carries its scale bar on the last page only; unset, every page has one (sealed)."""
    crowded_case(tmp_path)
    def scale_pages(out):
        pages = sorted(out.parent.glob(f"{out.stem}_page*.pdf"))
        assert len(pages) >= 2
        return [any(t.replace(".", "", 1).isdigit() and "." in t for t in texts(p)) for p in pages]
    _, pdf_all = render("scale_all")
    assert all(scale_pages(pdf_all))
    _, pdf_last = render("scale_last", GG_SCALE_PAGES="last")
    got = scale_pages(pdf_last); assert got[-1] and not any(got[:-1])
