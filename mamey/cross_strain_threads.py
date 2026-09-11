"""mamey/cross_strain_threads.py — cross-strain shared biosynthetic-thread arc figure (DRAFT v9.7.103).

WHAT IT DRAWS. Strains arranged on a ring; an arc joins two strains when they SHARE a biosynthetic
COMPOUND CLASS (e.g. both carry an HSAF/PTM thread, both a ranthipeptide). Node colour = host
association (bee/wasp/moss/…). Edge colour = the shared class. This visualizes the cross-host recurrence
findings (e.g. the five-strain HSAF/PTM antifungal thread) as a single deliverable during analysis.

CLAIM-SAFETY CONTRACT (this is the whole reason it's a deterministic module, not a freehand plot):
  * Edges are CLASS-LEVEL CO-OCCURRENCE, never product identity and never raw kcb_top. An edge means
    "both strains carry biosynthetic capacity for class X", not "both make the same molecule". The data
    source is the cohort B2_Product_Class_Matrix (strain × class capacity counts), the same matrix the
    cohort heatmap uses — so the edges inherit the heatmap's capacity-level semantics.
  * The STANDING permanent-exclusion classes (genus_reference.STANDING_EXCLUSIONS) AND the UBIQUITOUS
    set (saccharide/NAPAA/siderophore/ectoine/melanin/terpene/…) are dropped: a class every strain
    carries is not an ecologically informative "shared thread" — drawing it manufactures a cross-host
    signal that is really just "everyone makes siderophores". This is the single most important guard.
  * RELEASE-AWARE. A cross-strain figure spans the AS cohort and is therefore PRIVATE by construction.
    In a public-tier render, strain IDs are redacted to AS-XXX. The caller passes release; the public
    path must never emit a real AS-### label.
  * Data-only PNG + companion <stem>_data.csv (edge list) + claim-safe footer, per the figure contract.

NOT a scoring change; deterministic; no LLM.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re
from itertools import combinations
from pathlib import Path
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

# Centralized exclusion SSOT (registry-sourced); fall back conservatively if unavailable.
try:
    from .genus_reference import STANDING_EXCLUSIONS as _STANDING
except Exception:
    _STANDING = frozenset({"saccharide", "fatty_acid"})

# Ubiquitous / habitat-non-specific classes — not ecologically informative as a "shared thread".
# Mirrors figures_split.UBIQUITOUS; kept here explicitly so a cross-strain edge can never be drawn
# for a class that every strain trivially carries.
#
# LANTHIPEPTIDE SUBDIVISION (user ruling, v9.7.103): the bare/umbrella `lanthipeptide` term is too
# common to be an informative thread and is dropped, BUT a class-RESOLVED variant (lanthipeptide_classI,
# lanthipeptide-class-iii, lanthipeptide_II, …) IS informative and is kept. The same logic applies to
# `lassopeptide` only at the umbrella level. We therefore exclude the umbrella token but NOT its
# class-resolved children — see _is_excluded() for the exact (non-substring) matching rule.
# v9.7.371 fix: the real B2_Product_Class_Matrix column names (master_workbook.py
# CANONICAL_V1_HEADERS) are "NI-siderophore" and "NRP-metallophore" -- there is no column
# literally named "siderophore", so the bare token never matched and iron-acquisition classes
# (confirmed near-universal/convergent across this cohort per cohort_synthesis.py's own documented
# finding) were NEVER excluded, exactly the "everyone makes siderophores" false-signal failure
# mode this guard's own docstring names as "the single most important guard". Kept the bare
# "siderophore" token too as a defensive substring match for any future differently-named column.
UBIQUITOUS = {"saccharide", "napaa", "ectoine", "siderophore", "ni-siderophore", "nrp-metallophore",
              "melanin", "terpene", "betalactone", "butyrolactone", "lanthipeptide",
              "lassopeptide", "hgle"}

# Umbrella terms excluded ONLY in their bare form; a class-resolved child survives.
_SUBDIVIDABLE = {"lanthipeptide", "lassopeptide"}
_CLASS_QUALIFIER = re.compile(r"(class|i{1,3}\b|iv\b|[1-4]\b)", re.I)

_NON_CLASS_COLS = {"strain", "label_provenance", "counts_reliability", "host", "host_association", "release"}
_LABEL_PROVENANCE = frozenset({"RAW_ANTISMASH", "GENE_BACKED"})

_AS_ID = re.compile(r"\bAS-?\d{2,}\b", re.I)


def _excluded_classes() -> set[str]:
    """Flat drop-set (standing ∪ ubiquitous), umbrella terms included. Use _is_excluded() for
    per-class decisions so the lanthipeptide/lassopeptide subdivision is honored; this flat set is
    retained for the footer ledger of what could be dropped."""
    return {c.lower() for c in _STANDING} | {c.lower() for c in UBIQUITOUS}


def _is_excluded(class_name: str) -> bool:
    """True if this class column should be dropped from cross-strain edges.

    Honors the lanthipeptide/lassopeptide subdivision: the bare umbrella token is excluded, but a
    class-RESOLVED variant (lanthipeptide_classI, lanthipeptide-class-iii, …) is kept.
    """
    c = str(class_name).strip().lower()
    if c in _excluded_classes():
        # exact umbrella match is excluded; a resolved child is a different (longer) token and won't be
        # caught here unless it's literally in the set
        if c in _SUBDIVIDABLE:
            return True
        # standing/ubiquitous non-subdividable exact hit
        if c not in _SUBDIVIDABLE:
            return True
    # umbrella-prefix case: keep class-resolved children, drop the bare/qualifier-less umbrella variants
    for umb in _SUBDIVIDABLE:
        if c.startswith(umb) and c != umb:
            tail = c[len(umb):]
            return not bool(_CLASS_QUALIFIER.search(tail))
    return False


def redact_strain(label: str) -> str:
    """Public-tier redaction: any AS-### strain id -> AS-XXX. Non-AS labels pass through."""
    return _AS_ID.sub("AS-XXX", str(label))


def derive_threads(rows: list[dict], min_strains_per_class: int = 3,
                   label_provenance: str = "RAW_ANTISMASH") -> tuple[list[dict], list[dict], list[str]]:
    """From B2 strain×class rows, derive (nodes, edges, dropped_classes).

    nodes: [{"strain","host"}]; edges: [{"a","b","class"}] for every pair of strains sharing a
    non-excluded class that is present (count>0) in both AND that is carried by at least
    `min_strains_per_class` strains (user ruling v9.7.103: default 3, so a thread links a real recurrence,
    not a single coincidental pair). Returns the dropped classes for the ledger.

    HOST is read ONLY from a trusted column (`host` / `host_association`); it is never inferred. An
    absent/blank host resolves to "unknown" (grey), never a guess (user ruling v9.7.103).
    """
    label_provenance = str(label_provenance).upper()
    if label_provenance not in _LABEL_PROVENANCE:
        raise ValueError(f"label_provenance must be one of {sorted(_LABEL_PROVENANCE)}")
    if not rows:
        return [], [], []
    if "label_provenance" in rows[0]:
        rows = [r for r in rows
                if str(r.get("label_provenance", "")).upper() == label_provenance
                or (label_provenance == "RAW_ANTISMASH" and not str(r.get("label_provenance", "")).strip())]
        if not rows:
            return [], [], []
    class_cols = [k for k in rows[0].keys() if k not in _NON_CLASS_COLS]
    kept_classes = [c for c in class_cols if not _is_excluded(c)]
    dropped = sorted(c for c in class_cols if _is_excluded(c))

    nodes, present = [], {}  # present[class] = [strains with count>0]
    for r in rows:
        s = str(r.get("strain", "")).strip()
        if not s:
            continue
        # host strictly from a trusted column; no inference, blank -> "unknown"
        raw_host = r.get("host", r.get("host_association", ""))
        host = str(raw_host).strip().lower() if raw_host not in (None, "") else "unknown"
        nodes.append({"strain": s, "host": host})
        for c in kept_classes:
            try:
                n = int(float(r.get(c) or 0))
            except (ValueError, TypeError):
                n = 0
            if n > 0:
                present.setdefault(c, []).append(s)

    edges = []
    for c, strains in present.items():
        uniq = sorted(set(strains))
        if len(uniq) < min_strains_per_class:
            continue
        for a, b in combinations(uniq, 2):
            edges.append({"a": a, "b": b, "class": c})
    return nodes, edges, dropped


def render_threads_figure(rows: list[dict], png_path, *, release: str = "PRIVATE",
                          strain_label: str = "AS-series cohort",
                          label_provenance: str = "RAW_ANTISMASH", plt=None):
    """Render the arc figure. release='PUBLIC' redacts AS-### node labels to AS-XXX.

    Returns {"status","png","csv","nodes","edges","dropped_classes","release"} or a skip dict.
    """
    if plt is None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    import math

    label_provenance = str(label_provenance).upper()
    nodes, edges, dropped = derive_threads(rows, label_provenance=label_provenance)
    if not nodes:
        return {"status": "SKIPPED", "reason": "no strain rows in B2 matrix"}
    if not edges:
        return {"status": "SKIPPED", "reason": "no shared non-excluded class threads between strains"}

    public = str(release).upper() == "PUBLIC"
    disp = (lambda s: redact_strain(s)) if public else (lambda s: s)

    # ring layout
    n = len(nodes)
    ang = {nd["strain"]: (2 * math.pi * i / n) for i, nd in enumerate(nodes)}
    pos = {s: (math.cos(a), math.sin(a)) for s, a in ang.items()}

    host_color = {"bee": "#E1A93B", "wasp": "#B4462F", "moss": "#3E8E5A",
                  "host-unconfirmed": "#9A9A9A", "unknown": "#9A9A9A"}
    classes = sorted({e["class"] for e in edges})
    cmap = plt.get_cmap("tab10")
    class_color = {c: cmap(i % 10) for i, c in enumerate(classes)}

    fig, ax = plt.subplots(figsize=(11, 9))
    # edges as quadratic arcs toward centre
    for e in edges:
        (x0, y0), (x1, y1) = pos[e["a"]], pos[e["b"]]
        mx, my = (x0 + x1) / 2 * 0.55, (y0 + y1) / 2 * 0.55  # pull toward centre
        t = [i / 24 for i in range(25)]
        bx = [(1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u ** 2 * x1 for u in t]
        by = [(1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u ** 2 * y1 for u in t]
        ax.plot(bx, by, color=class_color[e["class"]], lw=2.0, alpha=0.75, zorder=1)

    for nd in nodes:
        s = nd["strain"]; x, y = pos[s]
        ax.scatter([x], [y], s=620, color=host_color.get(nd["host"], "#9A9A9A"),
                   edgecolor="white", linewidth=1.5, zorder=3)
        ax.text(x, y, disp(s), ha="center", va="center", fontsize=7.5,
                color="white", fontweight="bold", zorder=4)
        ax.text(x * 1.18, y * 1.18, disp(s), ha="center", va="center", fontsize=9, fontweight="bold")

    # legends
    from matplotlib.lines import Line2D
    class_handles = [Line2D([0], [0], color=class_color[c], lw=3, label=c) for c in classes]
    host_seen = sorted({nd["host"] for nd in nodes})
    host_handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=host_color.get(h, "#9A9A9A"),
                           markersize=11, label=h) for h in host_seen]
    leg1 = ax.legend(handles=class_handles, title="Shared biosynthetic thread (class-level)",
                     loc="upper left", bbox_to_anchor=(-0.02, 1.0), fontsize=7, title_fontsize=8, frameon=False)
    ax.add_artist(leg1)
    ax.legend(handles=host_handles, title="Host association", loc="lower left",
              bbox_to_anchor=(-0.02, 0.0), fontsize=8, title_fontsize=8, frameon=False)

    ax.set_title("Cross-strain shared biosynthetic threads (class-level capacity)\n"
                 f"{strain_label} · recurrent compound classes link strains across host associations",
                 fontsize=12, fontweight="bold")
    foot = ("Data-only · class-level biosynthetic CAPACITY co-occurrence, not product identity and not "
            "activity · an edge = both strains carry capacity for that class (B2 matrix), never a shared "
            "molecule · KCB = similarity, not identity · ubiquitous/standing-exclusion classes "
            f"(saccharide, NAPAA, siderophore, …) dropped: {', '.join(dropped) or 'none present'}"
            f" · label provenance: {label_provenance}"
            + (" · PUBLIC tier: strain IDs redacted to AS-XXX" if public else " · PRIVATE (AS cohort)"))
    ax.text(0.5, -0.09, foot, transform=ax.transAxes, ha="center", va="top", fontsize=6, color="#444",
            wrap=True)
    ax.set_xlim(-1.45, 1.45); ax.set_ylim(-1.45, 1.45); ax.set_aspect("equal"); ax.axis("off")

    png_path = Path(png_path)
    fig.savefig(png_path, dpi=_safe_dpi(fig, 220), bbox_inches="tight"); plt.close(fig)

    csv_path = png_path.with_name(png_path.stem + "_data.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["strain_a", "strain_b", "shared_class", "label_provenance", "release"])
        for e in edges:
            w.writerow([disp(e["a"]), disp(e["b"]), e["class"], label_provenance, release])
    return {"status": "PASS", "png": str(png_path), "csv": str(csv_path),
            "nodes": len(nodes), "edges": len(edges), "dropped_classes": dropped,
            "release": release, "label_provenance": label_provenance}
