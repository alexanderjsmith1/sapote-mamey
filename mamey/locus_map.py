"""mamey/locus_map.py — deterministic gene-arrow locus maps, matplotlib PNG (v9.7.90).

SIBLING (not a duplicate): `mamey/figures/locus_map.py` is a separate, stdlib-only SVG renderer
(no matplotlib dependency) with its own generic-role palette. This module is the PNG path used by
the main figure pipeline (cli / render_all_figures / compile_report) and reads the extensible
chemotype-role palette from mamey/data/locus_role_palette.json. Different format + dependency
profile + role granularity — both are intentional.


Single-BGC maps (top AB/AF leads, Mode B BGCs) and paired maps (RG-GMCI HIGH pairs).
Pure deterministic extraction-layer figure; no LLM. Reads antiSMASH
gene_functions/sec_met_domain qualifiers (NOT `product`), so a CDS with an empty
product still gets a role.

Reproduces the AS-XXX phosphonate three-locus figure exactly. The role palette lives in
mamey/data/locus_role_palette.json so chemotype roles extend without code edits; unknown
genes fall to "other / hypothetical" (never crash). The in-run path renders from the region
GBK already open during inventory — no K0 dependency. Post-seal re-render uses the sealed
per-CDS table (K0) as the row source.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import re
from pathlib import Path
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow, Patch
    from matplotlib.ticker import MaxNLocator, FuncFormatter
    _HAVE_MPL = True
except ImportError as _e:  # figure deps are optional; clear message, not a traceback (#35)
    _HAVE_MPL = False
    _MPL_ERR = str(_e)

    def _require_mpl():
        raise RuntimeError(
            "Figure generation needs matplotlib. Install the figures extra: "
            "`pip install -e '.[figures]'` (or `.[all]`). "
            f"(import error: {_MPL_ERR})")

_PALETTE_PATH = Path(__file__).parent / "data" / "locus_role_palette.json"
FOOTER = ("Data-only figure · capacity-level, not a product claim · "
          "gene roles = antiSMASH rule/smCOG annotation (not BLASTP-confirmed) · "
          "KCB = similarity, not identity · arrows to scale within each panel")


def _load_palette() -> tuple[list[tuple], tuple, list[tuple]]:
    """Load the ordered palette from JSON. Returns (rules, default_role, short_labels)
    where rules is [(compiled_regex, role, color, is_core), ...]."""
    d = json.loads(_PALETTE_PATH.read_text(encoding="utf-8"))
    rules = [(re.compile(e["regex"], re.I), e["role"], e["color"], e["is_core"])
             for e in d["palette"]]
    dr = d["default_role"]
    default = (dr["role"], dr["color"], dr["is_core"])
    short = [tuple(pair) for pair in d["short_labels"]]
    return rules, default, short


# loaded once at import; unknown tokens fall to the default (never crash)
_RULES, _DEFAULT_ROLE, _SHORT = _load_palette()


def classify(blob: str):
    """Map a gene_functions/sec_met_domain blob to (role, color, is_core); first hit wins."""
    for rx, role, color, core in _RULES:
        if rx.search(blob):
            return role, color, core
    return _DEFAULT_ROLE


def _short(role: str) -> str:
    for k, v in _SHORT:
        if k.lower() in role.lower():
            return v
    return ""


def cds_rows_from_gbk(gbk_path):
    """Extract CDS rows from one antiSMASH region GBK. Returns (rows, region_len)."""
    from Bio import SeqIO
    rec = next(SeqIO.parse(str(gbk_path), "genbank"))
    rows = []
    for i, ft in enumerate((f for f in rec.features if f.type == "CDS"), 1):
        q = ft.qualifiers
        blob = " ".join(q.get("gene_functions", []) + q.get("sec_met_domain", []) + q.get("note", []))
        role, color, core = classify(blob)
        rows.append({
            "locus_tag": (q.get("locus_tag") or [f"cds{i:02d}"])[0],
            "order": i, "start": int(ft.location.start), "end": int(ft.location.end),
            "strand": ft.location.strand or 1, "length_aa": len((q.get("translation") or [""])[0]),
            "gene_functions": blob, "role": role, "color": color, "is_core": core,
        })
    return rows, len(rec.seq)


def cds_rows_from_gene_context(gene_context_path, bgc_id):
    """Re-hydrate CDS rows for one BGC directly from a <SID>_gene_context.jsonl file.

    An explicit file-path loader for the rich per-CDS blob (sec_met_domains + the full smCOG
    gene_functions string). It builds the same gene_functions + sec_met_domains blob the palette
    _meta specifies, so a gene annotated only by smCOG (transport / regulation / redox / tailoring)
    gets its real role instead of falling to grey 'other / hypothetical'.

    NOTE (v9.7.117 reconciliation): the analysis-chat patch that motivated this reported the renderer
    being fed the THIN <SID>_gene_by_gene_all_bgcs.csv (gene_functions = placeholder 'biosynthetic
    context'), giving 82% grey. That thin-CSV path is NOT what the current tree's renderers use — both
    the in-run path (cds_rows_from_gbk, full GBK qualifiers) and the post-seal path
    (load_gene_context + cds_rows_from_table) already read the rich blob and produce ~64% grey on
    AS-XXX. So this loader does not fix a live bug in those paths; it is a verified, explicit
    file-path entry point for the rich source (useful for ad-hoc/offline re-renders that would
    otherwise reach for the thin CSV). Determinism holds — same palette/classify, same authoritative
    blob. Verified on AS-XXX: BGC001 grey 87% (sec_met-only) → 68% (full blob), 15 genes recovered.
    Returns rows in the cds_rows_from_table dict format, or [] if the file/bgc is absent.
    """
    import ast
    p = Path(gene_context_path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as fh:
        lines = fh.readlines()
    # the jsonl has a header line (line 0); records follow
    for line in lines[1:]:
        try:
            d = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if d.get("bgc_id") != bgc_id:
            continue
        cds = d.get("cds", [])
        if isinstance(cds, str):
            try:
                cds = ast.literal_eval(cds)
            except (ValueError, SyntaxError):
                return []
        rows = []
        for i, c in enumerate(cds, 1):
            sm = c.get("sec_met_domains", [])
            if isinstance(sm, str):
                sm = ast.literal_eval(sm) if sm.startswith("[") else ([sm] if sm else [])
            gf = str(c.get("gene_functions", "") or "")
            # full blob = sec_met_domains + the real smCOG gene_functions string (the fix)
            blob = (" ".join(sm) + " " + gf).strip()
            rows.append({
                "locus_tag": c.get("locus_tag") or f"cds{i:02d}",
                "order": int(c.get("order") or i),
                "start": int(c.get("start") or 0),
                "end": int(c.get("end") or 0),
                "strand": c.get("strand", 1),
                "length_aa": int(c.get("length_aa") or c.get("aa_length") or 0),
                "gene_functions": blob,
            })
        return cds_rows_from_table(rows)
    return []


def cds_rows_from_table(rows):
    """Re-hydrate CDS rows from the sealed per-CDS table (K0) for post-seal re-render.
    Accepts dict rows with start/end/strand and either a gene_functions blob or sec_met_domains;
    re-derives role/color/is_core via the same palette so post-seal == in-run."""
    out = []
    for i, r in enumerate(rows, 1):
        blob = r.get("gene_functions") or r.get("sec_met_domains") or ""
        if isinstance(blob, list):
            blob = " ".join(blob)
        role, color, core = classify(blob)
        strand = r.get("strand", 1)
        strand = 1 if str(strand) in ("1", "+") else (-1 if str(strand) in ("-1", "-") else 1)
        out.append({
            "locus_tag": r.get("locus_tag") or f"cds{i:02d}",
            "order": int(r.get("order") or i),
            "start": int(r.get("start") or 0), "end": int(r.get("end") or 0),
            "strand": strand, "length_aa": int(r.get("length_aa") or r.get("aa_length") or 0),
            "gene_functions": blob, "role": role, "color": color, "is_core": core,
        })
    return out


SPARSE_MAX = 18          # <= this many genes -> horizontal locus labels; more -> rotated 90deg
LABEL_FONT_PT = 6.0      # LS-2: per-arrow locus label must stay >= 6.0pt
USE_FULL_WHEN_SPARSE = False   # True -> 'ctg162_11' on sparse panels; False -> suffix '11' (contig is in subtitle)

# LOCUS_MAP_RENDER (v9.7.122): suppress a rotated locus label when its gene is too narrow in
# display coordinates for the label to clear its neighbours. Display-geometry-driven, NOT
# role-driven — a gene is suppressed because it is physically too narrow on screen, never
# because it is deemed unimportant. Every gene still appears in the companion _data.csv.
_FIG_USABLE_PTS = 768.0   # 13 in × 72 pt/in × ~82% usable panel width
_MIN_LABEL_PTS = 9.0      # below this display width, a rotated 6 pt label collides with neighbours


def _label_visible(gene_bp_width: int, span: int, dense: bool) -> bool:
    """Whether a per-arrow locus label fits without colliding. Sparse panels always show all."""
    if not dense:
        return True
    if span <= 0:
        return False
    gene_pts = _FIG_USABLE_PTS * (gene_bp_width / span)
    return gene_pts >= _MIN_LABEL_PTS


def _label_visibility_for_rows(rows) -> list[bool]:
    """Return one visibility decision per gene, preserving companion-data order.

    Dense maps may suppress physically colliding labels, but the suppression must
    never be silent: :func:`render_locus_map` reports the shown/total count on the
    figure and records this boolean for every gene in the companion CSV.
    """
    if not rows:
        return []
    maxx = max(r["end"] for r in rows)
    minx = min(r["start"] for r in rows)
    span = maxx - minx
    dense = len(rows) > SPARSE_MAX
    return [
        bool(r.get("locus_tag")) and _label_visible(r["end"] - r["start"], span, dense)
        for r in rows
    ]


def _locus_suffix(locus_tag: str) -> str:
    """ctg162_11 -> '11'. The contig (NODE_162 / ctg162) is already in the panel subtitle, so the
    suffix is the minimal per-arrow disambiguator and keeps dense panels overlap-safe."""
    return locus_tag.split("_")[-1] if "_" in (locus_tag or "") else (locus_tag or "")


def _draw_panel(ax, rows, title):
    maxx = max(r["end"] for r in rows)
    minx = min(r["start"] for r in rows)
    span = maxx - minx
    dense = len(rows) > SPARSE_MAX
    visibility = _label_visibility_for_rows(rows)
    for r, label_is_visible in zip(rows, visibility):
        x0, x1 = r["start"], r["end"]
        hl = min(900, (x1 - x0) * 0.35)
        if r["strand"] == 1:
            ax.add_patch(FancyArrow(x0, 0, x1 - x0, 0, width=0.5, head_width=0.5, head_length=hl,
                                    length_includes_head=True, color=r["color"], ec="black", lw=0.4))
        else:
            ax.add_patch(FancyArrow(x1, 0, x0 - x1, 0, width=0.5, head_width=0.5, head_length=hl,
                                    length_includes_head=True, color=r["color"], ec="black", lw=0.4))
        if r["is_core"]:
            lab = _short(r["role"])
            if lab:
                ax.text((x0 + x1) / 2, 0.55, lab, ha="center", va="bottom", fontsize=7, fontweight="bold")
        # v9.7.91 (issue 2.3): per-arrow assembly locus tag BELOW the arrow so each data point is
        # tied to ctgN_M. Horizontal when sparse; rotated 90deg when dense (overlap-safe). LS-2: 6.0pt.
        locus_text = (r.get("locus_tag", "") if (USE_FULL_WHEN_SPARSE and not dense)
                      else _locus_suffix(r.get("locus_tag", "")))
        # LOCUS_MAP_RENDER (v9.7.122): on dense panels, draw the label only when the gene is wide
        # enough in display coords that a rotated label won't collide. Every gene is still in the CSV.
        if locus_text and label_is_visible:
            ax.text((x0 + x1) / 2, -0.55, locus_text, ha="center", va="top",
                    fontsize=LABEL_FONT_PT, rotation=(90 if dense else 0), color="#222")
    # v9.7.116: zoom to the gene span, not full-contig coordinates. A BGC at a contig end was
    # crushed into an illegible right-edge sliver when plotted against the whole contig; pad the
    # gene span instead (min 500 bp) so the cluster fills the panel.
    _pad = max(span * 0.04, 500)
    ax.set_xlim(minx - _pad, maxx + _pad)
    # LOCUS_MAP_RENDER (v9.7.122): tiered y-limits — wider bottom margin on denser panels gives a
    # clear channel between the lowest rotated gene labels and the x-axis tick labels.
    very_dense = len(rows) > 35
    if very_dense:
        ax.set_ylim(-2.4, 1.5)   # 36+ genes (BGC033-class, 71 genes)
    elif dense:
        ax.set_ylim(-2.0, 1.5)   # 19–35 genes
    else:
        ax.set_ylim(-1.4, 1.4)   # <= 18 genes (horizontal labels)
    ax.set_yticks([])
    # LOCUS_MAP_RENDER: cap x-ticks and show kb so large bp coordinates don't crowd/overlap.
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune="both"))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.1f}k"))
    ax.tick_params(axis="x", labelsize=7, labelrotation=45, pad=2)
    ax.set_xlabel("position (kb)", fontsize=7.5, labelpad=3)
    ax.set_title(title, fontsize=9, loc="left", pad=4)
    ax.spines[["top", "right", "left"]].set_visible(False)


def _legend_handles(all_rows):
    seen = {}
    for r in all_rows:
        seen.setdefault(r["role"], r["color"])
    ordered = sorted(seen.items(),
                     key=lambda kv: (0 if ("step" in kv[0] or "module" in kv[0] or "machinery" in kv[0]) else 1, kv[0]))
    return [Patch(facecolor=c, edgecolor="black", label=role) for role, c in ordered]


def render_locus_map(panels, out_png, out_csv, suptitle, claim_prefix=""):
    if not _HAVE_MPL:
        _require_mpl()
    """panels: list of (title, cds_rows). 1 panel = single-BGC map; 2+ = paired/stacked.
    Returns (out_png, out_csv). The footer artist is placed strictly below the legend band
    (the anti-overlap fix); test_locus_map pins this so it can't regress.

    `out_png` is read as a filesystem path; matplotlib chooses the output format from
    the extension. Passing `.svg` produces vector SVG (used by the post-seal
    compile-report flow); `.png` produces raster as before. (W5, v9.7.149c.)
    """
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(13, 3.0 * n + 2.2))
    if n == 1:
        axes = [axes]
    all_rows = []
    for ax, (title, rows) in zip(axes, panels):
        _draw_panel(ax, rows, title); all_rows += rows
    # LOCUS_MAP_RENDER (v9.7.122): description is a caption BELOW the legend (caption convention),
    # not a suptitle stacked above the first panel's title. Band, bottom to top:
    #   footer (y=0.010) < caption (y=0.055) < legend (y0=0.09) < axes (rect y0=0.17).
    fig.tight_layout(rect=[0, 0.17, 1, 1.00])
    fig.legend(handles=_legend_handles(all_rows), loc="lower center", ncol=4,
               fontsize=7.4, frameon=False, bbox_to_anchor=(0.5, 0.09))
    visibility_by_panel = [_label_visibility_for_rows(rows) for _, rows in panels]
    label_total = sum(len(values) for values in visibility_by_panel)
    label_shown = sum(sum(values) for values in visibility_by_panel)
    label_note = (
        f"labels shown {label_shown}/{label_total}; full locus index in companion CSV"
        if label_total else "no locus labels available; see companion CSV"
    )
    fig.text(0.5, 0.055, f"{suptitle} · {label_note}",
             ha="center", va="top", fontsize=8.6, color="#1a1a2e")
    fig.text(0.5, 0.010, ((claim_prefix + " · ") if claim_prefix else "") + FOOTER,
             ha="center", fontsize=6.4, color="#777")
    # v9.7.374: render/write to a same-extension .tmp sibling then os.replace() into place, so a
    # process killed mid-savefig/mid-write (SIGKILL/OOM/power loss) — including on a post-seal
    # re-render over a package that already carries a valid prior figure/CSV — cannot truncate a
    # previously-valid deliverable to zero/partial bytes. The .tmp path keeps the real suffix
    # (".tmp" + original extension, not appended after it) so matplotlib's extension-based format
    # autodetection in savefig() still resolves to the correct SVG/PNG writer.
    out_png = Path(out_png)
    out_csv = Path(out_csv)
    _png_tmp = out_png.with_name(out_png.stem + ".tmp" + out_png.suffix)
    fig.savefig(_png_tmp, dpi=_safe_dpi(fig, 150), bbox_inches="tight"); plt.close(fig)
    os.replace(_png_tmp, out_png)
    _csv_tmp = out_csv.with_name(out_csv.name + ".tmp")
    with open(_csv_tmp, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["panel", "locus_tag", "order", "start", "end", "strand", "length_aa",
                    "role", "label_visible_on_figure", "gene_functions"])
        for (title, rows), visibility in zip(panels, visibility_by_panel):
            for r, label_is_visible in zip(rows, visibility):
                w.writerow([title, r["locus_tag"], r["order"], r["start"], r["end"],
                            "+" if r["strand"] == 1 else "-", r["length_aa"], r["role"],
                            "YES" if label_is_visible else "NO", r["gene_functions"][:200]])
    os.replace(_csv_tmp, out_csv)
    return str(out_png), str(out_csv)


# ── W5 (v9.7.149c): post-seal compile-report adapter ──────────────────────────
#
# The wishlist asked for an xml.etree.ElementTree-based SVG renderer. Reusing
# the canonical matplotlib renderer is the right call (a parallel renderer
# would diverge from the house style + palette). matplotlib emits SVG natively
# from a `.svg` file extension. See W5 findings doc for the trade-off rationale.

# Gene-by-gene CSV column-name candidates (mirrors the robustness pattern
# established in session_resume + figures_smoke).
_GENE_BGC_COLS    = ("bgc_id", "BGC_ID")
_GENE_LOCUS_COLS  = ("locus_tag", "locus", "gene")
_GENE_START_COLS  = ("gene_start", "start", "cds_start")
_GENE_END_COLS    = ("gene_end", "end", "cds_end")
_GENE_STRAND_COLS = ("strand", "Strand")
_GENE_DOMAIN_COLS = ("sec_met_domains", "aSDomains", "domain_annotations",
                     "gene_functions")
_GENE_AA_COLS     = ("aa_length", "length_aa", "length")


def _first_field(row: dict, cols: tuple) -> str:
    """Return the first non-empty value from `row` for any column in `cols`."""
    for c in cols:
        v = row.get(c)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def _read_gene_csv(pkg) -> tuple[list[dict], str]:
    """Locate + read `<strain>_gene_by_gene_all_bgcs.csv` from a sealed package.

    Returns (rows, csv_path). Returns ([], "") if the file is absent or
    unreadable. Never raises.
    """
    pkg = Path(pkg)
    candidates = sorted(pkg.glob("*_gene_by_gene_all_bgcs.csv"))
    if not candidates:
        return [], ""
    try:
        with open(candidates[0], newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f)), str(candidates[0])
    except (OSError, csv.Error, UnicodeDecodeError):
        return [], ""


def _rows_for_bgc(all_rows: list[dict], bgc_id: str) -> list[dict]:
    """Filter `all_rows` to the rows whose bgc_id column matches `bgc_id`,
    then map them onto the schema `cds_rows_from_table()` expects.

    Defensive: coerces `aa_length` / `length_aa` to a clean integer string;
    if it's anything other than parseable, drops it (zero downstream). This
    guards against CSV column-shift corruption (e.g. an unquoted ';'-list
    rendered as a ',' list overflowing the header) — symptom of F3 from W2
    rediscovered here.
    """
    out: list[dict] = []
    for r in all_rows:
        if _first_field(r, _GENE_BGC_COLS) != bgc_id:
            continue
        start = _first_field(r, _GENE_START_COLS)
        end = _first_field(r, _GENE_END_COLS)
        try:
            start_i = int(float(start)) if start else 0
            end_i = int(float(end)) if end else 0
        except (TypeError, ValueError):
            # Skip malformed row — non-blocking per wishlist
            continue
        # Defensive aa_length coercion — pass int as int, not raw string
        aa_raw = _first_field(r, _GENE_AA_COLS)
        try:
            aa_int = int(float(aa_raw)) if aa_raw else 0
        except (TypeError, ValueError):
            aa_int = 0
        out.append({
            "locus_tag": _first_field(r, _GENE_LOCUS_COLS) or f"cds{len(out)+1:02d}",
            "start": start_i,
            "end": end_i,
            "strand": _first_field(r, _GENE_STRAND_COLS) or "1",
            "sec_met_domains": _first_field(r, _GENE_DOMAIN_COLS),
            "aa_length": aa_int,
        })
    return out


def render_for_compile_report(package_dir, top_n: int = 5,
                              out_subdir: str = "locus_maps",
                              fmt: str = "svg",
                              renderer: str = "v8") -> dict:
    """Generate locus maps for the top-N BGCs of a sealed package, reading
    purely from `<strain>_gene_by_gene_all_bgcs.csv` (no GBK zip required).

    Output: `<pkg>/<out_subdir>/<BGC_ID>_locus_map.<fmt>` + companion `_data.csv`
    per BGC. Top-N is taken from the triage board's `Corrected_rank` ascending.

    `fmt` controls the matplotlib output extension and is "svg" by default
    (unchanged vector behaviour for environments with a working SVG→PDF chain).
    v9.7.152 (AS-XXX Bug 3): pass `fmt="png"` when the downstream PDF pipeline
    has no SVG rasterizer (xelatex's svg package needs Inkscape or
    ImageMagick→rsvg-convert; neither is always present), which otherwise makes
    PDF generation a hard, silent blocker. Unrecognized values degrade to
    "svg"; leading dots and case are normalized.

    Returns a dict:
        {"out": str, "rendered": [bgc_id, ...],
         "skipped": {bgc_id: reason, ...}, "skipped_reason": str | None}

    ``renderer="v8"`` is the evidence-dense default (LOCUS_MAP_V8, landed v9.7.405 on the
    owner's ruling): every exact locus tag shown, deterministic MIBiG per-gene comparator,
    PNG + SVG + exact-locus CSV + receipt. ``renderer="legacy"`` keeps the prior arrow map as
    a bounded compatibility comparison.

    Never raises. If matplotlib is unavailable, returns rendered=[] with a
    skipped_reason. Per-BGC failures land in `skipped` and don't block the rest.
    """
    if str(renderer).strip().lower() != "legacy":
        try:
            from .locus_map_v8 import render_for_compile_report_v8
            return render_for_compile_report_v8(
                package_dir, top_n=top_n, out_subdir=out_subdir, fmt=fmt)
        except Exception as exc:
            # Post-seal figures stay non-blocking, but a v8 failure is reported explicitly
            # rather than silently substituting the lower-information legacy map.
            return {"out": str(Path(package_dir) / out_subdir), "rendered": [], "skipped": {},
                    "skipped_reason": f"v8 renderer unavailable: {type(exc).__name__}: {exc}",
                    "renderer": "v8"}

    pkg = Path(package_dir)
    out_dir = pkg / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    # v9.7.152: normalize fmt; unrecognized values degrade to svg (the prior
    # default), so a bad value never raises or writes a garbage extension.
    ext = (fmt or "svg").lstrip(".").lower()
    if ext not in ("svg", "png"):
        ext = "svg"

    # Sanity check matplotlib (the module-level import already loaded it; this
    # just gives a clean degraded-mode return if something is wrong).
    try:
        import matplotlib  # noqa: F401
    except Exception:
        return {"out": str(out_dir), "rendered": [], "skipped": {},
                "skipped_reason": "matplotlib not available"}

    # Gene table — required
    all_rows, gene_csv_path = _read_gene_csv(pkg)
    if not all_rows:
        return {"out": str(out_dir), "rendered": [], "skipped": {},
                "skipped_reason": "no gene_by_gene_all_bgcs.csv in package"}

    # Top-N from triage board
    triage_glob = sorted(pkg.glob("*_4_triage_board.csv"))
    if not triage_glob:
        return {"out": str(out_dir), "rendered": [], "skipped": {},
                "skipped_reason": "no triage board CSV in package"}

    try:
        with open(triage_glob[0], newline="", encoding="utf-8") as f:
            triage_rows = list(csv.DictReader(f))
    except (OSError, csv.Error):
        return {"out": str(out_dir), "rendered": [], "skipped": {},
                "skipped_reason": "triage board unreadable"}

    def _rank_key(r):
        try:
            return float(r.get("Corrected_rank") or r.get("Rank") or 1e9)
        except (TypeError, ValueError):
            return 1e9

    ranked = sorted(triage_rows, key=_rank_key)[:top_n]

    rendered: list[str] = []
    skipped: dict[str, str] = {}

    for tr in ranked:
        bgc_id = (tr.get("BGC_ID") or tr.get("bgc_id") or "").strip()
        if not bgc_id:
            continue
        rows = _rows_for_bgc(all_rows, bgc_id)
        if not rows:
            skipped[bgc_id] = "no rows in gene_by_gene CSV for this BGC"
            continue
        try:
            cds_rows = cds_rows_from_table(rows)
            svg_path = out_dir / f"{bgc_id}_locus_map.{ext}"
            csv_path = out_dir / f"{bgc_id}_locus_map_data.csv"
            node = (tr.get("Node_ID") or tr.get("Contig") or
                    tr.get("Node") or "").strip()
            title = f"{bgc_id}" + (f" · {node}" if node else "")
            suptitle = (f"Locus map for {bgc_id}"
                        + (f" on {node}" if node else "")
                        + " (capacity-level; antiSMASH role annotations).")
            render_locus_map([(title, cds_rows)], str(svg_path),
                             str(csv_path), suptitle=suptitle)
            rendered.append(bgc_id)
        except Exception as e:
            # Non-blocking — record and continue
            skipped[bgc_id] = f"{type(e).__name__}: {e}"
            continue

    return {"out": str(out_dir), "rendered": rendered,
            "skipped": skipped, "skipped_reason": None}
