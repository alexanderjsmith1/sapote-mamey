"""chatgpt_commands.py — ChatGPT-safe Mamey subcommands (v9.7.80 P1 patch).

Implements:
  - render_figures_command: post-seal figure rendering with figure_manifest.csv + FIGURE_QA.md
  - mode_b_command: first-class Mode B top-lead cards from a sealed package

Both commands operate entirely from sealed package outputs (manifest.json, triage board CSV)
and never re-run antiSMASH or source scans. Safe for short-cap ChatGPT tool sessions.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import io
import json
import os
import sys
from pathlib import Path
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi


def _atomic_write_text(path, text, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated chatgpt-safe-command deliverable on disk (matches mamey/packaging.py's helper)."""
    path = str(path)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# render-figures command
# ---------------------------------------------------------------------------

def render_figures_command(args) -> int:
    """Render figures from a sealed Mamey package (post-seal, ChatGPT-safe).

    Emits:
      - top_antibacterial_leads.png
      - top_antifungal_leads.png
      - figure_manifest.csv
      - FIGURE_QA.md
      - NO_FIGURES_RENDERED.md  (if matplotlib absent or render fails)
    """
    pkg = Path(args.package).resolve()
    if not (pkg / "manifest.json").exists():
        sys.stderr.write(f"ERROR: manifest.json not found in {pkg}\n")
        return 1


    # v9.7.111 proposal: mamey-native workbook figure set — DAPR/RG-GMCI/ecology/completeness
    # figures that avoid raw antiSMASH count ranking. Raw BGC count appears only as QC.
    if getattr(args, "figure_set", "standard") in {"mamey-native", "compiled-mamey"}:
        from .mamey_native_figures import render_mamey_native_figure_set
        wb_path = getattr(args, "workbook", None)
        if not wb_path:
            sys.stderr.write("ERROR: --figure-set mamey-native requires --workbook <Mamey_Master.xlsx>\n")
            return 1
        out = Path(args.outdir) if getattr(args, "outdir", None) else pkg / "mamey_native_figures"
        res = render_mamey_native_figure_set(wb_path, out, max_labels=getattr(args, "top_n", 16))
        emit(f"  mamey-native figures: {res['status']} ({res.get('figure_count', 0)} rendered) -> {out}")
        return 0

    # v9.7.90: cohort-class — strain x biosynthetic-class capacity heatmap from a cohort workbook.
    if getattr(args, "figure_set", "standard") == "cohort-class":
        from .cohort_class_heatmap import render_cohort_class_heatmap
        wb_path = getattr(args, "workbook", None)
        if not wb_path:
            emit("ERROR: --figure-set cohort-class requires --workbook <cohort.xlsx>", file=sys.stderr)
            return 1
        out = Path(args.outdir) if getattr(args, "outdir", None) else pkg / "cohort_figures"
        out.mkdir(parents=True, exist_ok=True)
        res = render_cohort_class_heatmap(
            wb_path, out / "cohort_class_capacity_heatmap.png",
            out / "cohort_class_capacity_heatmap_data.csv", claim_prefix="PRIVATE",
            label_provenance=getattr(args, "label_provenance", "RAW_ANTISMASH"))
        emit(f"  cohort-class heatmap: {res['status']} "
              f"({res.get('n_strains', 0)} strains x {res.get('n_classes', 0)} classes) -> {out}")
        return 0

    # Locus-map v8 (v9.7.405): package-native exact-locus rendering with a deterministic MIBiG
    # comparator, per-gene similarity/coverage, selected-gene and domain/HMM/motif layers.
    # Post-seal and non-blocking, like every other figure set.
    if getattr(args, "figure_set", "standard") == "locus-maps":
        from .locus_map import render_for_compile_report
        requested_out = Path(args.outdir) if getattr(args, "outdir", None) else pkg / "locus_maps"
        try:
            out_subdir = requested_out.relative_to(pkg).as_posix()
        except ValueError:
            sys.stderr.write("ERROR: locus-map v8 --outdir must resolve inside the sealed package\n")
            return 1
        res = render_for_compile_report(pkg, top_n=getattr(args, "top_n", 10),
                                        out_subdir=out_subdir)
        n = len(res.get("rendered", []))
        sys.stdout.write(f"  locus-maps v8 (post-seal): {n} maps -> {requested_out}\n")
        if res.get("skipped_reason"):
            sys.stdout.write(f"  skipped: {res['skipped_reason']}\n")
        if res.get("skipped"):
            sys.stdout.write(f"  per-BGC holds: {res['skipped']}\n")
        return 0

    # v9.7.89: domain-level figure set — render from the domain_level/ output (run it if absent),
    # then return. Post-seal and non-blocking, like the standard set.
    if getattr(args, "figure_set", "standard") == "domain-level":
        from .domain_figures import render_domain_figures
        from .domain_level import run_domain_level
        dl_dir = pkg / "domain_level"
        if not (dl_dir / "domain_complexity_metrics_by_bgc.csv").exists():
            run_domain_level(pkg, source_antismash=getattr(args, "source_antismash", None),
                             top_n=getattr(args, "top_n", 10))
        fig_out = Path(args.outdir) if getattr(args, "outdir", None) else dl_dir / "figures"
        res = render_domain_figures(dl_dir, outdir=fig_out)
        emit(f"  domain-level figures: {res['status']} ({len(res['figures'])} rendered) -> {fig_out}")
        if res["warnings"]:
            emit(f"  warnings: {res['warnings']}")
        return 0

    outdir = Path(args.outdir) if getattr(args, "outdir", None) else pkg / "figures_rendered"
    outdir.mkdir(parents=True, exist_ok=True)
    top_n = getattr(args, "top_n", 10)
    style = getattr(args, "style", "chatgpt-node-first")
    node_first = (style == "chatgpt-node-first")

    manifest_rows: list[dict] = []
    qa_lines: list[str] = [
        "# Lead figure QA",
        f"style: {style}",
        "",
    ]

    emit(f"render-figures: package={pkg}", f"  outdir={outdir}  top_n={top_n}  style={style}", sep="\n")

    # Load triage board
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    if not candidates:
        msg = "triage board not found -- cannot render lead figures"
        qa_lines.append(f"[FAIL] {msg}")
        _atomic_write_text(outdir / "FIGURE_QA.md", "\n".join(qa_lines))
        _atomic_write_text(
            outdir / "NO_FIGURES_RENDERED.md",
            "# No figures rendered\n\nTriage board missing from package.\n",
        )
        emit(f"  [FAIL] {msg}")
        return 1

    triage_csv = candidates[0]
    with open(triage_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    def _label(row: dict) -> str:
        from .exact_identity import exact_locus_from_mapping, exact_locus_from_native_inventory_row
        if "Contig" in row and "Node_ID" in row:
            return exact_locus_from_native_inventory_row(strain_name, row).exact_locus
        return exact_locus_from_mapping(strain_name, row)

    def _score(row: dict, col: str) -> float:
        import math
        value = row.get(col)
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"LEAD_FIGURE_SCORE_INVALID: {col} requires a finite numeric value") from exc
        if not math.isfinite(number):
            raise ValueError(f"LEAD_FIGURE_SCORE_INVALID: {col} requires a finite numeric value")
        return number

    active = [r for r in rows
              if not r.get("Standing_rule")
              and r.get("Primary_metab_flag") != "YES"]

    rendered_ok = 0
    errors: list[str] = []

    try:
        import json
        manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
        legacy_strain = manifest.get("strain")
        strain_name = manifest.get("strain_id") or manifest.get("display_name") or (
            legacy_strain.get("strain_id") if isinstance(legacy_strain, dict) else None
        )
        # Validate all identities before emitting either chart.
        for row in rows:
            _label(row)
        qa_lines[0] = f"# Lead figure QA -- {strain_name}"
        ab_ranked = sorted(active, key=lambda r: _score(r, "AB_auto"), reverse=True)[:top_n]
        af_ranked = sorted(active, key=lambda r: _score(r, "AF_auto"), reverse=True)[:top_n]

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        def _bar_figure(ranked: list, score_col: str, title: str, fname: str, color: str) -> bool:
            labels = [_label(r) for r in ranked]
            scores = [_score(r, score_col) for r in ranked]
            if not scores:
                return False
            h = max(4.0, len(labels) * 0.45)
            width = max(10.0, 7.0 + max(map(len, labels), default=0) * 0.065)
            fig, ax = plt.subplots(figsize=(width, h))
            y = list(range(len(labels)))
            ax.barh(y, scores, color=color, edgecolor="#333", linewidth=0.6)
            ax.set_yticks(y)
            ax.set_yticklabels(labels, fontsize=8)
            ax.invert_yaxis()
            ax.set_xlabel(f"{title} score (DAPR auto)", fontsize=9)
            ax.set_title(title, fontsize=11, fontweight="bold")
            ax.grid(axis="x", linestyle="--", alpha=0.4)
            plt.tight_layout()
            out_png = outdir / fname
            fig.savefig(str(out_png), dpi=_safe_dpi(fig, 120), bbox_inches="tight")
            w_px = int(fig.get_size_inches()[0] * 120)
            h_px = int(fig.get_size_inches()[1] * 120)
            plt.close(fig)
            size = out_png.stat().st_size
            manifest_rows.append({
                "filename": fname,
                "source_table": triage_csv.name,
                "row_count": len(ranked),
                "dimensions": f"{w_px}x{h_px}",
                "render_status": "OK",
                "file_bytes": size,
            })
            qa_lines.append(f"[PASS] {fname}  size={size} bytes  rows={len(ranked)}")
            return True

        ok = _bar_figure(
            ab_ranked, "AB_auto",
            f"Top {top_n} Antibacterial Leads -- {strain_name}",
            "top_antibacterial_leads.png", "#2c6fad",
        )
        if ok:
            rendered_ok += 1
        ok = _bar_figure(
            af_ranked, "AF_auto",
            f"Top {top_n} Antifungal Leads -- {strain_name}",
            "top_antifungal_leads.png", "#2a9d5c",
        )
        if ok:
            rendered_ok += 1

    except ImportError as exc:
        msg = f"matplotlib not available: {exc} -- no PNG figures rendered"
        errors.append(msg)
        qa_lines.append(f"[SKIP] {msg}")
    except Exception as exc:  # noqa: BLE001
        msg = f"figure render error: {exc}"
        errors.append(msg)
        qa_lines.append(f"[FAIL] {msg}")

    # Always emit figure_manifest.csv
    manifest_csv = outdir / "figure_manifest.csv"
    _mf_buf = io.StringIO()
    writer = _SafeDictWriter(
        _mf_buf,
        fieldnames=["filename", "source_table", "row_count", "dimensions",
                    "render_status", "file_bytes"],
    )
    writer.writeheader()
    writer.writerows(manifest_rows)
    _atomic_write_text(manifest_csv, _mf_buf.getvalue())

    if not manifest_rows:
        qa_lines.append("[SKIP] NO_FIGURES_RENDERED -- see errors above")
        _atomic_write_text(
            outdir / "NO_FIGURES_RENDERED.md",
            "# No figures rendered\n\nSee FIGURE_QA.md for reason.\n",
        )

    qa_lines += ["", f"Total PNG rendered: {rendered_ok}", f"Errors: {len(errors)}", "",
                 # v9.7.88 9.7.88-D: state explicitly that this is the lead subset, not the full
                 # in-run suite — so a 2-of-15 result is documented, not a silent gap. The full
                 # figure suite (composition, length histogram, DAPR scatter, funnel, genome atlas,
                 # KCB anchors, novelty, edge-composition, CCTT map, class distribution) is produced
                 # in-run by `--brief standard`; post-seal render-figures is the lightweight lead view.
                 "## Coverage",
                 f"This is the post-seal **lead subset** ({rendered_ok} of the full in-run figure "
                 "suite): the antibacterial/antifungal top-lead bar charts. The remaining in-run "
                 "figures (composition, length histogram, DAPR scatter, funnel, genome atlas, KCB "
                 "anchors, novelty, edge composition, CCTT map, class distribution) require a full "
                 "`--brief standard` run; they are not regenerated post-seal because their render "
                 "inputs are not all retained in the sealed package. This is intended, not a failure.",
                 ""]
    _atomic_write_text(outdir / "FIGURE_QA.md", "\n".join(qa_lines))

    emit(f"  Figures rendered: {rendered_ok}  |  errors: {len(errors)}", f"  figure_manifest.csv: {manifest_csv}", f"  FIGURE_QA.md: {outdir / 'FIGURE_QA.md'}", sep="\n")
    return 0 if rendered_ok > 0 else (1 if errors else 0)


# ---------------------------------------------------------------------------
# mode-b command
# ---------------------------------------------------------------------------

_CLAIM_CEILINGS = {
    "inventory only": "Weak class signal or architecture E with no KCB",
    "source-derived similarity": "KCB anchor is a source-genome cluster, not a validated compound",
    "candidate family similarity": "KCB/domain evidence supports a compound family; no chemistry confirmed",
    "candidate product-level similarity": "Validated/strong family anchor; isolation + HRMS needed for confirmation",
    "confirmed product": "Chemistry/literature/manual validation supports compound identity",
}


def _claim_ceiling(row: dict, bgc: dict, n_genes: int = 0) -> str:
    kcb = 0.0
    try:
        kcb = float(bgc.get("kcb_cumulative") or row.get("KCB_score") or 0)
    except (TypeError, ValueError):
        pass
    arch = row.get("Arch") or bgc.get("architecture_confidence", "")
    kp = 0
    try:
        kp = int(bgc.get("kcb_protein_hits") or 0)
    except (TypeError, ValueError):
        pass
    sr = row.get("Standing_rule", "")
    # CUT A (v9.7.223): reconcile with the ONE coverage rule (antismash_evidence.kcb_*). A product-
    # level ceiling needs a substantial protein-hit count (>=5, and >=~30% of the cluster when the
    # gene count is known) AND no hard KCB-comparator-vs-antiSMASH-class disagreement.
    from mamey.antismash_evidence import kcb_class_mismatch
    substantial = kp >= 5 and (n_genes <= 0 or kp >= max(2, int(0.3 * n_genes)))
    comparator = str(bgc.get("clusterblast_top") or row.get("KCB_clusterblast") or bgc.get("kcb_top") or "")
    prods = str(row.get("Products") or bgc.get("products") or "")
    class_mismatch = kcb_class_mismatch(comparator, prods)
    if sr or arch in ("E",):
        return "inventory only"
    if kcb > 50000 and kp >= 5 and substantial and not class_mismatch and arch not in ("D", "E"):
        return "candidate product-level similarity"
    if kcb > 5000 and kp >= 4 and not class_mismatch:
        return "candidate family similarity"
    if kcb > 0:
        return "source-derived similarity"
    return "inventory only"


def mode_b_command(args) -> int:
    """Emit Mode B top-lead cards from a sealed Mamey package (first-class output, ChatGPT-safe).

    Emits:
      - <strain>_Mode_B_Top_Leads.md   -- markdown cards, one per top lead
      - <strain>_Mode_B_Top_Leads.csv  -- structured table, one row per top lead
    """
    from . import __version__

    pkg = Path(args.package).resolve()
    if not (pkg / "manifest.json").exists():
        sys.stderr.write(f"ERROR: manifest.json not found in {pkg}\n")
        return 1

    top_n = getattr(args, "top_n", 10)
    node_first = getattr(args, "node_first", True)

    # Load manifest
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        sys.stderr.write(
            "ERROR: manifest.json root must be an object; "
            "refusing Mode B source selection\n"
        )
        return 1

    strain_record = manifest.get("strain")
    if strain_record is not None and not isinstance(strain_record, dict):
        sys.stderr.write(
            "ERROR: manifest strain field must be an object; "
            "refusing Mode B source selection\n"
        )
        return 1

    nested_strain_id = strain_record.get("strain_id") if strain_record else None
    flat_strain_id = manifest.get("strain_id")
    for locator, value in (
        ("strain.strain_id", nested_strain_id),
        ("strain_id", flat_strain_id),
    ):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            sys.stderr.write(
                f"ERROR: manifest {locator} must be a non-empty string; "
                "refusing Mode B source selection\n"
            )
            return 1
    if nested_strain_id and flat_strain_id and nested_strain_id != flat_strain_id:
        sys.stderr.write(
            "ERROR: conflicting manifest strain identifiers "
            f"{nested_strain_id!r} and {flat_strain_id!r}; "
            "refusing Mode B source selection\n"
        )
        return 1
    strain_id = nested_strain_id or flat_strain_id
    if not strain_id:
        sys.stderr.write(
            "ERROR: manifest strain identifier is missing; "
            "refusing Mode B source selection\n"
        )
        return 1
    bgcs_by_id = {b["bgc_id"]: b for b in manifest.get("bgcs", [])}
    tta_per_bgc = (manifest.get("source_scans", {})
                           .get("blda_tta", {})
                           .get("per_bgc", {}))
    res_per_bgc = (manifest.get("source_scans", {})
                            .get("resistance_tiers", {})
                            .get("per_bgc", {}))

    # Load RGGMCI pairs
    rggmci_pairs: list[dict] = []
    rggmci_csv = pkg / f"{strain_id}_4A_RGGMCI_ranked_pairs.csv"
    if rggmci_csv.exists():
        with open(rggmci_csv, newline="", encoding="utf-8") as fh:
            rggmci_pairs = list(csv.DictReader(fh))

    def _rggmci_context(bgc_id: str) -> str:
        pairs = [r for r in rggmci_pairs
                 if bgc_id in (r.get("bgc_a", ""), r.get("bgc_b", ""))]
        high = [r for r in pairs if "HIGH" in r.get("rggmci_confidence", "")]
        mod = [r for r in pairs if "MODERATE" in r.get("rggmci_confidence", "")]
        parts = []
        if high:
            parts.append(f"HIGH x{len(high)}")
        if mod:
            parts.append(f"MODERATE x{len(mod)}")
        # P-TT v9.7.100: surface terminus-truncation splits — the strongest, physically-grounded rescue.
        # Only non-LOW partners (a small contig pairs with many Edge fragments; confidence picks the real arm).
        tt = [r for r in pairs
              if (str(r.get("terminus_truncation_rescue", "")).lower() == "true"
                  or r.get("subject_tiling_verdict") == "TERMINUS_TRUNCATION_SPLIT")
              and "LOW" not in r.get("rggmci_confidence", "")]
        if tt:
            tt_sorted = sorted(tt, key=lambda r: -float(r.get("rggmci_score") or 0))
            partners = "; ".join((r["bgc_b"] if r["bgc_a"] == bgc_id else r["bgc_a"]) for r in tt_sorted[:4])
            parts.append(f"TERMINUS-TRUNCATION SPLIT with {partners}")
        return "; ".join(parts) or "none"

    # Load triage board
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    expected_triage = pkg / f"{strain_id}_4_triage_board.csv"
    if not expected_triage.is_file():
        sys.stderr.write(
            f"ERROR: expected triage board {expected_triage.name!r} not found in {pkg}; "
            "refusing ambiguous Mode B source selection\n"
        )
        return 1
    if candidates != [expected_triage]:
        names = ", ".join(path.name for path in candidates) or "(none)"
        sys.stderr.write(
            f"ERROR: expected exactly one triage board {expected_triage.name!r}; "
            f"found {names}; refusing ambiguous Mode B source selection\n"
        )
        return 1
    triage_csv = expected_triage

    outdir = Path(args.outdir) if getattr(args, "outdir", None) else pkg / "mode_b"
    outdir.mkdir(parents=True, exist_ok=True)
    with open(triage_csv, newline="", encoding="utf-8") as fh:
        triage_rows = list(csv.DictReader(fh))

    def _score(row: dict, col: str) -> float:
        try:
            return float(row.get(col) or 0)
        except (TypeError, ValueError):
            return 0.0

    active = [r for r in triage_rows
              if not r.get("Standing_rule")
              and r.get("Primary_metab_flag") != "YES"]
    ranked_all = sorted(
        active,
        key=lambda r: _score(r, "AB_auto") + _score(r, "AF_auto"),
        reverse=True,
    )
    ranked = ranked_all[:top_n]

    inventory_bgc_ids = sorted(str(b.get("bgc_id", "")) for b in manifest.get("bgcs", []) if b.get("bgc_id"))
    emitted_candidate_ids = [str(r.get("BGC_ID", "")) for r in ranked if r.get("BGC_ID")]
    emitted_set = set(emitted_candidate_ids)
    requested_full_inventory = bool(inventory_bgc_ids) and int(top_n or 0) >= len(inventory_bgc_ids)
    missing_bgc_ids = [bgc_id for bgc_id in inventory_bgc_ids if bgc_id not in emitted_set] if requested_full_inventory else []
    if not inventory_bgc_ids:
        coverage_status = "INVENTORY_UNKNOWN_MODEB_COVERAGE"
    elif requested_full_inventory and missing_bgc_ids:
        coverage_status = "PARTIAL_NATIVE_MODEB_COVERAGE"
    elif requested_full_inventory:
        coverage_status = "FULL_NATIVE_MODEB_COVERAGE"
    elif len(ranked) < min(int(top_n or 0), len(ranked_all)):
        coverage_status = "PARTIAL_TOPN_MODEB_COVERAGE"
    else:
        coverage_status = "TOPN_NATIVE_MODEB_COVERAGE"

    md_lines = [
        f"# Mode B Top-{top_n} Lead Cards -- {strain_id}",
        f"Generated by Mamey v{__version__} mode-b subcommand.",
        f"Source package: {pkg}",
        "",
        "> Claim-safety: All class assignments are bioinformatic predictions.",
        "> KCB comparisons are similarity signals, not identity.",
        "> Bioactivity links are mechanistic hypotheses requiring experimental validation.",
        "",
    ]
    # v9.7.88 roadmap #1: load the sealed normalized gene context so each Mode B card can carry a
    # true per-CDS gene table (the gene-by-gene walkthrough) instead of only BGC-level summary.
    try:
        from .gene_context import load_gene_context as _load_gc
        _gene_ctx = _load_gc(pkg, strain_id)
    except Exception:
        _gene_ctx = {}

    # P-CBG (v9.7.100): load the ClusterBlast per-gene correspondence so each card can show, per CDS, which
    # reference cluster gene it hits and at what identity/coverage — the locus characterised against its
    # reference. This is the evidence repeatedly reconstructed by hand for the indolocarbazole core.
    _cbg_best: dict[str, list[dict]] = {}
    try:
        _cbg_path = pkg / f"{strain_id}_4A2_ClusterBlast_gene_map.json"
        if _cbg_path.exists():
            _cbg_best = (json.loads(_cbg_path.read_text(encoding="utf-8")) or {}).get("per_gene_best_hit", {}) or {}
    except Exception:
        _cbg_best = {}

    def _clusterblast_block_md(bgc_id: str, max_rows: int = 40) -> list[str]:
        hits = _cbg_best.get(bgc_id, [])
        if not hits:
            return []
        out = ["", f"**ClusterBlast per-gene correspondence ({len(hits)} CDS with reference hits):**",
               "> %identity = similarity to a reference protein, not product identity.", "",
               "| Query CDS | → Reference gene | %id | %cov | BLAST score | Reference |",
               "|-----------|------------------|-----|------|-------------|-----------|"]
        for h in hits[:max_rows]:
            cov = h.get("pct_coverage")
            cov_s = f"{cov:.0f}" if isinstance(cov, (int, float)) else "--"
            ref = h.get("reference", "")
            src = (h.get("reference_source") or "")[:28]
            out.append(f"| {h.get('query_gene','?')} | {h.get('subject_gene','?')} | "
                       f"{h.get('pct_identity','--')} | {cov_s} | {h.get('blast_score','--')} | "
                       f"{ref} ({src}) |")
        out.append("")
        return out

    def _gene_table_md(bgc_id: str, max_rows: int = 40) -> list[str]:
        rows = _gene_ctx.get(bgc_id, [])
        if not rows:
            return ["", "*Gene-level table unavailable (package predates v9.7.88 gene context, "
                    "or no CDS mapped to this BGC).*", ""]
        out = ["", f"**Gene-by-gene ({len(rows)} CDS"
               + (f", first {max_rows} shown" if len(rows) > max_rows else "") + "):**", "",
               "| Locus | Coords | Str | aa | sec_met domains | TTA |",
               "|-------|--------|-----|----|-----------------|-----|"]
        for r in rows[:max_rows]:
            doms = ", ".join(r.get("sec_met_domains", [])[:4]) or "--"
            strand = "+" if r.get("strand") in (1, "+", None) else "-"
            out.append(f"| {r.get('locus_tag') or '?'} | "
                       f"{r.get('start')}-{r.get('end')} | {strand} | "
                       f"{r.get('aa_length') if r.get('aa_length') is not None else '--'} | "
                       f"{doms} | {r.get('tta_codons', 0)} |")
        out.append("")
        return out

    # v9.7.89 (request §9): if --with-domain-level, run/load the domain-level enrichment so each
    # card can carry domain burden + claim ceilings — turning Mode B from ranked-lead explanation
    # into real biosynthetic evidence review. Post-seal and non-blocking: a failure just omits the
    # block (the card still renders). Loads existing domain_level/ output if present, else runs it.
    _dom_complexity: dict[str, dict] = {}
    _dom_claims: dict[str, dict] = {}
    _dom_mode = None
    if getattr(args, "with_domain_level", False):
        try:
            import csv as _csv_dl
            from .domain_level import run_domain_level as _run_dl
            _dl_dir = pkg / "domain_level"
            _need_run = not (_dl_dir / "domain_complexity_metrics_by_bgc.csv").exists()
            if _need_run:
                _rec = _run_dl(pkg, source_antismash=getattr(args, "source_antismash", None),
                               top_n=getattr(args, "top_n", 10))
                _dom_mode = _rec.get("mode")
            else:
                try:
                    _rcj = json.loads((_dl_dir / "domain_level_receipt.json").read_text(encoding="utf-8"))
                    _dom_mode = _rcj.get("mode")
                except Exception:
                    _dom_mode = "preexisting"
            _cx_path = _dl_dir / "domain_complexity_metrics_by_bgc.csv"
            if _cx_path.exists():
                with open(_cx_path, newline="", encoding="utf-8") as _f:
                    for _r in _csv_dl.DictReader(_f):
                        _dom_complexity[_r["BGC_ID"]] = _r
            _cl_path = _dl_dir / "domain_safe_unsafe_claims.csv"
            if _cl_path.exists():
                with open(_cl_path, newline="", encoding="utf-8") as _f:
                    for _r in _csv_dl.DictReader(_f):
                        _dom_claims[_r["BGC_ID"]] = _r
        except Exception as _dl_err:
            emit(f"  [WARN] domain-level enrichment unavailable: {_dl_err}")

    def _domain_block_md(bgc_id: str) -> list[str]:
        cx = _dom_complexity.get(bgc_id)
        cl = _dom_claims.get(bgc_id)
        if not cx and not cl:
            return []
        out = ["", "**Domain-level evidence"
               + (f" ({_dom_mode})" if _dom_mode else "") + ":**", ""]
        if cx:
            out += [
                "| Domain burden | Count |",
                "|---------------|-------|",
                f"| Total domains | {cx.get('Domain_total','--')} |",
                f"| Unique domains | {cx.get('Unique_domain_names','--')} |",
                f"| Biosynthetic core | {cx.get('Biosynthetic_core_domain_count','--')} |",
                f"| Tailoring | {cx.get('Tailoring_domain_count','--')} |",
                f"| Transport | {cx.get('Transport_domain_count','--')} |",
                f"| Regulatory | {cx.get('Regulatory_domain_count','--')} |",
                "",
            ]
            if cx.get("Architecture_archetype"):
                out += [f"**Architecture archetype:** {cx.get('Architecture_archetype')}", ""]
        if cl:
            out += [
                f"**Domain safe claim:** {cl.get('Safe_domain_claims','')}",
                "",
                f"**Domain unsafe claim:** {cl.get('Unsafe_domain_claims','')}",
                "",
                f"**Domain claim ceiling:** {cl.get('Domain_claim_ceiling','')}",
                "",
            ]
        return out

    csv_rows: list[dict] = []
    receipt_cards: list[dict] = []

    for rank, row in enumerate(ranked, 1):
        bgc_id = row.get("BGC_ID", "?")
        bgc = bgcs_by_id.get(bgc_id, {})
        contig = row.get("Contig", "").split(".")[0]
        region = bgc.get("antismash_region", "")
        prods = bgc.get("products", row.get("Products", ""))
        prods_str = "; ".join(prods) if isinstance(prods, list) else str(prods)
        arch = row.get("Arch") or bgc.get("architecture_confidence", "?")
        cls_conf = row.get("Class_Conf") or bgc.get("architecture_class_confidence", "?")
        kcb_top = row.get("KCB_top") or bgc.get("kcb_top", "")
        kcb_score = bgc.get("kcb_cumulative", "") or row.get("KCB_score", "")
        kcb_prots = bgc.get("kcb_protein_hits", "")
        length_kb = bgc.get("length_kb", "")
        boundary = row.get("Boundary") or bgc.get("edge_status", "?")
        ab = _score(row, "AB_auto")
        af = _score(row, "AF_auto")
        nov = _score(row, "Novelty_auto")
        cctt = row.get("CCTT_triggers", "")
        tta = tta_per_bgc.get(bgc_id, {})
        tta_tier = tta.get("bldA_tier", "?")
        tta_n = tta.get("tta_codons", "?")
        res_tier = res_per_bgc.get(bgc_id, {}).get("tier", "?")
        rggmci_ctx = _rggmci_context(bgc_id)
        ceiling = _claim_ceiling(row, bgc, n_genes=len(_gene_ctx.get(bgc_id, [])))
        umed_gap = row.get("UMED_gap", "")

        label = f"{contig} ({bgc_id})" if node_first else bgc_id
        has_kcb = bool(str(kcb_top).strip())
        kcb_top_str = (str(kcb_top)[:100] + ("…" if len(str(kcb_top)) > 100 else "")) if has_kcb else "No KCB"
        if has_kcb:
            kcb_sentence = f"KCB similarity: {kcb_top_str} (score {kcb_score}, {kcb_prots} proteins)."
        else:
            kcb_sentence = "No KCB anchor was detected for this BGC."

        safe_claim = (
            f"BGC {bgc_id} ({contig}) encodes biosynthetic capacity consistent with "
            f"a {prods_str[:80]} pathway; {ceiling}. "
            f"{kcb_sentence} "
            f"Product identity requires isolation and chemical characterisation."
        )

        _card_start = len(md_lines)
        md_lines += [
            "---",
            f"## Rank {rank}: {label} -- {prods_str[:80]}",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| BGC_ID | {bgc_id} |",
            f"| Assembly Locator | {contig} {region} |",
            f"| Boundary | {boundary} |",
            f"| Products | {prods_str} |",
            f"| Architecture | {arch} (class confidence: {cls_conf}) |",
            f"| Length | {length_kb} kb |",
            f"| KCB anchor | {kcb_top_str} |",
            f"| KCB score / proteins | {kcb_score} / {kcb_prots} |",
            f"| Antibacterial score | {ab} |",
            f"| Antifungal score | {af} |",
            f"| Novelty | {nov} |",
            f"| CCTT triggers | {cctt or '--'} |",
            f"| bldA tier / TTA codons | {tta_tier} / {tta_n} |",
            f"| Resistance tier | {res_tier} |",
            f"| UMED gap | {umed_gap or '--'} |",
            f"| RG-GMCI context | {rggmci_ctx} |",
            f"| Safe-claim ceiling | **{ceiling}** |",
            "",
            f"**Safe claim:** {safe_claim}",
            "",
        ]
        # v9.7.88: true gene-by-gene walkthrough from the sealed gene context
        md_lines += _gene_table_md(bgc_id)
        # P-CBG v9.7.100: ClusterBlast per-gene reference correspondence
        md_lines += _clusterblast_block_md(bgc_id)
        # v9.7.89: domain-level evidence block (request §9) when --with-domain-level
        md_lines += _domain_block_md(bgc_id)
        # Native Mode B receipts must be ingest-compatible: persist the exact markdown
        # slice for this card so `mamey ingest-receipts --receipt Mode_B_Coverage_Receipt.json`
        # can record generated cards instead of rejecting the coverage receipt as schema-only.
        receipt_cards.append({
            "bgc_id": bgc_id,
            "mode_b_md": "\n".join(md_lines[_card_start:]).strip() + "\n",
            "source": "mamey mode-b native card",
            "rank": rank,
        })
        # record the gene count on the structured row so the CSV reflects coverage
        _n_genes = len(_gene_ctx.get(bgc_id, []))
        _cx = _dom_complexity.get(bgc_id, {})
        _cl = _dom_claims.get(bgc_id, {})
        csv_rows.append({
            "Rank": rank,
            "BGC_ID": bgc_id,
            "Assembly_Locator": f"{contig} {region}",
            "Boundary": boundary,
            "Products": prods_str,
            "Architecture": arch,
            "Class_Conf": cls_conf,
            "Length_kb": length_kb,
            "KCB_top": kcb_top_str,
            "KCB_score": kcb_score,
            "KCB_proteins": kcb_prots,
            "AB_score": ab,
            "AF_score": af,
            "Novelty": nov,
            "CCTT_triggers": cctt,
            "bldA_tier": tta_tier,
            "TTA_codons": tta_n,
            "Resistance_tier": res_tier,
            "UMED_gap": umed_gap,
            "RGGMCI_context": rggmci_ctx,
            "Safe_claim_ceiling": ceiling,
            "n_genes": _n_genes,
            "Domain_total": _cx.get("Domain_total", ""),
            "Core_domain_burden": _cx.get("Biosynthetic_core_domain_count", ""),
            "Tailoring_domain_burden": _cx.get("Tailoring_domain_count", ""),
            "Domain_claim_ceiling": _cl.get("Domain_claim_ceiling", ""),
        })

    md_path = outdir / f"{strain_id}_Mode_B_Top_Leads.md"
    _atomic_write_text(md_path, "\n".join(md_lines))

    csv_path = outdir / f"{strain_id}_Mode_B_Top_Leads.csv"
    if csv_rows:
        _lb_buf = io.StringIO()
        writer = _SafeDictWriter(_lb_buf, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
        _atomic_write_text(csv_path, _lb_buf.getvalue())

    coverage_receipt = {
        "schema_version": "mode_b_coverage_receipt_v2",
        "receipt_kind": "native_mode_b_coverage_and_cards",
        "strain_id": strain_id,
        "session_id": f"mamey_mode_b_{strain_id}",
        "requested_top_n": int(top_n or 0),
        "inventory_bgc_count": len(inventory_bgc_ids),
        "emitted_card_count": len(csv_rows),
        "coverage_status": coverage_status,
        "missing_bgc_ids": missing_bgc_ids,
        "emitted_bgc_ids": [r.get("BGC_ID", "") for r in csv_rows],
        "strict_all": bool(getattr(args, "strict_all", False)),
        # Ingest-compatible Sapote receipt payload. This closes the v9.7.141 receipt mismatch:
        # native mode-b output can now be consumed by `mamey ingest-receipts` directly.
        "cards": receipt_cards,
    }
    coverage_path = outdir / "Mode_B_Coverage_Receipt.json"
    _atomic_write_text(coverage_path, json.dumps(coverage_receipt, indent=2))

    emit(f"  Mode B top-{top_n} cards: {md_path}", f"  Mode B CSV: {csv_path}", f"  Mode B coverage receipt: {coverage_path}", f"  Leads covered: {len(csv_rows)}", sep="\n")
    if coverage_status == "PARTIAL_NATIVE_MODEB_COVERAGE":
        emit(
            f"  WARNING: Mode B emitted {len(csv_rows)} cards but inventory contains "
            f"{len(inventory_bgc_ids)} BGCs; missing {len(missing_bgc_ids)} BGC IDs. "
            "See Mode_B_Coverage_Receipt.json."
        )
        if getattr(args, "strict_all", False):
            return 2
    return 0
