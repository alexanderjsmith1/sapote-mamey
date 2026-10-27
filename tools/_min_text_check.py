"""Read back the smallest drawn text size from a figure PDF (M5_452_render_cards_min_text_8pt).

Effective size of a text run = font size x the scale of the text and graphics matrices (pypdf visitor). The page width is the
printed width when the figure is placed at 100 %. Used by the R figure cards after drawing: refuse (exit 2) when any run is
below the floor or the page is not the declared print width. Usage: python tools/_min_text_check.py fig.pdf --min-pt 8 --width-in 3.5"""
import argparse, io, json, math, re, sys
from pypdf import PdfReader


def _mul(m, n):
    """PDF matrix product (row-vector convention): apply m, then n."""
    a, b, c, d, e, f = m; A, B, C, D, E, F = n
    return [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F]


def _visit_drawn_text(page, visitor, runs=False):
    """Bind buffered visitor text to the last text-show matrix, not a pre-Tm memo.

    pypdf may report buffered text at Tf/ET/position changes with a stale
    memo matrix. Its operand visitor exposes the matrix at Tj/TJ instead.
    Copy it: extractor matrices are mutable. Keep font decoding in pypdf.

    C114 workarounds (pypdf 6.14): the ' and " operators move to the next line (T*) after the before-visitor
    fires, and pypdf's own post-T* matrix is wrong (its baseline goes to 0), so the move is applied here from the
    tracked leading (TL; TD sets TL = -ty): tm' = [1 0 0 1 0 -TL] x tm. Text inside a Form XObject is
    reported with form-local matrices and then a second time as one whole-form run; inner runs are composed
    with the form /Matrix and the outer transform, and the repeated whole-form run is skipped.

    Merged runs: pypdf buffers consecutive text-show operators of one text object that stay on one line with one
    font resource, and reports them as one text with one matrix (the last one). A 4 pt run followed by an 8 pt run
    on the same baseline was read as 8 pt. With runs=True the visitor gets a sixth argument: the (cm, tm) of every
    text-show operator merged into the reported text, composed like cm, so a size check can take the smallest.
    Position readers keep the five-argument call and the last-run matrix.
    """
    shown = None
    leading = 0.0     # text leading TL, needed for T* inside ' and "
    pending = None    # matrix for a ' or " run, applied once the operator has finished
    ops = []          # operators being processed (before pushes, after pops)
    forms = []        # per open form: [composed matrix, inner operator seen, saved shown]
    pushed = []       # per open Do: whether it opened a form
    resources = [page.get("/Resources")]
    merged = []       # (cm, tm) of each text-show operator whose text pypdf still holds in its buffer

    def before(op, operands, cm, tm):
        nonlocal shown, leading, pending
        if forms:
            forms[-1][1] = True
        ops.append(op)
        if op == b"TL" and operands:
            leading = float(operands[0])
        elif op == b"TD" and len(operands) >= 2:
            leading = -float(operands[1])
        if op in (b"Tj", b"TJ"):
            shown = (list(cm), list(tm))
            merged.append(shown)
        elif op in (b"'", b'"'):
            # runs flushed while pypdf processes this operator keep their own matrix; the quoted run gets the new line
            a, b, c, d, e, f = (float(v) for v in tm)
            pending = (list(cm), [a, b, c, d, e - leading * c, f - leading * d])
        elif op == b"Do":
            opened = False
            try:
                res = resources[-1].get_object() if resources[-1] is not None else None
                xobj = res["/XObject"].get_object()[operands[0]].get_object()
                if xobj.get("/Subtype") == "/Form":
                    outer = _mul(list(cm), forms[-1][0]) if forms else list(cm)
                    matrix = [float(v) for v in xobj.get("/Matrix", [1, 0, 0, 1, 0, 0])]
                    forms.append([_mul(matrix, outer), False, shown])
                    resources.append(xobj.get("/Resources") or resources[-1])
                    opened = True
            except (KeyError, TypeError, AttributeError):
                opened = False    # not a readable form: no transform to compose, and pypdf skips it too
            pushed.append(opened)

    def after(op, operands, cm, tm):
        nonlocal shown, pending
        if ops:
            ops.pop()
        if op in (b"'", b'"') and pending is not None:
            shown, pending = pending, None
            merged.append(shown)
        elif op == b"Do" and pushed and pushed.pop():
            shown = forms.pop()[2]
            resources.pop()
        if op in (b"BT", b"ET", b"Tf", b"cm", b"Do"):
            merged.clear()    # pypdf's text buffer is empty after these, whether or not it reported anything

    def visit(text, cm, tm, font, size):
        batch = list(merged); merged.clear()    # every report empties pypdf's buffer
        if text and text.strip():
            in_do = bool(ops) and ops[-1] == b"Do"
            if in_do and pushed and pushed[-1] and forms and forms[-1][1]:
                return    # pypdf's repeated whole-form run: its inner runs were already reported
            if shown is not None:
                cm, tm = shown
            batch = batch or [(cm, tm)]
            outer = forms[:-1] if (in_do and pushed and pushed[-1]) else forms
            if outer:
                cm = _mul(list(cm), outer[-1][0])
                batch = [(_mul(list(c), outer[-1][0]), t) for c, t in batch]
        else:
            batch = [(cm, tm)]
        if runs:
            visitor(text, cm, tm, font, size, batch)
        else:
            visitor(text, cm, tm, font, size)

    page.extract_text(visitor_text=visit, visitor_operand_before=before, visitor_operand_after=after)


def _page_text_sizes(page):
    """(drawn size in pt, text) per reported run of one page; a merged run takes its smallest text-show operator."""
    sizes = []

    def visit(text, cm, tm, font_dict, font_size, batch):
        if text and text.strip():
            def size(cm, tm):
                a, b, c, d = (cm[0] * tm[0] + cm[2] * tm[1], cm[1] * tm[0] + cm[3] * tm[1],
                              cm[0] * tm[2] + cm[2] * tm[3], cm[1] * tm[2] + cm[3] * tm[3])
                return round(font_size * math.sqrt(abs(a * d - b * c)), 3)
            sizes.append((min(size(c, t) for c, t in batch), text.strip()[:40]))
    _visit_drawn_text(page, visit, runs=True)
    return sizes


def text_sizes(pdf):
    sizes = []
    for page in PdfReader(pdf).pages:
        sizes += _page_text_sizes(page)
    return sizes


def check(pdf, min_pt, width_in):
    reader = PdfReader(pdf); box = reader.pages[0].mediabox
    page_w = float(box.width) / 72
    sizes = text_sizes(pdf)
    smallest = min(sizes) if sizes else (None, "")
    ok = bool(sizes) and smallest[0] >= min_pt - 0.05 and abs(page_w - width_in) < 0.02
    return dict(pdf=str(pdf), page_width_in=round(page_w, 3), declared_width_in=width_in, min_text_pt=min_pt,
                text_runs=len(sizes), smallest_pt=smallest[0], smallest_text=smallest[1], status="PASS" if ok else "FAIL")


def pdf_printed_sizes(data, print_width_in):
    """Smallest text of a PDF (bytes) printed at print_width_in: each page is scaled to that width.
    Returns (printed pt, drawn pt, text, page width in) or None when the PDF has no text runs."""
    best = None
    for page in PdfReader(io.BytesIO(data)).pages:
        page_w = float(page.mediabox.width)
        for drawn, text in _page_text_sizes(page):
            printed = drawn * print_width_in * 72.0 / page_w
            if best is None or printed < best[0]:
                best = (printed, drawn, text, page_w / 72.0)
    return best


_SVG_UNDRAWN = {"defs", "metadata", "title", "desc", "style", "script", "clipPath", "mask", "symbol", "marker", "pattern"}
_SVG_TEXT = {"text", "tspan", "textPath"}
_SVG_LEN = re.compile(r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(px|pt|pc|in|cm|mm|em|%)?\s*$")
_SVG_PX = {None: 1.0, "px": 1.0, "pt": 96 / 72, "pc": 16.0, "in": 96.0, "cm": 96 / 2.54, "mm": 96 / 25.4}
_SVG_FONT_SHORTHAND = re.compile(r"(?:^|\s)((?:\d+\.?\d*|\.\d+)(?:px|pt|pc|in|cm|mm|em|%)?)(?=/|\s)")
_SVG_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


def _svg_length(value, inherited=None):
    m = _SVG_LEN.match(value or "")
    if not m:
        return None
    v, unit = float(m.group(1)), m.group(2)
    if unit in ("em", "%"):
        return None if inherited is None else v * inherited / (100.0 if unit == "%" else 1.0)
    return v * _SVG_PX[unit]


def _svg_style(el):
    out = {}
    for part in (el.get("style") or "").split(";"):
        k, sep, v = part.partition(":")
        if sep:
            out[k.strip().lower()] = v.strip()
    return out


def _svg_font_size(el, inherited):
    """(size in user units, ok). ok is False when a size is given in a form this reader does not resolve."""
    style = _svg_style(el)
    raw = style.get("font-size") or el.get("font-size")
    if raw is None and "font" in style:
        m = _SVG_FONT_SHORTHAND.search(" " + style["font"] + " ")
        raw = m.group(1) if m else style["font"]
    if raw is None:
        return inherited, True
    size = _svg_length(raw, inherited)
    return (size, size is not None)


def _svg_det(transform):
    """Area scale (determinant) of an SVG transform list, or None when it cannot be read."""
    det, pos = 1.0, 0
    text = transform or ""
    for m in _SVG_TRANSFORM.finditer(text):
        if text[pos:m.start()].strip(" ,\t\n"):
            return None
        pos = m.end()
        try:
            v = [float(x) for x in re.split(r"[\s,]+", m.group(2).strip()) if x]
        except ValueError:
            return None
        kind = m.group(1)
        if kind == "matrix" and len(v) == 6:
            det *= v[0] * v[3] - v[1] * v[2]
        elif kind == "scale" and len(v) in (1, 2):
            det *= v[0] * (v[1] if len(v) == 2 else v[0])
        elif kind in ("translate", "rotate", "skewX", "skewY") and v:
            pass
        else:
            return None
    return det if not text[pos:].strip(" ,\t\n") else None


def svg_printed_sizes(data, print_width_in):
    """Smallest drawn text of an SVG (bytes) printed at print_width_in, from font-size (attribute, style or font
    shorthand; px, pt, pc, in, cm, mm, em, %) and the transforms above it. The page width is the root width, the
    viewBox mapped with the default 'meet' fit. Returns ((printed pt, drawn pt, text, page width in) or None, reason)."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.parse(io.BytesIO(data)).getroot()
    except ET.ParseError as exc:
        return None, f"SVG not parsed ({exc})"
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return None, "not an SVG document"
    vb = [float(x) for x in re.split(r"[\s,]+", (root.get("viewBox") or "").strip()) if x] if root.get("viewBox") else None
    if vb is not None and (len(vb) != 4 or vb[2] <= 0 or vb[3] <= 0):
        return None, "unreadable viewBox"
    width, height = _svg_length(root.get("width")), _svg_length(root.get("height"))
    if root.get("width") and width is None or (width is not None and width <= 0):
        return None, f"page width {root.get('width')!r} is not an absolute length"
    if (root.get("preserveAspectRatio") or "").strip().startswith("none") and vb:
        return None, "preserveAspectRatio none: text is stretched unevenly"
    if vb and width:
        k = width / vb[2] if not height else min(width / vb[2], height / vb[3])
        page_px = width
    elif vb:
        k, page_px = 1.0, vb[2]
    elif width:
        k, page_px = 1.0, width
    else:
        return None, "no page width or viewBox"
    found, reason = [], []

    def hidden(el):
        style = _svg_style(el)
        return (el.tag.rsplit("}", 1)[-1] in _SVG_UNDRAWN or el.get("display") == "none" or style.get("display") == "none"
                or el.get("visibility") == "hidden" or style.get("visibility") == "hidden")

    def walk(el, size, det, in_text):
        if hidden(el):
            return
        name = el.tag.rsplit("}", 1)[-1]
        if name == "svg" and el is not root:
            reason.append("nested svg viewport"); return
        d = _svg_det(el.get("transform"))
        if d is None:
            reason.append(f"unreadable transform {el.get('transform')!r}"); return
        size, ok = _svg_font_size(el, size)
        if not ok:
            reason.append(f"unreadable font size on <{name}>"); return
        det *= d
        text_here = in_text or name in _SVG_TEXT
        if text_here and (el.text or "").strip():
            if size is None:
                reason.append(f"no font size for {el.text.strip()[:40]!r}")
            else:
                found.append((size * math.sqrt(abs(det)), el.text.strip()[:40]))
        for child in el:
            walk(child, size, det, text_here)
            if text_here and (child.tail or "").strip():
                if size is None:
                    reason.append(f"no font size for {child.tail.strip()[:40]!r}")
                else:
                    found.append((size * math.sqrt(abs(det)), child.tail.strip()[:40]))

    walk(root, None, 1.0, False)
    if reason:
        return None, "; ".join(sorted(set(reason))[:3])
    if not found:
        return None, "no text elements (text drawn as outlines or raster)"
    user, text = min(found)
    page_in = page_px / 96.0
    return (user * k * print_width_in * 72.0 / page_px, user * k * 0.75, text, page_in), ""


def printed_min_text(data, kind, print_width_in):
    """Smallest text size in pt of a vector figure (kind 'pdf' or 'svg', given as bytes) printed at print_width_in.
    Returns dict(source, smallest_pt, drawn_pt, smallest_text, page_width_in, reason); smallest_pt is None when the
    file cannot be measured (reason says why). Never a pass by default."""
    out = dict(source=kind, smallest_pt=None, drawn_pt=None, smallest_text="", page_width_in=None, reason="")
    try:
        if kind == "pdf":
            best, why = pdf_printed_sizes(data, print_width_in), "no text runs in the PDF (text drawn as outlines or raster)"
        elif kind == "svg":
            best, why = svg_printed_sizes(data, print_width_in)
        else:
            best, why = None, f"unsupported companion {kind!r}"
    except Exception as exc:  # unreadable companion: report, never pass
        best, why = None, f"{kind.upper()} not read ({type(exc).__name__}: {exc})"
    if best is None:
        out["reason"] = why
        return out
    out.update(smallest_pt=round(best[0], 2), drawn_pt=round(best[1], 2), smallest_text=best[2], page_width_in=round(best[3], 3))
    return out


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
