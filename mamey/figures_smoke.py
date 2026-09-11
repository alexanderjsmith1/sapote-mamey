"""figures_smoke.py — smoke-mode figure generation from triage + inventory CSVs.

Three figures, all derivable from data that exists in smoke-mode packages (no
`deep_data.json` required):

  1. fig_bgc_ranking.png       — top-15 BGCs by region length, coloured by boundary
  2. fig_class_composition.png — compound-class counts (standing-rule exclusions removed)
  3. fig_assembly_tier.png     — stacked bar of Interior / Edge / Full-contig fractions

Outputs go to `<pkg>/smoke_figures/`. Each figure ships with a companion
`fig_<id>_data.csv` (per the Developer or User's standing rule: data-only PNGs + sidecar CSV).

Non-blocking: if matplotlib is unavailable, the triage CSV is malformed, or any
individual figure raises, we degrade silently and return what we managed.

Wishlist W2 Part B (v9.7.149b → next).
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import pathlib
from typing import Optional


# House palette (matches cohort_figures style; boundary-by-shade for the
# ranking and tier figures)
from .boundary_palette import BLUE_GRADIENT as _BOUNDARY_COLOURS
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi
_DEFAULT_COLOUR = "#9aa5b1"  # neutral grey for unknown boundary

# Column-name candidates per logical field (mirrors session_resume robustness)
# v9.7.184 P4: on the REAL triage board, Assembly_Locator holds a locus string
# (e.g. "NZ_..._region001") while Boundary holds the Interior/Edge/Full-contig status. The old
# order put Assembly_Locator FIRST, so _first() returned the locus string and every BGC fell to
# the "Other" bucket in _fig_assembly_tier — zeroing the boundary composition on real strains.
# Read Boundary first; keep Assembly_Locator as a legacy fallback (older fixtures/inventories that
# stored the status under that key) so both schemas resolve correctly.
_LOC_COLS    = ("Boundary", "boundary", "Assembly_Locator", "assembly_locator")
_LEN_COLS    = ("Length_kb", "Region_Length_kb", "length_kb", "region_length_kb")
_CLASS_COLS  = ("Products", "Class", "products", "class")
_STAND_COLS  = ("Standing_rule", "standing_rule", "Downgrade")
_BGCID_COLS  = ("BGC_ID", "bgc_id")

# v9.7.374: the Assembly_Locator fallback in _LOC_COLS above is only a valid alias for
# boundary status on the TRIAGE board's legacy schema. On the INVENTORY CSV (_2_inventory.csv,
# cli.py _write_package), Assembly_Locator has always held a locus string (e.g.
# "NZ_CP012345.1_region001") and inventory carries no Boundary column at all. When
# _pick_source() falls back to inventory (its documented corrupt-triage recovery path),
# _first(r, _LOC_COLS) silently resolves to that locus string and every BGC either gets
# dumped into the assembly-tier "Other" bucket (zeroing the real Interior/Edge/Full-contig
# split) or, in the ranking figure, gets coloured/legended off a per-locus garbage token
# instead of a real boundary class. Only accept a resolved value that actually names a
# boundary status; anything else is treated as unresolved, so the fallback degrades to "no
# figure" rather than a wrong one.
_KNOWN_BOUNDARY_TOKENS = {"Interior", "Edge", "Full-contig", "Full_contig", "FullContig", "Unknown"}


def _resolve_boundary(row: dict) -> str:
    """Like _first(row, _LOC_COLS), but only accepts a value that names a real boundary
    status. Guards the Assembly_Locator fallback against inventory rows, where that column
    is always a locus string, never a boundary label."""
    for c in _LOC_COLS:
        v = row.get(c)
        if v in (None, ""):
            continue
        v = str(v).strip()
        if v in _KNOWN_BOUNDARY_TOKENS:
            return v
    return ""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate(package_dir, out_subdir: str = "smoke_figures") -> dict:
    """Generate the three smoke-mode figures for a sealed package.

    Returns a dict:
        {"out": str, "figures": int, "files": [str], "skipped_reason": str|None}

    Never raises. If matplotlib is missing, returns figures=0 with a reason.
    """
    pkg = pathlib.Path(package_dir)
    out = pkg / out_subdir
    out.mkdir(parents=True, exist_ok=True)

    plt = _import_matplotlib()
    if plt is None:
        # v9.7.151 (bunny-hop 60-file): record silent skips in the
        # package's issue_log so a user later wondering "where are my
        # figures?" can grep one place. Failure to write the log is
        # itself non-blocking (we already have no figures; we will not
        # turn that into a hard fail over a log line).
        try:
            with (pkg / "issue_log.md").open("a", encoding="utf-8") as _ilf:
                _ilf.write(
                    "\n- [SKIP] figures_smoke: matplotlib not available; "
                    "no smoke figures rendered. Install matplotlib + numpy "
                    "(see docs/PREREQUISITES.md) to populate this set.\n")
        except OSError:
            pass
        return {"out": str(out), "figures": 0, "files": [],
                "skipped_reason": "matplotlib not available"}

    triage = _read_csv_safe(_find_one(pkg, "*_4_triage_board.csv"))
    inventory = _read_csv_safe(_find_one(pkg, "*_2_inventory.csv"))

    if not triage and not inventory:
        try:
            with (pkg / "issue_log.md").open("a", encoding="utf-8") as _ilf:
                _ilf.write(
                    "\n- [SKIP] figures_smoke: no triage or inventory CSV "
                    "found in package; figures_smoke produced 0 figures.\n")
        except OSError:
            pass
        return {"out": str(out), "figures": 0, "files": [],
                "skipped_reason": "no triage or inventory CSV found"}

    made: list[str] = []
    for fn in (_fig_bgc_ranking, _fig_class_composition, _fig_assembly_tier):
        try:
            path = fn(plt, triage, inventory, out)
            if path:
                made.append(path.name)
        except Exception:
            # Non-blocking per the wishlist: a single bad figure must not
            # block the others or the run.
            continue

    return {"out": str(out), "figures": len(made), "files": made,
            "skipped_reason": None}


# ---------------------------------------------------------------------------
# Figure 1 — BGC ranking by region length
# ---------------------------------------------------------------------------

def _pick_source(triage: list[dict], inventory: list[dict]) -> list[dict]:
    """Choose the better source between triage and inventory.

    Triage is preferred when it contains rows with valid BGC_IDs. If the
    triage parses to rows but none have a BGC_ID column (the corrupt-CSV
    case — e.g. a binary-byte parse that produces garbage column names),
    inventory is used instead. This keeps figures alive when only one of
    the two CSVs is usable.
    """
    triage_usable = any(_first(r, _BGCID_COLS) for r in triage)
    if triage_usable:
        return triage
    return inventory


def _fig_bgc_ranking(plt, triage: list[dict], inventory: list[dict],
                     out_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Horizontal bar of top-15 BGCs by region length, coloured by boundary.

    Length comes from inventory CSV's `Length_kb` if present (triage doesn't
    carry it in current schemas); boundary comes from `Assembly_Locator` or
    `Boundary`. If lengths are unavailable we fall back to Corrected_rank
    descending — i.e. top-15 by rank.
    """
    # Build a per-BGC view with length + boundary
    inv_by_id = {_first(r, _BGCID_COLS): r for r in inventory
                 if _first(r, _BGCID_COLS)}
    rows = []
    source = _pick_source(triage, inventory)
    for r in source:
        bgc_id = _first(r, _BGCID_COLS)
        if not bgc_id:
            continue
        boundary = _resolve_boundary(r) or _resolve_boundary(inv_by_id.get(bgc_id, {}))
        length = _safe_float(_first(r, _LEN_COLS))
        if length is None and inv_by_id.get(bgc_id):
            length = _safe_float(_first(inv_by_id[bgc_id], _LEN_COLS))
        rows.append({"bgc_id": bgc_id, "length": length,
                     "boundary": boundary or "Unknown"})

    if not rows:
        return None

    # Sort by length desc (None last); take top 15
    rows.sort(key=lambda x: (x["length"] is None,
                             -(x["length"] or 0)))
    rows = rows[:15]

    # If all lengths are None, the figure is uninformative — bail.
    if all(r["length"] is None for r in rows):
        return None

    fig, ax = plt.subplots(figsize=(7.2, max(2.4, 0.32 * len(rows) + 1.0)))
    y_pos = list(range(len(rows)))[::-1]  # longest at top
    lengths = [r["length"] or 0 for r in rows]
    colours = [_BOUNDARY_COLOURS.get(r["boundary"], _DEFAULT_COLOUR)
               for r in rows]
    labels  = [r["bgc_id"] for r in rows]

    ax.barh(y_pos, lengths, color=colours, edgecolor="#1a1a1a", linewidth=0.4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Region length (kb)")
    ax.set_title("Top 15 BGCs by region length", loc="left", fontsize=11)

    # Legend (one swatch per boundary actually present)
    present_boundaries = list({r["boundary"] for r in rows})
    handles = [plt.Rectangle((0, 0), 1, 1,
                             color=_BOUNDARY_COLOURS.get(b, _DEFAULT_COLOUR))
               for b in present_boundaries]
    ax.legend(handles, present_boundaries, loc="lower right", fontsize=7,
              frameon=False)

    png_path = out_dir / "fig_bgc_ranking.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=_safe_dpi(fig, 150))
    plt.close(fig)

    _write_sidecar(out_dir / "fig_bgc_ranking_data.csv",
                   ["bgc_id", "length_kb", "boundary"],
                   [[r["bgc_id"], r["length"] if r["length"] is not None else "",
                     r["boundary"]] for r in rows])
    return png_path


# ---------------------------------------------------------------------------
# Figure 2 — Compound class composition
# ---------------------------------------------------------------------------

def _fig_class_composition(plt, triage: list[dict], inventory: list[dict],
                           out_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Bar chart of compound-class counts among non-excluded BGCs.

    Source: triage board's `Products` column, dropping rows where
    `Standing_rule` is non-empty (saccharide, NAPAA, hglE-KS-PREV-001, etc).
    """
    if not triage:
        return None

    counts: dict[str, int] = {}
    for r in triage:
        if _first(r, _STAND_COLS):
            continue  # excluded
        cls = _first(r, _CLASS_COLS)
        if not cls:
            continue
        # Some pipelines emit "NRPS; PKS" as a single cell — count each token
        for token in (t.strip() for t in cls.replace(",", ";").split(";")):
            if token:
                counts[token] = counts.get(token, 0) + 1

    if not counts:
        return None

    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    classes = [c for c, _ in ordered]
    values  = [v for _, v in ordered]

    fig, ax = plt.subplots(figsize=(max(5.0, 0.6 * len(classes) + 2.0), 3.8))
    ax.bar(classes, values, color="#1f3a93", edgecolor="#1a1a1a", linewidth=0.4)
    ax.set_ylabel("product-label token count")
    ax.set_title("Product-label token frequency (all tokens per BGC; standing-rule rows excluded)",
                 loc="left", fontsize=11)
    for tick in ax.get_xticklabels():
        tick.set_rotation(35)
        tick.set_ha("right")

    png_path = out_dir / "fig_class_composition.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=_safe_dpi(fig, 150))
    plt.close(fig)

    _write_sidecar(out_dir / "fig_class_composition_data.csv",
                   ["class", "count"],
                   [[c, v] for c, v in ordered])
    return png_path


# ---------------------------------------------------------------------------
# Figure 3 — Assembly-tier composition
# ---------------------------------------------------------------------------

def _fig_assembly_tier(plt, triage: list[dict], inventory: list[dict],
                       out_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Stacked bar showing the Interior / Edge / Full-contig fractions for
    the cohort BGCs (a one-bar visual of boundary composition).
    """
    source = _pick_source(triage, inventory)
    if not source:
        return None

    counts = {"Interior": 0, "Edge": 0, "Full-contig": 0, "Other": 0}
    for r in source:
        b = _resolve_boundary(r)
        norm = b.replace("_", "-")
        if norm == "Interior":
            counts["Interior"] += 1
        elif norm == "Edge":
            counts["Edge"] += 1
        elif norm in ("Full-contig", "FullContig"):
            counts["Full-contig"] += 1
        elif b:
            counts["Other"] += 1

    total = sum(counts.values())
    if total == 0:
        return None

    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    left = 0
    bars: list[tuple[str, int, str]] = []
    for name in ("Interior", "Edge", "Full-contig", "Other"):
        v = counts[name]
        if v == 0:
            continue
        colour = _BOUNDARY_COLOURS.get(name, _DEFAULT_COLOUR)
        ax.barh([0], [v], left=left, color=colour,
                edgecolor="#1a1a1a", linewidth=0.4, label=f"{name} ({v})")
        bars.append((name, v, colour))
        left += v
    ax.set_yticks([])
    ax.set_xlim(0, total)
    ax.set_xlabel("BGC count")
    ax.set_title(f"Assembly-locator composition (n={total})",
                 loc="left", fontsize=11)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.6),
              ncol=len(bars), fontsize=8, frameon=False)

    png_path = out_dir / "fig_assembly_tier.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=_safe_dpi(fig, 150))
    plt.close(fig)

    _write_sidecar(out_dir / "fig_assembly_tier_data.csv",
                   ["boundary", "count"],
                   [[name, counts[name]]
                    for name in ("Interior", "Edge", "Full-contig", "Other")
                    if counts[name] > 0])
    return png_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_matplotlib():
    """Return the pyplot module or None. Forces the Agg backend."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _find_one(pkg: pathlib.Path, pattern: str) -> Optional[pathlib.Path]:
    matches = sorted(pkg.glob(pattern))
    return matches[0] if matches else None


def _read_csv_safe(path: Optional[pathlib.Path]) -> list[dict]:
    if not path or not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _first(row: dict, cols: tuple[str, ...]) -> str:
    for c in cols:
        v = row.get(c)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def _safe_float(v) -> Optional[float]:
    if v in (None, "", "—"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _write_sidecar(path: pathlib.Path, header: list[str],
                   rows: list[list]) -> None:
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = _SafeWriter(f)
            w.writerow(header)
            w.writerows(rows)
    except OSError:
        pass
