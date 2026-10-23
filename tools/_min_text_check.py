"""Read back the smallest drawn text size from a figure PDF (M5_452_render_cards_min_text_8pt).

Effective size of a text run = font size x the scale of the text and graphics matrices (pypdf visitor). The page width is the
printed width when the figure is placed at 100 %. Used by the R figure cards after drawing: refuse (exit 2) when any run is
below the floor or the page is not the declared print width. Usage: python tools/_min_text_check.py fig.pdf --min-pt 8 --width-in 3.5"""
import argparse, json, math, sys
from pypdf import PdfReader


def _visit_drawn_text(page, visitor):
    """Bind buffered visitor text to the last text-show matrix, not a pre-Tm memo.

    pypdf may report buffered text at Tf/ET/position changes with a stale
    memo matrix. Its operand visitor exposes the matrix at Tj/TJ instead.
    Copy it: extractor matrices are mutable. Keep font decoding in pypdf.
    """
    shown = None

    def before(op, operands, cm, tm):
        nonlocal shown
        if op in (b"Tj", b"TJ", b"'", b'"'):
            shown = (list(cm), list(tm))

    def visit(text, cm, tm, font, size):
        if text and text.strip() and shown is not None:
            cm, tm = shown
        visitor(text, cm, tm, font, size)

    page.extract_text(visitor_text=visit, visitor_operand_before=before)


def text_sizes(pdf):
    sizes = []
    for page in PdfReader(pdf).pages:
        def visit(text, cm, tm, font_dict, font_size):
            if text and text.strip():
                a, b, c, d = (cm[0] * tm[0] + cm[2] * tm[1], cm[1] * tm[0] + cm[3] * tm[1],
                              cm[0] * tm[2] + cm[2] * tm[3], cm[1] * tm[2] + cm[3] * tm[3])
                sizes.append((round(font_size * math.sqrt(abs(a * d - b * c)), 3), text.strip()[:40]))
        _visit_drawn_text(page, visit)
    return sizes


def check(pdf, min_pt, width_in):
    reader = PdfReader(pdf); box = reader.pages[0].mediabox
    page_w = float(box.width) / 72
    sizes = text_sizes(pdf)
    smallest = min(sizes) if sizes else (None, "")
    ok = bool(sizes) and smallest[0] >= min_pt - 0.05 and abs(page_w - width_in) < 0.02
    return dict(pdf=str(pdf), page_width_in=round(page_w, 3), declared_width_in=width_in, min_text_pt=min_pt,
                text_runs=len(sizes), smallest_pt=smallest[0], smallest_text=smallest[1], status="PASS" if ok else "FAIL")


def add_args(parser):
    """--min-text-pt (default 8) and --print-width (default: 3.5 in for a single-column design, 7.2 in otherwise)."""
    parser.add_argument("--min-text-pt", type=float, default=8.0,
                        help="smallest printed text size in pt at the print width (docs/FIGURE_STYLE.md gate: 8)")
    parser.add_argument("--print-width", type=float, default=None,
                        help="declared print width in inches (3.5 single column, 7.2 double); default from the design width")


def enforce(pdf, min_pt):
    """Fail closed after drawing: read the drawn PDF back and refuse when any text run is under min_pt or the page is not the
    print width recorded by tools/sapote_min_text.R (<stem>_min_text.json). Writes <stem>_min_text_check.json either way."""
    from pathlib import Path
    pdf = Path(pdf); rec = json.loads(pdf.with_name(pdf.stem + "_min_text.json").read_text())
    width = rec["print_width_in"]; width = width[0] if isinstance(width, list) else width
    r = check(str(pdf), float(min_pt), float(width))
    pdf.with_name(pdf.stem + "_min_text_check.json").write_text(json.dumps(r, indent=1) + "\n")
    if r["status"] != "PASS":
        raise RuntimeError(f"MIN_TEXT_CHECK_FAILED: smallest text {r['smallest_pt']} pt ({r['smallest_text']!r}) at "
                           f"{r['page_width_in']} in; floor {min_pt} pt at {width} in")
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf"); ap.add_argument("--min-pt", type=float, default=8.0); ap.add_argument("--width-in", type=float, required=True)
    a = ap.parse_args(); r = check(a.pdf, a.min_pt, a.width_in)
    print(json.dumps(r)); sys.exit(0 if r["status"] == "PASS" else 2)


def _font_length(text, basefont, size):
    """Advance width (pt) of text in the Arial face named by the PDF BaseFont (subset prefix ignored), via matplotlib's font finder
    and Pillow; the embedded subset fonts re-map character codes, so their /Widths cannot be read by Unicode."""
    from matplotlib import font_manager
    from PIL import ImageFont
    name = str(basefont or "").split("+")[-1].lower()
    fp = font_manager.FontProperties(family="Arial", weight="bold" if "bold" in name else "normal",
                                     style="italic" if ("italic" in name or "oblique" in name) else "normal")
    path = font_manager.findfont(fp, fallback_to_default=True)
    return ImageFont.truetype(path, 1000).getlength(text) / 1000 * size


def pdf_text_boxes(pdf):
    """Upright text boxes (pt) of the drawn PDF, one per line: consecutive text runs on one baseline that abut (gap within +/- 0.5 em)
    are merged, as ggtext/plotmath draw one line in several runs. Rotated text (axis titles) is skipped.
    Returns a list of (text, x0, x1, y0, y1)."""
    from pypdf import PdfReader
    page = PdfReader(str(pdf)).pages[0]; runs = []
    def visit(text, cm, tm, font, fs):
        if not text.strip() or font is None:
            return
        a, b, c, d, e, f = [float(v) for v in tm]; ca, cb, cc, cd, ce, cf = [float(v) for v in cm]
        if abs(b) > 1e-6 or abs(c) > 1e-6:
            return
        size = abs(a * float(fs or 1) * ca); lead = len(text) - len(text.lstrip()); bf = font.get("/BaseFont")
        start = ca * e + ce; yb = cd * f + cf
        # pypdf reports the text-object origin for every run of a mixed-font line: a run that repeats the previous run's origin and
        # baseline continues after it (advance = previous run's full width, trailing spaces included)
        if runs and abs(runs[-1][5] - start) < 1e-6 and abs(runs[-1][3] - yb) < 1e-6:
            start = runs[-1][6]
        x0 = start + (_font_length(text[:lead], bf, size) if lead else 0.0)
        runs.append([text.strip(), x0, x0 + _font_length(text.strip(), bf, size), yb, size, ca * e + ce, start + _font_length(text, bf, size)])
    _visit_drawn_text(page, visit)
    lines = []
    for r in sorted(runs, key=lambda r: (round(r[3], 1), r[1])):
        # M5_452 overlap_check_columns: join only runs that do not overlap (gap >= -0.25 pt). The old window (-0.5 em .. +0.5 em) also
        # joined overlapping runs, so two separate labels running into each other on one baseline became one "line" and were never compared.
        if lines and abs(lines[-1][3] - r[3]) < 0.1 and -0.25 <= r[1] - lines[-1][2] <= 0.5 * r[4]:
            lines[-1][0] += " " + r[0]; lines[-1][2] = max(lines[-1][2], r[2]); continue
        lines.append(list(r))
    return [(t, x0, x1, yb - 0.72 * s, yb + 0.21 * s) for t, x0, x1, yb, s, *_ in lines]


def pdf_text_overlaps(pdf, tol=0.25):
    """Pairs of upright text lines in the drawn PDF whose boxes overlap by more than tol pt in both directions: the delivered artwork,
    so device-dependent label placement (ggrepel) cannot pass on one device and collide on another."""
    bx = sorted(set(pdf_text_boxes(pdf)), key=lambda r: r[1]); hits = []
    for i, (t1, a0, a1, b0, b1) in enumerate(bx):
        for t2, c0, c1, d0, d1 in bx[i + 1:]:
            if c0 >= a1 - tol:
                break
            if d0 < b1 - tol and b0 < d1 - tol:
                hits.append(f"{t1} | {t2}")
    return hits


def pdf_stroke_segments(pdf, rgb, tol=0.01):
    """Straight two-point stroked subpaths drawn in stroke colour rgb (0-1), in PDF points (y up): (x0, y0, x1, y1). The current
    transform (q/Q/cm) is followed, so cairo's flipped page matrix is handled. Curves and rectangles are not segments."""
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    reader = PdfReader(str(pdf)); page = reader.pages[0]; ops = ContentStream(page.get_contents(), reader).operations

    def mul(m, n):
        a, b, c, d, e, f = m; A, B, C, D, E, F = n
        return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)
    ctm, stack, sc, path, segs = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), [], None, [], []
    for args, op in ops:
        op = op.decode() if isinstance(op, bytes) else op
        if op == "q":
            stack.append((ctm, sc))
        elif op == "Q":
            ctm, sc = stack.pop() if stack else (ctm, sc)
        elif op == "cm":
            ctm = mul(tuple(float(v) for v in args), ctm)
        elif op in ("SC", "SCN", "RG"):
            try:
                sc = tuple(float(v) for v in args)
            except (TypeError, ValueError):
                sc = None
        elif op == "G":
            sc = (float(args[0]),) * 3
        elif op in ("m", "l"):
            x, y = float(args[0]), float(args[1]); p = (ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5])
            if op == "m" or not path or path[-1] is None:
                path.append([p])
            else:
                path[-1].append(p)
        elif op in ("c", "v", "y", "re"):
            path.append(None)
        elif op in ("S", "s"):
            if sc is not None and len(sc) == 3 and all(abs(u - v) <= tol for u, v in zip(sc, rgb)):
                segs += [(*sp[0], *sp[-1]) for sp in path if sp and len(sp) == 2]
            path = []
        elif op in ("f", "F", "f*", "B", "B*", "b", "b*", "n"):
            path = []
    return segs


def pdf_axis_panels(pdf, ncol):
    """Panel frames (x0, x1, y0, y1) in PDF points, left to right, from the black axis lines (theme_classic): per page column the longest
    horizontal black segment gives x0-x1 and the bottom, the longest vertical one gives the y extent."""
    from pypdf import PdfReader
    width = float(PdfReader(str(pdf)).pages[0].mediabox.width); colw = width / ncol
    segs = pdf_stroke_segments(pdf, (0.0, 0.0, 0.0), tol=0.02); frames = []
    for c in range(ncol):
        inside = [s for s in segs if c * colw <= (s[0] + s[2]) / 2 < (c + 1) * colw]
        hor = [s for s in inside if abs(s[1] - s[3]) < 0.01]; ver = [s for s in inside if abs(s[0] - s[2]) < 0.01]
        if not hor or not ver:
            continue
        h = max(hor, key=lambda s: abs(s[2] - s[0])); v = max(ver, key=lambda s: abs(s[3] - s[1]))
        frames.append((min(h[0], h[2]), max(h[0], h[2]), min(v[1], v[3]), max(v[1], v[3])))
    return frames


def pdf_axis_panels_grid(pdf, nrow, ncol, n_panels):
    """m5_452_protein_pcoa_multiset_grid: panel frames (x0, x1, y0, y1) in PDF points for a page of n_panels drawn row by row in an
    nrow x ncol grid (top row first, left to right), from the black axis lines (theme_classic). Per page column, the long horizontal
    black segments (> 30% of the column width) are the x axes of that column's panels, top to bottom; each is paired with the longest
    vertical black segment starting at its left end (the y axis). Returns [] unless exactly n_panels frames are found."""
    from pypdf import PdfReader
    width = float(PdfReader(str(pdf)).pages[0].mediabox.width); colw = width / ncol
    segs = pdf_stroke_segments(pdf, (0.0, 0.0, 0.0), tol=0.02); cells = {}
    for c in range(ncol):
        inside = [s for s in segs if c * colw <= (s[0] + s[2]) / 2 < (c + 1) * colw]
        hor = sorted((s for s in inside if abs(s[1] - s[3]) < 0.01 and abs(s[2] - s[0]) > 0.3 * colw), key=lambda s: -s[1])
        ver = [s for s in inside if abs(s[0] - s[2]) < 0.01]
        for r, h in enumerate(hor[:nrow]):
            x0, x1, y = min(h[0], h[2]), max(h[0], h[2]), h[1]
            vs = [v for v in ver if abs(v[0] - x0) < 1.0 and abs(min(v[1], v[3]) - y) < 1.0]
            if vs:
                v = max(vs, key=lambda v: abs(v[3] - v[1])); cells[(r, c)] = (x0, x1, y, max(v[1], v[3]))
    frames = [cells[(i // ncol, i % ncol)] for i in range(n_panels) if (i // ncol, i % ncol) in cells]
    return frames if len(frames) == n_panels else []


def page_label_faults_frames(pdf, frames, max_leader_in, leader_rgb, tol=0.25):
    """m5_452_protein_pcoa_multiset_grid: as page_label_faults, but each text box or leader is assigned to the panel frame whose centre is
    nearest (grid pages have panels in rows as well as columns). Returns {panel index: [fault, ...]}."""
    centre = [((f[0] + f[1]) / 2, (f[2] + f[3]) / 2) for f in frames]
    near = lambda x, y: min(range(len(frames)), key=lambda k: (centre[k][0] - x) ** 2 + (centre[k][1] - y) ** 2)
    faults = {k: [] for k in range(len(frames))}
    bx = sorted(set(pdf_text_boxes(pdf)), key=lambda r: r[1])
    for i, (t1, a0, a1, b0, b1) in enumerate(bx):
        for t2, c0, c1, d0, d1 in bx[i + 1:]:
            if c0 >= a1 - tol:
                break
            if d0 < b1 - tol and b0 < d1 - tol:
                for k in {near((a0 + a1) / 2, (b0 + b1) / 2), near((c0 + c1) / 2, (d0 + d1) / 2)}:
                    faults[k].append(f"overlap: {t1} | {t2}")
    for x0, y0, x1, y1 in pdf_stroke_segments(pdf, leader_rgb):
        length = math.hypot(x1 - x0, y1 - y0) / 72
        if length > max_leader_in + 0.005:
            faults[near((x0 + x1) / 2, (y0 + y1) / 2)].append(f"leader {length:.2f} in > {max_leader_in} in")
    return faults


def page_label_faults(pdf, ncol, max_leader_in, leader_rgb, tol=0.25):
    """M5_452 page, read from the drawn PDF: per page column (one panel per column) the overlapping upright text pairs and the label
    leaders (stroked leader_rgb segments) longer than max_leader_in inches (+0.005 in for rounding). Returns {column: [fault, ...]}."""
    from pypdf import PdfReader
    width = float(PdfReader(str(pdf)).pages[0].mediabox.width); colw = width / ncol
    column = lambda x: min(ncol - 1, max(0, int(x // colw)))
    faults = {c: [] for c in range(ncol)}
    bx = sorted(set(pdf_text_boxes(pdf)), key=lambda r: r[1])
    for i, (t1, a0, a1, b0, b1) in enumerate(bx):
        for t2, c0, c1, d0, d1 in bx[i + 1:]:
            if c0 >= a1 - tol:
                break
            if d0 < b1 - tol and b0 < d1 - tol:
                for c in {column((a0 + a1) / 2), column((c0 + c1) / 2)}:
                    faults[c].append(f"overlap: {t1} | {t2}")
    for x0, y0, x1, y1 in pdf_stroke_segments(pdf, leader_rgb):
        length = math.hypot(x1 - x0, y1 - y0) / 72
        if length > max_leader_in + 0.005:
            faults[column((x0 + x1) / 2)].append(f"leader {length:.2f} in > {max_leader_in} in")
    return faults
