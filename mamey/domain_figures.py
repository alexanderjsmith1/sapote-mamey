"""domain_figures.py — native domain-level figures (v9.7.89).

Three figure types from the domain-level tables (request §8):
  A. domain_role_burden_heatmap   — top BGCs x role categories, cell = domain count
  B. core_biosynthetic_domain_burden — core vs accessory domain burden per BGC
  C. <Strain>_<BGC>_domain_strip  — node-first ordered domain arrows for one BGC

Post-seal, non-blocking: a render failure writes a skip card and leaves prior outputs intact.
Each PNG ships a companion `<name>_data.csv` (data-only-PNG standard) and a figure_manifest.csv row.
Style settings live in mamey/data/domain_level/domain_figure_specs.v1.json, not in code.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from .figure_save import save_figure

_DATA = Path(__file__).parent / "data" / "domain_level"


def _load_specs() -> dict:
    return json.loads((_DATA / "domain_figure_specs.v1.json").read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _node_label(assembly_locator: str, bgc_id: str) -> str:
    # node/contig-first label per the BGC-anchoring rule.
    # Include the antiSMASH region when the locator carries one, so two BGCs on the
    # SAME contig (e.g. NODE_6 region002=BGC041 vs region003=BGC042) get distinct,
    # non-ambiguous titles instead of a bare "NODE_6 (...)" that reads as one locus
    # (audit Worst #8: node-scoped labels mislead when a contig carries >=2 BGCs).
    loc = assembly_locator or ""
    node = loc.split("_length")[0].split(" ")[0] or loc
    region = ""
    for tok in loc.replace(".", " ").split():
        if tok.lower().startswith("region"):
            region = tok
            break
    return f"{node} {region} ({bgc_id})".replace("  ", " ") if region else f"{node} ({bgc_id})"


def _manifest_row(fname: str, source: str, rows: int, dims: str, status: str) -> dict:
    return {"filename": fname, "source_table": source, "row_count": rows,
            "dimensions": dims, "status": status}


def _save_pair(fig, png: Path, *, source: str, rows: int) -> None:
    save_figure(
        fig,
        figure_id=png.stem,
        out_stem=png.with_suffix(""),
        renderer="domain_figures",
        package_dir=png.parent,
        provenance=f"source_table={source};row_count={rows}",
    )


def _atomic_csv_write(path: Path, write_fn) -> None:
    """Write a CSV via a same-directory `.tmp` + `os.replace()` so a crash mid-write
    (disk-full, OOM-kill, SIGTERM) never leaves a truncated/corrupt file at `path` -- a bare
    `open(path, "w")` truncates the target the instant it opens, before a single row is
    written, so an interrupted write destroys a perfectly good prior file. Matches the
    established tmp+replace pattern already used for this exact failure mode elsewhere in this
    codebase (bgc_l0_program.py::_write_rows, cross_strain_figures.py::_write_csv,
    figures_extra.py/figures_sapote.py::_write_csv)."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            write_fn(fh)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
    os.replace(tmp, path)


def render_domain_figures(domain_level_dir: str | Path, outdir: str | Path | None = None,
                          per_bgc_strip_top: int = 6) -> dict[str, Any]:
    """Render the domain-level figure set from a domain_level/ output directory. Never raises.
    Returns {"status", "figures": [...], "manifest_rows": [...], "warnings": [...]}."""
    dl = Path(domain_level_dir)
    out = Path(outdir) if outdir else dl / "figures"
    out.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"status": "OK", "figures": [], "manifest_rows": [], "warnings": []}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        (out / "DOMAIN_LEVEL_FIGURES_SKIPPED_NO_TABLE.md").write_text(
            f"# Domain-level figures skipped\n\nmatplotlib unavailable: {e}\n"
            "Core package and domain-level tables remain valid.\n", encoding="utf-8")
        result["status"] = "SKIPPED"
        result["warnings"].append(f"matplotlib unavailable: {e}")
        return result

    # AUDIT_378: this whole preamble used to run unguarded between the two SKIPPED
    # gates above/below -- a missing/malformed domain_figure_specs.v1.json (version-skewed
    # schema, truncated file, etc.) raised straight out of this "Never raises" function (its
    # own docstring's contract), through render-figures callers that trust that contract with
    # no defensive try/except of their own (chatgpt_commands.py::render_figures_command's
    # domain-level branch calls this with zero wrapping, unlike its render_all_figures.py
    # sibling). Wrapped so a bad spec/table degrades to the same graceful SKIPPED card as the
    # other guarded failure modes in this function, instead of crashing the whole CLI command.
    try:
        specs = _load_specs()
        role_counts = _read_csv(dl / "domain_role_counts_by_bgc.csv")
        complexity = _read_csv(dl / "domain_complexity_metrics_by_bgc.csv")
        domain_rows = _read_csv(dl / "domain_rows_long.csv")
    except Exception as e:
        (out / "DOMAIN_LEVEL_FIGURES_SKIPPED_NO_TABLE.md").write_text(
            f"# Domain-level figures skipped\n\nspec/table load failed: {e}\n"
            "Core package and domain-level tables remain valid.\n", encoding="utf-8")
        result["status"] = "SKIPPED"
        result["warnings"].append(f"spec/table load failed: {e}")
        return result

    if not role_counts and not complexity:
        (out / "DOMAIN_LEVEL_FIGURES_SKIPPED_NO_TABLE.md").write_text(
            "# Domain-level figures skipped\n\nNo domain-level tables found. "
            "Run `mamey domain-level --package <pkg>` first.\n", encoding="utf-8")
        result["status"] = "SKIPPED"
        result["warnings"].append("no domain-level tables present")
        return result

    # ---- Figure A: role-burden heatmap (BGC x role) ----
    try:
        _render_heatmap(role_counts, out, specs, plt, result)
    except Exception as e:
        result["warnings"].append(f"heatmap failed: {e}")

    # ---- Figure B: core biosynthetic vs accessory burden ----
    try:
        _render_core_burden(complexity, out, specs, plt, result)
    except Exception as e:
        result["warnings"].append(f"core-burden failed: {e}")

    # ---- Figure C: per-BGC domain strips (top N) ----
    try:
        _render_domain_strips(domain_rows, complexity, out, specs, plt, result, per_bgc_strip_top)
    except Exception as e:
        result["warnings"].append(f"domain strips failed: {e}")

    # write/extend a figure manifest
    if result["manifest_rows"]:
        man = out / "figure_manifest.csv"

        def _write_manifest(fh):
            w = _SafeDictWriter(fh, fieldnames=["filename", "source_table", "row_count",
                                               "dimensions", "status"])
            w.writeheader()
            for r in result["manifest_rows"]:
                w.writerow(r)
        _atomic_csv_write(man, _write_manifest)
    return result


def _render_heatmap(role_counts, out, specs, plt, result):
    if not role_counts:
        return
    # build BGC x role matrix
    bgcs, roles = [], []
    mat: dict[tuple, int] = {}
    for r in role_counts:
        key = _node_label(r.get("Assembly_Locator", ""), r["BGC_ID"])
        role = r["domain_role_category"]
        if key not in bgcs:
            bgcs.append(key)
        if role not in roles:
            roles.append(role)
        mat[(key, role)] = mat.get((key, role), 0) + int(r["count"])
    roles = sorted(roles)
    import numpy as np
    grid = np.array([[mat.get((b, rl), 0) for rl in roles] for b in bgcs], dtype=float)
    fs = specs["figure_a_heatmap"]["min_figsize"]
    fig, ax = plt.subplots(figsize=(max(fs[0], 0.5 * len(roles) + 3),
                                    max(fs[1], 0.4 * len(bgcs) + 2)))
    im = ax.imshow(grid, cmap=specs["figure_a_heatmap"]["cmap"], aspect="auto")
    ax.set_xticks(range(len(roles))); ax.set_xticklabels(roles, rotation=60, ha="right", fontsize=6)
    ax.set_yticks(range(len(bgcs))); ax.set_yticklabels(bgcs, fontsize=6.5)
    ax.set_title(specs["figure_a_heatmap"]["title"], fontsize=9.5)
    if specs["figure_a_heatmap"]["annotate_cells"]:
        for i in range(len(bgcs)):
            for j in range(len(roles)):
                v = int(grid[i, j])
                if v:
                    ax.text(j, i, v, ha="center", va="center", fontsize=5.5,
                            color="black" if grid[i, j] < grid.max() * 0.6 else "white")
    fig.colorbar(im, ax=ax, shrink=0.6, label="domain count")
    png = out / "domain_role_burden_heatmap.png"
    _save_pair(fig, png, source="domain_role_counts_by_bgc.csv", rows=len(role_counts)); plt.close(fig)
    # companion data CSV
    def _write_heatmap_csv(fh):
        w = _SafeWriter(fh); w.writerow(["BGC"] + roles)
        for i, b in enumerate(bgcs):
            w.writerow([b] + [int(grid[i, j]) for j in range(len(roles))])
    _atomic_csv_write(out / "domain_role_burden_heatmap_data.csv", _write_heatmap_csv)
    result["figures"].append(png.name)
    result["manifest_rows"].append(_manifest_row(
        png.name, "domain_role_counts_by_bgc.csv", len(bgcs),
        f"{len(bgcs)}x{len(roles)}", "PASS"))


def _render_core_burden(complexity, out, specs, plt, result):
    if not complexity:
        return
    rows = sorted(complexity, key=lambda r: int(r.get("Biosynthetic_core_domain_count") or 0),
                  reverse=True)
    labels = [_node_label(r.get("Assembly_Locator", ""), r["BGC_ID"]) for r in rows]
    core = [int(r.get("Biosynthetic_core_domain_count") or 0) for r in rows]
    accessory = [int(r.get("Domain_total") or 0) - c for r, c in zip(rows, core)]
    import numpy as np
    y = np.arange(len(rows))
    fs = specs["figure_b_core_burden"]["min_figsize"]
    fig, ax = plt.subplots(figsize=(fs[0], max(fs[1], 0.4 * len(rows) + 1.5)))
    ax.barh(y, core, color=specs["figure_b_core_burden"]["core_color"], label="biosynthetic core")
    ax.barh(y, accessory, left=core, color=specs["figure_b_core_burden"]["accessory_color"],
            label="accessory/other")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=6.5); ax.invert_yaxis()
    ax.set_xlabel("domain count", fontsize=8)
    ax.set_title(specs["figure_b_core_burden"]["title"], fontsize=9.5, pad=16)
    ax.legend(fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2)
    png = out / "core_biosynthetic_domain_burden.png"
    _save_pair(fig, png, source="domain_complexity_metrics_by_bgc.csv", rows=len(complexity)); plt.close(fig)
    def _write_core_burden_csv(fh):
        w = _SafeWriter(fh); w.writerow(["BGC", "core", "accessory", "total"])
        for lab, c, a in zip(labels, core, accessory):
            w.writerow([lab, c, a, c + a])
    _atomic_csv_write(out / "core_biosynthetic_domain_burden_data.csv", _write_core_burden_csv)
    result["figures"].append(png.name)
    result["manifest_rows"].append(_manifest_row(
        png.name, "domain_complexity_metrics_by_bgc.csv", len(rows), f"{len(rows)} bars", "PASS"))


def _render_domain_strips(domain_rows, complexity, out, specs, plt, result, top_n):
    if not domain_rows:
        return
    palette = specs["role_palette"]
    by_bgc: dict[str, list[dict]] = defaultdict(list)
    meta: dict[str, dict] = {}
    for r in domain_rows:
        by_bgc[r["BGC_ID"]].append(r)
        meta[r["BGC_ID"]] = {"Strain": r.get("Strain", ""),
                             "Assembly_Locator": r.get("Assembly_Locator", "")}
    # order BGCs by core burden (from complexity) so strips are produced for the strongest leads
    order = [r["BGC_ID"] for r in sorted(
        complexity, key=lambda r: int(r.get("Biosynthetic_core_domain_count") or 0), reverse=True)]
    order = [b for b in order if b in by_bgc] or list(by_bgc.keys())
    max_doms = specs["global"]["max_strip_domains"]
    for bgc_id in order[:top_n]:
        doms = sorted(by_bgc[bgc_id], key=lambda d: int(d.get("cds_start") or 0))
        collapsed_note = ""
        if len(doms) > max_doms:
            collapsed_note = f" (first {max_doms} of {len(doms)} shown)"
            doms = doms[:max_doms]
        strain = meta[bgc_id]["Strain"]
        fs = specs["figure_c_domain_strip"]["min_figsize"]
        fig, ax = plt.subplots(figsize=(fs[0], fs[1]))
        h = specs["figure_c_domain_strip"]["arrow_height"]
        for i, d in enumerate(doms):
            role = d.get("domain_role_category", "Other accessory/domain")
            color = palette.get(role, "#e0e0e0")
            strand = str(d.get("strand", "1"))
            # arrow direction by strand
            if strand in ("-1", "-"):
                ax.annotate("", xy=(i, 0), xytext=(i + 0.8, 0),
                            arrowprops=dict(arrowstyle="-|>", color=color, lw=6))
            else:
                ax.annotate("", xy=(i + 0.8, 0), xytext=(i, 0),
                            arrowprops=dict(arrowstyle="-|>", color=color, lw=6))
            ax.text(i + 0.4, 0.45, d.get("domain_name", "")[:12], ha="center", va="bottom",
                    fontsize=4.5, rotation=45)
        ax.set_xlim(-0.5, len(doms) + 0.5); ax.set_ylim(-1, 1.5)
        ax.set_yticks([]); ax.set_xticks([])
        title = specs["figure_c_domain_strip"]["title_template"].format(
            strain=strain, bgc=_node_label(meta[bgc_id]["Assembly_Locator"], bgc_id))
        ax.set_title(title + collapsed_note, fontsize=8.5)
        # role legend (categories present in this strip)
        present_roles = sorted({d.get("domain_role_category", "") for d in doms if d.get("domain_role_category")})
        from matplotlib.patches import Patch
        handles = [Patch(facecolor=palette.get(r, "#e0e0e0"), label=r) for r in present_roles]
        ax.legend(handles=handles, fontsize=4.5, loc="upper center",
                  bbox_to_anchor=(0.5, -0.05), ncol=min(4, len(present_roles)), framealpha=0.9)
        # BC2-408: add_claim_safety_footer()'s own docstring requires "a bottom margin of at least
        # 0.13" reserved by the caller -- this figure never reserved any, and its legend sits at
        # axes-fraction y=-0.05 (just below the axes), which on a strip plot whose axes occupy
        # nearly the whole figure lands almost exactly where the mandatory claim-safety text is
        # placed (figure-fraction y=0.052/0.029/0.008). Verified live against a real render
        # (AS-XXX/BGC031): the legend swatches/labels visually overlap and obscure "Similarity is
        # not identity; capacity is not production; missing or unbound evidence is not biological
        # absence." -- the one sentence every figure in this project is required to carry legibly.
        # Reserve the margin explicitly, per the callee's own documented contract.
        fig.subplots_adjust(bottom=0.32)
        safe_strain = strain.replace("-", "").replace(" ", "")
        png = out / f"{safe_strain}_{bgc_id}_domain_strip.png"
        _save_pair(fig, png, source="domain_rows_long.csv", rows=len(doms)); plt.close(fig)
        result["figures"].append(png.name)
        result["manifest_rows"].append(_manifest_row(
            png.name, "domain_rows_long.csv", len(doms),
            f"{len(doms)} domains" + (collapsed_note or ""), "PASS"))
