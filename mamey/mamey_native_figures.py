"""mamey_native_figures.py — workbook-native Mamey figure set.

This module renders cohort/master-workbook figures that emphasize Mamey logic rather
than raw antiSMASH region counts. Raw BGC counts are allowed only in QC/caution
figures because fragmented assemblies can inflate antiSMASH row counts.
"""
from __future__ import annotations
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import warnings as _warnings

import os
from pathlib import Path
from typing import Iterable
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

FIGURE_SET_SPEC = [
    ("ab_af_portfolio", "Mamey lead portfolio: antibacterial vs antifungal", "headline"),
    ("dual_track_leads", "Dual-track lead comparison by strain", "headline"),
    ("top_antibacterial", "Top antibacterial lead strains", "headline"),
    ("top_antifungal", "Top antifungal lead strains", "headline"),
    ("best_score_vs_fragmentation", "Best lead score vs fragmentation burden", "qc_context"),
    ("ecology_readiness", "Ecology readiness ranking", "context"),
    ("lead_vs_ecology", "Lead priority versus ecology readiness", "context"),
    ("rggmci_state_summary", "RG-GMCI state summary", "rescue_logic"),
    ("rggmci_vs_contigs", "RG-GMCI state versus fragmentation burden", "rescue_logic"),
    ("workflow_completion", "Workflow-completion distribution", "operations"),
    ("module_completeness", "Module completeness heatmap for high-priority strains", "operations"),
    ("class_presence", "Class presence/absence matrix for high-priority strains", "profile_not_count"),
    ("raw_bgc_qc_only", "Raw BGC counts are fragmentation-sensitive QC only", "qc_only"),
    ("max_kcb_support", "Strongest known-cluster support by strain", "support"),
    ("full_depth_inventory", "Full-depth package inventory", "operations"),
]

RAW_BGC_COUNT_POLICY = (
    "Raw BGC counts are fragmentation-sensitive and must not be used as a headline biological ranking. "
    "They may appear only as QC/context panels that explain why Mamey correction is needed."
)


def _require_deps():
    try:
        import pandas as pd  # noqa: F401
        import numpy as np  # noqa: F401
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401
    except Exception as e:  # pragma: no cover - depends on optional runtime deps
        raise RuntimeError(f"mamey-native figures require pandas/numpy/matplotlib: {e}") from e


def _num(series):
    import pandas as pd
    return pd.to_numeric(series, errors="coerce")


def _rg_bucket(x: object) -> str:
    s = str(x).upper()
    if "PROMOTED" in s:
        return "Promoted"
    if "REVIEW" in s:
        return "Review triggered"
    if "NOT_APPLICABLE" in s:
        return "Not applicable"
    if "PASS" in s and "NULL" in s:
        return "Pass-null / no promotion"
    if "PROVISIONAL" in s or "DISPUTED" in s or "REJECTED" in s:
        return "Provisional/disputed"
    if "PASS" in s:
        return "Pass / other"
    return "Other / malformed"


def render_mamey_native_figure_set(workbook: str | Path, outdir: str | Path, *, max_labels: int = 16) -> dict:
    """Render the standard workbook-native figure pack.

    Parameters
    ----------
    workbook:
        Mamey master workbook containing Strain_Registry, DAPR, RG-GMCI, completeness,
        ecology, package, and class-matrix sheets.
    outdir:
        Output directory for PNGs plus figure_manifest.csv and FIGURE_QA.md.
    max_labels:
        Maximum number of strain labels to annotate on dense scatter plots.
    """
    _require_deps()
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    workbook = Path(workbook)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    xl = pd.ExcelFile(workbook)
    # --- v9.7.115 schema adapter: the canonical v1.1 workbook uses CODED sheet names (A2_/C1_/C2_/D1_)
    # and snake_case columns; this engine was written against the pre-v1.1 legacy names. Resolve both
    # through alias maps (legacy names kept as fallbacks) so the native figure set renders from a
    # current workbook without any workbook change. Without this, the engine raises "missing required
    # sheets", or (after sheet bridging) silently drops every drifted column and returns NO_FIGURES.
    _SHEET_ALIASES = {
        "Strain_Registry":           ["Strain_Registry", "A2_Strain_Registry"],
        "DAPR_Antibacterial":        ["DAPR_Antibacterial", "C1_DAPR_Antibacterial"],
        "DAPR_Antifungal":           ["DAPR_Antifungal", "C2_DAPR_Antifungal"],
        "RG-GMCI_All_Strains":       ["RG-GMCI_All_Strains", "D1_RGGMCI_All_Strains"],
        "Master_Completeness_Audit": ["Master_Completeness_Audit", "A4_Completeness_Audit"],
        "BGC_Class_Matrix":          ["BGC_Class_Matrix", "B2_Product_Class_Matrix"],
        "BGC_Master":                ["BGC_Master", "B1_BGC_Master"],
    }
    # coded/snake_case column -> the legacy column name this engine uses internally.
    _COL_ALIASES = {
        "strain": "Strain", "taxonomy": "Taxonomy", "contigs": "Contigs", "n50": "N50",
        "bgc_count": "BGC regions", "package_status": "Package status",
        "overall_completion": "Overall completion", "completion": "Overall completion",
        "ab_score": "AB score", "af_score": "AF score", "score": "Score",
    }

    def _resolve_sheet(logical):
        for name in _SHEET_ALIASES.get(logical, [logical]):
            if name in xl.sheet_names:
                return name
        return None

    def _read(logical):
        name = _resolve_sheet(logical)
        if name is None:
            return None
        df = pd.read_excel(workbook, sheet_name=name)
        # normalize coded columns back to the legacy names, but never clobber a legacy column that
        # already exists (so a workbook carrying both forms keeps the legacy one).
        rename = {coded: legacy for coded, legacy in _COL_ALIASES.items()
                  if coded in df.columns and legacy not in df.columns}
        return df.rename(columns=rename) if rename else df

    required = ["Strain_Registry", "DAPR_Antibacterial", "DAPR_Antifungal", "RG-GMCI_All_Strains"]
    missing = [s for s in required if _resolve_sheet(s) is None]
    if missing:
        raise ValueError(f"workbook missing required sheets for mamey-native figures: {missing}")

    registry = _read("Strain_Registry")
    ab = _read("DAPR_Antibacterial")
    af = _read("DAPR_Antifungal")
    rg = _read("RG-GMCI_All_Strains")
    comp = _read("Master_Completeness_Audit")
    if comp is None: comp = pd.DataFrame()
    eco = pd.read_excel(workbook, sheet_name="Ecology_Readiness_Audit") if "Ecology_Readiness_Audit" in xl.sheet_names else pd.DataFrame()
    pkg = pd.read_excel(workbook, sheet_name="FullDepth_Package_Index") if "FullDepth_Package_Index" in xl.sheet_names else pd.DataFrame()
    classmat = _read("BGC_Class_Matrix")
    if classmat is None: classmat = pd.DataFrame()
    bgc = _read("BGC_Master")
    if bgc is None: bgc = pd.DataFrame()

    ab["Score"] = _num(ab.get("Score"))
    af["Score"] = _num(af.get("Score"))
    ab_best = ab.dropna(subset=["Score"]).sort_values("Score", ascending=False).drop_duplicates("Strain")
    af_best = af.dropna(subset=["Score"]).sort_values("Score", ascending=False).drop_duplicates("Strain")

    p = registry[[c for c in ["Strain", "Taxonomy", "Contigs", "N50", "BGC regions", "Overall completion", "Package status", "AB score", "AF score"] if c in registry.columns]].copy()
    for c in ["AB score", "AF score", "Contigs", "N50", "BGC regions"]:
        if c in p.columns:
            p[c] = _num(p[c])
    p["Best_score"] = p[[c for c in ["AB score", "AF score"] if c in p.columns]].max(axis=1)
    p["Dual_score"] = p[[c for c in ["AB score", "AF score"] if c in p.columns]].mean(axis=1)

    # Project deliverable rule: figures display strains as "Genus species strain <ID>", not bare ID.
    # Build a Strain -> display-label map from the registry Taxonomy column; fall back to the bare
    # strain ID when taxonomy is absent. `_disp` resolves any strain id to its display label.
    def _make_display(strain, taxonomy):
        s = str(strain).strip()
        tax = str(taxonomy).strip() if taxonomy is not None else ""
        if not tax or tax.lower() in ("nan", "not verified", "none", ""):
            return s
        return f"{tax} strain {s}"
    _disp_map = {}
    if "Taxonomy" in p.columns:
        for _, _r in p.iterrows():
            _disp_map[str(_r["Strain"])] = _make_display(_r["Strain"], _r.get("Taxonomy"))
    def _disp(strain):
        return _disp_map.get(str(strain), str(strain))
    if "Strain" in p.columns:
        p["Display"] = p["Strain"].map(_disp)

    manifest: list[dict] = []

    def save(fig, filename: str, title: str, desc: str, data=None):
        # v9.7.374: render to a same-extension .tmp sibling then os.replace() into place, so a
        # process killed mid-savefig (SIGKILL/OOM/power loss) — including on a re-render over an
        # outdir that already carries a valid prior figure of the same name — cannot truncate a
        # previously-valid deliverable to zero/partial bytes.
        target = outdir / filename
        tmp = target.with_name(target.stem + ".tmp" + target.suffix)
        fig.savefig(tmp, dpi=_safe_dpi(fig, 180), bbox_inches="tight")
        plt.close(fig)
        os.replace(tmp, target)
        # v9.7.409: ship a tidy, figure-ready `<stem>_data.csv` beside every PNG (the exact values
        # the figure plots) so each native figure is R/ggplot2-reproducible without re-reading the
        # workbook. Written atomically like the PNG; a sidecar failure never blocks the figure.
        if data is not None:
            import csv as _csv
            _hdr, _rows = data
            _csv_path = target.with_name(target.stem + "_data.csv")
            _csv_tmp = _csv_path.with_name(_csv_path.name + ".tmp")
            try:
                with open(_csv_tmp, "w", newline="", encoding="utf-8") as _fh:
                    _w = _SafeWriter(_fh); _w.writerow(_hdr); _w.writerows(_rows)
                os.replace(_csv_tmp, _csv_path)
            except OSError as _swallowed_exc:  # pragma: no cover - disk/permission only; keep the figure
                _warnings.warn(f"mamey_native_figures.py: non-blocking step skipped ({type(_swallowed_exc).__name__}: {_swallowed_exc})", RuntimeWarning, stacklevel=2)  # v9.7.409: was a silent swallow
        manifest.append({"file": filename, "title": title, "description": desc})

    # 1 AB/AF scatter
    if {"AB score", "AF score"}.issubset(p.columns):
        df = p.dropna(subset=["AB score", "AF score"]).copy()
        if not df.empty:
            fig, ax = plt.subplots(figsize=(10, 8))
            # v9.7.115: guard for an absent Contigs column. df.get("Contigs", 100) returns the scalar
            # 100 (not a Series) when the column is missing, so the chained .fillna() crashed. The
            # native-figure schema adapter now makes more workbooks readable — including ones without
            # Contigs — so this previously-unreachable path is now hit. Fall back to a constant size.
            if "Contigs" in df.columns:
                sizes = df["Contigs"].fillna(100).clip(lower=20)
                sizes = 35 + 240 * (sizes - sizes.min()) / (sizes.max() - sizes.min() + 1e-9)
            else:
                sizes = 80
            ax.scatter(df["AB score"], df["AF score"], s=sizes, alpha=0.65)
            ax.axvline(90, linestyle="--", linewidth=1)
            ax.axhline(90, linestyle="--", linewidth=1)
            for _, r in df.sort_values("Best_score", ascending=False).head(max_labels).iterrows():
                ax.text(r["AB score"] + 0.5, r["AF score"] + 0.5, _disp(r["Strain"]), fontsize=7)
            ax.set_xlim(0, 105); ax.set_ylim(0, 105)
            ax.set_xlabel("Top antibacterial DAPR score")
            ax.set_ylabel("Top antifungal DAPR score")
            ax.set_title("Mamey lead portfolio: antibacterial vs antifungal")
            ax.text(2, 101.5, "Point size ≈ assembly fragmentation burden (contig count).", fontsize=8)
            save(fig, "mamey_native_01_ab_vs_af_portfolio.png", "AB vs AF lead portfolio", "Headline Mamey-native AB/AF DAPR comparison; not based on raw BGC count.",
                 data=(["strain", "ab_score", "af_score"],
                       [[r["Strain"], r["AB score"], r["AF score"]] for _, r in df.iterrows()]))

    # 2 dual track
    df = p.dropna(subset=["AB score", "AF score"]).sort_values(["Dual_score", "Best_score"], ascending=False).head(16) if {"AB score", "AF score"}.issubset(p.columns) else pd.DataFrame()
    if not df.empty:
        fig, ax = plt.subplots(figsize=(11, 8))
        y = np.arange(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            ax.plot([r["AB score"], r["AF score"]], [i, i], linewidth=1)
        ax.scatter(df["AB score"], y, label="Antibacterial")
        ax.scatter(df["AF score"], y, label="Antifungal")
        ax.set_yticks(y); ax.set_yticklabels([_disp(x) for x in df["Strain"]]); ax.invert_yaxis()
        ax.set_xlim(0, 105); ax.set_xlabel("DAPR score"); ax.set_ylabel("Strain")
        ax.set_title("Dual-track lead comparison by strain"); ax.legend(loc="lower right")
        save(fig, "mamey_native_02_dual_track_leads.png", "Dual-track lead comparison", "Dumbbell comparison of antibacterial and antifungal DAPR scores.",
             data=(["strain", "ab_score", "af_score"],
                   [[r["Strain"], r["AB score"], r["AF score"]] for _, r in df.iterrows()]))

    def ranked_bar(df, score_col, title, xlabel, filename):
        if df.empty:
            return
        d = df.head(15).sort_values(score_col)
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh([_disp(x) for x in d["Strain"]], d[score_col])
        for i, v in enumerate(d[score_col]):
            ax.text(v + 0.4, i, f"{int(v)}", va="center", fontsize=8)
        ax.set_xlim(0, 105); ax.set_xlabel(xlabel); ax.set_ylabel("Strain"); ax.set_title(title)
        save(fig, filename, title, f"Ranked DAPR lead figure: {xlabel}.",
             data=(["strain", "score"], [[s, v] for s, v in zip(d["Strain"], d[score_col])]))

    ranked_bar(ab_best, "Score", "Top antibacterial lead strains", "Top antibacterial DAPR score", "mamey_native_03_top_antibacterial.png")
    ranked_bar(af_best, "Score", "Top antifungal lead strains", "Top antifungal DAPR score", "mamey_native_04_top_antifungal.png")

    # RG-GMCI summary
    if "Final state" in rg.columns:
        rg["State_bucket"] = rg["Final state"].map(_rg_bucket)
        d = rg["State_bucket"].value_counts().sort_values()
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(d.index, d.values)
        for i, v in enumerate(d.values): ax.text(v + 0.2, i, str(int(v)), va="center", fontsize=8)
        ax.set_xlabel("Number of records"); ax.set_ylabel("RG-GMCI bucket"); ax.set_title("RG-GMCI state summary")
        save(fig, "mamey_native_08_rggmci_state_summary.png", "RG-GMCI state summary", "How often Mamey promotes, reviews, or passes-null cross-contig rescue states.",
             data=(["rggmci_bucket", "n_records"], [[i, int(v)] for i, v in d.items()]))

    # Raw BGC QC-only
    if {"Contigs", "BGC regions"}.issubset(p.columns):
        df = p.dropna(subset=["Contigs", "BGC regions"])
        if not df.empty:
            fig, ax = plt.subplots(figsize=(10, 7))
            ax.scatter(df["Contigs"], df["BGC regions"], alpha=0.7)
            ax.set_xscale("log")
            ax.set_xlabel("Assembly contig count (log scale)")
            ax.set_ylabel("BGC regions in strain registry")
            ax.set_title("Raw BGC counts are fragmentation-sensitive QC only")
            ax.text(0.02, 0.02, RAW_BGC_COUNT_POLICY, transform=ax.transAxes, fontsize=8)
            save(fig, "mamey_native_13_raw_bgc_qc_only.png", "Raw BGC counts are QC-only", RAW_BGC_COUNT_POLICY,
                 data=(["strain", "contigs", "bgc_regions"],
                       [[r.get("Strain"), r["Contigs"], r["BGC regions"]] for _, r in df.iterrows()]))

    # Optional sheets: simple operational summaries
    if not eco.empty and "Readiness score" in eco.columns:
        eco["Readiness_num"] = _num(eco["Readiness score"])
        d = eco[["Strain", "Readiness_num"]].dropna().sort_values("Readiness_num", ascending=False).head(20).sort_values("Readiness_num")
        if not d.empty:
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.barh([_disp(x) for x in d["Strain"]], d["Readiness_num"])
            ax.set_xlabel("Ecology readiness score"); ax.set_ylabel("Strain"); ax.set_title("Ecology readiness ranking")
            save(fig, "mamey_native_06_ecology_readiness.png", "Ecology readiness ranking", "Context-rich strains for biological interpretation and follow-up.",
                 data=(["strain", "readiness_score"], [[r["Strain"], r["Readiness_num"]] for _, r in d.iterrows()]))

    if not pkg.empty and "Full-depth status" in pkg.columns:
        d = pkg["Full-depth status"].astype(str).value_counts().sort_values()
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(d.index, d.values)
        ax.set_xlabel("Number of packages"); ax.set_ylabel("Full-depth package status"); ax.set_title("Full-depth package inventory")
        save(fig, "mamey_native_15_full_depth_inventory.png", "Full-depth package inventory", "Operational count of recorded full-depth packages.",
             data=(["full_depth_status", "n_packages"], [[i, int(v)] for i, v in d.items()]))

    if not bgc.empty and "KCB/comparison score" in bgc.columns:
        bgc["KCB_num"] = _num(bgc["KCB/comparison score"])
        d = bgc.groupby("Strain")["KCB_num"].max().dropna().reset_index().sort_values("KCB_num", ascending=False).head(15).sort_values("KCB_num")
        if not d.empty:
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.barh([_disp(x) for x in d["Strain"]], d["KCB_num"])
            ax.set_xlabel("Maximum KCB/comparison score in BGC_Master")
            ax.set_ylabel("Strain"); ax.set_title("Strongest known-cluster support by strain")
            save(fig, "mamey_native_14_max_kcb_support.png", "Strongest known-cluster support", "KCB similarity support; not product identity.",
                 data=(["strain", "max_kcb_score"], [[r["Strain"], r["KCB_num"]] for _, r in d.iterrows()]))

    import csv
    _manifest_path = outdir / "figure_manifest.csv"
    _manifest_tmp = _manifest_path.with_name(_manifest_path.name + ".tmp")
    with open(_manifest_tmp, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=["file", "title", "description"])
        w.writeheader(); w.writerows(manifest)
    os.replace(_manifest_tmp, _manifest_path)
    qa = ["# FIGURE_QA — mamey-native", "", f"workbook: {workbook}", f"figures_rendered: {len(manifest)}", "", RAW_BGC_COUNT_POLICY]
    _qa_path = outdir / "FIGURE_QA.md"
    _qa_tmp = _qa_path.with_name(_qa_path.name + ".tmp")
    _qa_tmp.write_text("\n".join(qa) + "\n", encoding="utf-8")
    _qa_tmp.replace(_qa_path)
    if manifest:
        return {"status": "PASS", "figure_count": len(manifest), "outdir": str(outdir), "figures": manifest}
    # v9.7.115: distinguish "sheets resolved but the cohort is unscored" (empty Sapote scaffolds) from
    # a genuine read/drift failure. Without this the engine returns a flat NO_FIGURES for both, which
    # masks the next schema drift behind the benign unscored-cohort case (the same silent-degradation
    # class as the gate vacuous-pass bugs). Here the required sheets DID resolve (we passed the check
    # above), so if every lead/score source is empty the cause is no scoring pass, not unreadable input.
    def _all_scoreless(*frames):
        for fr in frames:
            if fr is not None and not fr.empty and "Score" in fr.columns and fr["Score"].notna().any():
                return False
        return True
    registry_scored = any(c in p.columns for c in ("AB score", "AF score")) and \
        p[[c for c in ("AB score", "AF score") if c in p.columns]].notna().any().any()
    if _all_scoreless(ab, af) and not registry_scored:
        return {"status": "NO_DATA", "figure_count": 0, "outdir": str(outdir), "figures": [],
                "detail": "required sheets resolved, but no DAPR lead scores or registry scores are "
                          "present — the cohort has not been through a Sapote scoring pass yet "
                          "(empty scaffolds). This is not a schema/read failure."}
    return {"status": "NO_FIGURES", "figure_count": 0, "outdir": str(outdir), "figures": []}
